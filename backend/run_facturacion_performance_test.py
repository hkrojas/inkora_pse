"""Prueba de rendimiento para facturacion async con ApisPeru real.

Mide:
- latencia HTTP de encolado
- tiempo total hasta exito/fallo del job
- tiempo promedio de cola y procesamiento
- throughput por minuto

Usa el tenant 7 / RUC 20606751509, que es el unico emisor fiscal confirmado
como operativo en este entorno.
"""

from __future__ import annotations

import json
import math
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import requests

import crud
import models
import schemas
from database import SessionLocal

BASE_URL = os.getenv("LOAD_TEST_BASE_URL", "http://127.0.0.1:8000")
TENANT_ID = int(os.getenv("LOAD_TEST_TENANT_ID", "7"))
EMAIL = os.getenv("LOAD_TEST_EMAIL", "backend.apisperu.verify.20260411_140659@printflow.pe")
PASSWORD = os.getenv("LOAD_TEST_PASSWORD", "test123456")
TIPO_COMPROBANTE = os.getenv("LOAD_TEST_TIPO_COMPROBANTE", "01")
CLIENT_RUC = os.getenv("LOAD_TEST_CLIENT_RUC", "20549781234")
CLIENT_NAME = os.getenv("LOAD_TEST_CLIENT_NAME", "CLIENTE PRUEBA CARGA 20549781234")
LEVELS = [1, 3, 6, 12, 24, 36, 48, 60, 100]
ITEM_PRICE = "118.00"
POLL_SECONDS = 2.0


@dataclass
class BatchContext:
    level: int
    quote_ids: list[int]
    job_ids: list[int]


def _now_iso() -> str:
    return datetime.now().isoformat()


def _pctl(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    pos = max(0, min(len(values) - 1, math.ceil((pct / 100.0) * len(values)) - 1))
    return values[pos]


def _safe_mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def _round_or_none(value: float | None, digits: int = 3) -> float | None:
    return None if value is None else round(value, digits)


def _login() -> str:
    response = requests.post(
        f"{BASE_URL}/token",
        data={"username": EMAIL, "password": PASSWORD, "grant_type": "password"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _ensure_subscription_capacity(required_docs: int) -> dict:
    db = SessionLocal()
    try:
        subscription = db.query(models.Subscription).filter(models.Subscription.tenant_id == TENANT_ID).first()
        if not subscription:
            raise RuntimeError(f"No se encontro subscription para tenant {TENANT_ID}.")
        before = {
            "max_documents": subscription.max_documents,
            "documents_used": subscription.documents_used,
        }
        target = max(subscription.max_documents or 0, (subscription.documents_used or 0) + required_docs + 100)
        subscription.max_documents = target
        db.commit()
        return {"before": before, "test_max_documents": target}
    finally:
        db.close()


def _ensure_client() -> int:
    db = SessionLocal()
    try:
        client = (
            db.query(models.Cliente)
            .filter(
                models.Cliente.tenant_id == TENANT_ID,
                models.Cliente.numero_documento == CLIENT_RUC,
            )
            .first()
        )
        if client:
            return client.id
        client = models.Cliente(
            tenant_id=TENANT_ID,
            tipo_documento="6",
            numero_documento=CLIENT_RUC,
            razon_social=CLIENT_NAME,
            direccion="Direccion de prueba Lima",
        )
        db.add(client)
        db.commit()
        db.refresh(client)
        return client.id
    finally:
        db.close()


def _ensure_quote_pool(total_needed: int, client_id: int) -> list[int]:
    db = SessionLocal()
    try:
        linked_source_ids_subquery = (
            db.query(models.Cotizacion.source_quote_id)
            .filter(
                models.Cotizacion.tenant_id == TENANT_ID,
                models.Cotizacion.document_kind == "fiscal_document",
                models.Cotizacion.source_quote_id.isnot(None),
                models.Cotizacion.estado != "anulada",
            )
        )
        pending_ids = [
            row[0]
            for row in (
                db.query(models.Cotizacion.id)
                .filter(
                    models.Cotizacion.tenant_id == TENANT_ID,
                    models.Cotizacion.estado == "pendiente",
                    models.Cotizacion.document_kind == "quotation",
                    ~models.Cotizacion.id.in_(linked_source_ids_subquery),
                )
                .order_by(models.Cotizacion.id.asc())
                .all()
            )
        ]
        if len(pending_ids) >= total_needed:
            return pending_ids[:total_needed]

        user = (
            db.query(models.User)
            .filter(models.User.tenant_id == TENANT_ID)
            .order_by(models.User.id.asc())
            .first()
        )
        if not user:
            raise RuntimeError(f"No se encontro usuario para tenant {TENANT_ID}.")

        missing = total_needed - len(pending_ids)
        for index in range(missing):
            quote = crud.create_cotizacion(
                db,
                schemas.CotizacionCreate(
                    cliente_id=client_id,
                    moneda="PEN",
                    tipo_comprobante="00",
                    observaciones=f"LOAD-TEST-{index + 1}",
                    items=[
                        schemas.CotizacionItemCreate(
                            descripcion=f"SERVICIO PRUEBA CARGA {index + 1}",
                            cantidad=1,
                            precio_unitario=ITEM_PRICE,
                        )
                    ],
                ),
                user.id,
                TENANT_ID,
            )
            pending_ids.append(quote.id)
        return pending_ids[:total_needed]
    finally:
        db.close()


def _emit_async(token: str, quote_id: int) -> dict:
    start = time.perf_counter()
    try:
        response = requests.post(
            f"{BASE_URL}/cotizaciones/{quote_id}/facturar",
            params={"mode": "async"},
            headers=_headers(token),
            json={"tipo_comprobante": TIPO_COMPROBANTE},
            timeout=60,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        body = response.json() if "application/json" in response.headers.get("content-type", "") else {"raw": response.text[:400]}
        return {
            "quote_id": quote_id,
            "http_status": response.status_code,
            "ok": response.status_code in (200, 202),
            "enqueue_ms": round(elapsed_ms, 3),
            "body": body,
            "job_id": body.get("job_id") if isinstance(body, dict) else None,
        }
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return {
            "quote_id": quote_id,
            "http_status": 0,
            "ok": False,
            "enqueue_ms": round(elapsed_ms, 3),
            "error": str(exc),
            "body": None,
            "job_id": None,
        }


def _read_jobs(job_ids: Iterable[int]) -> dict[int, dict]:
    db = SessionLocal()
    try:
        rows = (
            db.query(models.DocumentEmissionJob)
            .filter(models.DocumentEmissionJob.id.in_(list(job_ids)))
            .all()
        )
        output: dict[int, dict] = {}
        for row in rows:
            output[row.id] = {
                "status": row.status,
                "attempts": row.attempts,
                "created_at": row.created_at,
                "processing_started_at": row.processing_started_at,
                "finished_at": row.finished_at,
                "last_error": row.last_error,
            }
        return output
    finally:
        db.close()


def _wait_for_jobs(job_ids: list[int], max_wait_seconds: int) -> dict[int, dict]:
    deadline = time.time() + max_wait_seconds
    final_states = {"succeeded", "failed"}
    last_snapshot: dict[int, dict] = {}
    while time.time() < deadline:
        snapshot = _read_jobs(job_ids)
        last_snapshot = snapshot
        if snapshot and all(snapshot.get(job_id, {}).get("status") in final_states for job_id in job_ids):
            return snapshot
        time.sleep(POLL_SECONDS)
    return last_snapshot


def _summarize_batch(level: int, request_results: list[dict], jobs_snapshot: dict[int, dict], started_at_wall: float) -> dict:
    enqueue_values = sorted(result["enqueue_ms"] for result in request_results if result.get("enqueue_ms") is not None)
    http_ok = sum(1 for result in request_results if result.get("ok"))
    http_codes: dict[str, int] = {}
    sample_errors: list[str] = []
    for result in request_results:
        code = str(result.get("http_status"))
        http_codes[code] = http_codes.get(code, 0) + 1
        if not result.get("ok"):
            sample_errors.append(json.dumps(result, ensure_ascii=False)[:400])

    completion_values: list[float] = []
    queue_wait_values: list[float] = []
    processing_values: list[float] = []
    final_statuses: dict[str, int] = {}
    job_failures: list[str] = []

    for job_id in sorted(jobs_snapshot):
        item = jobs_snapshot[job_id]
        status = item.get("status") or "missing"
        final_statuses[status] = final_statuses.get(status, 0) + 1
        if status == "failed" and item.get("last_error"):
            job_failures.append(f"job_id={job_id}: {item['last_error']}")

        created_at = item.get("created_at")
        processing_started_at = item.get("processing_started_at")
        finished_at = item.get("finished_at")
        if created_at and finished_at:
            completion_values.append((finished_at - created_at).total_seconds())
        if created_at and processing_started_at:
            queue_wait_values.append((processing_started_at - created_at).total_seconds())
        if processing_started_at and finished_at:
            processing_values.append((finished_at - processing_started_at).total_seconds())

    batch_completion_wall_s = time.time() - started_at_wall
    successful_jobs = sum(1 for item in jobs_snapshot.values() if item.get("status") == "succeeded")
    failed_jobs = sum(1 for item in jobs_snapshot.values() if item.get("status") == "failed")

    throughput_docs_per_min = 0.0
    if batch_completion_wall_s > 0:
        throughput_docs_per_min = successful_jobs / (batch_completion_wall_s / 60.0)

    return {
        "concurrency": level,
        "requests_sent": len(request_results),
        "http_ok": http_ok,
        "http_ok_pct": round((http_ok / len(request_results)) * 100.0, 2) if request_results else 0.0,
        "http_codes": http_codes,
        "enqueue_avg_ms": _round_or_none(_safe_mean(enqueue_values)),
        "enqueue_p50_ms": _round_or_none(_pctl(enqueue_values, 50)),
        "enqueue_p90_ms": _round_or_none(_pctl(enqueue_values, 90)),
        "enqueue_p99_ms": _round_or_none(_pctl(enqueue_values, 99)),
        "enqueue_max_ms": _round_or_none(max(enqueue_values) if enqueue_values else None),
        "batch_completion_wall_s": round(batch_completion_wall_s, 3),
        "job_success": successful_jobs,
        "job_failed": failed_jobs,
        "job_success_pct": round((successful_jobs / len(jobs_snapshot)) * 100.0, 2) if jobs_snapshot else 0.0,
        "job_avg_completion_s": _round_or_none(_safe_mean(completion_values)),
        "job_p50_completion_s": _round_or_none(_pctl(sorted(completion_values), 50)),
        "job_p90_completion_s": _round_or_none(_pctl(sorted(completion_values), 90)),
        "job_avg_queue_wait_s": _round_or_none(_safe_mean(queue_wait_values)),
        "job_avg_processing_s": _round_or_none(_safe_mean(processing_values)),
        "throughput_docs_per_min": round(throughput_docs_per_min, 3),
        "final_statuses": final_statuses,
        "sample_errors": (sample_errors + job_failures)[:10],
        "job_ids": sorted(jobs_snapshot.keys()),
    }


def main() -> int:
    started_at = _now_iso()
    repo_root = Path(__file__).resolve().parent.parent
    output_dir = repo_root / "Pruebas" / f"load_test_facturacion_async_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    total_docs_needed = sum(LEVELS)
    token = _login()
    client_id = _ensure_client()
    subscription_info = _ensure_subscription_capacity(total_docs_needed)
    quote_pool = _ensure_quote_pool(total_docs_needed, client_id)

    manifest: dict = {
        "started_at": started_at,
        "base_url": BASE_URL,
        "tenant_id": TENANT_ID,
        "tenant_user": EMAIL,
        "tenant_ruc": "20606751509",
        "mode": "async",
        "tipo_comprobante": TIPO_COMPROBANTE,
        "levels": LEVELS,
        "client_id": client_id,
        "quotes_precreated": len(quote_pool),
        "subscription_before": subscription_info["before"],
        "subscription_test_max": subscription_info["test_max_documents"],
        "results": [],
    }
    (output_dir / "manifest_progress.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    cursor = 0
    for index, level in enumerate(LEVELS, start=1):
        quote_ids = quote_pool[cursor: cursor + level]
        cursor += level
        if len(quote_ids) != level:
            manifest["stopped_early"] = True
            manifest["stop_reason"] = f"Sin suficientes cotizaciones para nivel {level}"
            break

        started_at_wall = time.time()
        request_results: list[dict] = []
        with ThreadPoolExecutor(max_workers=level) as executor:
            futures = [executor.submit(_emit_async, token, quote_id) for quote_id in quote_ids]
            for future in as_completed(futures):
                request_results.append(future.result())

        job_ids = [result["job_id"] for result in request_results if result.get("job_id")]
        if len(job_ids) != level:
            jobs_snapshot = {}
            if job_ids:
                jobs_snapshot = _wait_for_jobs(job_ids, max_wait_seconds=max(240, len(job_ids) * 8))
            batch_summary = _summarize_batch(level, request_results, jobs_snapshot, started_at_wall)
            batch_summary["warning"] = "No todos los requests devolvieron job_id."
            manifest["results"].append(batch_summary)
            (output_dir / f"batch_{index:03d}.json").write_text(json.dumps(batch_summary, ensure_ascii=False, indent=2), encoding="utf-8")
            (output_dir / "manifest_progress.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            manifest["stopped_early"] = True
            manifest["stop_reason"] = f"Respuesta incompleta en nivel {level}"
            break

        max_wait_seconds = max(240, level * 8)
        jobs_snapshot = _wait_for_jobs(job_ids, max_wait_seconds=max_wait_seconds)
        batch_summary = _summarize_batch(level, request_results, jobs_snapshot, started_at_wall)
        manifest["results"].append(batch_summary)
        (output_dir / f"batch_{index:03d}.json").write_text(json.dumps(batch_summary, ensure_ascii=False, indent=2), encoding="utf-8")
        (output_dir / "manifest_progress.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        if batch_summary["job_success_pct"] < 95.0:
            manifest["stopped_early"] = True
            manifest["stop_reason"] = f"Exito menor a 95% en nivel {level}"
            break

    capacity_level = 0
    for result in manifest["results"]:
        if result["job_success_pct"] >= 95.0:
            capacity_level = result["concurrency"]

    manifest["finished_at"] = _now_iso()
    manifest["duration_seconds"] = round(
        datetime.fromisoformat(manifest["finished_at"]).timestamp() - datetime.fromisoformat(started_at).timestamp(),
        3,
    )
    manifest["capacity_estimate"] = {
        "highest_tested_concurrency": manifest["results"][-1]["concurrency"] if manifest["results"] else 0,
        "highest_concurrency_95pct_success": capacity_level,
    }
    final_path = output_dir / "manifest_final.json"
    final_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    table = [
        {
            "users": result["concurrency"],
            "http_ok_pct": result["http_ok_pct"],
            "job_success_pct": result["job_success_pct"],
            "enqueue_avg_ms": result["enqueue_avg_ms"],
            "job_avg_completion_s": result["job_avg_completion_s"],
            "throughput_docs_per_min": result["throughput_docs_per_min"],
        }
        for result in manifest["results"]
    ]
    print(json.dumps({"output_dir": str(output_dir.resolve()), "capacity_estimate": manifest["capacity_estimate"], "table": table}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
