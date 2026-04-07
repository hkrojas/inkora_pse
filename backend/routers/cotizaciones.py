from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from services import comunicacion_service
import crud
import models
import schemas
from api_dependencies import get_current_user, get_db, get_db_tenant
from config import settings
from services import pdf_storage_service

router = APIRouter(tags=["cotizaciones"])


@router.get("/cotizaciones/", response_model=List[schemas.CotizacionResponse])
def read_cotizaciones(
    skip: int = 0,
    limit: int = 100,
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


@router.get("/public/cotizaciones/{uuid_publico}/pdf")
async def descargar_pdf_publico(
    uuid_publico: str,
    pin: str,
    db: Session = Depends(get_db),
):
    cotizacion = crud.get_cotizacion_by_uuid(db, uuid_publico)
    if not cotizacion:
        raise HTTPException(404, "Enlace no valido o expirado.")
    if (
        not cotizacion.cliente
        or str(cotizacion.cliente.numero_documento).strip() != pin.strip()
    ):
        raise HTTPException(401, "PIN de seguridad incorrecto.")
    if cotizacion.sunat_pdf_url:
        return {"url": cotizacion.sunat_pdf_url}
    raise HTTPException(
        202,
        "El documento se esta generando en la nube, por favor intente en unos segundos.",
    )


@router.get("/cotizaciones/{cotizacion_id}/pdf")
async def descargar_pdf_interno(
    cotizacion_id: int,
    background_tasks: BackgroundTasks,
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
        return {"url": documento_pdf.sunat_pdf_url}

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
    cliente = cotizacion.cliente
    telefono_cliente = getattr(cliente, "telefono", "") if cliente else ""
    email_cliente = getattr(cliente, "email", "") if cliente else ""
    wp_link = comunicacion_service.generar_link_whatsapp(
        cotizacion,
        telefono_cliente,
        url_publica,
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
