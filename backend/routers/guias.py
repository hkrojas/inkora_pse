from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

import crud
import fiscal_time
from services import emission_queue_service, facturacion_service, fiscal_provider_service, smartpse_response
from services import gre_ubl_service
from services import guide_pdf_service
from services import internal_transfer_service, sale_dispatch_service
from services import beta_feature_flags
import models
import schemas
from api_dependencies import (
    get_current_user,
    get_db_tenant,
    require_admin,
    require_document_emitter,
    require_emission_allowed,
)
from api_utils import raise_internal_server_error
from models.tenants import USAGE_LIMIT_KIND_GUIA
from rate_limit import limiter
from access_control import can_access_all_tenant_resources

router = APIRouter(tags=["guias"])


def _guide_artifact_response(guia, artifact_type: str) -> Response:
    if artifact_type == "xml":
        content = guia.sunat_xml_content
        label = "XML firmado"
    else:
        content = smartpse_response.extract_cdr_xml(guia.provider_response)
        label = "CDR"

    if not content:
        raise HTTPException(404, f"{label} no disponible para esta guía.")

    prefix = "R-" if artifact_type == "cdr" else ""
    filename = f"{prefix}{guia.serie}-{str(guia.correlativo).zfill(6)}.xml"
    return Response(
        content=content.encode("utf-8") if isinstance(content, str) else content,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


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


def _raise_dispatch_error(exc: sale_dispatch_service.DispatchError):
    raise HTTPException(status_code=exc.status_code, detail=exc.detail())


def _ensure_dispatch_owner(dispatch, current_user):
    if not can_access_all_tenant_resources(current_user) and dispatch.created_by_user_id != current_user.id:
        raise HTTPException(404, "Despacho no encontrado.")


def _guide_detail_payload(db: Session, guia, current_user) -> dict:
    payload = schemas.GuiaRemisionResponse.model_validate(guia).model_dump()
    dispatch = guia.dispatch or guia.internal_transfer_dispatch
    reservation_status = None
    if dispatch and dispatch.lines:
        statuses = {line.reservation_status for line in dispatch.lines}
        reservation_status = next(iter(statuses)) if len(statuses) == 1 else "mixed"
    latest_job = db.query(models.DocumentEmissionJob).filter(
        models.DocumentEmissionJob.tenant_id == guia.tenant_id,
        models.DocumentEmissionJob.resource_type == models.EMISSION_JOB_RESOURCE_GUIA,
        models.DocumentEmissionJob.resource_id == guia.id,
    ).order_by(models.DocumentEmissionJob.created_at.desc(), models.DocumentEmissionJob.id.desc()).first()
    payload.update({
        "internal_transfer_id": (
            guia.internal_transfer_dispatch.transfer_id
            if guia.internal_transfer_dispatch_id and guia.internal_transfer_dispatch
            else None
        ),
        "dispatch_status": dispatch.status if dispatch else None,
        "reservation_status": reservation_status,
        "departure_confirmed_at": dispatch.departure_confirmed_at if dispatch else None,
        "external_gre_reference": guia.external_gre_reference,
        "goods_invoice_reference": guia.goods_invoice_reference,
        "actions": sale_dispatch_service.guide_action_availability(db, guia, current_user),
        "emission_job": latest_job,
    })
    return payload


@router.post("/guias-remision/", response_model=schemas.GuiaRemisionResponse)
def crear_guia_remision(
    guia_data: schemas.GuiaRemisionCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    if guia_data.motivo_traslado != "01":
        raise HTTPException(
            status_code=422,
            detail={
                "code": "SPECIALIZED_GUIDE_FLOW_REQUIRED",
                "message": "Use el flujo específico del motivo de traslado seleccionado.",
            },
        )
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
    tipo_documento: str | None = Query(default=None, pattern="^(09|31)$"),
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
        tipo_documento=tipo_documento,
        tab=tab,
        motivo=motivo,
        modalidad=modalidad,
        desde=desde_dt,
        hasta=hasta_dt,
        q=q,
    )


@router.post(
    "/guias-remision/desde-factura",
    response_model=schemas.SaleDispatchResponse,
    status_code=201,
)
def crear_guia_desde_factura(
    payload: schemas.SaleDispatchFromInvoiceCreate,
    response: Response,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
    _emission_check: models.User = Depends(require_emission_allowed),
):
    if not crud.get_cotizacion(db, payload.fiscal_document_id, current_user):
        raise HTTPException(404, "Factura no encontrada para el usuario autenticado.")
    try:
        dispatch, created = sale_dispatch_service.create_from_invoice(
            db, current_user.tenant_id, current_user.id, payload
        )
        if not created:
            response.status_code = 200
        return dispatch
    except sale_dispatch_service.DispatchError as exc:
        db.rollback()
        _raise_dispatch_error(exc)


@router.post(
    "/guias-remision/desde-comprobante",
    response_model=schemas.SaleDispatchResponse,
    status_code=201,
)
def crear_guia_desde_comprobante(
    payload: schemas.SaleDispatchFromDocumentCreate,
    response: Response,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
    _emission_check: models.User = Depends(require_emission_allowed),
):
    if not crud.get_cotizacion(db, payload.fiscal_document_id, current_user):
        raise HTTPException(404, "Comprobante no encontrado para el usuario autenticado.")
    try:
        dispatch, created = sale_dispatch_service.create_from_document(
            db, current_user.tenant_id, current_user.id, payload
        )
        if not created:
            response.status_code = 200
        return dispatch
    except sale_dispatch_service.DispatchError as exc:
        db.rollback()
        _raise_dispatch_error(exc)


@router.get("/despachos/{dispatch_id}", response_model=schemas.SaleDispatchResponse)
def obtener_despacho(
    dispatch_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    dispatch = sale_dispatch_service.get_dispatch(db, current_user.tenant_id, dispatch_id)
    if not dispatch:
        raise HTTPException(404, "Despacho no encontrado.")
    _ensure_dispatch_owner(dispatch, current_user)
    return dispatch


@router.put("/guias-remision/{guia_id}", response_model=schemas.SaleDispatchResponse)
def editar_borrador_guia(
    guia_id: int,
    payload: schemas.SaleDispatchUpdate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
    _emission_check: models.User = Depends(require_emission_allowed),
):
    guia = crud.get_guia_remision(db, guia_id, current_user)
    if not guia or not guia.dispatch_id:
        raise HTTPException(404, "Guía vinculada a despacho no encontrada.")
    try:
        return sale_dispatch_service.update_dispatch(
            db, current_user.tenant_id, guia.dispatch_id, payload, user_id=current_user.id
        )
    except sale_dispatch_service.DispatchError as exc:
        db.rollback()
        _raise_dispatch_error(exc)


@router.post("/guias-remision/{guia_id}/cancelar-borrador", response_model=schemas.SaleDispatchResponse)
def cancelar_borrador_guia(
    guia_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
):
    guia = crud.get_guia_remision(db, guia_id, current_user)
    if not guia or not guia.dispatch_id:
        raise HTTPException(404, "Guía vinculada a despacho no encontrada.")
    try:
        return sale_dispatch_service.cancel_dispatch(db, current_user.tenant_id, guia.dispatch_id)
    except sale_dispatch_service.DispatchError as exc:
        db.rollback()
        _raise_dispatch_error(exc)


@router.post("/guias-remision/{guia_id}/validar")
def validar_guia(
    guia_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
):
    guia = crud.get_guia_remision(db, guia_id, current_user)
    if not guia:
        raise HTTPException(404, "Guía no encontrada.")
    return sale_dispatch_service.validate_guide_for_emission(db, guia)


@router.post("/despachos/{dispatch_id}/confirmar-salida", response_model=schemas.SaleDispatchResponse)
def confirmar_salida_despacho(
    dispatch_id: int,
    payload: schemas.DispatchDepartureConfirm,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
    _emission_check: models.User = Depends(require_emission_allowed),
):
    try:
        dispatch = sale_dispatch_service.get_dispatch(db, current_user.tenant_id, dispatch_id)
        if not dispatch:
            raise HTTPException(404, "Despacho no encontrado.")
        _ensure_dispatch_owner(dispatch, current_user)
        return sale_dispatch_service.confirm_departure(
            db, current_user.tenant_id, dispatch_id, current_user.id, payload.idempotency_key
        )
    except sale_dispatch_service.DispatchError as exc:
        db.rollback()
        _raise_dispatch_error(exc)


@router.post("/guias-remision/transportista", response_model=schemas.GuiaRemisionResponse, status_code=201)
def crear_guia_transportista(
    payload: schemas.TransportGuideCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
    _emission_check: models.User = Depends(require_emission_allowed),
):
    try:
        guide, created = sale_dispatch_service.create_transport_guide(
            db, current_user.tenant_id, current_user.id, payload
        )
        if not created:
            return guide
        return guide
    except sale_dispatch_service.DispatchError as exc:
        db.rollback()
        _raise_dispatch_error(exc)


@router.post(
    "/guias-remision/desde-traslado-interno",
    response_model=schemas.GuiaRemisionResponse,
    status_code=201,
)
def crear_guia_desde_traslado_interno(
    payload: schemas.InternalTransferGuideCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
    _emission_check: models.User = Depends(require_emission_allowed),
):
    beta_feature_flags.require_fiscal_feature_enabled(
        db,
        current_user.tenant_id,
        beta_feature_flags.FISCAL_FEATURE_GUIDES,
        current_user=current_user,
    )
    beta_feature_flags.require_fiscal_feature_enabled(
        db,
        current_user.tenant_id,
        beta_feature_flags.FISCAL_FEATURE_INTERNAL_TRANSFERS,
        current_user=current_user,
    )
    try:
        guide, _ = internal_transfer_service.create_guide(
            db, current_user.tenant_id, current_user.id, payload
        )
        return guide
    except internal_transfer_service.InternalTransferError as exc:
        db.rollback()
        detail = {"code": exc.code, "message": str(exc)}
        if exc.context is not None:
            detail["context"] = exc.context
        raise HTTPException(status_code=exc.status_code, detail=detail)


@router.post("/guias-remision/{guia_id}/gre-transportista-externa", response_model=schemas.GuiaRemisionResponse)
def registrar_gre_transportista_externa(
    guia_id: int,
    payload: schemas.GuideExternalRegistration,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
):
    try:
        return sale_dispatch_service.register_external_carrier_guide(
            db, current_user.tenant_id, current_user.id, guia_id, payload
        )
    except sale_dispatch_service.DispatchError as exc:
        db.rollback()
        _raise_dispatch_error(exc)


@router.post(
    "/guias-remision/{guia_id}/verificar-referencia-externa",
    response_model=schemas.GuideExternalReferenceResponse,
)
def verificar_referencia_gre_externa(
    guia_id: int,
    payload: schemas.ExternalGuideVerification,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_admin),
):
    try:
        return sale_dispatch_service.verify_external_guide_reference(
            db, current_user.tenant_id, current_user.id, guia_id, payload
        )
    except sale_dispatch_service.DispatchError as exc:
        db.rollback()
        _raise_dispatch_error(exc)


@router.get("/guias-remision/{guia_id}", response_model=schemas.GuiaRemisionDetailResponse)
def obtener_guia_remision(
    guia_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """Obtiene el detalle de una guía de remisión por ID."""
    guia = crud.get_guia_remision(db, guia_id, current_user)
    if not guia:
        raise HTTPException(404, "Guia de Remision no encontrada.")
    return _guide_detail_payload(db, guia, current_user)


@router.get("/guias-remision/{guia_id}/xml")
def descargar_xml_guia_remision(
    guia_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    guia = crud.get_guia_remision(db, guia_id, current_user)
    if not guia:
        raise HTTPException(404, "Guía de Remisión no encontrada.")
    return _guide_artifact_response(guia, "xml")


@router.get("/guias-remision/{guia_id}/cdr")
def descargar_cdr_guia_remision(
    guia_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    guia = crud.get_guia_remision(db, guia_id, current_user)
    if not guia:
        raise HTTPException(404, "Guía de Remisión no encontrada.")
    return _guide_artifact_response(guia, "cdr")


@router.get("/guias-remision/{guia_id}/pdf")
def descargar_pdf_guia_remision(
    guia_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    guia = crud.get_guia_remision(db, guia_id, current_user)
    if not guia:
        raise HTTPException(404, "Guía de Remisión no encontrada.")
    content = guide_pdf_service.build_guide_pdf(guia, current_user.tenant)
    filename = f"{guia.serie}-{str(guia.correlativo).zfill(6)}.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


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
@limiter.limit("10/minute")
def emitir_guia_remision_endpoint(
    request: Request,
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
    if guia.estado == "pendiente_smartpse":
        existing_job = crud.get_emission_job_by_key(
            db, current_user.tenant_id, f"emit:guide:{guia.id}"
        )
        if existing_job:
            return JSONResponse(
                status_code=202,
                content=emission_queue_service.build_job_acceptance_payload(
                    existing_job,
                    message="La guía ya está encolada; consulte el resultado sin reenviarla.",
                    resource_id=guia.id,
                    resource_type=models.EMISSION_JOB_RESOURCE_GUIA,
                    internal_order_number=guia.internal_order_number,
                ),
            )
        raise HTTPException(400, "La guía ya fue enviada. Use consultar para conciliar sin reenviar.")
    if guia.estado != "pendiente":
        raise HTTPException(
            400,
            (
                f"Operacion bloqueada: La guia {guia.serie}-{str(guia.correlativo).zfill(6)} "
                f"no se puede emitir desde el estado '{guia.estado}'. "
                "Solo las guías en borrador o pendientes de conciliación pueden procesarse."
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
        if resolved_mode != emission_queue_service.EMISSION_MODE_ASYNC:
            raise HTTPException(
                400,
                "Las guías se emiten exclusivamente por cola. Usa mode=async.",
            )
        if resolved_mode == emission_queue_service.EMISSION_MODE_ASYNC:
            validation = sale_dispatch_service.validate_guide_for_emission(db, guia)
            if not validation["valid"]:
                raise HTTPException(status_code=422, detail=validation)
            # Fiscal data is immutable from this point forward. The worker must
            # send this exact snapshot, never rebuild it from mutable masters.
            guia.fecha_emision = fiscal_time.now_lima_naive()
            frozen_payload = jsonable_encoder(
                facturacion_service._base_payload_gre(guia, current_user)
            )
            guia.frozen_payload = frozen_payload
            guia.frozen_xml = gre_ubl_service.build_despatch_xml(frozen_payload)
            guia.emission_environment = (
                "demo" if facturacion_service._smartpse_demo_mode(current_user) else "production"
            )
            sale_dispatch_service.mark_guide_pending(db, guia)
            db.flush()
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
    except HTTPException:
        raise
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


@router.post("/guias-remision/{guia_id}/consultar")
def consultar_guia_remision_endpoint(
    guia_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
):
    guia = crud.get_guia_remision(db, guia_id, current_user)
    if not guia:
        raise HTTPException(404, "Guía de remisión no encontrada.")
    if guia.estado != "pendiente_smartpse":
        raise HTTPException(409, "Solo se concilian guías con resultado fiscal pendiente.")
    job, _ = emission_queue_service.enqueue_guide_consult_job(db, guia, current_user)
    return JSONResponse(
        status_code=202,
        content=emission_queue_service.build_job_acceptance_payload(
            job,
            message="Consulta de resultado GRE encolada sin reenviar el documento.",
            resource_id=guia.id,
            resource_type=models.EMISSION_JOB_RESOURCE_GUIA,
            internal_order_number=guia.internal_order_number,
        ),
    )
