from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import crud
from services import emission_queue_service, facturacion_service, fiscal_provider_service
from services import beta_feature_flags
import models
import schemas
from api_dependencies import (
    get_current_user,
    get_db_tenant,
    require_document_emitter,
    require_emission_allowed,
)
from api_utils import raise_internal_server_error
from models.tenants import USAGE_LIMIT_KIND_GUIA

router = APIRouter(tags=["guias"])


def _quota_error(exc: "crud.QuotaExceededError") -> HTTPException:
    lim = exc.limit
    return HTTPException(
        status_code=402,
        detail={
            "code": "QUOTA_EXCEEDED",
            "message": (
                f"Cuota de guias excedida: {exc.used}/{lim.max_count} "
                f"({lim.period}). Contacta al superadmin para ampliar el limite."
            ),
            "limit_kind": lim.document_kind,
            "period": lim.period,
            "max": lim.max_count,
            "used": exc.used,
            "scope": "user" if lim.user_id else "tenant",
            "contact": "contacto@inkora.pe",
        },
    )


def _gre_credentials_warning_message() -> str:
    return (
        "El tenant no tiene credenciales SUNAT GRE completas para guias Smart PSE. "
        "Configuralas desde superadmin antes de emitir."
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


@router.get("/guias-remision/", response_model=schemas.GuiaRemisionPageResponse)
def listar_guias_remision(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=100),
    estado: str | None = Query(default=None),
    tab: str | None = Query(default="all", pattern="^(all|pending|smartpse|transit|emitted|cancelled|voided)$"),
    motivo: str | None = Query(default=None),
    modalidad: str | None = Query(default=None),
    desde: str | None = Query(default=None),
    hasta: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    desde_dt = None
    hasta_dt = None
    if desde:
        try:
            desde_dt = datetime.fromisoformat(desde)
        except ValueError:
            raise HTTPException(400, "Fecha 'desde' invalida. Usa formato YYYY-MM-DD.")
    if hasta:
        try:
            hasta_dt = datetime.fromisoformat(hasta).replace(hour=23, minute=59, second=59)
        except ValueError:
            raise HTTPException(400, "Fecha 'hasta' invalida. Usa formato YYYY-MM-DD.")

    return crud.get_guias_remision_page(
        db,
        current_user,
        skip,
        limit,
        estado=estado,
        tab=tab,
        motivo=motivo,
        modalidad=modalidad,
        desde=desde_dt,
        hasta=hasta_dt,
        q=q,
    )


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
    _emission_check: models.User = Depends(require_emission_allowed),
    mode: str | None = Query(default=None, pattern="^(sync|async)$"),
):
    beta_feature_flags.require_fiscal_feature_enabled(
        db,
        current_user.tenant_id,
        beta_feature_flags.FISCAL_FEATURE_GUIDES,
        current_user=current_user,
    )
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
    if not fiscal_provider_service.has_smartpse_credentials(tenant):
        reason = fiscal_provider_service.smartpse_block_reason(tenant)
        raise HTTPException(
            status_code=400,
            detail=(
                "Pre-validacion fallida: El tenant no tiene credenciales Smart PSE configuradas. "
                f"{reason or 'Contacta al administrador para aprovisionar Smart PSE.'}"
            ),
        )

    if not current_user.is_superadmin:
        try:
            crud.check_emission_quota(
                db, current_user.tenant_id, current_user.id, USAGE_LIMIT_KIND_GUIA
            )
        except crud.QuotaExceededError as exc:
            raise _quota_error(exc)

    has_gre_credentials = fiscal_provider_service.has_smartpse_gre_credentials(tenant)
    if not has_gre_credentials:
        reason = fiscal_provider_service.smartpse_gre_block_reason(tenant)
        raise HTTPException(
            status_code=400,
            detail=(
                "Pre-validacion fallida: El tenant no tiene credenciales SUNAT GRE configuradas. "
                f"{reason or _gre_credentials_warning_message()}"
            ),
        )

    try:
        resolved_mode = emission_queue_service.resolve_emission_mode(mode)
        if resolved_mode == emission_queue_service.EMISSION_MODE_ASYNC:
            job, _ = emission_queue_service.enqueue_guide_job(db, guia, current_user)
            return JSONResponse(
                status_code=202,
                content=emission_queue_service.build_job_acceptance_payload(
                    job,
                    message="Guía encolada para emisión fiscal.",
                    resource_id=guia.id,
                    resource_type=models.EMISSION_JOB_RESOURCE_GUIA,
                    internal_order_number=guia.internal_order_number,
                ),
            )

        resultado = facturacion_service.emitir_guia_remision(guia, current_user)
        crud.guardar_respuesta_sunat_gre(
            db,
            guia.id,
            resultado,
            tenant_id=current_user.tenant_id,
        )
        return resultado
    except facturacion_service.FacturacionException as exc:
        crud.guardar_error_sunat_gre(
            db,
            guia.id,
            str(exc),
            tenant_id=current_user.tenant_id,
        )
        detail = str(exc)
        raise HTTPException(400, detail)
    except Exception as exc:
        raise_internal_server_error(
            "emitir_guia_remision_endpoint",
            "Error en el servicio de guias de remision.",
            exc,
        )
