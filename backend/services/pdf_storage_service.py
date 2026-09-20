import hashlib
import json

import models
from database import SessionLocal, apply_tenant_context, reset_tenant_context
from fastapi.concurrency import run_in_threadpool
from logging_utils import get_logger
from services import pdf_generator, storage_service
from sqlalchemy.orm import Session


logger = get_logger(__name__)


def _pdf_source_fingerprint(cotizacion: models.Cotizacion) -> str:
    payload = {
        "id": cotizacion.id,
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
    existing_reference = cotizacion.sunat_pdf_url
    if not force and existing_reference and (
        storage_service.is_private_storage_reference(existing_reference)
        or not storage_service.is_remote_url(existing_reference)
    ):
        return existing_reference

    import time

    source_fingerprint = _pdf_source_fingerprint(cotizacion)

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
        models.Cotizacion.id == cotizacion.id,
        models.Cotizacion.tenant_id == cotizacion.tenant_id,
    ).first()
    if not current or _pdf_source_fingerprint(current) != source_fingerprint:
        logger.info(
            "pdf_generation_discarded_stale",
            extra={
                "event": "pdf_generation_discarded_stale",
                "context": f"tenant_id={cotizacion.tenant_id} cotizacion_id={cotizacion.id}",
            },
        )
        return None
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
    finally:
        if tenant_token is not None:
            reset_tenant_context(tenant_token)
        db.close()
