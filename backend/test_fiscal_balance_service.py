from datetime import datetime
from decimal import Decimal

import pytest

import models
from conftest import make_cliente, make_cotizacion, make_tenant, make_user
from services.document_flow_service import (
    DOCUMENT_KIND_CREDIT_NOTE,
    DOCUMENT_KIND_DEBIT_NOTE,
    DOCUMENT_KIND_FISCAL_DOCUMENT,
    DOCUMENT_KIND_QUOTATION,
    DOCUMENT_STATUS_ISSUED,
    DOCUMENT_STATUS_PENDING,
)
from services.fiscal_balance_service import (
    get_credit_note_available_amount,
    get_fiscal_document_balance,
)


def _make_document(
    db_session,
    *,
    tenant,
    user,
    cliente,
    serie: str,
    correlativo: int,
    document_kind: str,
    tipo_comprobante: str,
    estado: str,
    total: str,
    source_quote_id: int | None = None,
    nota_referencia_id: int | None = None,
) -> models.Cotizacion:
    doc = models.Cotizacion(
        tenant_id=tenant.id,
        cliente_id=cliente.id,
        usuario_id=user.id,
        serie=serie,
        correlativo=correlativo,
        fecha_emision=datetime(2026, 4, 15, 10, 0, 0),
        document_kind=document_kind,
        tipo_comprobante=tipo_comprobante,
        estado=estado,
        source_quote_id=source_quote_id,
        nota_referencia_id=nota_referencia_id,
        total_gravada=Decimal(total),
        total_exonerada=Decimal("0.00"),
        total_inafecta=Decimal("0.00"),
        total_igv=Decimal("0.00"),
        total_venta=Decimal(total),
        monto_pagado=Decimal("0.00"),
        saldo_pendiente=Decimal(total),
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


def _make_payment(
    db_session,
    *,
    tenant,
    cotizacion_id: int,
    amount: str,
    source_quote_id: int | None = None,
    fiscal_document_id: int | None = None,
    tipo: str = "pago",
) -> models.Pago:
    payment = models.Pago(
        tenant_id=tenant.id,
        cotizacion_id=cotizacion_id,
        source_quote_id=source_quote_id,
        fiscal_document_id=fiscal_document_id,
        monto_pagado=Decimal(amount),
        metodo_pago="Transferencia",
        fecha_pago=datetime(2026, 4, 16, 10, 0, 0),
        tipo=tipo,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    return payment


def test_fiscal_document_balance_uses_accepted_notes_and_linked_payments(db_session):
    tenant = make_tenant(db_session, "FBS01")
    user = make_user(db_session, tenant, email="fbs01@test.com")
    cliente = make_cliente(db_session, tenant, "FBS01")
    quote = make_cotizacion(
        db_session,
        tenant,
        user,
        cliente,
        total="1000.00",
        document_kind=DOCUMENT_KIND_QUOTATION,
    )
    fiscal = _make_document(
        db_session,
        tenant=tenant,
        user=user,
        cliente=cliente,
        serie="F001",
        correlativo=1,
        document_kind=DOCUMENT_KIND_FISCAL_DOCUMENT,
        tipo_comprobante="01",
        estado=DOCUMENT_STATUS_ISSUED,
        total="1000.00",
        source_quote_id=quote.id,
    )
    _make_document(
        db_session,
        tenant=tenant,
        user=user,
        cliente=cliente,
        serie="NC01",
        correlativo=1,
        document_kind=DOCUMENT_KIND_CREDIT_NOTE,
        tipo_comprobante="07",
        estado=DOCUMENT_STATUS_ISSUED,
        total="118.00",
        source_quote_id=quote.id,
        nota_referencia_id=fiscal.id,
    )
    _make_document(
        db_session,
        tenant=tenant,
        user=user,
        cliente=cliente,
        serie="NC01",
        correlativo=2,
        document_kind=DOCUMENT_KIND_CREDIT_NOTE,
        tipo_comprobante="07",
        estado="rechazada",
        total="200.00",
        source_quote_id=quote.id,
        nota_referencia_id=fiscal.id,
    )
    _make_document(
        db_session,
        tenant=tenant,
        user=user,
        cliente=cliente,
        serie="ND01",
        correlativo=1,
        document_kind=DOCUMENT_KIND_DEBIT_NOTE,
        tipo_comprobante="08",
        estado=DOCUMENT_STATUS_ISSUED,
        total="59.00",
        source_quote_id=quote.id,
        nota_referencia_id=fiscal.id,
    )
    _make_payment(
        db_session,
        tenant=tenant,
        cotizacion_id=quote.id,
        source_quote_id=quote.id,
        fiscal_document_id=fiscal.id,
        amount="200.00",
    )
    _make_payment(
        db_session,
        tenant=tenant,
        cotizacion_id=quote.id,
        source_quote_id=quote.id,
        fiscal_document_id=None,
        amount="50.00",
    )

    balance = get_fiscal_document_balance(db_session, tenant.id, fiscal.id)

    assert balance.document_total == Decimal("1000.00")
    assert balance.credit_notes_total == Decimal("118.00")
    assert balance.debit_notes_total == Decimal("59.00")
    assert balance.primary_payments_total == Decimal("200.00")
    assert balance.legacy_payments_total == Decimal("50.00")
    assert balance.payments_total == Decimal("250.00")
    assert balance.net_total == Decimal("941.00")
    assert balance.saldo_pendiente == Decimal("691.00")
    assert balance.credit_note_available_amount == Decimal("941.00")
    assert get_credit_note_available_amount(db_session, tenant.id, fiscal.id) == Decimal("941.00")


def test_fiscal_document_balance_is_tenant_scoped_and_ignores_other_tenant_data(db_session):
    tenant = make_tenant(db_session, "FBS02")
    other_tenant = make_tenant(db_session, "FBS03")
    user = make_user(db_session, tenant, email="fbs02@test.com")
    other_user = make_user(db_session, other_tenant, email="fbs03@test.com")
    cliente = make_cliente(db_session, tenant, "FBS02")
    other_cliente = make_cliente(db_session, other_tenant, "FBS03")
    quote = make_cotizacion(db_session, tenant, user, cliente, total="500.00")
    fiscal = _make_document(
        db_session,
        tenant=tenant,
        user=user,
        cliente=cliente,
        serie="F002",
        correlativo=1,
        document_kind=DOCUMENT_KIND_FISCAL_DOCUMENT,
        tipo_comprobante="01",
        estado=DOCUMENT_STATUS_ISSUED,
        total="500.00",
        source_quote_id=quote.id,
    )
    _make_document(
        db_session,
        tenant=other_tenant,
        user=other_user,
        cliente=other_cliente,
        serie="NC02",
        correlativo=1,
        document_kind=DOCUMENT_KIND_CREDIT_NOTE,
        tipo_comprobante="07",
        estado=DOCUMENT_STATUS_ISSUED,
        total="499.00",
        nota_referencia_id=fiscal.id,
    )
    _make_payment(
        db_session,
        tenant=other_tenant,
        cotizacion_id=fiscal.id,
        fiscal_document_id=fiscal.id,
        amount="300.00",
    )

    balance = get_fiscal_document_balance(db_session, tenant.id, fiscal.id)

    assert balance.credit_notes_total == Decimal("0.00")
    assert balance.payments_total == Decimal("0.00")
    assert balance.saldo_pendiente == Decimal("500.00")

    with pytest.raises(ValueError, match="Documento fiscal aceptado"):
        get_fiscal_document_balance(db_session, other_tenant.id, fiscal.id)


def test_fiscal_document_balance_rejects_non_accepted_or_non_fiscal_documents(db_session):
    tenant = make_tenant(db_session, "FBS04")
    user = make_user(db_session, tenant, email="fbs04@test.com")
    cliente = make_cliente(db_session, tenant, "FBS04")
    pending_fiscal = _make_document(
        db_session,
        tenant=tenant,
        user=user,
        cliente=cliente,
        serie="F004",
        correlativo=1,
        document_kind=DOCUMENT_KIND_FISCAL_DOCUMENT,
        tipo_comprobante="01",
        estado=DOCUMENT_STATUS_PENDING,
        total="100.00",
    )
    quote = make_cotizacion(
        db_session,
        tenant,
        user,
        cliente,
        total="100.00",
        document_kind=DOCUMENT_KIND_QUOTATION,
    )

    with pytest.raises(ValueError, match="Documento fiscal aceptado"):
        get_fiscal_document_balance(db_session, tenant.id, pending_fiscal.id)
    with pytest.raises(ValueError, match="Documento fiscal aceptado"):
        get_fiscal_document_balance(db_session, tenant.id, quote.id)


def test_legacy_source_quote_fallback_does_not_override_fiscal_document_id(db_session):
    tenant = make_tenant(db_session, "FBS05")
    user = make_user(db_session, tenant, email="fbs05@test.com")
    cliente = make_cliente(db_session, tenant, "FBS05")
    quote = make_cotizacion(db_session, tenant, user, cliente, total="300.00")
    fiscal = _make_document(
        db_session,
        tenant=tenant,
        user=user,
        cliente=cliente,
        serie="F005",
        correlativo=1,
        document_kind=DOCUMENT_KIND_FISCAL_DOCUMENT,
        tipo_comprobante="01",
        estado=DOCUMENT_STATUS_ISSUED,
        total="300.00",
        source_quote_id=quote.id,
    )
    other_fiscal = _make_document(
        db_session,
        tenant=tenant,
        user=user,
        cliente=cliente,
        serie="F006",
        correlativo=1,
        document_kind=DOCUMENT_KIND_FISCAL_DOCUMENT,
        tipo_comprobante="01",
        estado=DOCUMENT_STATUS_ISSUED,
        total="300.00",
        source_quote_id=quote.id,
    )
    _make_payment(
        db_session,
        tenant=tenant,
        cotizacion_id=quote.id,
        source_quote_id=quote.id,
        fiscal_document_id=other_fiscal.id,
        amount="75.00",
    )
    _make_payment(
        db_session,
        tenant=tenant,
        cotizacion_id=quote.id,
        source_quote_id=quote.id,
        fiscal_document_id=None,
        amount="25.00",
    )

    balance = get_fiscal_document_balance(db_session, tenant.id, fiscal.id)

    assert balance.primary_payments_total == Decimal("0.00")
    assert balance.legacy_payments_total == Decimal("25.00")
    assert balance.payments_total == Decimal("25.00")
    assert balance.saldo_pendiente == Decimal("275.00")


def test_prefiscal_advances_are_not_counted_by_legacy_source_quote_fallback(db_session):
    tenant = make_tenant(db_session, "FBS06")
    user = make_user(db_session, tenant, email="fbs06@test.com")
    cliente = make_cliente(db_session, tenant, "FBS06")
    quote = make_cotizacion(db_session, tenant, user, cliente, total="300.00")
    fiscal = _make_document(
        db_session,
        tenant=tenant,
        user=user,
        cliente=cliente,
        serie="F007",
        correlativo=1,
        document_kind=DOCUMENT_KIND_FISCAL_DOCUMENT,
        tipo_comprobante="01",
        estado=DOCUMENT_STATUS_ISSUED,
        total="300.00",
        source_quote_id=quote.id,
    )
    _make_payment(
        db_session,
        tenant=tenant,
        cotizacion_id=quote.id,
        source_quote_id=quote.id,
        fiscal_document_id=None,
        amount="80.00",
        tipo="adelanto",
    )
    _make_payment(
        db_session,
        tenant=tenant,
        cotizacion_id=quote.id,
        source_quote_id=quote.id,
        fiscal_document_id=None,
        amount="25.00",
        tipo="pago",
    )

    balance = get_fiscal_document_balance(db_session, tenant.id, fiscal.id)

    assert balance.legacy_payments_total == Decimal("25.00")
    assert balance.payments_total == Decimal("25.00")
    assert balance.saldo_pendiente == Decimal("275.00")
