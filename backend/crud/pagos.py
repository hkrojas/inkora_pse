"""crud/pagos.py - Pagos y adelantos de cliente al tenant."""
from decimal import Decimal

from sqlalchemy import desc
from sqlalchemy.orm import Session

import models
import schemas
from crud._base import (
    _get_tenant_resource,
    get_source_quote,
    resolve_payment_anchor_document,
)
from services.document_flow_service import (
    DOCUMENT_KIND_FISCAL_DOCUMENT,
    DOCUMENT_STATUS_ISSUED,
    DOCUMENT_STATUS_VOIDED,
    is_fiscal_document,
    is_note_document,
    is_quote_document,
)
from services.fiscal_balance_service import get_fiscal_document_balance


def _latest_fiscal_document_for_quote_any_status(
    db: Session,
    *,
    tenant_id: int,
    source_quote_id: int,
):
    return (
        db.query(models.Cotizacion)
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.source_quote_id == source_quote_id,
            models.Cotizacion.document_kind == DOCUMENT_KIND_FISCAL_DOCUMENT,
        )
        .order_by(desc(models.Cotizacion.id))
        .first()
    )


def _accepted_fiscal_document_for_quote(
    db: Session,
    *,
    tenant_id: int,
    source_quote_id: int,
):
    return (
        db.query(models.Cotizacion)
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.source_quote_id == source_quote_id,
            models.Cotizacion.document_kind == DOCUMENT_KIND_FISCAL_DOCUMENT,
            models.Cotizacion.estado == DOCUMENT_STATUS_ISSUED,
            models.Cotizacion.tipo_comprobante.in_(("01", "03")),
        )
        .order_by(desc(models.Cotizacion.id))
        .first()
    )


def _resolve_pago_context(
    db: Session,
    *,
    document_id: int,
    tenant_id: int,
):
    document = _get_tenant_resource(db, models.Cotizacion, document_id, tenant_id)
    if not document:
        raise ValueError("Cotizacion no encontrada")
    if is_note_document(document):
        raise ValueError("No se pueden registrar pagos sobre notas de credito o debito.")

    if is_fiscal_document(document):
        source_quote = get_source_quote(db, document) or document
        if document.estado == DOCUMENT_STATUS_VOIDED:
            raise ValueError("No se pueden registrar pagos sobre comprobantes anulados.")
        if document.estado == DOCUMENT_STATUS_ISSUED:
            return source_quote, document, True
        return source_quote, document, False

    if not is_quote_document(document):
        raise ValueError("Documento no soportado para registrar pagos.")

    source_quote = document
    if source_quote.estado == DOCUMENT_STATUS_VOIDED:
        raise ValueError("No se pueden registrar pagos sobre cotizaciones anuladas.")

    accepted_fiscal = _accepted_fiscal_document_for_quote(
        db,
        tenant_id=tenant_id,
        source_quote_id=source_quote.id,
    )
    if accepted_fiscal:
        return source_quote, accepted_fiscal, True

    latest_fiscal = _latest_fiscal_document_for_quote_any_status(
        db,
        tenant_id=tenant_id,
        source_quote_id=source_quote.id,
    )
    if latest_fiscal and latest_fiscal.estado == DOCUMENT_STATUS_VOIDED:
        raise ValueError("No se pueden registrar pagos sobre comprobantes anulados.")

    return source_quote, None, False


def _pre_fiscal_balance(source_quote) -> Decimal:
    return Decimal(str(source_quote.total_venta or 0)) - Decimal(
        str(source_quote.monto_pagado or 0)
    )


def apply_prefiscal_advances_to_fiscal_document(
    db: Session,
    tenant_id: int,
    fiscal_document_id: int,
    *,
    commit: bool = True,
):
    fiscal_document = (
        db.query(models.Cotizacion)
        .filter(
            models.Cotizacion.id == fiscal_document_id,
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.document_kind == DOCUMENT_KIND_FISCAL_DOCUMENT,
        )
        .with_for_update()
        .first()
    )
    if not fiscal_document:
        raise ValueError("Documento fiscal no encontrado para el tenant.")
    if fiscal_document.estado == DOCUMENT_STATUS_VOIDED:
        raise ValueError("No se pueden aplicar adelantos a comprobantes anulados.")
    if fiscal_document.estado != DOCUMENT_STATUS_ISSUED:
        raise ValueError(
            "Los adelantos pre-fiscales no se aplican hasta que el comprobante sea aceptado."
        )
    if fiscal_document.tipo_comprobante not in ("01", "03"):
        raise ValueError("Solo se pueden aplicar adelantos a facturas o boletas.")
    if fiscal_document.source_quote_id is None:
        return []

    advances = (
        db.query(models.Pago)
        .filter(
            models.Pago.tenant_id == tenant_id,
            models.Pago.source_quote_id == fiscal_document.source_quote_id,
            models.Pago.fiscal_document_id.is_(None),
            models.Pago.tipo == "adelanto",
        )
        .with_for_update()
        .all()
    )

    for payment in advances:
        payment.fiscal_document_id = fiscal_document.id
        payment.tipo = "pago"

    db.flush()
    if commit:
        db.commit()
        for payment in advances:
            db.refresh(payment)
    return advances


def registrar_pago(db: Session, cotizacion_id: int, pago_data: schemas.PagoCreate, tenant_id: int):
    monto = Decimal(str(pago_data.monto_pagado))
    source_quote, fiscal_document, use_fiscal_balance = _resolve_pago_context(
        db,
        document_id=cotizacion_id,
        tenant_id=tenant_id,
    )

    if use_fiscal_balance:
        balance = get_fiscal_document_balance(db, tenant_id, fiscal_document.id)
        saldo_actual = balance.saldo_pendiente
        saldo_legacy_despues = saldo_actual - monto
    else:
        saldo_actual = _pre_fiscal_balance(source_quote)
        saldo_legacy_despues = saldo_actual - monto

    if monto > saldo_actual:
        if use_fiscal_balance:
            raise ValueError("El pago excede el saldo fiscal pendiente.")
        raise ValueError(
            f"El monto ({monto}) excede el saldo pendiente ({saldo_actual}). "
            f"Ya pagado: {source_quote.monto_pagado}"
        )

    from datetime import datetime as _dt
    fecha_pago = getattr(pago_data, "fecha_pago", None) or _dt.now()
    payment_type = "pago" if use_fiscal_balance else "adelanto"
    db_pago = models.Pago(
        tenant_id=tenant_id,
        cotizacion_id=source_quote.id,
        source_quote_id=source_quote.id,
        fiscal_document_id=fiscal_document.id if use_fiscal_balance else None,
        internal_order_number=source_quote.internal_order_number,
        monto_pagado=monto,
        metodo_pago=pago_data.metodo_pago,
        fecha_pago=fecha_pago,
        referencia_operacion=pago_data.referencia_operacion,
        tipo=payment_type,
    )

    nuevo_pagado = Decimal(str(source_quote.monto_pagado or 0)) + monto
    source_quote.monto_pagado = nuevo_pagado
    source_quote.saldo_pendiente = saldo_legacy_despues

    try:
        db.add(db_pago)
        db.commit()
        db.refresh(db_pago)
        db.refresh(source_quote)
        return db_pago
    except Exception as e:
        db.rollback()
        raise e


def get_pagos_cotizacion(db: Session, cotizacion_id: int, tenant_id: int):
    source_quote, _ = resolve_payment_anchor_document(db, cotizacion_id, tenant_id)
    if not source_quote:
        return []
    return db.query(models.Pago).filter(
        models.Pago.cotizacion_id == source_quote.id,
        models.Pago.tenant_id == tenant_id,
    ).order_by(models.Pago.fecha_pago.desc()).all()
