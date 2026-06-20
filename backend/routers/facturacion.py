from collections.abc import Callable
from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session, joinedload

import crud
from config import settings
from fiscal_catalogs import (
    normalize_internal_product_code,
    normalize_sunat_unit_code,
    normalize_tax_affectation_code,
)
from services import emission_queue_service, facturacion_service
from services import calculations
from services import fiscal_provider_service
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
from rate_limit import limiter
from services import fiscal_artifact_service, pdf_storage_service
from services.facturacion_background_service import process_direct_sunat_emission_bg
from models.tenants import (
    USAGE_LIMIT_KIND_BOLETA,
    USAGE_LIMIT_KIND_FACTURA,
    USAGE_LIMIT_KIND_NOTA_CREDITO,
    USAGE_LIMIT_KIND_NOTA_DEBITO,
)
from services.fiscal_balance_service import ensure_credit_note_within_available_amount

router = APIRouter(tags=["facturacion"])

VALID_TIPOS_COMPROBANTE = {"01", "03", "07", "08"}
DOCUMENT_STATUS_FACTURADA = "facturada"
DOCUMENT_STATUS_ANULADA = "anulada"
DOCUMENT_STATUS_PENDIENTE = "pendiente"
DOCUMENT_KIND_QUOTATION = "quotation"
FISCAL_PAGE_STATUSES = ("sent", "pending", "rejected")


def _parse_date_bounds(desde: str | None, hasta: str | None) -> tuple[datetime | None, datetime | None]:
    desde_dt = None
    hasta_dt = None
    if desde:
        try:
            desde_dt = datetime.fromisoformat(desde if len(desde) > 10 else f"{desde}T00:00:00")
        except ValueError:
            _raise_bad_request("Fecha 'desde' invalida. Usa formato YYYY-MM-DD.")
    if hasta:
        try:
            hasta_dt = datetime.fromisoformat(hasta if len(hasta) > 10 else f"{hasta}T23:59:59")
        except ValueError:
            _raise_bad_request("Fecha 'hasta' invalida. Usa formato YYYY-MM-DD.")
    return desde_dt, hasta_dt


def _fiscal_doc_tab_filter(tab: str | None):
    normalized = (tab or "all").strip().lower()
    accepted_artifact = or_(
        models.Cotizacion.sunat_cdr_url.isnot(None),
        models.Cotizacion.sunat_cdr_content.isnot(None),
    )
    if normalized == "draft":
        return models.Cotizacion.estado == "borrador"
    if normalized == "emitted":
        return accepted_artifact & models.Cotizacion.sunat_error.is_(None)
    if normalized == "pending":
        return (
            models.Cotizacion.estado.notin_([
                "borrador",
                DOCUMENT_STATUS_ANULADA,
            ])
            & ~accepted_artifact
            & models.Cotizacion.sunat_error.is_(None)
        )
    if normalized == "rejected":
        return models.Cotizacion.sunat_error.isnot(None)
    if normalized == "voided":
        return models.Cotizacion.estado == DOCUMENT_STATUS_ANULADA
    return None


def _fiscal_doc_counts(base_query) -> dict[str, int]:
    def count_for(tab: str) -> int:
        query = base_query.with_entities(func.count(models.Cotizacion.id))
        filter_expr = _fiscal_doc_tab_filter(tab)
        if filter_expr is not None:
            query = query.filter(filter_expr)
        return query.scalar() or 0

    return {
        "all": count_for("all"),
        "draft": count_for("draft"),
        "emitted": count_for("emitted"),
        "pending": count_for("pending"),
        "rejected": count_for("rejected"),
        "voided": count_for("voided"),
    }


def _status_counts(base_query, model) -> dict[str, int]:
    counts = {"all": base_query.with_entities(func.count(model.id)).scalar() or 0}
    for status in FISCAL_PAGE_STATUSES:
        counts[status] = (
            base_query.with_entities(func.count(model.id))
            .filter(model.status == status)
            .scalar()
            or 0
        )
    return counts


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
    has_smartpse = fiscal_provider_service.has_smartpse_credentials(tenant)
    return tenant, False, has_smartpse


def _ensure_emission_credentials(
    db: Session,
    tenant_id: int,
) -> tuple[models.Tenant | None, bool, bool]:
    tenant, has_direct_sunat, has_smartpse = _get_tenant_emission_capabilities(db, tenant_id)
    if not has_smartpse:
        reason = fiscal_provider_service.smartpse_block_reason(tenant)
        detail = (
            "Pre-validacion fallida: El tenant no tiene credenciales Smart PSE configuradas. "
            f"{reason or 'Contacta al administrador para aprovisionar Smart PSE.'}"
        )
        raise HTTPException(
            status_code=400,
            detail=detail,
        )
    return tenant, has_direct_sunat, has_smartpse


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
    if doc_afectado.sunat_error or not (doc_afectado.sunat_xml_url or doc_afectado.sunat_xml_content):
        _raise_bad_request(
            (
                "Operacion bloqueada: Solo se pueden emitir Notas de Credito/Debito "
                "contra comprobantes aceptados por SUNAT."
            )
        )


def _ensure_document_can_be_voided(comprobante) -> None:
    if comprobante.estado == DOCUMENT_STATUS_FACTURADA:
        sunat_error = getattr(comprobante, "sunat_error", None)
        xml_url = getattr(comprobante, "sunat_xml_url", None)
        xml_content = getattr(comprobante, "sunat_xml_content", None)
        has_sunat_error = isinstance(sunat_error, str) and bool(sunat_error.strip())
        has_sunat_artifact = (
            (isinstance(xml_url, str) and bool(xml_url.strip()))
            or (isinstance(xml_content, str) and bool(xml_content.strip()))
        )
        if not has_sunat_error and has_sunat_artifact:
            return
        _raise_bad_request(
            (
                "Operacion bloqueada: Solo se pueden dar de baja comprobantes "
                "aceptados por SUNAT."
            )
        )

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


def _raise_legacy_fiscal_endpoint_gone(replacement_path: str) -> None:
    raise HTTPException(
        status_code=410,
        detail=(
            "Endpoint fiscal legacy desactivado para launch. "
            f"Usa la ruta persistente {replacement_path}."
        ),
    )


def _validate_issue_date_not_future(quote) -> None:
    fecha_emision = getattr(quote, "fecha_emision", None)
    if not fecha_emision:
        return

    today = (
        datetime.now(fecha_emision.tzinfo).date()
        if fecha_emision.tzinfo is not None
        else datetime.now().date()
    )
    if fecha_emision.date() > today:
        raise HTTPException(
            400,
            "Pre-validacion fallida: La fecha de emision no puede ser futura.",
        )


def _validate_sunat_line_item(item, index: int) -> None:
    descripcion = str(getattr(item, "descripcion", "") or "").strip()
    if not descripcion:
        raise HTTPException(
            400,
            f"Pre-validacion fallida: El item {index} no tiene descripcion.",
        )
    if len(descripcion) > 500:
        raise HTTPException(
            400,
            f"Pre-validacion fallida: La descripcion del item {index} excede 500 caracteres.",
        )

    if calculations.to_decimal(getattr(item, "cantidad", 0)) <= 0:
        raise HTTPException(
            400,
            f"Pre-validacion fallida: La cantidad del item {index} debe ser mayor a cero.",
        )
    if calculations.to_decimal(getattr(item, "precio_unitario", 0)) <= 0:
        raise HTTPException(
            400,
            f"Pre-validacion fallida: El precio del item {index} debe ser mayor a cero.",
        )

    unidad = getattr(item, "unidad_medida", None)
    afectacion = getattr(item, "tipo_afectacion_igv", None)
    codigo = getattr(item, "codigo_producto", None)
    try:
        normalize_sunat_unit_code(unidad if isinstance(unidad, str) else None)
        normalize_tax_affectation_code(afectacion if isinstance(afectacion, str) else None)
        normalize_internal_product_code(codigo if isinstance(codigo, str) else None)
    except ValueError as exc:
        raise HTTPException(
            400,
            f"Pre-validacion fallida en item {index}: {exc}",
        ) from exc


def _parse_credit_due_date(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _validate_credit_payment_schedule(quote) -> None:
    condicion_pago = str(getattr(quote, "condicion_pago", "") or "").strip().lower()
    if not condicion_pago or condicion_pago == "contado":
        return

    total_venta = calculations.redondear(getattr(quote, "total_venta", 0))
    fecha_emision = getattr(quote, "fecha_emision", None)
    cuotas_raw = getattr(quote, "cuotas_pago", None) or []
    cuotas = []

    for index, cuota in enumerate(cuotas_raw, start=1):
        if not isinstance(cuota, dict):
            raise HTTPException(
                400,
                f"Pre-validacion fallida: La cuota {index} no tiene formato valido.",
            )
        fecha_pago = _parse_credit_due_date(cuota.get("fecha_pago") or cuota.get("fechaPago"))
        monto = calculations.redondear(cuota.get("monto", 0))
        if not fecha_pago:
            raise HTTPException(
                400,
                f"Pre-validacion fallida: La cuota {index} no tiene fecha de vencimiento valida.",
            )
        if monto <= 0:
            raise HTTPException(
                400,
                f"Pre-validacion fallida: El monto de la cuota {index} debe ser mayor a cero.",
            )
        cuotas.append({"fecha_pago": fecha_pago, "monto": monto})

    if not cuotas:
        fecha_vencimiento = getattr(quote, "fecha_vencimiento", None)
        if not fecha_vencimiento:
            raise HTTPException(
                400,
                "Pre-validacion fallida: Las facturas al credito requieren al menos una cuota.",
            )
        cuotas.append({"fecha_pago": fecha_vencimiento, "monto": total_venta})

    if len(cuotas) > 999:
        raise HTTPException(
            400,
            "Pre-validacion fallida: SUNAT admite como maximo 999 cuotas.",
        )

    if fecha_emision:
        emission_date = fecha_emision.date()
        for index, cuota in enumerate(cuotas, start=1):
            if cuota["fecha_pago"].date() <= emission_date:
                raise HTTPException(
                    400,
                    f"Pre-validacion fallida: La cuota {index} debe vencer despues de la fecha de emision.",
                )

    total_cuotas = calculations.redondear(
        sum((cuota["monto"] for cuota in cuotas), calculations.Decimal("0.00"))
    )
    if total_cuotas != total_venta:
        raise HTTPException(
            400,
            (
                "Pre-validacion fallida: La suma de cuotas "
                f"({total_cuotas}) debe coincidir con el total del comprobante ({total_venta})."
            ),
        )


def _require_beta_fiscal_feature(
    db: Session,
    current_user: models.User,
    feature_key: str,
) -> None:
    beta_feature_flags.require_fiscal_feature_enabled(
        db,
        current_user.tenant_id,
        feature_key,
        current_user=current_user,
    )


def _validate_launch_operation(tipo_operacion: str | None) -> None:
    normalized = str(tipo_operacion or "0101").strip() or "0101"
    if normalized != "0101":
        raise HTTPException(
            400,
            (
                "Pre-validacion fallida: Por ahora solo se emite venta interna "
                "(tipoOperacion 0101). Exportacion y detraccion manual requieren "
                "campos fiscales adicionales."
            ),
        )


def _validate_serie_override(tipo_comprobante: str, serie_override: str | None) -> None:
    if not serie_override:
        return

    serie = serie_override.strip().upper()
    if len(serie) != 4 or not serie.isalnum():
        raise HTTPException(
            400,
            "Pre-validacion fallida: La serie debe tener 4 caracteres alfanumericos.",
        )

    if serie.isdigit():
        return
    if tipo_comprobante == "01" and not serie.startswith("F"):
        raise HTTPException(
            400,
            "Pre-validacion fallida: Las facturas deben usar serie Fxxx o serie numerica de contingencia.",
        )
    if tipo_comprobante == "03" and not serie.startswith("B"):
        raise HTTPException(
            400,
            "Pre-validacion fallida: Las boletas deben usar serie Bxxx o serie numerica de contingencia.",
        )


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

    # 7-8. Fecha y lineas fiscales listas para APISPeru/SUNAT
    _validate_issue_date_not_future(quote)
    _validate_credit_payment_schedule(quote)

    for index, item in enumerate(quote.items, start=1):
        _validate_sunat_line_item(item, index)

    if quote.estado == DOCUMENT_STATUS_ANULADA:
        raise HTTPException(
            400,
            "Pre-validacion fallida: No se puede facturar una cotizacion anulada.",
        )


@router.post("/cotizaciones/{cotizacion_id}/facturar")
@limiter.limit("10/minute")
def emitir_comprobante(
    request: Request,
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
    _validate_launch_operation(payload.tipo_operacion)
    _validate_serie_override(payload.tipo_comprobante, payload.serie_override)

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
        if resultado.get("cdr_xml"):
            background_tasks.add_task(
                fiscal_artifact_service.process_cdr_background,
                fiscal_document.id,
                current_user.tenant_id,
                resultado.get("cdr_xml"),
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
@limiter.limit("10/minute")
def emitir_nota(
    request: Request,
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
    try:
        note_feature = beta_feature_flags.feature_for_note_type(nota_data.tipo_nota)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    _require_beta_fiscal_feature(db, current_user, note_feature)

    if not current_user.is_superadmin:
        nota_kind = (
            USAGE_LIMIT_KIND_NOTA_CREDITO if nota_data.tipo_nota == "credito"
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
            items=nota_data.items,
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

        ensure_credit_note_within_available_amount(
            db,
            current_user.tenant_id,
            db_nota.id,
        )
        resultado = facturacion_service.emitir_nota(
            nota=db_nota,
            doc_afectado=doc_afectado,
            user=current_user,
            cod_motivo=nota_data.cod_motivo,
            descripcion=nota_data.descripcion_motivo,
            tipo_nota=nota_data.tipo_nota,
        )
        updated_note = crud.guardar_respuesta_sunat(
            db,
            db_nota.id,
            resultado,
            tenant_id=current_user.tenant_id,
        )
        if resultado.get("cdr_xml"):
            background_tasks.add_task(
                fiscal_artifact_service.process_cdr_background,
                db_nota.id,
                current_user.tenant_id,
                resultado.get("cdr_xml"),
            )
        if (
            resultado.get("success")
            and updated_note
            and updated_note.estado != DOCUMENT_STATUS_FACTURADA
        ):
            raise HTTPException(
                status_code=409,
                detail=updated_note.sunat_error
                or "La nota no pudo marcarse como aceptada.",
            )
        return resultado
    except HTTPException:
        raise
    except ValueError as exc:
        if "db_nota" in locals() and db_nota:
            crud.guardar_error_sunat(
                db,
                db_nota.id,
                str(exc),
                tenant_id=current_user.tenant_id,
            )
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
@limiter.limit("10/minute")
def anular_documento(
    request: Request,
    data: schemas.AnulacionCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
    _emission_check: models.User = Depends(require_emission_allowed),
    mode: str | None = Query(default=None, pattern="^(sync|async)$"),
):
    _require_beta_fiscal_feature(
        db,
        current_user,
        beta_feature_flags.FISCAL_FEATURE_VOIDING,
    )
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


@router.get("/notas/", response_model=List[schemas.FiscalNoteListResponse])
def list_notas(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=100),
    tipo_nota: str | None = Query(default=None, pattern="^(07|08|credito|debito|nc|nd)$"),
    estado: str | None = Query(default=None),
    desde: str | None = Query(default=None),
    hasta: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    from services.document_flow_service import DOCUMENT_KIND_CREDIT_NOTE, DOCUMENT_KIND_DEBIT_NOTE
    from sqlalchemy import desc, or_
    from sqlalchemy.orm import joinedload

    query = (
        db.query(models.Cotizacion)
        .options(
            joinedload(models.Cotizacion.cliente),
            joinedload(models.Cotizacion.source_quote),
            joinedload(models.Cotizacion.nota_referencia),
        )
        .filter(models.Cotizacion.document_kind.in_([DOCUMENT_KIND_CREDIT_NOTE, DOCUMENT_KIND_DEBIT_NOTE]))
        .filter(models.Cotizacion.tenant_id == current_user.tenant_id)
    )

    if tipo_nota:
        normalized_tipo = tipo_nota.strip().lower()
        query = query.filter(
            models.Cotizacion.tipo_comprobante == (
                "07" if normalized_tipo in {"07", "credito", "nc"} else "08"
            )
        )
    if estado:
        query = query.filter(models.Cotizacion.estado == estado)
    if desde:
        try:
            query = query.filter(models.Cotizacion.fecha_emision >= datetime.fromisoformat(desde))
        except ValueError:
            _raise_bad_request("Fecha 'desde' invalida. Usa formato YYYY-MM-DD.")
    if hasta:
        try:
            hasta_dt = datetime.fromisoformat(hasta)
            query = query.filter(models.Cotizacion.fecha_emision <= hasta_dt.replace(hour=23, minute=59, second=59))
        except ValueError:
            _raise_bad_request("Fecha 'hasta' invalida. Usa formato YYYY-MM-DD.")
    if q:
        term = f"%{q.strip()}%"
        query = query.outerjoin(models.Cliente, models.Cotizacion.cliente_id == models.Cliente.id).filter(
            or_(
                models.Cliente.razon_social.ilike(term),
                models.Cliente.nombre_comercial.ilike(term),
                models.Cliente.numero_documento.ilike(term),
                models.Cotizacion.serie.ilike(term),
                models.Cotizacion.document_number.ilike(term),
                models.Cotizacion.nota_motivo_descripcion.ilike(term),
            )
        )

    query = query.order_by(desc(models.Cotizacion.id))
    return query.offset(skip).limit(limit).all()


@router.get("/notas/page", response_model=schemas.FiscalNotePageResponse)
def list_notas_page(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=100),
    tipo_nota: str | None = Query(default=None, pattern="^(07|08|credito|debito|nc|nd)$"),
    tab: str | None = Query(default="all", pattern="^(all|draft|emitted|pending|rejected|voided)$"),
    estado: str | None = Query(default=None),
    desde: str | None = Query(default=None),
    hasta: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    from services.document_flow_service import DOCUMENT_KIND_CREDIT_NOTE, DOCUMENT_KIND_DEBIT_NOTE

    desde_dt, hasta_dt = _parse_date_bounds(desde, hasta)
    base = (
        db.query(models.Cotizacion)
        .options(
            joinedload(models.Cotizacion.cliente),
            joinedload(models.Cotizacion.source_quote),
            joinedload(models.Cotizacion.nota_referencia),
        )
        .filter(models.Cotizacion.document_kind.in_([DOCUMENT_KIND_CREDIT_NOTE, DOCUMENT_KIND_DEBIT_NOTE]))
        .filter(models.Cotizacion.tenant_id == current_user.tenant_id)
    )
    if tipo_nota:
        normalized_tipo = tipo_nota.strip().lower()
        base = base.filter(
            models.Cotizacion.tipo_comprobante == (
                "07" if normalized_tipo in {"07", "credito", "nc"} else "08"
            )
        )
    if estado:
        base = base.filter(models.Cotizacion.estado == estado)
    if desde_dt:
        base = base.filter(models.Cotizacion.fecha_emision >= desde_dt)
    if hasta_dt:
        base = base.filter(models.Cotizacion.fecha_emision <= hasta_dt)
    if q:
        term = f"%{q.strip()}%"
        base = base.outerjoin(models.Cliente, models.Cotizacion.cliente_id == models.Cliente.id).filter(
            or_(
                models.Cliente.razon_social.ilike(term),
                models.Cliente.nombre_comercial.ilike(term),
                models.Cliente.numero_documento.ilike(term),
                models.Cotizacion.serie.ilike(term),
                models.Cotizacion.nota_motivo_descripcion.ilike(term),
            )
        )

    counts = _fiscal_doc_counts(base)
    page_query = base
    tab_filter = _fiscal_doc_tab_filter(tab)
    if tab_filter is not None:
        page_query = page_query.filter(tab_filter)
    total = page_query.with_entities(func.count(models.Cotizacion.id)).scalar() or 0
    items = page_query.order_by(desc(models.Cotizacion.id)).offset(skip).limit(limit).all()
    return {"items": items, "total": total, "skip": skip, "limit": limit, "counts": counts}


@router.get("/facturas-emitidas/", response_model=List[schemas.FiscalDocumentListResponse])
def list_facturas_emitidas(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    tipo_comprobante: str | None = Query(default=None, pattern="^(01|03)$"),
    estado: str | None = Query(default=None),
    moneda: str | None = Query(default=None, pattern="^(PEN|USD)$"),
    desde: str | None = Query(default=None),
    hasta: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=80),
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
        )
        .filter(models.Cotizacion.document_kind == DOCUMENT_KIND_FISCAL_DOCUMENT)
        .filter(models.Cotizacion.tenant_id == current_user.tenant_id)
    )

    if tipo_comprobante:
        query = query.filter(models.Cotizacion.tipo_comprobante == tipo_comprobante)
    if estado:
        query = query.filter(models.Cotizacion.estado == estado)
    if moneda:
        query = query.filter(models.Cotizacion.moneda == moneda)
    if desde:
        try:
            query = query.filter(models.Cotizacion.fecha_emision >= datetime.fromisoformat(desde))
        except ValueError:
            _raise_bad_request("Fecha 'desde' invalida. Usa formato YYYY-MM-DD.")
    if hasta:
        try:
            hasta_dt = datetime.fromisoformat(hasta)
            query = query.filter(models.Cotizacion.fecha_emision <= hasta_dt.replace(hour=23, minute=59, second=59))
        except ValueError:
            _raise_bad_request("Fecha 'hasta' invalida. Usa formato YYYY-MM-DD.")
    if q:
        term = f"%{q.strip()}%"
        query = query.join(models.Cliente, models.Cotizacion.cliente_id == models.Cliente.id).filter(
            (models.Cliente.razon_social.ilike(term))
            | (models.Cliente.nombre_comercial.ilike(term))
            | (models.Cliente.numero_documento.ilike(term))
            | (models.Cotizacion.serie.ilike(term))
        )

    query = query.order_by(desc(models.Cotizacion.id))
    return query.offset(skip).limit(limit).all()


@router.get("/facturas-emitidas/page", response_model=schemas.FiscalDocumentPageResponse)
def list_facturas_emitidas_page(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=100),
    tipo_comprobante: str | None = Query(default=None, pattern="^(01|03)$"),
    tab: str | None = Query(default="all", pattern="^(all|draft|emitted|pending|rejected|voided)$"),
    estado: str | None = Query(default=None),
    moneda: str | None = Query(default=None, pattern="^(PEN|USD)$"),
    desde: str | None = Query(default=None),
    hasta: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    from services.document_flow_service import DOCUMENT_KIND_FISCAL_DOCUMENT

    desde_dt, hasta_dt = _parse_date_bounds(desde, hasta)
    base = (
        db.query(models.Cotizacion)
        .options(joinedload(models.Cotizacion.cliente))
        .filter(models.Cotizacion.document_kind == DOCUMENT_KIND_FISCAL_DOCUMENT)
        .filter(models.Cotizacion.tenant_id == current_user.tenant_id)
    )
    if tipo_comprobante:
        base = base.filter(models.Cotizacion.tipo_comprobante == tipo_comprobante)
    if estado:
        base = base.filter(models.Cotizacion.estado == estado)
    if moneda:
        base = base.filter(models.Cotizacion.moneda == moneda)
    if desde_dt:
        base = base.filter(models.Cotizacion.fecha_emision >= desde_dt)
    if hasta_dt:
        base = base.filter(models.Cotizacion.fecha_emision <= hasta_dt)
    if q:
        term = f"%{q.strip()}%"
        base = base.outerjoin(models.Cliente, models.Cotizacion.cliente_id == models.Cliente.id).filter(
            or_(
                models.Cliente.razon_social.ilike(term),
                models.Cliente.nombre_comercial.ilike(term),
                models.Cliente.numero_documento.ilike(term),
                models.Cotizacion.serie.ilike(term),
            )
        )

    counts = _fiscal_doc_counts(base)
    page_query = base
    tab_filter = _fiscal_doc_tab_filter(tab)
    if tab_filter is not None:
        page_query = page_query.filter(tab_filter)
    total = page_query.with_entities(func.count(models.Cotizacion.id)).scalar() or 0
    items = page_query.order_by(desc(models.Cotizacion.id)).offset(skip).limit(limit).all()
    return {"items": items, "total": total, "skip": skip, "limit": limit, "counts": counts}


@router.get("/retenciones/", response_model=List[schemas.RetencionResponse])
def list_retenciones(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=100),
    status: str | None = Query(default=None, pattern="^(sent|pending|rejected)$"),
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
            desde_dt = datetime.fromisoformat(desde if len(desde) > 10 else f"{desde}T00:00:00")
        except ValueError:
            _raise_bad_request("Fecha 'desde' invalida. Usa formato YYYY-MM-DD.")
    if hasta:
        try:
            hasta_dt = datetime.fromisoformat(hasta if len(hasta) > 10 else f"{hasta}T23:59:59")
        except ValueError:
            _raise_bad_request("Fecha 'hasta' invalida. Usa formato YYYY-MM-DD.")

    return crud.list_retenciones(
        db,
        current_user.tenant_id,
        skip=skip,
        limit=limit,
        status=status,
        desde=desde_dt,
        hasta=hasta_dt,
        q=q,
    )


@router.get("/retenciones/page", response_model=schemas.RetencionPageResponse)
def list_retenciones_page(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=100),
    status: str | None = Query(default=None, pattern="^(sent|pending|rejected)$"),
    desde: str | None = Query(default=None),
    hasta: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    desde_dt, hasta_dt = _parse_date_bounds(desde, hasta)
    base = db.query(models.RetencionFiscal).filter(models.RetencionFiscal.tenant_id == current_user.tenant_id)
    if desde_dt:
        base = base.filter(models.RetencionFiscal.fecha_emision >= desde_dt)
    if hasta_dt:
        base = base.filter(models.RetencionFiscal.fecha_emision <= hasta_dt)
    if q:
        term = f"%{q.strip()}%"
        base = base.filter(
            or_(
                models.RetencionFiscal.serie.ilike(term),
                models.RetencionFiscal.correlativo.ilike(term),
                models.RetencionFiscal.proveedor_num_doc.ilike(term),
                models.RetencionFiscal.proveedor_rzn_social.ilike(term),
                models.RetencionFiscal.ticket.ilike(term),
                models.RetencionFiscal.sunat_error.ilike(term),
            )
        )
    counts = _status_counts(base, models.RetencionFiscal)
    page_query = base.filter(models.RetencionFiscal.status == status) if status else base
    total = page_query.with_entities(func.count(models.RetencionFiscal.id)).scalar() or 0
    items = page_query.order_by(desc(models.RetencionFiscal.id)).offset(skip).limit(limit).all()
    return {"items": items, "total": total, "skip": skip, "limit": limit, "counts": counts}


@router.post("/retenciones/emitir", response_model=schemas.RetencionResponse)
@limiter.limit("10/minute")
def emitir_retencion(
    request: Request,
    payload: schemas.RetencionCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
    _emission_check: models.User = Depends(require_emission_allowed),
):
    _require_beta_fiscal_feature(
        db,
        current_user,
        beta_feature_flags.FISCAL_FEATURE_RETENTIONS,
    )
    provider_payload = facturacion_service.build_retencion_payload(
        payload.model_dump(),
        current_user,
    )
    retencion = crud.create_retencion(
        db,
        tenant_id=current_user.tenant_id,
        usuario_id=current_user.id,
        payload=provider_payload,
    )

    try:
        result = facturacion_service.emitir_retencion(provider_payload, current_user, prepared=True)
        return crud.mark_retencion_sent(
            db,
            retencion.id,
            result=result,
            tenant_id=current_user.tenant_id,
        )
    except facturacion_service.FacturacionException as exc:
        crud.mark_retencion_rejected(
            db,
            retencion.id,
            error=str(exc),
            tenant_id=current_user.tenant_id,
        )
        raise HTTPException(400, str(exc))
    except Exception as exc:
        crud.mark_retencion_rejected(
            db,
            retencion.id,
            error="Error interno al emitir retencion.",
            tenant_id=current_user.tenant_id,
        )
        raise_internal_server_error(
            "emitir_retencion",
            "Error al emitir retencion.",
            exc,
        )


@router.post("/retenciones/emitir-legacy", include_in_schema=False)
def emitir_retencion_legacy():
    _raise_legacy_fiscal_endpoint_gone("/retenciones/emitir")


@router.get("/percepciones/", response_model=List[schemas.PercepcionResponse])
def list_percepciones(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=100),
    status: str | None = Query(default=None, pattern="^(sent|pending|rejected)$"),
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
            desde_dt = datetime.fromisoformat(desde if len(desde) > 10 else f"{desde}T00:00:00")
        except ValueError:
            _raise_bad_request("Fecha 'desde' invalida. Usa formato YYYY-MM-DD.")
    if hasta:
        try:
            hasta_dt = datetime.fromisoformat(hasta if len(hasta) > 10 else f"{hasta}T23:59:59")
        except ValueError:
            _raise_bad_request("Fecha 'hasta' invalida. Usa formato YYYY-MM-DD.")

    return crud.list_percepciones(
        db,
        current_user.tenant_id,
        skip=skip,
        limit=limit,
        status=status,
        desde=desde_dt,
        hasta=hasta_dt,
        q=q,
    )


@router.get("/percepciones/page", response_model=schemas.PercepcionPageResponse)
def list_percepciones_page(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=100),
    status: str | None = Query(default=None, pattern="^(sent|pending|rejected)$"),
    desde: str | None = Query(default=None),
    hasta: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    desde_dt, hasta_dt = _parse_date_bounds(desde, hasta)
    base = db.query(models.PercepcionFiscal).filter(models.PercepcionFiscal.tenant_id == current_user.tenant_id)
    if desde_dt:
        base = base.filter(models.PercepcionFiscal.fecha_emision >= desde_dt)
    if hasta_dt:
        base = base.filter(models.PercepcionFiscal.fecha_emision <= hasta_dt)
    if q:
        term = f"%{q.strip()}%"
        base = base.filter(
            or_(
                models.PercepcionFiscal.serie.ilike(term),
                models.PercepcionFiscal.correlativo.ilike(term),
                models.PercepcionFiscal.cliente_num_doc.ilike(term),
                models.PercepcionFiscal.cliente_rzn_social.ilike(term),
                models.PercepcionFiscal.ticket.ilike(term),
                models.PercepcionFiscal.sunat_error.ilike(term),
            )
        )
    counts = _status_counts(base, models.PercepcionFiscal)
    page_query = base.filter(models.PercepcionFiscal.status == status) if status else base
    total = page_query.with_entities(func.count(models.PercepcionFiscal.id)).scalar() or 0
    items = page_query.order_by(desc(models.PercepcionFiscal.id)).offset(skip).limit(limit).all()
    return {"items": items, "total": total, "skip": skip, "limit": limit, "counts": counts}


@router.post("/percepciones/emitir", response_model=schemas.PercepcionResponse)
@limiter.limit("10/minute")
def emitir_percepcion(
    request: Request,
    payload: schemas.PercepcionCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
    _emission_check: models.User = Depends(require_emission_allowed),
):
    _require_beta_fiscal_feature(
        db,
        current_user,
        beta_feature_flags.FISCAL_FEATURE_PERCEPTIONS,
    )
    provider_payload = facturacion_service.build_percepcion_payload(
        payload.model_dump(),
        current_user,
    )
    percepcion = crud.create_percepcion(
        db,
        tenant_id=current_user.tenant_id,
        usuario_id=current_user.id,
        payload=provider_payload,
    )

    try:
        result = facturacion_service.emitir_percepcion(provider_payload, current_user, prepared=True)
        return crud.mark_percepcion_sent(
            db,
            percepcion.id,
            result=result,
            tenant_id=current_user.tenant_id,
        )
    except facturacion_service.FacturacionException as exc:
        crud.mark_percepcion_rejected(
            db,
            percepcion.id,
            error=str(exc),
            tenant_id=current_user.tenant_id,
        )
        raise HTTPException(400, str(exc))
    except Exception as exc:
        crud.mark_percepcion_rejected(
            db,
            percepcion.id,
            error="Error interno al emitir percepcion.",
            tenant_id=current_user.tenant_id,
        )
        raise_internal_server_error(
            "emitir_percepcion",
            "Error al emitir percepcion.",
            exc,
        )


@router.post("/percepciones/emitir-legacy", include_in_schema=False)
def emitir_percepcion_legacy():
    _raise_legacy_fiscal_endpoint_gone("/percepciones/emitir")


@router.get("/resumen-diario/", response_model=List[schemas.ResumenDiarioResponse])
def list_resumenes_diarios(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=100),
    status: str | None = Query(default=None, pattern="^(sent|pending|rejected)$"),
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
            desde_dt = datetime.fromisoformat(desde if len(desde) > 10 else f"{desde}T00:00:00")
        except ValueError:
            _raise_bad_request("Fecha 'desde' invalida. Usa formato YYYY-MM-DD.")
    if hasta:
        try:
            hasta_dt = datetime.fromisoformat(hasta if len(hasta) > 10 else f"{hasta}T23:59:59")
        except ValueError:
            _raise_bad_request("Fecha 'hasta' invalida. Usa formato YYYY-MM-DD.")

    return crud.list_resumenes_diarios(
        db,
        current_user.tenant_id,
        skip=skip,
        limit=limit,
        status=status,
        desde=desde_dt,
        hasta=hasta_dt,
        q=q,
    )


@router.get("/resumen-diario/page", response_model=schemas.ResumenDiarioPageResponse)
def list_resumenes_diarios_page(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=100),
    status: str | None = Query(default=None, pattern="^(sent|pending|rejected)$"),
    desde: str | None = Query(default=None),
    hasta: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    desde_dt, hasta_dt = _parse_date_bounds(desde, hasta)
    base = db.query(models.ResumenDiario).filter(models.ResumenDiario.tenant_id == current_user.tenant_id)
    if desde_dt:
        base = base.filter(models.ResumenDiario.fec_resumen >= desde_dt)
    if hasta_dt:
        base = base.filter(models.ResumenDiario.fec_resumen <= hasta_dt)
    if q:
        term = f"%{q.strip()}%"
        base = base.filter(
            or_(
                models.ResumenDiario.correlativo.ilike(term),
                models.ResumenDiario.ticket.ilike(term),
                models.ResumenDiario.sunat_error.ilike(term),
            )
        )
    counts = _status_counts(base, models.ResumenDiario)
    page_query = base.filter(models.ResumenDiario.status == status) if status else base
    total = page_query.with_entities(func.count(models.ResumenDiario.id)).scalar() or 0
    items = page_query.order_by(desc(models.ResumenDiario.id)).offset(skip).limit(limit).all()
    return {"items": items, "total": total, "skip": skip, "limit": limit, "counts": counts}


@router.post("/resumen-diario/enviar", response_model=schemas.ResumenDiarioResponse)
@limiter.limit("10/minute")
def enviar_resumen_diario(
    request: Request,
    payload: schemas.ResumenDiarioCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
    _emission_check: models.User = Depends(require_emission_allowed),
):
    _require_beta_fiscal_feature(
        db,
        current_user,
        beta_feature_flags.FISCAL_FEATURE_DAILY_SUMMARY,
    )
    provider_payload = facturacion_service.build_resumen_diario_payload(
        payload.model_dump(by_alias=True),
        current_user,
    )
    resumen = crud.create_resumen_diario(
        db,
        tenant_id=current_user.tenant_id,
        usuario_id=current_user.id,
        payload=provider_payload,
    )

    try:
        result = facturacion_service.emitir_resumen_diario(provider_payload, current_user, prepared=True)
        return crud.mark_resumen_diario_sent(
            db,
            resumen.id,
            result=result,
            tenant_id=current_user.tenant_id,
        )
    except facturacion_service.FacturacionException as exc:
        crud.mark_resumen_diario_rejected(
            db,
            resumen.id,
            error=str(exc),
            tenant_id=current_user.tenant_id,
        )
        raise HTTPException(400, str(exc))
    except Exception as exc:
        crud.mark_resumen_diario_rejected(
            db,
            resumen.id,
            error="Error interno al enviar resumen diario.",
            tenant_id=current_user.tenant_id,
        )
        raise_internal_server_error(
            "enviar_resumen_diario",
            "Error al enviar resumen diario.",
            exc,
        )


@router.get("/reversiones/", response_model=List[schemas.ReversionResponse])
def list_reversiones(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=100),
    status: str | None = Query(default=None, pattern="^(sent|pending|rejected)$"),
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
            desde_dt = datetime.fromisoformat(desde if len(desde) > 10 else f"{desde}T00:00:00")
        except ValueError:
            _raise_bad_request("Fecha 'desde' invalida. Usa formato YYYY-MM-DD.")
    if hasta:
        try:
            hasta_dt = datetime.fromisoformat(hasta if len(hasta) > 10 else f"{hasta}T23:59:59")
        except ValueError:
            _raise_bad_request("Fecha 'hasta' invalida. Usa formato YYYY-MM-DD.")

    return crud.list_reversiones(
        db,
        current_user.tenant_id,
        skip=skip,
        limit=limit,
        status=status,
        desde=desde_dt,
        hasta=hasta_dt,
        q=q,
    )


@router.get("/reversiones/page", response_model=schemas.ReversionPageResponse)
def list_reversiones_page(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=100),
    status: str | None = Query(default=None, pattern="^(sent|pending|rejected)$"),
    desde: str | None = Query(default=None),
    hasta: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    desde_dt, hasta_dt = _parse_date_bounds(desde, hasta)
    base = db.query(models.ReversionFiscal).filter(models.ReversionFiscal.tenant_id == current_user.tenant_id)
    if desde_dt:
        base = base.filter(models.ReversionFiscal.fec_comunicacion >= desde_dt)
    if hasta_dt:
        base = base.filter(models.ReversionFiscal.fec_comunicacion <= hasta_dt)
    if q:
        term = f"%{q.strip()}%"
        base = base.filter(
            or_(
                models.ReversionFiscal.correlativo.ilike(term),
                models.ReversionFiscal.ticket.ilike(term),
                models.ReversionFiscal.sunat_error.ilike(term),
            )
        )
    counts = _status_counts(base, models.ReversionFiscal)
    page_query = base.filter(models.ReversionFiscal.status == status) if status else base
    total = page_query.with_entities(func.count(models.ReversionFiscal.id)).scalar() or 0
    items = page_query.order_by(desc(models.ReversionFiscal.id)).offset(skip).limit(limit).all()
    return {"items": items, "total": total, "skip": skip, "limit": limit, "counts": counts}


@router.post("/reversiones/enviar", response_model=schemas.ReversionResponse)
@limiter.limit("10/minute")
def enviar_reversion(
    request: Request,
    payload: schemas.ReversionCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
    _emission_check: models.User = Depends(require_emission_allowed),
):
    _require_beta_fiscal_feature(
        db,
        current_user,
        beta_feature_flags.FISCAL_FEATURE_REVERSIONS,
    )
    provider_payload = facturacion_service.build_reversion_payload(
        payload.model_dump(by_alias=True),
        current_user,
    )
    reversion = crud.create_reversion(
        db,
        tenant_id=current_user.tenant_id,
        usuario_id=current_user.id,
        payload=provider_payload,
    )

    try:
        result = facturacion_service.emitir_reversion(
            provider_payload,
            current_user,
            prepared=True,
            poll_async=False,
        )
        return crud.mark_reversion_sent(
            db,
            reversion.id,
            result=result,
            tenant_id=current_user.tenant_id,
        )
    except facturacion_service.FacturacionException as exc:
        crud.mark_reversion_rejected(
            db,
            reversion.id,
            error=str(exc),
            tenant_id=current_user.tenant_id,
        )
        raise HTTPException(400, str(exc))
    except Exception as exc:
        crud.mark_reversion_rejected(
            db,
            reversion.id,
            error="Error interno al enviar reversion.",
            tenant_id=current_user.tenant_id,
        )
        raise_internal_server_error(
            "enviar_reversion",
            "Error al enviar reversion.",
            exc,
        )


@router.post("/reversiones/enviar-legacy", include_in_schema=False)
def enviar_reversion_legacy():
    _raise_legacy_fiscal_endpoint_gone("/reversiones/enviar")


@router.post("/facturacion/{tipo_archivo}")
@limiter.limit("30/minute")
def recuperar_archivo_api(
    request: Request,
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
