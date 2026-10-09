"""Reproducible synthetic read benchmark. Only accepts a dedicated LOCAL database.

Usage: python scripts/benchmark_read_egress.py --url postgresql://.../inkora_read_egress
Creates/removes its own random schema; never accesses public business tables.
Payload bytes estimate decoded SQL result values, NOT Supabase billable egress.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time
from types import ModuleType, SimpleNamespace
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import conftest  # isolated test settings, no real credentials
import crud
import models
import schemas
from database import Base
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


def old_module(path, revision):
    source = subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT).decode("utf-8")
    module = ModuleType("read_benchmark_" + Path(path).stem)
    exec(compile(source, path, "exec"), module.__dict__)
    return module


def measure(db, call):
    durations = []
    captured = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            captured.append((statement, parameters))
    result = None
    for _ in range(3):
        db.expunge_all()
        captured.clear()
        event.listen(db.bind, "before_cursor_execute", capture)
        try:
            start = time.perf_counter()
            result = call()
            durations.append((time.perf_counter() - start) * 1000)
        finally:
            event.remove(db.bind, "before_cursor_execute", capture)
    result_bytes = 0
    server_ms = 0.0
    for statement, parameters in captured:
        rows = db.connection().exec_driver_sql(statement, parameters).fetchall()
        result_bytes += sum(len(str(value).encode("utf-8")) for row in rows for value in row if value is not None)
        explain = db.connection().exec_driver_sql("EXPLAIN (ANALYZE, FORMAT JSON) " + statement, parameters).scalar()
        server_ms += explain[0]["Execution Time"]
    return result, {"selects": len(captured), "result_value_bytes": result_bytes,
                    "median_application_ms": round(statistics.median(durations), 3),
                    "server_execution_ms": round(server_ms, 3)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--baseline", default="0298d26ec08ccaec4bbabfacab788b8c1aed7b2e")
    args = parser.parse_args()
    url = make_url(args.url)
    if not url.drivername.startswith("postgresql") or url.host not in {"localhost", "127.0.0.1", "::1"} or not (url.database or "").startswith("inkora_read_"):
        raise SystemExit("Requires a local disposable inkora_read_* database")
    schema = "read_benchmark_" + uuid.uuid4().hex
    admin = create_engine(url)
    with admin.begin() as conn:
        conn.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        Base.metadata.create_all(engine)
        with Session(engine, expire_on_commit=False) as db:
            tenant = conftest.make_tenant(db, "BENCH")
            user = conftest.make_user(db, tenant, email="read-benchmark@test.local")
            client = conftest.make_cliente(db, tenant, "BENCH", numero_documento="20123456781")
            scope = SimpleNamespace(id=user.id, tenant_id=tenant.id, rol=user.rol, is_superadmin=False)
            for i in range(100):
                common = dict(tenant_id=tenant.id, usuario_id=user.id, cliente_id=client.id,
                    fecha_emision=datetime(2026, 9, 10) + timedelta(seconds=i), total_gravada=100, total_igv=18, total_venta=118,
                    monto_pagado=0, saldo_pendiente=118, sunat_xml_content="x" * 50000,
                    sunat_cdr_content="c" * 50000, sunat_qr_svg="q" * 50000,
                    provider_response={"payload": "p" * 50000})
                quote = models.Cotizacion(**common, serie="COT", correlativo=i+1, document_kind="quotation", tipo_comprobante="00", estado="pendiente")
                db.add(quote)
                db.flush()
                fiscal = models.Cotizacion(**common, serie="F001", correlativo=i+1, source_quote_id=quote.id,
                    document_kind="fiscal_document", tipo_comprobante="01", estado="facturada")
                db.add(fiscal)
                db.add(models.GuiaRemision(tenant_id=tenant.id, usuario_id=user.id, cliente_id=client.id,
                    cotizacion_id=quote.id, serie="T001", correlativo=i+1, estado="emitida",
                    fecha_emision=datetime(2026, 9, 10), fecha_traslado=datetime(2026, 9, 10),
                    motivo_traslado="01", modalidad_traslado="02", peso_bruto_total=1,
                    partida_ubigeo="150101", partida_direccion="Origen", llegada_ubigeo="150101", llegada_direccion="Destino",
                    sunat_xml_content="x" * 50000, provider_response={"payload": "p" * 50000}))
            db.commit()
            old_guides = old_module("backend/crud/guias.py", args.baseline)
            old_quotes = old_module("backend/crud/_cotizaciones_quotes.py", args.baseline)
            old_shared = old_module("backend/crud/_cotizaciones_shared.py", args.baseline)
            old_quotes._build_quote_listing_query = old_shared._build_quote_listing_query
            old_reports = old_module("backend/crud/reportes.py", args.baseline)
            old_router = old_module("backend/routers/reportes.py", args.baseline)
            from routers import reportes
            from crud.guias import get_guias_remision_page
            from test_reportes import _download_report_workbook
            original_docs = crud.get_reporte_mensual
            original_amounts = reportes._monthly_collection_amounts
            def report(legacy):
                crud.get_reporte_mensual = old_reports.get_reporte_mensual if legacy else original_docs
                reportes._monthly_collection_amounts = old_router._monthly_collection_amounts if legacy else original_amounts
                try:
                    book = _download_report_workbook(db, scope, anio=2026, mes=9)
                    return list(book.active.values)
                finally:
                    crud.get_reporte_mensual = original_docs
                    reportes._monthly_collection_amounts = original_amounts
            comparisons = {}
            for size in (15, 100):
                for name, before, after, contract in [
                    ("guides", old_guides.get_guias_remision_page, get_guias_remision_page, schemas.GuiaRemisionPageResponse),
                    ("quotes", old_quotes.get_cotizaciones_page, crud.get_cotizaciones_page, schemas.CotizacionPageResponse),
                ]:
                    old_value, old_metrics = measure(db, lambda: contract.model_validate(before(db, scope, limit=size)).model_dump(mode="json"))
                    new_value, new_metrics = measure(db, lambda: contract.model_validate(after(db, scope, limit=size)).model_dump(mode="json"))
                    assert old_value == new_value, name
                    comparisons[f"{name}_{size}"] = {"before": old_metrics, "after": new_metrics}
            old_value, old_metrics = measure(db, lambda: report(True))
            new_value, new_metrics = measure(db, lambda: report(False))
            assert old_value == new_value, [(a, b) for a, b in zip(old_value, new_value) if a != b][:2]
            comparisons["monthly_excel_100"] = {"before": old_metrics, "after": new_metrics}
            print(json.dumps({"baseline": args.baseline, "synthetic_rows": {"quotes": 100, "fiscal": 100, "guides": 100},
                "note": "Decoded result-value bytes; not protocol bytes or billable egress. Local warm measurements, three repetitions.",
                "comparisons": comparisons}, indent=2))
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        admin.dispose()


if __name__ == "__main__":
    main()
