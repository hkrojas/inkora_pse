"""Saldo fiscal neto para cobranza y limites de notas."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

import models
from services.document_flow_service import (
    DOCUMENT_KIND_CREDIT_NOTE,
    DOCUMENT_KIND_DEBIT_NOTE,
    DOCUMENT_KIND_FISCAL_DOCUMENT,
    DOCUMENT_STATUS_ISSUED,
)

_ZERO = Decimal("0.00")
_MONEY_QUANT = Decimal("0.01")


@dataclass(frozen=True)
class FiscalDocumentBalance:
    tenant_id: int
    fiscal_document_id: int
    source_quote_id: int | None
    document_total: Decimal
    credit_notes_total: Decimal
    debit_notes_total: Decimal
    payments_total: Decimal
    primary_payments_total: Decimal
    legacy_payments_total: Decimal
    net_total: Decimal
    saldo_pendiente: Decimal
    credit_note_available_amount: Decimal


def _money(value) -> Decimal:
    return Decimal(str(value if value is not None else _ZERO)).quantize(_MONEY_QUANT)


def _sum_money(db: Session, *filters) -> Decimal:
    value = db.query(func.sum(models.Cotizacion.total_venta)).filter(*filters).scalar()
    return _money(value)


def _sum_payments(db: Session, *filters) -> Decimal:
    value = db.query(func.sum(models.Pago.monto_pagado)).filter(*filters).scalar()
    return _money(value)


def _get_accepted_fiscal_document(
    db: Session,
    tenant_id: int,
    fiscal_document_id: int,
) -> models.Cotizacion:
    document = (
        db.query(models.Cotizacion)
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.id == fiscal_document_id,
            models.Cotizacion.document_kind == DOCUMENT_KIND_FISCAL_DOCUMENT,
            models.Cotizacion.estado == DOCUMENT_STATUS_ISSUED,
            models.Cotizacion.tipo_comprobante.in_(("01", "03")),
        )
        .first()
    )
    if not document:
        raise ValueError("Documento fiscal aceptado no encontrado para el tenant.")
    return document


def _sum_accepted_notes(
    db: Session,
    *,
    tenant_id: int,
    fiscal_document_id: int,
    document_kind: str,
) -> Decimal:
    return _sum_money(
        db,
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.nota_referencia_id == fiscal_document_id,
        models.Cotizacion.document_kind == document_kind,
        models.Cotizacion.estado == DOCUMENT_STATUS_ISSUED,
    )


def _sum_primary_payments(
    db: Session,
    *,
    tenant_id: int,
    fiscal_document_id: int,
) -> Decimal:
    return _sum_payments(
        db,
        models.Pago.tenant_id == tenant_id,
        models.Pago.fiscal_document_id == fiscal_document_id,
    )


def _sum_legacy_source_quote_payments(
    db: Session,
    *,
    tenant_id: int,
    source_quote_id: int | None,
) -> Decimal:
    if source_quote_id is None:
        return _ZERO
    return _sum_payments(
        db,
        models.Pago.tenant_id == tenant_id,
        models.Pago.fiscal_document_id.is_(None),
        models.Pago.source_quote_id == source_quote_id,
        models.Pago.tipo == "pago",
    )


def get_fiscal_document_balance(
    db: Session,
    tenant_id: int,
    fiscal_document_id: int,
) -> FiscalDocumentBalance:
    fiscal_document = _get_accepted_fiscal_document(db, tenant_id, fiscal_document_id)

    document_total = _money(fiscal_document.total_venta)
    credit_notes_total = _sum_accepted_notes(
        db,
        tenant_id=tenant_id,
        fiscal_document_id=fiscal_document.id,
        document_kind=DOCUMENT_KIND_CREDIT_NOTE,
    )
    debit_notes_total = _sum_accepted_notes(
        db,
        tenant_id=tenant_id,
        fiscal_document_id=fiscal_document.id,
        document_kind=DOCUMENT_KIND_DEBIT_NOTE,
    )
    primary_payments_total = _sum_primary_payments(
        db,
        tenant_id=tenant_id,
        fiscal_document_id=fiscal_document.id,
    )
    legacy_payments_total = _sum_legacy_source_quote_payments(
        db,
        tenant_id=tenant_id,
        source_quote_id=fiscal_document.source_quote_id,
    )

    payments_total = primary_payments_total + legacy_payments_total
    net_total = document_total - credit_notes_total + debit_notes_total
    credit_note_available_amount = max(net_total, _ZERO)

    return FiscalDocumentBalance(
        tenant_id=tenant_id,
        fiscal_document_id=fiscal_document.id,
        source_quote_id=fiscal_document.source_quote_id,
        document_total=document_total,
        credit_notes_total=credit_notes_total,
        debit_notes_total=debit_notes_total,
        payments_total=payments_total,
        primary_payments_total=primary_payments_total,
        legacy_payments_total=legacy_payments_total,
        net_total=net_total,
        saldo_pendiente=net_total - payments_total,
        credit_note_available_amount=credit_note_available_amount,
    )


def get_credit_note_available_amount(
    db: Session,
    tenant_id: int,
    fiscal_document_id: int,
) -> Decimal:
    return get_fiscal_document_balance(
        db,
        tenant_id,
        fiscal_document_id,
    ).credit_note_available_amount


def ensure_credit_note_within_available_amount(
    db: Session,
    tenant_id: int,
    note_id: int,
) -> Decimal:
    """Revalida una nota de credito antes de emitirla o aceptarla."""
    note_probe = (
        db.query(models.Cotizacion)
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.id == note_id,
        )
        .first()
    )
    if not note_probe:
        raise ValueError("Nota fiscal no encontrada para el tenant.")

    is_credit_note = (
        note_probe.document_kind == DOCUMENT_KIND_CREDIT_NOTE
        or note_probe.tipo_comprobante == "07"
    )
    if not is_credit_note:
        return _ZERO

    if not note_probe.nota_referencia_id:
        raise ValueError("La nota de credito no tiene documento afectado.")

    fiscal_document = (
        db.query(models.Cotizacion)
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.id == note_probe.nota_referencia_id,
            models.Cotizacion.document_kind == DOCUMENT_KIND_FISCAL_DOCUMENT,
            models.Cotizacion.estado == DOCUMENT_STATUS_ISSUED,
            models.Cotizacion.tipo_comprobante.in_(("01", "03")),
        )
        .with_for_update()
        .first()
    )
    if not fiscal_document:
        raise ValueError("Documento fiscal afectado aceptado no encontrado para el tenant.")

    note = (
        db.query(models.Cotizacion)
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.id == note_id,
        )
        .with_for_update()
        .first()
    )
    if not note:
        raise ValueError("Nota fiscal no encontrada para el tenant.")

    accepted_credit_notes_total = _sum_money(
        db,
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.nota_referencia_id == fiscal_document.id,
        models.Cotizacion.document_kind == DOCUMENT_KIND_CREDIT_NOTE,
        models.Cotizacion.estado == DOCUMENT_STATUS_ISSUED,
        models.Cotizacion.id != note.id,
    )
    accepted_debit_notes_total = _sum_accepted_notes(
        db,
        tenant_id=tenant_id,
        fiscal_document_id=fiscal_document.id,
        document_kind=DOCUMENT_KIND_DEBIT_NOTE,
    )
    available = max(
        _money(fiscal_document.total_venta)
        - accepted_credit_notes_total
        + accepted_debit_notes_total,
        _ZERO,
    )
    note_total = _money(note.total_venta)
    if note_total > available:
        raise ValueError(
            "La nota de credito excede el monto fiscal disponible "
            f"al momento de emision ({available})."
        )
    return available
