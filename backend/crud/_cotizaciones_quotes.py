from __future__ import annotations

from datetime import datetime
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
from services.client_snapshot_service import build_cliente_snapshot
from services.document_flow_service import (
    DOCUMENT_KIND_QUOTATION,
    DOCUMENT_STATUS_PENDING,
    DOCUMENT_STATUS_VOIDED,
    is_quote_document,
)


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

    items_db, items_procesados_para_suma = _build_quote_items(db, cotizacion, tenant_id)
    totales = calculations.sumarizar_cotizacion(
        items_procesados_para_suma
    )
    nuevo_correlativo, internal_order_number = _next_quote_identity(db, tenant_id)

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

    db_cotizacion = models.Cotizacion(
        cliente_id=db_cliente.id,
        cliente_snapshot=cliente_snapshot,
        usuario_id=usuario_id,
        tenant_id=tenant_id,
        fecha_emision=cotizacion.fecha_emision or datetime.now(),
        fecha_vencimiento=cotizacion.fecha_vencimiento,
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

    # La cotizacion conserva su COT, pero el PDF comercial se regenera bajo demanda.
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
    return create_cotizacion(db, payload, usuario.id, original.tenant_id)


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
