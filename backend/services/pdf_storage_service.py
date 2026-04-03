import pdf_generator
from services import storage_service
from sqlalchemy.orm import Session
import models
from database import SessionLocal

async def generate_and_upload_pdf(db: Session, cotizacion: models.Cotizacion):
    """
    Genera el PDF interno, lo sube a Supabase Storage y actualiza la URL en BD.
    Sincrónico/Awaitable (Usado por endpoints o tareas de background).
    """
    if cotizacion.sunat_pdf_url and "supabase.co" in cotizacion.sunat_pdf_url:
        return cotizacion.sunat_pdf_url
    
    # 1. Generar el binario del PDF
    pdf_buffer = pdf_generator.generar_pdf_cotizacion(cotizacion, cotizacion.tenant)
    pdf_bytes = pdf_buffer.getvalue()
    
    # 2. Subir a Supabase Storage
    # Formato: facturas/{serie}-{correlativo}-{uuid}.pdf (Fase 4 - Unicidad)
    folder = f"cotizaciones/tenant_{cotizacion.tenant_id}"
    filename = f"{cotizacion.serie}-{cotizacion.correlativo}-{cotizacion.uuid_publico[:8]}.pdf"
    
    public_url = await storage_service.upload_to_storage(
        file_bytes=pdf_bytes,
        folder_name=folder,
        filename=filename,
        content_type="application/pdf"
    )
    
    # 3. Persistir la URL en la base de datos
    cotizacion.sunat_pdf_url = public_url
    db.commit()
    
    return public_url

async def process_pdf_background(cotizacion_id: int):
    """
    Tarea para BackgroundTasks: Genera y sube el PDF sin bloquear la respuesta principal.
    """
    db = SessionLocal()
    try:
        cotizacion = db.query(models.Cotizacion).filter(models.Cotizacion.id == cotizacion_id).first()
        if cotizacion:
            await generate_and_upload_pdf(db, cotizacion)
    finally:
        db.close()
