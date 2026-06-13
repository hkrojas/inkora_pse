from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from services import comunicacion_service
import crud
import models
import schemas
from api_dependencies import get_current_user, get_db, get_db_tenant
from config import settings
from rate_limit import limiter
from services import pdf_storage_service, storage_service
from services.client_snapshot_service import resolve_document_cliente_snapshot

router = APIRouter(tags=["cotizaciones"])


def _resolve_pdf_download_url(documento_pdf) -> str:
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


@router.get("/cotizaciones/", response_model=List[schemas.CotizacionListResponse])
def read_cotizaciones(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=50),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    return crud.get_cotizaciones(db, current_user, skip, limit)


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
        db_cotizacion = crud.update_cotizacion(
            db,
            cotizacion_id,
            cotizacion,
            current_user,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))

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
    return RedirectResponse(url=_resolve_pdf_download_url(cotizacion), status_code=307)


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

    documento_pdf = cotizacion
    if cotizacion.document_kind == "quotation" and cotizacion.linked_fiscal_document:
        documento_pdf = cotizacion.linked_fiscal_document

    if documento_pdf.sunat_pdf_url:
        resolved_url = _resolve_pdf_download_url(documento_pdf)
        if redirect:
            return RedirectResponse(url=resolved_url, status_code=307)
        return {"url": resolved_url}

    background_tasks.add_task(
        pdf_storage_service.process_pdf_background,
        documento_pdf.id,
        current_user.tenant_id,
    )
    raise HTTPException(202, "Generando PDF en segundo plano... Reintente en un momento.")


@router.get("/cotizaciones/{cotizacion_id}/compartir")
async def compartir_cotizacion(
    cotizacion_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    cotizacion = crud.get_cotizacion(db, cotizacion_id, current_user)
    if not cotizacion:
        raise HTTPException(404, "Documento no encontrado o sin acceso")

    base_url = settings.BACKEND_URL.rstrip("/")
    url_publica = f"{base_url}/public/cotizaciones/{cotizacion.uuid_publico}/pdf"
    cliente_snapshot = resolve_document_cliente_snapshot(cotizacion)
    telefono_cliente = (
        cliente_snapshot.get("whatsapp")
        or cliente_snapshot.get("telefono")
        or ""
    )
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
