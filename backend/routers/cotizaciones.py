from datetime import date, datetime, time
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from services import comunicacion_service
import crud
import models
import schemas
from api_dependencies import get_current_user, get_db, get_db_tenant
from config import settings
from rate_limit import limiter
from services import document_download_service, pdf_storage_service, storage_service
from services.client_snapshot_service import resolve_document_cliente_snapshot

router = APIRouter(tags=["cotizaciones"])


def _resolve_pdf_download_url(documento_pdf) -> str:
    _ensure_pdf_ready(documento_pdf)
    try:
        resolved_url = storage_service.resolve_storage_download_url(
            getattr(documento_pdf, "sunat_pdf_url", None)
        )
    except Exception as exc:
        raise HTTPException(500, f"No se pudo preparar la descarga del PDF: {exc}")

    if not resolved_url:
        raise HTTPException(
            202,
            "El documento se esta generando en la nube, por favor intente en unos segundos.",
        )
    return resolved_url


def _ensure_pdf_ready(document):
    try:
        pdf_storage_service.ensure_fiscal_pdf_ready(document, allow_existing=True)
    except pdf_storage_service.FiscalPdfNotReady as exc:
        raise HTTPException(409, str(exc)) from exc


def _resolve_pdf_document(db, source):
    linked_id = getattr(source, "linked_fiscal_document_id", None)
    if getattr(source, "document_kind", "quotation") != "quotation" or not linked_id:
        return source
    document = db.query(models.Cotizacion).filter(
        models.Cotizacion.id == linked_id,
        models.Cotizacion.tenant_id == source.tenant_id,
        models.Cotizacion.source_quote_id == source.id,
        models.Cotizacion.document_kind == "fiscal_document",
    ).first()
    if not document:
        raise HTTPException(404, "Comprobante vinculado no encontrado.")
    return document


def _refresh_pdf_delivery(db, document):
    if getattr(document, "document_kind", "quotation") == "quotation":
        return document
    current = db.query(models.Cotizacion).filter(
        models.Cotizacion.id == document.id,
        models.Cotizacion.tenant_id == document.tenant_id,
    ).populate_existing().first()
    if not current:
        raise HTTPException(404, "Comprobante no encontrado.")
    _ensure_pdf_ready(current)
    return current


async def _prepare_pdf(db, document):
    try:
        return await pdf_storage_service.generate_and_upload_pdf(db, document)
    except pdf_storage_service.FiscalPdfNotReady as exc:
        raise HTTPException(409, str(exc)) from exc


def _pdf_delivery_version(document):
    fingerprint = (pdf_storage_service._pdf_source_fingerprint(document)
                   if getattr(document, "document_kind", "quotation") != "quotation" else None)
    return document.sunat_pdf_url, fingerprint


def _check_pdf_delivery(db, document, version):
    current = _refresh_pdf_delivery(db, document)
    if _pdf_delivery_version(current) != version:
        raise HTTPException(202, "El PDF cambio durante la descarga. Reintente.")
    return current


@router.get("/cotizaciones/", response_model=List[schemas.CotizacionListResponse])
def read_cotizaciones(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=50),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    return crud.get_cotizaciones(db, current_user, skip, limit)


@router.get("/cotizaciones/page", response_model=schemas.CotizacionPageResponse)
def read_cotizaciones_page(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=50),
    q: Optional[str] = Query(default=None, max_length=120),
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    return crud.get_cotizaciones_page(
        db,
        current_user,
        skip=skip,
        limit=limit,
        q=q,
        date_from=datetime.combine(desde, time.min) if desde else None,
        date_to=datetime.combine(hasta, time.max) if hasta else None,
    )


@router.post("/cotizaciones/", response_model=schemas.CotizacionResponse)
def create_cotizacion(
    cotizacion: schemas.CotizacionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    db_cotizacion = crud.create_cotizacion(
        db,
        cotizacion,
        current_user.id,
        current_user.tenant_id,
    )
    background_tasks.add_task(
        pdf_storage_service.process_pdf_background,
        db_cotizacion.id,
        current_user.tenant_id,
    )
    return db_cotizacion


@router.put("/cotizaciones/{cotizacion_id}", response_model=schemas.CotizacionResponse)
def update_cotizacion(
    cotizacion_id: int,
    cotizacion: schemas.CotizacionUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    try:
        db_cotizacion = crud.update_cotizacion(db, cotizacion_id, cotizacion, current_user)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    if not db_cotizacion:
        raise HTTPException(404, "Cotizacion no encontrada")
    background_tasks.add_task(
        pdf_storage_service.process_pdf_background,
        db_cotizacion.id,
        db_cotizacion.tenant_id,
    )
    return db_cotizacion


@router.post(
    "/cotizaciones/{cotizacion_id}/duplicar",
    response_model=schemas.CotizacionResponse,
    status_code=201,
)
def duplicar_cotizacion(
    cotizacion_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    try:
        db_cotizacion = crud.duplicate_cotizacion(db, cotizacion_id, current_user)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    if not db_cotizacion:
        raise HTTPException(404, "Cotizacion no encontrada")

    background_tasks.add_task(
        pdf_storage_service.process_pdf_background,
        db_cotizacion.id,
        current_user.tenant_id,
    )
    return db_cotizacion


@router.get("/cotizaciones/{cotizacion_id}", response_model=schemas.CotizacionResponse)
def read_cotizacion(
    cotizacion_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    result = crud.get_cotizacion(db, cotizacion_id, current_user)
    if not result:
        raise HTTPException(404)
    return result


@router.delete("/cotizaciones/{cotizacion_id}")
def delete_cotizacion(
    cotizacion_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    try:
        result = crud.delete_cotizacion(db, cotizacion_id, current_user)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    if result is None:
        raise HTTPException(404, "Cotizacion no encontrada")
    return {"msg": "Eliminado"}


@router.get("/public/cotizaciones/{uuid_publico}/pdf")
@limiter.limit("30/minute")
async def descargar_pdf_publico(
    request: Request,
    uuid_publico: str,
    pin: Optional[str] = None,  # Parámetro legacy; ignorado. El UUID v4 es el secreto.
    db: Session = Depends(get_db),
):
    """
    Acceso público a PDF de cotización/comprobante.

    Seguridad: el UUID v4 actúa como token de acceso (122 bits de entropía).
    El parámetro `pin` se acepta por compatibilidad con clientes existentes pero
    no se valida — el DNI del cliente es información pública y no aporta seguridad real.
    """
    cotizacion = crud.get_cotizacion_by_uuid(db, uuid_publico)
    if not cotizacion:
        raise HTTPException(404, "Enlace no valido o expirado.")
    _ensure_pdf_ready(cotizacion)
    if getattr(cotizacion, "document_kind", "quotation") != "quotation":
        reference = await _prepare_pdf(db, cotizacion)
        if not reference:
            raise HTTPException(202, "El comprobante cambio durante la generacion del PDF. Reintente.")
        cotizacion = _refresh_pdf_delivery(db, cotizacion)
    version = _pdf_delivery_version(cotizacion)
    url = _resolve_pdf_download_url(cotizacion)
    _check_pdf_delivery(db, cotizacion, version)
    return RedirectResponse(url=url, status_code=307)


@router.get("/cotizaciones/{cotizacion_id}/pdf")
@limiter.limit("30/minute")
async def descargar_pdf_interno(
    request: Request,
    cotizacion_id: int,
    background_tasks: BackgroundTasks,
    redirect: bool = Query(default=False),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    cotizacion = crud.get_cotizacion(db, cotizacion_id, current_user)
    if not cotizacion:
        raise HTTPException(404)

    documento_pdf = _resolve_pdf_document(db, cotizacion)

    _ensure_pdf_ready(documento_pdf)
    if not documento_pdf.sunat_pdf_url or documento_pdf.document_kind != "quotation":
        reference = await _prepare_pdf(db, documento_pdf)
        if not reference:
            raise HTTPException(202, "La cotizacion cambio mientras se generaba el PDF. Reintente.")
        db.refresh(documento_pdf)
    documento_pdf = _refresh_pdf_delivery(db, documento_pdf)
    version = _pdf_delivery_version(documento_pdf)
    resolved_url = _resolve_pdf_download_url(documento_pdf)
    _check_pdf_delivery(db, documento_pdf, version)
    if redirect:
        return RedirectResponse(url=resolved_url, status_code=307)
    return {"url": resolved_url}


@router.get("/cotizaciones/{cotizacion_id}/pdf/download")
@limiter.limit("30/minute")
async def descargar_pdf_interno_como_archivo(
    request: Request,
    cotizacion_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    cotizacion = crud.get_cotizacion(db, cotizacion_id, current_user)
    if not cotizacion:
        raise HTTPException(404, "Cotizacion no encontrada")
    documento_pdf = _resolve_pdf_document(db, cotizacion)

    reference = getattr(documento_pdf, "sunat_pdf_url", None)
    _ensure_pdf_ready(documento_pdf)
    if documento_pdf.document_kind != "quotation" or not storage_service.is_private_storage_reference(reference):
        reference = await _prepare_pdf(db, documento_pdf)
        if not reference:
            raise HTTPException(202, "La cotizacion cambio mientras se generaba el PDF. Reintente.")
    version = _pdf_delivery_version(documento_pdf)
    if version[0] != reference:
        raise HTTPException(202, "El PDF cambio durante la descarga. Reintente.")
    try:
        content = await run_in_threadpool(storage_service.download_private_storage_reference, reference)
    except Exception as exc:
        raise HTTPException(502, "No se pudo recuperar el PDF almacenado.") from exc

    documento_pdf = _check_pdf_delivery(db, documento_pdf, version)

    filename = document_download_service.build_document_download_filename(documento_pdf)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/cotizaciones/{cotizacion_id}/compartir")
async def compartir_cotizacion(
    cotizacion_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    cotizacion = crud.get_cotizacion(db, cotizacion_id, current_user)
    if not cotizacion:
        raise HTTPException(404, "Documento no encontrado o sin acceso")

    # Share the same fiscal document as the internal PDF download. Existing
    # public UUIDs for quotations continue to identify those quotations.
    cotizacion = _resolve_pdf_document(db, cotizacion)
    _ensure_pdf_ready(cotizacion)

    base_url = settings.BACKEND_URL.rstrip("/")
    url_publica = f"{base_url}/public/cotizaciones/{cotizacion.uuid_publico}/pdf"
    cliente_snapshot = resolve_document_cliente_snapshot(cotizacion)
    telefono_cliente = cliente_snapshot.get("whatsapp") or cliente_snapshot.get("telefono") or ""
    email_cliente = cliente_snapshot.get("email") or ""
    wp_link = comunicacion_service.generar_link_whatsapp(
        cotizacion,
        telefono_cliente,
        url_publica,
        current_user.tenant,
    )
    mailto_link = comunicacion_service.generar_link_mailto(
        cotizacion,
        email_cliente,
        url_publica,
        current_user.tenant,
    )
    return {
        "url_compartir": url_publica,
        "whatsapp_link": wp_link,
        "mailto_link": mailto_link,
    }
