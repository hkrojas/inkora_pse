import hashlib
import json

import models
from database import SessionLocal, apply_tenant_context, reset_tenant_context
from fastapi.concurrency import run_in_threadpool
from logging_utils import get_logger
from services import fiscal_evidence_service, pdf_generator, storage_service
from sqlalchemy.orm import Session


logger = get_logger(__name__)


class FiscalPdfNotReady(ValueError):
    pass


def has_legacy_accepted_pdf(document):
    response = getattr(document, "provider_response", None) or {}
    evidence = response.get("inkora_evidence", {}) if isinstance(response, dict) else {}
    return (getattr(document, "estado", None) == "facturada"
            and not getattr(document, "sunat_error", None)
            and getattr(document, "provider_verification_status", None) in {None, "verified"}
            and bool(getattr(document, "sunat_cdr_content", None) or getattr(document, "sunat_cdr_url", None))
            and not evidence.get("signed_xml_sha256")
            and storage_service.is_private_storage_reference(getattr(document, "sunat_pdf_url", None)))


def ensure_fiscal_pdf_ready(document, *, allow_existing=False):
    if allow_existing and has_legacy_accepted_pdf(document):
        return
    if getattr(document, "document_kind", "quotation") != "quotation" and not fiscal_evidence_service.has_deliverable_xml(document):
        raise FiscalPdfNotReady("El PDF estara disponible cuando se reciba y verifique el XML firmado.")


def _pdf_source_fingerprint(cotizacion: models.Cotizacion) -> str:
    payload = {
        "id": cotizacion.id,
        "fiscal_xml_sha256": hashlib.sha256((getattr(cotizacion, "sunat_xml_content", None) or "").encode()).hexdigest(),
        "fiscal_qr": getattr(cotizacion, "sunat_qr_payload", None),
        "fiscal_hash": getattr(cotizacion, "sunat_hash", None),
        "cliente_id": cotizacion.cliente_id,
        "cliente_snapshot": getattr(cotizacion, "cliente_snapshot", None),
        "fecha_emision": cotizacion.fecha_emision,
        "fecha_vencimiento": cotizacion.fecha_vencimiento,
        "moneda": cotizacion.moneda,
        "observaciones": cotizacion.observaciones,
        "condicion_pago": cotizacion.condicion_pago,
        "quote_payment_methods": getattr(cotizacion, "quote_payment_methods", None),
        "quote_selected_wallet_id": getattr(cotizacion, "quote_selected_wallet_id", None),
        "totals": [
            cotizacion.total_gravada,
            cotizacion.total_exonerada,
            cotizacion.total_inafecta,
            cotizacion.total_igv,
            cotizacion.total_venta,
        ],
        "items": [
            {
                "id": item.id,
                "producto_id": item.producto_id,
                "codigo": item.codigo_producto,
                "descripcion": item.descripcion,
                "cantidad": item.cantidad,
                "precio_unitario": item.precio_unitario,
                "unidad": item.unidad_medida,
                "afectacion": item.tipo_afectacion_igv,
            }
            for item in cotizacion.items or []
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


async def generate_and_upload_pdf(db: Session, cotizacion: models.Cotizacion, *, force: bool = False):
    """
    Genera el PDF interno, lo sube a Supabase Storage privado y persiste la referencia.
    """
    document_id, tenant_id = cotizacion.id, cotizacion.tenant_id
    # Preserve issued historical representations (including their payment data).
    # Newly signed documents always use the XML/QR fingerprint below.
    if not force and has_legacy_accepted_pdf(cotizacion):
        return cotizacion.sunat_pdf_url
    ensure_fiscal_pdf_ready(cotizacion)
    source_fingerprint = _pdf_source_fingerprint(cotizacion)
    existing_reference = cotizacion.sunat_pdf_url
    if not force and existing_reference and (
        storage_service.is_private_storage_reference(existing_reference)
        or not storage_service.is_remote_url(existing_reference)
    ) and (getattr(cotizacion, "document_kind", "quotation") == "quotation"
           or f"-{source_fingerprint[:12]}.pdf" in existing_reference):
        return existing_reference

    import time

    document_kind = getattr(cotizacion, "document_kind", "quotation")
    started_at = time.perf_counter()
    if document_kind == "quotation":
        pdf_buffer = await run_in_threadpool(
            pdf_generator.generar_pdf_cotizacion,
            cotizacion,
            cotizacion.tenant,
        )
    else:
        pdf_buffer = await run_in_threadpool(
            pdf_generator.create_comprobante_pdf,
            cotizacion,
            cotizacion.tenant,
        )

    pdf_bytes = pdf_buffer.getvalue()
    generation_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info(
        "pdf_generation_completed",
        extra={
            "event": "pdf_generation_completed",
            "duration_ms": generation_ms,
            "context": f"tenant_id={cotizacion.tenant_id} cotizacion_id={cotizacion.id} bytes={len(pdf_bytes)}",
        },
    )

    folder = f"cotizaciones/tenant_{cotizacion.tenant_id}"
    filename = (
        f"{cotizacion.serie}-{cotizacion.correlativo}-"
        f"{cotizacion.uuid_publico[:8]}-{source_fingerprint[:12]}.pdf"
    )

    private_reference = await run_in_threadpool(
        storage_service.upload_to_storage,
        pdf_bytes,
        folder,
        filename,
        "application/pdf",
    )

    db.expire_all()
    current = db.query(models.Cotizacion).filter(
        models.Cotizacion.id == document_id,
        models.Cotizacion.tenant_id == tenant_id,
    ).populate_existing().with_for_update().first()
    if not current or _pdf_source_fingerprint(current) != source_fingerprint:
        logger.info(
            "pdf_generation_discarded_stale",
            extra={
                "event": "pdf_generation_discarded_stale",
                "context": f"tenant_id={tenant_id} cotizacion_id={document_id}",
            },
        )
        return None
    # A rejection/void may arrive while the renderer or Storage is running.
    # The row lock covers only this final check and reference persistence.
    ensure_fiscal_pdf_ready(current)
    current.sunat_pdf_url = private_reference
    db.commit()

    return private_reference


async def process_pdf_background(cotizacion_id: int, tenant_id: int):
    """
    Tarea para BackgroundTasks: genera y sube el PDF sin bloquear la respuesta principal.
    """
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
            await generate_and_upload_pdf(db, cotizacion)
    except FiscalPdfNotReady:
        db.rollback()
        logger.info("pdf_generation_no_longer_deliverable", extra={
            "event": "pdf_generation_no_longer_deliverable",
            "context": f"tenant_id={tenant_id} cotizacion_id={cotizacion_id}",
        })
    finally:
        if tenant_token is not None:
            reset_tenant_context(tenant_token)
        db.close()
