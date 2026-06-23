from __future__ import annotations

import zipfile
from io import BytesIO

import models
from database import SessionLocal, apply_tenant_context, reset_tenant_context
from fastapi.concurrency import run_in_threadpool
from logging_utils import get_logger
from services import storage_service


logger = get_logger(__name__)


def package_cdr_xml_as_zip(cdr_xml: str, *, filename: str) -> bytes:
    xml_content = (cdr_xml or "").strip()
    if not xml_content:
        raise ValueError("No hay contenido CDR para empaquetar.")
    normalized_filename = (filename or "cdr.xml").strip().lstrip("/") or "cdr.xml"
    if not normalized_filename.lower().endswith(".xml"):
        normalized_filename = f"{normalized_filename}.xml"

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(normalized_filename, xml_content.encode("utf-8"))
    return buffer.getvalue()


def _document_correlativo(cotizacion: models.Cotizacion) -> str:
    raw = getattr(cotizacion, "correlativo", None)
    if raw is None:
        return "00000000"
    text = str(raw).strip()
    return text if not text.isdigit() else text.zfill(8)


def _cdr_basename(cotizacion: models.Cotizacion) -> str:
    serie = str(getattr(cotizacion, "serie", None) or "DOC").strip()
    return f"R-{serie}-{_document_correlativo(cotizacion)}"


async def persist_cdr_artifact(db, cotizacion: models.Cotizacion, cdr_xml: str | None) -> str | None:
    if not cdr_xml:
        return None

    existing = getattr(cotizacion, "sunat_cdr_url", None)
    if storage_service.is_private_storage_reference(existing):
        cotizacion.cdr_artifact_status = "ready"
        db.commit()
        return existing

    basename = _cdr_basename(cotizacion)
    file_bytes = package_cdr_xml_as_zip(cdr_xml, filename=f"{basename}.xml")
    folder = f"cotizaciones/tenant_{cotizacion.tenant_id}/cdr"
    reference = await run_in_threadpool(
        storage_service.upload_to_storage,
        file_bytes,
        folder,
        f"{basename}.zip",
        "application/zip",
    )
    cotizacion.sunat_cdr_url = reference
    cotizacion.cdr_artifact_status = "ready"
    db.commit()
    db.refresh(cotizacion)
    return reference


async def process_cdr_background(cotizacion_id: int, tenant_id: int, cdr_xml: str | None) -> None:
    if not cdr_xml:
        return

    db = SessionLocal()
    tenant_token = None
    try:
        tenant_token = apply_tenant_context(db, tenant_id)
        cotizacion = (
            db.query(models.Cotizacion)
            .filter(
                models.Cotizacion.id == cotizacion_id,
                models.Cotizacion.tenant_id == tenant_id,
            )
            .first()
        )
        if cotizacion:
            await persist_cdr_artifact(db, cotizacion, cdr_xml)
    except Exception as exc:
        try:
            failed = (
                db.query(models.Cotizacion)
                .filter(
                    models.Cotizacion.id == cotizacion_id,
                    models.Cotizacion.tenant_id == tenant_id,
                )
                .first()
            )
            if failed:
                failed.cdr_artifact_status = "failed"
                db.commit()
        except Exception:
            db.rollback()
        logger.warning(
            "cdr_artifact_persist_failed",
            extra={
                "event": "cdr_artifact_persist_failed",
                "context": f"tenant_id={tenant_id} cotizacion_id={cotizacion_id} error={exc}",
            },
        )
    finally:
        if tenant_token is not None:
            reset_tenant_context(tenant_token)
        db.close()
