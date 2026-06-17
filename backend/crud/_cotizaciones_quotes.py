from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session, joinedload

import models
import schemas
from access_control import can_access_all_tenant_resources
from crud._base import _retry_on_correlativo_conflict, get_cliente_for_tenant
from crud._cotizaciones_shared import (
    QUOTE_SERIE,
    _apply_quote_user_scope,
    _build_quote_detail_query,
    _build_quote_items,
    _build_quote_listing_query,
    _ensure_quote_balance_persisted,
    _next_quote_identity,
)
from services import calculations
from services.bank_account_validation import validate_and_normalize_bank_accounts
from services.client_snapshot_service import build_cliente_snapshot
from services.document_flow_service import (
    DOCUMENT_KIND_QUOTATION,
    DOCUMENT_STATUS_PENDING,
    DOCUMENT_STATUS_VOIDED,
    is_quote_document,
)


_QUOTE_DEFAULT_PAYMENT_CONDITION = "credito_15"
_QUOTE_CREDIT_TERM_DAYS = {
    "credito_7": 7,
    "credito_15": 15,
    "credito_30": 30,
    "credito_60": 60,
}


def _serialize_cuotas_pago(cuotas_pago) -> list[dict]:
    serialized = []
    for cuota in cuotas_pago or []:
        fecha_pago = getattr(cuota, "fecha_pago", None)
        monto = getattr(cuota, "monto", None)
        if not fecha_pago or monto is None:
            continue
        serialized.append(
            {
                "fecha_pago": fecha_pago.isoformat(),
                "monto": str(calculations.redondear(monto)),
            }
        )
    return serialized


def _resolve_quote_payment_terms(
    *,
    fecha_emision: datetime,
    fecha_vencimiento: datetime | None,
    condicion_pago: str | None,
) -> tuple[str, datetime | None]:
    resolved_condition = str(condicion_pago or "").strip().lower() or _QUOTE_DEFAULT_PAYMENT_CONDITION
    if fecha_vencimiento is not None:
        return resolved_condition, fecha_vencimiento
    if resolved_condition == "contado":
        return resolved_condition, None

    due_days = _QUOTE_CREDIT_TERM_DAYS.get(
        resolved_condition,
        _QUOTE_CREDIT_TERM_DAYS[_QUOTE_DEFAULT_PAYMENT_CONDITION],
    )
    return resolved_condition, fecha_emision + timedelta(days=due_days)


def _resolve_quote_selected_wallet_id(
    payment_methods,
    *,
    selected_wallet_id: str | None = None,
    default_wallet_id: str | None = None,
) -> str | None:
    wallet_ids = [
        str(method.get("id")).strip()
        for method in payment_methods or []
        if method.get("tipo") == "wallet" and str(method.get("id") or "").strip()
    ]
    for candidate in (selected_wallet_id, default_wallet_id):
        normalized = str(candidate or "").strip()
        if normalized and normalized in wallet_ids:
            return normalized
    return wallet_ids[0] if wallet_ids else None


def _pick_quote_wallet_snapshot(payment_methods, selected_wallet_id: str | None) -> dict | None:
    normalized_selected = str(selected_wallet_id or "").strip()
    if not normalized_selected:
        return None
    for method in payment_methods or []:
        if method.get("tipo") != "wallet":
            continue
        if str(method.get("id") or "").strip() == normalized_selected:
            return dict(method)
    return None


def _resolve_quote_payment_methods_snapshot(
    *,
    tenant_payment_methods,
    quote_payment_methods,
    selected_wallet_id: str | None = None,
    default_wallet_id: str | None = None,
) -> tuple[list[dict] | None, str | None]:
    normalized_tenant_methods = validate_and_normalize_bank_accounts(tenant_payment_methods or []) or []

    if quote_payment_methods is None:
        selected_bank_methods = [
            dict(method)
            for method in normalized_tenant_methods
            if method.get("tipo") == "bank" and method.get("mostrar_en_cotizaciones", True)
        ]
    else:
        selected_bank_methods = [
            dict(method)
            for method in quote_payment_methods or []
            if isinstance(method, dict) and method.get("tipo") == "bank"
        ]

    resolved_wallet_id = _resolve_quote_selected_wallet_id(
        normalized_tenant_methods,
        selected_wallet_id=selected_wallet_id,
        default_wallet_id=default_wallet_id,
    )
    wallet_snapshot = _pick_quote_wallet_snapshot(normalized_tenant_methods, resolved_wallet_id)

    snapshot: list[dict] = []
    if wallet_snapshot:
        snapshot.append(wallet_snapshot)
    snapshot.extend(selected_bank_methods)

    if quote_payment_methods is not None:
        return snapshot, resolved_wallet_id

    return (snapshot or None), resolved_wallet_id


def get_cotizaciones(
    db: Session,
    usuario: Optional[models.User] = None,
    skip: int = 0,
    limit: int = 100,
):
    query = _build_quote_listing_query(db)
    query = _apply_quote_user_scope(query, usuario)
    return query.offset(skip).limit(limit).all()


def get_cotizacion(
    db: Session,
    cotizacion_id: int,
    usuario: Optional[models.User] = None,
):
    query = _build_quote_detail_query(db).filter(models.Cotizacion.id == cotizacion_id)
    query = _apply_quote_user_scope(query, usuario)
    return query.first()


def get_cotizacion_by_uuid(db: Session, uuid_publico: str):
    return (
        db.query(models.Cotizacion)
        .options(
            joinedload(models.Cotizacion.cliente),
            joinedload(models.Cotizacion.tenant),
        )
        .filter(models.Cotizacion.uuid_publico == uuid_publico)
        .first()
    )


def create_cotizacion(
    db: Session,
    cotizacion: schemas.CotizacionCreate,
    usuario_id: int,
    tenant_id: int,
):
    return _retry_on_correlativo_conflict(
        _create_cotizacion_inner,
        db,
        cotizacion,
        usuario_id,
        tenant_id,
    )


def _create_cotizacion_inner(
    db: Session,
    cotizacion: schemas.CotizacionCreate,
    usuario_id: int,
    tenant_id: int,
):
    db_cliente = get_cliente_for_tenant(db, cotizacion.cliente_id, tenant_id)
    if not db_cliente:
        raise ValueError("Cliente no encontrado o no pertenece al tenant actual.")

    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    quote_payment_snapshot, quote_selected_wallet_id = _resolve_quote_payment_methods_snapshot(
        tenant_payment_methods=getattr(tenant, "bank_accounts", None) or [],
        quote_payment_methods=getattr(cotizacion, "quote_payment_methods", None),
        selected_wallet_id=getattr(cotizacion, "quote_selected_wallet_id", None),
        default_wallet_id=getattr(tenant, "quote_default_wallet_id", None),
    )

    items_db, items_procesados_para_suma = _build_quote_items(db, cotizacion, tenant_id)
    totales = calculations.sumarizar_cotizacion(items_procesados_para_suma)
    nuevo_correlativo, internal_order_number = _next_quote_identity(db, tenant_id)

    fecha_emision = cotizacion.fecha_emision or datetime.now()
    condicion_pago = (
        getattr(cotizacion, "condicion_pago", None)
        or getattr(db_cliente, "condicion_pago", None)
    )
    condicion_pago, fecha_vencimiento = _resolve_quote_payment_terms(
        fecha_emision=fecha_emision,
        fecha_vencimiento=cotizacion.fecha_vencimiento,
        condicion_pago=condicion_pago,
    )
    cuotas_pago = _serialize_cuotas_pago(getattr(cotizacion, "cuotas_pago", None))
    cliente_snapshot = build_cliente_snapshot(
        db_cliente,
        getattr(cotizacion, "cliente_snapshot", None).model_dump(exclude_none=False)
        if getattr(cotizacion, "cliente_snapshot", None)
        else None,
    )

    db_cotizacion = models.Cotizacion(
        cliente_id=db_cliente.id,
        cliente_snapshot=cliente_snapshot,
        quote_payment_methods=quote_payment_snapshot,
        quote_selected_wallet_id=quote_selected_wallet_id,
        usuario_id=usuario_id,
        tenant_id=tenant_id,
        fecha_emision=fecha_emision,
        fecha_vencimiento=fecha_vencimiento,
        moneda=cotizacion.moneda,
        tipo_comprobante=cotizacion.tipo_comprobante,
        document_kind=DOCUMENT_KIND_QUOTATION,
        internal_order_number=internal_order_number,
        correlativo=nuevo_correlativo,
        serie=QUOTE_SERIE,
        observaciones=getattr(cotizacion, "observaciones", None),
        condicion_pago=condicion_pago,
        cuotas_pago=cuotas_pago or None,
        total_gravada=totales["total_gravada"],
        total_exonerada=totales["total_exonerada"],
        total_inafecta=totales["total_inafecta"],
        total_igv=totales["total_igv"],
        total_venta=totales["total_venta"],
        saldo_pendiente=totales["total_venta"],
        items=items_db,
    )

    try:
        db.add(db_cotizacion)
        db.commit()
        db.refresh(db_cotizacion)
        _ensure_quote_balance_persisted(db, db_cotizacion, totales["total_venta"])
        return get_cotizacion(db, db_cotizacion.id)
    except Exception as exc:
        db.rollback()
        raise exc


def _has_active_derived_document(db: Session, cotizacion: models.Cotizacion) -> bool:
    return (
        db.query(models.Cotizacion.id)
        .filter(
            models.Cotizacion.source_quote_id == cotizacion.id,
            models.Cotizacion.document_kind != DOCUMENT_KIND_QUOTATION,
            models.Cotizacion.estado != DOCUMENT_STATUS_VOIDED,
        )
        .first()
        is not None
    )


def _ensure_cotizacion_editable(db: Session, cotizacion: models.Cotizacion) -> None:
    if not is_quote_document(cotizacion):
        raise ValueError("Solo se puede editar una cotizacion comercial.")
    if cotizacion.estado != DOCUMENT_STATUS_PENDING:
        raise ValueError("Solo se puede editar una cotizacion en estado pendiente.")
    if cotizacion.linked_fiscal_document_id or _has_active_derived_document(db, cotizacion):
        raise ValueError(
            "No se puede editar una cotizacion con comprobante fiscal asociado."
        )
    if Decimal(str(cotizacion.monto_pagado or 0)) > Decimal("0"):
        raise ValueError("No se puede editar una cotizacion con pagos asociados.")
    if getattr(cotizacion, "pagos", None):
        raise ValueError("No se puede editar una cotizacion con pagos asociados.")


def update_cotizacion(
    db: Session,
    cotizacion_id: int,
    cotizacion: schemas.CotizacionUpdate,
    usuario: models.User,
):
    query = db.query(models.Cotizacion).filter(models.Cotizacion.id == cotizacion_id)
    query = _apply_quote_user_scope(query, usuario)

    db_cotizacion = query.with_for_update().first()
    if not db_cotizacion:
        return None

    _ensure_cotizacion_editable(db, db_cotizacion)

    db_cliente = get_cliente_for_tenant(
        db,
        cotizacion.cliente_id,
        db_cotizacion.tenant_id,
    )
    if not db_cliente:
        raise ValueError("Cliente no encontrado o no pertenece al tenant actual.")

    tenant = db.query(models.Tenant).filter(models.Tenant.id == db_cotizacion.tenant_id).first()
    quote_payment_snapshot, quote_selected_wallet_id = _resolve_quote_payment_methods_snapshot(
        tenant_payment_methods=getattr(tenant, "bank_accounts", None) or [],
        quote_payment_methods=getattr(cotizacion, "quote_payment_methods", None),
        selected_wallet_id=getattr(cotizacion, "quote_selected_wallet_id", None),
        default_wallet_id=getattr(tenant, "quote_default_wallet_id", None),
    )

    items_db, items_procesados_para_suma = _build_quote_items(
        db,
        cotizacion,
        db_cotizacion.tenant_id,
    )
    totales = calculations.sumarizar_cotizacion(items_procesados_para_suma)
    condicion_pago = (
        getattr(cotizacion, "condicion_pago", None)
        or getattr(db_cliente, "condicion_pago", None)
    )
    cuotas_pago = _serialize_cuotas_pago(getattr(cotizacion, "cuotas_pago", None))
    cliente_snapshot = build_cliente_snapshot(
        db_cliente,
        getattr(cotizacion, "cliente_snapshot", None).model_dump(exclude_none=False)
        if getattr(cotizacion, "cliente_snapshot", None)
        else None,
    )

    db_cotizacion.cliente_id = db_cliente.id
    db_cotizacion.cliente_snapshot = cliente_snapshot
    db_cotizacion.quote_payment_methods = quote_payment_snapshot
    db_cotizacion.quote_selected_wallet_id = quote_selected_wallet_id
    if cotizacion.fecha_emision is not None:
        db_cotizacion.fecha_emision = cotizacion.fecha_emision
    db_cotizacion.fecha_vencimiento = cotizacion.fecha_vencimiento
    db_cotizacion.moneda = cotizacion.moneda
    db_cotizacion.tipo_comprobante = cotizacion.tipo_comprobante
    db_cotizacion.observaciones = getattr(cotizacion, "observaciones", None)
    db_cotizacion.condicion_pago = condicion_pago
    db_cotizacion.cuotas_pago = cuotas_pago or None
    db_cotizacion.total_gravada = totales["total_gravada"]
    db_cotizacion.total_exonerada = totales["total_exonerada"]
    db_cotizacion.total_inafecta = totales["total_inafecta"]
    db_cotizacion.total_igv = totales["total_igv"]
    db_cotizacion.total_venta = totales["total_venta"]
    db_cotizacion.saldo_pendiente = totales["total_venta"]
    db_cotizacion.items = items_db

    db_cotizacion.sunat_pdf_url = None
    db_cotizacion.sunat_xml_url = None
    db_cotizacion.sunat_cdr_url = None
    db_cotizacion.sunat_error = None
    db_cotizacion.sunat_xml_content = None
    db_cotizacion.sunat_hash = None
    db_cotizacion.sunat_qr_payload = None
    db_cotizacion.sunat_qr_svg = None

    try:
        db.commit()
        db.refresh(db_cotizacion)
        return get_cotizacion(db, db_cotizacion.id, usuario)
    except Exception as exc:
        db.rollback()
        raise exc


def duplicate_cotizacion(
    db: Session,
    cotizacion_id: int,
    usuario: models.User,
):
    original = get_cotizacion(db, cotizacion_id, usuario)
    if not original:
        return None

    if not is_quote_document(original):
        raise ValueError("Solo se puede duplicar una cotizacion comercial.")

    payload = schemas.CotizacionCreate(
        cliente_id=original.cliente_id,
        cliente_snapshot=original.cliente_snapshot,
        quote_payment_methods=original.quote_payment_methods,
        quote_selected_wallet_id=getattr(original, "quote_selected_wallet_id", None),
        fecha_vencimiento=original.fecha_vencimiento,
        moneda=original.moneda,
        tipo_comprobante=original.tipo_comprobante or "00",
        observaciones=original.observaciones,
        condicion_pago=original.condicion_pago,
        cuotas_pago=original.cuotas_pago or [],
        items=[
            schemas.CotizacionItemCreate(
                producto_id=item.producto_id,
                codigo_producto=item.codigo_producto,
                descripcion=item.descripcion,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                unidad_medida=item.unidad_medida,
                tipo_afectacion_igv=item.tipo_afectacion_igv,
            )
            for item in original.items or []
        ],
    )
    copia = create_cotizacion(db, payload, usuario.id, original.tenant_id)
    if (
        getattr(original, "quote_payment_methods", None) is not None
        or getattr(original, "quote_selected_wallet_id", None) is not None
    ):
        copia.quote_payment_methods = original.quote_payment_methods
        copia.quote_selected_wallet_id = getattr(original, "quote_selected_wallet_id", None)
        db.commit()
        db.refresh(copia)
        return get_cotizacion(db, copia.id, usuario)
    return copia


def delete_cotizacion(
    db: Session,
    cotizacion_id: int,
    usuario: models.User,
):
    query = db.query(models.Cotizacion).filter(models.Cotizacion.id == cotizacion_id)
    if getattr(usuario, "tenant_id", None):
        query = query.filter(models.Cotizacion.tenant_id == usuario.tenant_id)
    if not can_access_all_tenant_resources(usuario):
        query = query.filter(models.Cotizacion.usuario_id == usuario.id)

    cotizacion = query.with_for_update().first()
    if not cotizacion:
        return None

    if not is_quote_document(cotizacion):
        raise ValueError("Solo se puede eliminar una cotizacion comercial.")
    if cotizacion.estado != DOCUMENT_STATUS_PENDING:
        raise ValueError("Solo se puede eliminar una cotizacion en estado pendiente.")
    if cotizacion.linked_fiscal_document_id:
        raise ValueError(
            "No se puede eliminar una cotizacion con comprobante fiscal asociado."
        )

    try:
        db.delete(cotizacion)
        db.commit()
        return True
    except Exception as exc:
        db.rollback()
        raise exc
