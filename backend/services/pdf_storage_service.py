import models
from database import SessionLocal, apply_tenant_context, reset_tenant_context
from fastapi.concurrency import run_in_threadpool
from services import pdf_generator, storage_service
from sqlalchemy.orm import Session


async def generate_and_upload_pdf(db: Session, cotizacion: models.Cotizacion):
    """
    Genera el PDF interno, lo sube a Supabase Storage privado y persiste la referencia.
    """
    existing_reference = cotizacion.sunat_pdf_url
    if existing_reference and (
        storage_service.is_private_storage_reference(existing_reference)
        or not storage_service.is_remote_url(existing_reference)
    ):
        return existing_reference

    document_kind = getattr(cotizacion, "document_kind", "quotation")
    if document_kind == "quotation":
        pdf_buffer = await run_in_threadpool(pdf_generator.generar_pdf_cotizacion, cotizacion, cotizacion.tenant)
    else:
        pdf_buffer = await run_in_threadpool(pdf_generator.create_comprobante_pdf, cotizacion, cotizacion.tenant)

    pdf_bytes = pdf_buffer.getvalue()
    folder = f"cotizaciones/tenant_{cotizacion.tenant_id}"
    filename = f"{cotizacion.serie}-{cotizacion.correlativo}-{cotizacion.uuid_publico[:8]}.pdf"

    private_reference = await storage_service.upload_to_storage(
        file_bytes=pdf_bytes,
        folder_name=folder,
        filename=filename,
        content_type="application/pdf",
    )

    cotizacion.sunat_pdf_url = private_reference
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
