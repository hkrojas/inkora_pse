from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import crud
from services import facturacion_service
import models
import schemas
from api_dependencies import (
    get_current_user,
    get_db_tenant,
    require_document_emitter,
)
from api_utils import raise_internal_server_error

router = APIRouter(tags=["guias"])


def _gre_credentials_warning_message() -> str:
    return (
        "El tenant no tiene client_id/client_secret de SUNAT Nueva GRE configurados. "
        "Si el envio falla con error interno del proveedor, configure esas credenciales "
        "en el portal de ApisPeru para la empresa emisora."
    )


@router.post("/guias-remision/", response_model=schemas.GuiaRemisionResponse)
def crear_guia_remision(
    guia_data: schemas.GuiaRemisionCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    data = guia_data.model_dump()
    items_raw = data.pop("items", [])
    data["items"] = [item for item in items_raw]
    try:
        return crud.create_guia_remision(
            db,
            data,
            current_user.id,
            current_user.tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise_internal_server_error(
            "crear_guia_remision",
            "No se pudo crear la guia de remision.",
            exc,
        )


@router.get("/guias-remision/", response_model=List[schemas.GuiaRemisionResponse])
def listar_guias_remision(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    return crud.get_guias_remision(db, current_user, skip, limit)


@router.get("/guias-remision/{guia_id}", response_model=schemas.GuiaRemisionResponse)
def obtener_guia_remision(
    guia_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """Obtiene el detalle de una guía de remisión por ID."""
    guia = crud.get_guia_remision(db, guia_id, current_user)
    if not guia:
        raise HTTPException(404, "Guia de Remision no encontrada.")
    return guia


@router.get(
    "/guias-remision/{guia_id}/etiqueta",
    response_model=schemas.EtiquetaGuiaResponse,
    summary="Datos de etiqueta de despacho",
)
def obtener_etiqueta_guia(
    guia_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """
    Devuelve los datos estructurados para imprimir la etiqueta de despacho de una guía.
    El frontend o un servicio de impresión puede consumir este endpoint para generar
    la etiqueta en el formato que necesite (ZPL, PDF, HTML).
    """
    guia = crud.get_guia_remision(db, guia_id, current_user)
    if not guia:
        raise HTTPException(404, "Guia de Remision no encontrada.")

    tenant = current_user.tenant

    # Obtener datos del destinatario desde la cotización relacionada
    destinatario_nombre = None
    destinatario_documento = None
    destinatario_direccion = None

    if guia.cotizacion_id:
        cotizacion = crud.get_cotizacion(db, guia.cotizacion_id, current_user)
        if cotizacion and cotizacion.cliente:
            cliente = cotizacion.cliente
            destinatario_nombre = cliente.razon_social
            destinatario_documento = cliente.numero_documento
            # Preferir dirección de entrega del cliente, luego la fiscal
            destinatario_direccion = (
                getattr(cliente, "direccion_entrega", None)
                or cliente.direccion
            )

    numero_guia = None
    if guia.serie and guia.correlativo is not None:
        numero_guia = f"{guia.serie}-{str(guia.correlativo).zfill(6)}"

    return schemas.EtiquetaGuiaResponse(
        guia_id=guia.id,
        numero_guia=numero_guia,
        fecha_traslado=guia.fecha_traslado,
        remitente_nombre=tenant.business_name if tenant else "",
        remitente_ruc=tenant.business_ruc if tenant else "",
        remitente_direccion=tenant.business_address if tenant else None,
        destinatario_nombre=destinatario_nombre,
        destinatario_documento=destinatario_documento,
        destinatario_direccion=destinatario_direccion,
        partida_direccion=guia.partida_direccion,
        llegada_direccion=guia.llegada_direccion,
        peso_bruto_total=guia.peso_bruto_total,
        numero_bultos=guia.numero_bultos,
        motivo_traslado=guia.motivo_traslado,
        items=[
            schemas.GuiaRemisionItemResponse(
                id=item.id,
                descripcion=item.descripcion,
                cantidad=item.cantidad,
                unidad_medida=item.unidad_medida,
                codigo_producto=item.codigo_producto,
                peso_item=item.peso_item,
            )
            for item in guia.items
        ],
    )


@router.post("/guias-remision/{guia_id}/emitir")
def emitir_guia_remision_endpoint(
    guia_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
):
    guia = crud.get_guia_remision(db, guia_id, current_user)
    if not guia:
        raise HTTPException(404, "Guia de Remision no encontrada.")
    if guia.estado in ("emitida", "anulada"):
        raise HTTPException(
            400,
            (
                f"Operacion bloqueada: La guia {guia.serie}-{str(guia.correlativo).zfill(6)} "
                f"ya fue procesada (estado actual: '{guia.estado}'). "
                "No se puede emitir una guia duplicada ante SUNAT."
            ),
        )

    tenant = current_user.tenant
    if not tenant or not tenant.apisperu_token:
        raise HTTPException(
            status_code=400,
            detail=(
                "Pre-validacion fallida: El tenant no tiene token ApisPeru configurado. "
                "Contacta al administrador para configurar el token de empresa."
            ),
        )

    has_gre_credentials = bool(
        tenant and tenant.sunat_gre_client_id and tenant.sunat_gre_client_secret
    )

    try:
        resultado = facturacion_service.emitir_guia_remision(guia, current_user)
        crud.guardar_respuesta_sunat_gre(
            db,
            guia.id,
            resultado,
            tenant_id=current_user.tenant_id,
        )
        if not has_gre_credentials:
            resultado["gre_credentials_warning"] = _gre_credentials_warning_message()
        return resultado
    except facturacion_service.FacturacionException as exc:
        crud.guardar_error_sunat_gre(
            db,
            guia.id,
            str(exc),
            tenant_id=current_user.tenant_id,
        )
        detail = str(exc)
        if not has_gre_credentials:
            detail = f"{detail} {_gre_credentials_warning_message()}"
        raise HTTPException(400, detail)
    except Exception as exc:
        raise_internal_server_error(
            "emitir_guia_remision_endpoint",
            "Error en el servicio de guias de remision.",
            exc,
        )
