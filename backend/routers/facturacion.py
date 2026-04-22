from collections.abc import Callable
from typing import Any, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import crud
from services import emission_queue_service, facturacion_service
import models
import schemas
from api_dependencies import (
    get_current_user,
    get_db_tenant,
    require_document_emitter,
    require_emission_allowed,
)
from api_utils import raise_internal_server_error
from services import pdf_storage_service
from services.facturacion_background_service import process_direct_sunat_emission_bg
from models.tenants import (
    USAGE_LIMIT_KIND_BOLETA,
    USAGE_LIMIT_KIND_FACTURA,
    USAGE_LIMIT_KIND_NOTA_CREDITO,
    USAGE_LIMIT_KIND_NOTA_DEBITO,
)

router = APIRouter(tags=["facturacion"])

VALID_TIPOS_COMPROBANTE = {"01", "03", "07", "08"}
DOCUMENT_STATUS_FACTURADA = "facturada"
DOCUMENT_STATUS_ANULADA = "anulada"
DOCUMENT_STATUS_PENDIENTE = "pendiente"
DOCUMENT_KIND_QUOTATION = "quotation"


def _quota_error(exc: "crud.QuotaExceededError") -> HTTPException:
    lim = exc.limit
    return HTTPException(
        status_code=402,
        detail={
            "code": "QUOTA_EXCEEDED",
            "message": (
                f"Cuota de {lim.document_kind} excedida: {exc.used}/{lim.max_count} "
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


def _kind_from_tipo_comprobante(tipo: str) -> str | None:
    if tipo == "01":
        return USAGE_LIMIT_KIND_FACTURA
    if tipo == "03":
        return USAGE_LIMIT_KIND_BOLETA
    if tipo == "07":
        return USAGE_LIMIT_KIND_NOTA_CREDITO
    if tipo == "08":
        return USAGE_LIMIT_KIND_NOTA_DEBITO
    return None


def _raise_not_found(message: str) -> None:
    raise HTTPException(404, message)


def _raise_bad_request(detail: str) -> None:
    raise HTTPException(400, detail)


def _raise_value_error_as_http(exc: ValueError) -> None:
    detail = str(exc)
    normalized = detail.lower().replace("í", "i").replace("Ã­", "i")
    if "limite de documentos" in normalized:
        raise HTTPException(status_code=402, detail=detail)
    raise HTTPException(400, detail)


def _get_quote_or_404(
    db: Session,
    cotizacion_id: int,
    current_user: models.User,
):
    quote = crud.get_cotizacion(db, cotizacion_id, current_user)
    if not quote:
        _raise_not_found("Documento no encontrado")
    return quote


def _ensure_commercial_quote(quote) -> None:
    if quote.document_kind != DOCUMENT_KIND_QUOTATION:
        _raise_bad_request("La ruta de facturacion solo acepta cotizaciones comerciales.")


def _ensure_no_active_linked_fiscal_document(
    db: Session,
    quote,
    tenant_id: int,
) -> None:
    linked_fiscal_document = crud.get_latest_fiscal_document_for_quote(
        db,
        quote.id,
        tenant_id,
    )
    if linked_fiscal_document and linked_fiscal_document.estado != DOCUMENT_STATUS_ANULADA:
        _raise_bad_request(
            (
                f"Operacion bloqueada: La cotizacion {quote.serie}-{quote.correlativo} "
                f"ya tiene un documento fiscal asociado ({linked_fiscal_document.serie}-"
                f"{str(linked_fiscal_document.correlativo).zfill(6)}). "
                "Anule el documento existente antes de emitir uno nuevo."
            ),
        )


def _get_tenant_emission_capabilities(
    db: Session,
    tenant_id: int,
) -> tuple[models.Tenant | None, bool, bool]:
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    has_direct_sunat = bool(tenant and tenant.sunat_usuario_sol and tenant.sunat_cert_url)
    has_apisperu = bool(tenant and tenant.apisperu_token)
    return tenant, has_direct_sunat, has_apisperu


def _ensure_emission_credentials(
    db: Session,
    tenant_id: int,
) -> tuple[models.Tenant | None, bool, bool]:
    tenant, has_direct_sunat, has_apisperu = _get_tenant_emission_capabilities(db, tenant_id)
    if not has_direct_sunat and not has_apisperu:
        raise HTTPException(
            status_code=400,
            detail=(
                "Pre-validacion fallida: El tenant no tiene credenciales de emision configuradas. "
                "Contacta al administrador para configurar el token ApisPeru o las credenciales SUNAT."
            ),
        )
    return tenant, has_direct_sunat, has_apisperu


def _build_async_job_response(
    job,
    *,
    message: str,
    resource_id: int,
    internal_order_number: str | None,
) -> JSONResponse:
    return JSONResponse(
        status_code=202,
        content=emission_queue_service.build_job_acceptance_payload(
            job,
            message=message,
            resource_id=resource_id,
            resource_type=models.EMISSION_JOB_RESOURCE_COTIZACION,
            internal_order_number=internal_order_number,
        ),
    )


def _build_direct_emission_response(
    *,
    source_quote_id: int,
    fiscal_document,
) -> dict[str, Any]:
    return {
        "success": True,
        "source_quote_id": source_quote_id,
        "document_id": fiscal_document.id,
        "internal_order_number": fiscal_document.internal_order_number,
        "message": "Emision directa iniciada. El comprobante se procesara en segundo plano.",
        "sunat_response": {
            "success": True,
            "cdrResponse": {"description": "En cola para envio directo"},
        },
    }


def _attach_document_metadata(
    resultado: dict[str, Any],
    *,
    source_quote_id: int | None = None,
    document_id: int | None = None,
    internal_order_number: str | None = None,
) -> dict[str, Any]:
    if source_quote_id is not None:
        resultado["source_quote_id"] = source_quote_id
    if document_id is not None:
        resultado["document_id"] = document_id
    if internal_order_number is not None:
        resultado["internal_order_number"] = internal_order_number
    return resultado


def _resolve_fiscal_document_or_404(
    db: Session,
    comprobante_id: int,
    tenant_id: int,
    *,
    not_found_message: str,
):
    fiscal_document = crud.resolve_fiscal_document_reference(db, comprobante_id, tenant_id)
    if not fiscal_document:
        _raise_not_found(not_found_message)
    return fiscal_document


def _ensure_note_target_is_facturada(doc_afectado) -> None:
    if doc_afectado.estado not in (DOCUMENT_STATUS_FACTURADA,):
        _raise_bad_request(
            (
                "Operacion bloqueada: Solo se pueden emitir Notas de Credito/Debito "
                "contra comprobantes en estado 'facturada'. "
                f"Estado actual del documento {doc_afectado.serie}-{doc_afectado.correlativo}: "
                f"'{doc_afectado.estado}'."
            ),
        )


def _ensure_document_can_be_voided(comprobante) -> None:
    if comprobante.estado == DOCUMENT_STATUS_FACTURADA:
        return

    estado_msg = {
        DOCUMENT_STATUS_PENDIENTE: (
            "El documento aun no ha sido emitido ante SUNAT. No requiere anulacion."
        ),
        DOCUMENT_STATUS_ANULADA: (
            "El documento ya fue anulado previamente. No se puede procesar dos veces."
        ),
    }
    _raise_bad_request(
        "Operacion bloqueada: "
        f"{estado_msg.get(comprobante.estado, f'Estado invalido: {comprobante.estado}')}"
    )


def _run_facturacion_action(
    operation_name: str,
    error_message: str,
    action: Callable[[], Any],
):
    try:
        return action()
    except facturacion_service.FacturacionException as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise_internal_server_error(operation_name, error_message, exc)


def _validar_pre_emision(quote, tipo_comprobante: str):
    """
    Valida los pre-requisitos antes de enviar a SUNAT.
    Lanza HTTPException 400 con mensaje claro si algo no está listo.
    """
    cliente = quote.cliente

    # 1. Cliente asignado
    if not cliente:
        raise HTTPException(400, "Pre-validacion fallida: La cotizacion no tiene cliente asignado.")

    # 2. Documento de identidad del cliente
    if not cliente.numero_documento or len(cliente.numero_documento.strip()) < 8:
        raise HTTPException(
            400,
            "Pre-validacion fallida: El cliente no tiene numero de documento valido (minimo 8 digitos).",
        )

    # 3. Para facturas (tipo 01): el cliente debe tener RUC (11 digitos, tipo 6)
    if tipo_comprobante == "01":
        if cliente.tipo_documento != "6" or len(cliente.numero_documento.strip()) != 11:
            raise HTTPException(
                400,
                (
                    "Pre-validacion fallida: Las Facturas (tipo 01) requieren que el cliente "
                    "tenga RUC (11 digitos, tipo_documento='6'). "
                    f"Documento actual: {cliente.numero_documento} (tipo {cliente.tipo_documento})."
                ),
            )

    # 4. tipo_comprobante debe ser valido
    if tipo_comprobante not in VALID_TIPOS_COMPROBANTE:
        raise HTTPException(
            400,
            f"Pre-validacion fallida: tipo_comprobante '{tipo_comprobante}' no valido. "
            f"Valores permitidos: {', '.join(sorted(VALID_TIPOS_COMPROBANTE))}.",
        )

    # 5. Monto de venta debe ser > 0
    if not quote.total_venta or quote.total_venta <= 0:
        raise HTTPException(
            400,
            "Pre-validacion fallida: La cotizacion tiene total_venta igual a cero. No se puede facturar.",
        )

    # 6. Debe tener al menos un item
    if not quote.items:
        raise HTTPException(
            400,
            "Pre-validacion fallida: La cotizacion no tiene items. Agregue al menos un producto o servicio.",
        )

    # 7. Cotización no debe estar anulada
    if quote.estado == DOCUMENT_STATUS_ANULADA:
        raise HTTPException(
            400,
            "Pre-validacion fallida: No se puede facturar una cotizacion anulada.",
        )


@router.post("/cotizaciones/{cotizacion_id}/facturar")
def emitir_comprobante(
    cotizacion_id: int,
    payload: schemas.FacturarPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
    _emission_check: models.User = Depends(require_emission_allowed),
    mode: str | None = Query(default=None, pattern="^(sync|async)$"),
):
    quote = _get_quote_or_404(db, cotizacion_id, current_user)
    _ensure_commercial_quote(quote)

    # Pre-validación estructural antes de crear registro o contactar SUNAT
    _validar_pre_emision(quote, payload.tipo_comprobante)

    # Enforcement de cuotas (Fase 2 superadmin) — nunca bloquea cotizaciones
    kind = _kind_from_tipo_comprobante(payload.tipo_comprobante)
    if kind and not current_user.is_superadmin:
        try:
            crud.check_emission_quota(db, current_user.tenant_id, current_user.id, kind)
        except crud.QuotaExceededError as exc:
            raise _quota_error(exc)

    _ensure_no_active_linked_fiscal_document(db, quote, current_user.tenant_id)

    # Verificar que el tenant tiene alguna vía de emisión configurada
    _tenant, has_direct_sunat, _has_apisperu = _ensure_emission_credentials(
        db,
        current_user.tenant_id,
    )

    try:
        fiscal_document = crud.create_fiscal_document_from_quote(
            db,
            quote,
            current_user.id,
            payload.tipo_comprobante,
            payload.serie_override,
        )

        resolved_mode = emission_queue_service.resolve_emission_mode(mode)
        if resolved_mode == emission_queue_service.EMISSION_MODE_ASYNC:
            job, _ = emission_queue_service.enqueue_fiscal_document_job(
                db,
                fiscal_document,
                current_user,
                tipo_comprobante=payload.tipo_comprobante,
            )
            return _build_async_job_response(
                job,
                message="Documento encolado para emisión fiscal.",
                resource_id=fiscal_document.id,
                internal_order_number=fiscal_document.internal_order_number,
            )

        if has_direct_sunat:
            background_tasks.add_task(
                process_direct_sunat_emission_bg,
                fiscal_document.id,
                current_user.tenant_id,
            )
            background_tasks.add_task(
                pdf_storage_service.process_pdf_background,
                fiscal_document.id,
                current_user.tenant_id,
            )

            return _build_direct_emission_response(
                source_quote_id=quote.id,
                fiscal_document=fiscal_document,
            )

        resultado = facturacion_service.emitir_factura(
            fiscal_document,
            db,
            current_user,
            tipo_doc_override=payload.tipo_comprobante,
            tipo_operacion_override=payload.tipo_operacion,
            serie_override=payload.serie_override,
        )
        crud.guardar_respuesta_sunat(
            db,
            fiscal_document.id,
            resultado,
            tenant_id=current_user.tenant_id,
        )

        background_tasks.add_task(
            pdf_storage_service.process_pdf_background,
            fiscal_document.id,
            current_user.tenant_id,
        )
        return _attach_document_metadata(
            resultado,
            source_quote_id=quote.id,
            document_id=fiscal_document.id,
            internal_order_number=fiscal_document.internal_order_number,
        )

    except ValueError as exc:
        _raise_value_error_as_http(exc)

    except facturacion_service.FacturacionException as exc:
        if "fiscal_document" in locals() and fiscal_document:
            crud.guardar_error_sunat(
                db,
                fiscal_document.id,
                str(exc),
                tenant_id=current_user.tenant_id,
            )
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise_internal_server_error(
            "emitir_comprobante",
            "Error en el servicio de facturacion.",
            exc,
        )


@router.post("/notas/emitir")
def emitir_nota(
    nota_data: schemas.NotaCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
    _emission_check: models.User = Depends(require_emission_allowed),
    mode: str | None = Query(default=None, pattern="^(sync|async)$"),
):
    doc_afectado = _resolve_fiscal_document_or_404(
        db,
        nota_data.comprobante_afectado_id,
        current_user.tenant_id,
        not_found_message="Comprobante afectado no encontrado",
    )
    _ensure_note_target_is_facturada(doc_afectado)

    if not current_user.is_superadmin:
        nota_kind = (
            USAGE_LIMIT_KIND_NOTA_CREDITO if nota_data.tipo_nota == "07"
            else USAGE_LIMIT_KIND_NOTA_DEBITO
        )
        try:
            crud.check_emission_quota(db, current_user.tenant_id, current_user.id, nota_kind)
        except crud.QuotaExceededError as exc:
            raise _quota_error(exc)

    try:
        db_nota = crud.crear_nota_credito_debito(
            db=db,
            doc_afectado=doc_afectado,
            usuario_id=current_user.id,
            tipo_nota=nota_data.tipo_nota,
            cod_motivo=nota_data.cod_motivo,
            descripcion_motivo=nota_data.descripcion_motivo,
        )

        resolved_mode = emission_queue_service.resolve_emission_mode(mode)
        if resolved_mode == emission_queue_service.EMISSION_MODE_ASYNC:
            job, _ = emission_queue_service.enqueue_note_job(
                db,
                db_nota,
                current_user,
                tipo_nota=nota_data.tipo_nota,
                cod_motivo=nota_data.cod_motivo,
                descripcion_motivo=nota_data.descripcion_motivo,
            )
            return _build_async_job_response(
                job,
                message="Nota encolada para emisión fiscal.",
                resource_id=db_nota.id,
                internal_order_number=db_nota.internal_order_number,
            )

        resultado = facturacion_service.emitir_nota(
            nota=db_nota,
            doc_afectado=doc_afectado,
            user=current_user,
            cod_motivo=nota_data.cod_motivo,
            descripcion=nota_data.descripcion_motivo,
            tipo_nota=nota_data.tipo_nota,
        )
        crud.guardar_respuesta_sunat(
            db,
            db_nota.id,
            resultado,
            tenant_id=current_user.tenant_id,
        )
        return resultado
    except ValueError as exc:
        _raise_value_error_as_http(exc)
    except facturacion_service.FacturacionException as exc:
        if "db_nota" in locals() and db_nota:
            crud.guardar_error_sunat(
                db,
                db_nota.id,
                str(exc),
                tenant_id=current_user.tenant_id,
            )
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise_internal_server_error(
            "emitir_nota",
            "Error en el servicio de notas electronicas.",
            exc,
        )


@router.post("/bajas/anular")
def anular_documento(
    data: schemas.AnulacionCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
    _emission_check: models.User = Depends(require_emission_allowed),
    mode: str | None = Query(default=None, pattern="^(sync|async)$"),
):
    comprobante = _resolve_fiscal_document_or_404(
        db,
        data.comprobante_id,
        current_user.tenant_id,
        not_found_message="Comprobante no encontrado",
    )
    _ensure_document_can_be_voided(comprobante)

    try:
        resolved_mode = emission_queue_service.resolve_emission_mode(mode)
        if resolved_mode == emission_queue_service.EMISSION_MODE_ASYNC:
            job, _ = emission_queue_service.enqueue_void_document_job(
                db,
                comprobante,
                current_user,
                motivo=data.motivo,
            )
            return _build_async_job_response(
                job,
                message="Anulación encolada para procesamiento fiscal.",
                resource_id=comprobante.id,
                internal_order_number=comprobante.internal_order_number,
            )

        resultado = facturacion_service.anular_comprobante(
            comprobante,
            data.motivo,
            current_user,
        )
        crud.anular_cotizacion(
            db,
            comprobante.id,
            tenant_id=current_user.tenant_id,
        )
        return resultado
    except ValueError as exc:
        _raise_value_error_as_http(exc)
    except facturacion_service.FacturacionException as exc:
        crud.guardar_error_sunat(
            db,
            comprobante.id,
            str(exc),
            tenant_id=current_user.tenant_id,
        )
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise_internal_server_error(
            "anular_documento",
            "Error al anular el documento.",
            exc,
        )


@router.get("/notas/", response_model=List[schemas.CotizacionResponse])
def list_notas(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    from services.document_flow_service import DOCUMENT_KIND_CREDIT_NOTE, DOCUMENT_KIND_DEBIT_NOTE
    from sqlalchemy import desc
    from sqlalchemy.orm import joinedload
    query = (
        db.query(models.Cotizacion)
        .options(
            joinedload(models.Cotizacion.cliente),
            joinedload(models.Cotizacion.usuario),
            joinedload(models.Cotizacion.source_quote),
        )
        .filter(models.Cotizacion.document_kind.in_([DOCUMENT_KIND_CREDIT_NOTE, DOCUMENT_KIND_DEBIT_NOTE]))
        .filter(models.Cotizacion.tenant_id == current_user.tenant_id)
        .order_by(desc(models.Cotizacion.id))
    )
    return query.offset(skip).limit(limit).all()


@router.get("/facturas-emitidas/", response_model=List[schemas.CotizacionResponse])
def list_facturas_emitidas(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    from services.document_flow_service import DOCUMENT_KIND_FISCAL_DOCUMENT
    from sqlalchemy import desc
    from sqlalchemy.orm import joinedload
    query = (
        db.query(models.Cotizacion)
        .options(
            joinedload(models.Cotizacion.cliente),
            joinedload(models.Cotizacion.usuario),
        )
        .filter(models.Cotizacion.document_kind == DOCUMENT_KIND_FISCAL_DOCUMENT)
        .filter(models.Cotizacion.tenant_id == current_user.tenant_id)
        .order_by(desc(models.Cotizacion.id))
    )
    return query.offset(skip).limit(limit).all()


@router.post("/retenciones/emitir")
def emitir_retencion(
    payload: dict,
    current_user: models.User = Depends(require_document_emitter),
):
    return _run_facturacion_action(
        "emitir_retencion",
        "Error al emitir retención.",
        lambda: facturacion_service.emitir_retencion(payload, current_user),
    )


@router.post("/percepciones/emitir")
def emitir_percepcion(
    payload: dict,
    current_user: models.User = Depends(require_document_emitter),
):
    return _run_facturacion_action(
        "emitir_percepcion",
        "Error al emitir percepción.",
        lambda: facturacion_service.emitir_percepcion(payload, current_user),
    )


@router.post("/resumen-diario/enviar")
def enviar_resumen_diario(
    payload: dict,
    current_user: models.User = Depends(require_document_emitter),
):
    return _run_facturacion_action(
        "enviar_resumen_diario",
        "Error al enviar resumen diario.",
        lambda: facturacion_service.emitir_resumen_diario(payload, current_user),
    )


@router.post("/reversiones/enviar")
def enviar_reversion(
    payload: dict,
    current_user: models.User = Depends(require_document_emitter),
):
    return _run_facturacion_action(
        "enviar_reversion",
        "Error al enviar reversión.",
        lambda: facturacion_service.emitir_reversion(payload, current_user),
    )


@router.post("/facturacion/{tipo_archivo}")
def recuperar_archivo_api(
    tipo_archivo: str,
    payload: schemas.DescargaArchivoPayload,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    if tipo_archivo not in ["xml", "pdf", "cdr"]:
        _raise_bad_request("Tipo invalido")

    comprobante = _resolve_fiscal_document_or_404(
        db,
        payload.comprobante_id,
        current_user.tenant_id,
        not_found_message="Comprobante no encontrado",
    )

    try:
        contenido = facturacion_service.descargar_archivo(
            tipo_archivo,
            comprobante,
            current_user,
        )
        media_type = "application/pdf" if tipo_archivo == "pdf" else "application/xml"
        if tipo_archivo == "cdr":
            media_type = "application/zip"
        ext = tipo_archivo if tipo_archivo != "cdr" else "zip"
        filename = f"{comprobante.serie}-{comprobante.correlativo}.{ext}"
        return Response(
            content=contenido,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except facturacion_service.FacturacionException as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise_internal_server_error(
            "recuperar_archivo_api",
            "No se pudo recuperar el archivo solicitado.",
            exc,
        )


@router.get(
    "/emission-jobs/{job_id}",
    response_model=schemas.EmissionJobResponse,
    summary="Consultar estado de un job de emisión",
)
def get_emission_job_endpoint(
    job_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    job = crud.get_emission_job(db, job_id, current_user.tenant_id)
    if not job:
        raise HTTPException(404, "Job de emisión no encontrado.")
    return job


@router.get(
    "/emission-jobs",
    response_model=list[schemas.EmissionJobResponse],
    summary="Listar jobs de emisión del tenant",
)
def list_emission_jobs_endpoint(
    status: str | None = Query(default=None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    return crud.get_emission_jobs(
        db,
        current_user.tenant_id,
        status=status,
        skip=skip,
        limit=limit,
    )
