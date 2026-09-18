"""Pruebas obligatorias de reservas GRE sobre PostgreSQL real.

La ejecución de homologación debe definir:

    INKORA_TEST_POSTGRES_URL=postgresql://.../inkora_gre_test
    INKORA_REQUIRE_POSTGRES_TESTS=1

La base es exclusiva y desechable: el fixture elimina y recrea todas sus tablas.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
from threading import Barrier

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

import crud
import models
import schemas
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from database import Base
from services import sale_dispatch_service


def _postgres_url() -> str:
    value = os.getenv("INKORA_TEST_POSTGRES_URL", "").strip()
    required = os.getenv("INKORA_REQUIRE_POSTGRES_TESTS") == "1"
    if not value:
        if required:
            pytest.fail("INKORA_TEST_POSTGRES_URL es obligatoria para la homologacion PostgreSQL")
        pytest.skip("PostgreSQL GRE no configurado; use INKORA_REQUIRE_POSTGRES_TESTS=1 en homologacion")

    parsed = make_url(value)
    if not parsed.drivername.startswith("postgresql"):
        pytest.fail("INKORA_TEST_POSTGRES_URL debe usar PostgreSQL")
    if parsed.host not in {"127.0.0.1", "localhost", "::1"}:
        pytest.fail("La suite destructiva solo admite una instancia PostgreSQL local aislada")
    if not (parsed.database or "").startswith("inkora_gre_"):
        pytest.fail("La base desechable debe comenzar con inkora_gre_")
    return value


@pytest.fixture(scope="module")
def pg_session_factory():
    engine = create_engine(_postgres_url(), pool_pre_ping=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    try:
        yield factory
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def _accepted_invoice(factory, suffix: str, quantity: Decimal = Decimal("100")):
    with factory() as db:
        tenant = make_tenant(db, suffix)
        user = make_user(db, tenant, email=f"{suffix.lower()}@postgres.test")
        client = make_cliente(db, tenant, suffix)
        quote = make_quote_via_crud(db, tenant, user, client)
        invoice = crud.create_fiscal_document_from_quote(db, quote, user.id, "01")
        invoice.items[0].cantidad = quantity
        invoice.estado = "facturada"
        invoice.sunat_cdr_content = "<ApplicationResponse/>"
        invoice.provider_verification_status = "verified"
        invoice.dispatch_reconciliation_status = "not_required"
        db.commit()
        return tenant.id, user.id, invoice.id, invoice.items[0].id


def _payload(invoice_id: int, line_id: int, quantity: Decimal, key: str):
    return schemas.SaleDispatchFromInvoiceCreate(
        fiscal_document_id=invoice_id,
        idempotency_key=key,
        fecha_traslado=datetime.now(timezone.utc) + timedelta(days=1),
        peso_bruto_total=Decimal("10.000"),
        modalidad_traslado="02",
        partida_ubigeo="150101",
        partida_direccion="Av. Origen 100",
        llegada_ubigeo="150103",
        llegada_direccion="Av. Destino 200",
        vehiculo_placa="ABC123",
        conductor_nro_doc="72758912",
        conductor_nombres="Ana",
        conductor_apellidos="Rojas",
        conductor_licencia="Q12345678",
        lines=[schemas.DispatchLineSelection(
            fiscal_document_item_id=line_id,
            quantity=quantity,
            confirmed_as_goods=True,
        )],
    )


def _run_concurrently(factory, operations):
    barrier = Barrier(len(operations) + 1)

    def execute(operation):
        with factory() as db:
            barrier.wait(timeout=10)
            try:
                return ("ok", operation(db))
            except sale_dispatch_service.DispatchError as exc:
                db.rollback()
                return ("dispatch_error", exc.code)
            except Exception as exc:  # pragma: no cover - diagnostico de homologacion
                db.rollback()
                return ("unexpected", f"{type(exc).__name__}: {exc}")

    with ThreadPoolExecutor(max_workers=len(operations)) as pool:
        futures = [pool.submit(execute, operation) for operation in operations]
        barrier.wait(timeout=10)
        return [future.result(timeout=30) for future in futures]


def test_postgres_two_reservations_of_60_cannot_overallocate(pg_session_factory):
    tenant_id, user_id, invoice_id, line_id = _accepted_invoice(pg_session_factory, "PG601")
    payloads = [
        _payload(invoice_id, line_id, Decimal("60"), "pg-over-0001"),
        _payload(invoice_id, line_id, Decimal("60"), "pg-over-0002"),
    ]
    results = _run_concurrently(pg_session_factory, [
        lambda db, payload=payload: sale_dispatch_service.create_from_invoice(db, tenant_id, user_id, payload)
        for payload in payloads
    ])

    assert sorted(result[0] for result in results) == ["dispatch_error", "ok"], results
    assert any(result == ("dispatch_error", "DISPATCH_QUANTITY_EXCEEDED") for result in results)
    with pg_session_factory() as db:
        reserved = db.query(func.sum(models.SaleDispatchLine.quantity)).filter(
            models.SaleDispatchLine.tenant_id == tenant_id,
            models.SaleDispatchLine.reservation_status == models.DISPATCH_RESERVATION_ACTIVE,
        ).scalar()
        assert reserved == Decimal("60.0000")


def test_postgres_concurrent_40_and_60_reserve_exact_total(pg_session_factory):
    tenant_id, user_id, invoice_id, line_id = _accepted_invoice(pg_session_factory, "PG406")
    payloads = [
        _payload(invoice_id, line_id, Decimal("40"), "pg-split-0001"),
        _payload(invoice_id, line_id, Decimal("60"), "pg-split-0002"),
    ]
    results = _run_concurrently(pg_session_factory, [
        lambda db, payload=payload: sale_dispatch_service.create_from_invoice(db, tenant_id, user_id, payload)
        for payload in payloads
    ])
    assert [result[0] for result in results].count("ok") == 2

    with pg_session_factory() as db:
        context = sale_dispatch_service.get_invoice_dispatch_context(db, tenant_id, invoice_id)
        assert context["lines"][0]["available"] == Decimal("0.0000")


def test_postgres_same_idempotency_key_creates_one_dispatch(pg_session_factory):
    tenant_id, user_id, invoice_id, line_id = _accepted_invoice(pg_session_factory, "PGID1")
    payload = _payload(invoice_id, line_id, Decimal("25"), "pg-idempotency-0001")
    results = _run_concurrently(pg_session_factory, [
        lambda db: sale_dispatch_service.create_from_invoice(db, tenant_id, user_id, payload),
        lambda db: sale_dispatch_service.create_from_invoice(db, tenant_id, user_id, payload),
    ])
    assert [result[0] for result in results].count("ok") == 2
    created_flags = sorted(result[1][1] for result in results)
    assert created_flags == [False, True]

    with pg_session_factory() as db:
        assert db.query(models.SaleDispatch).filter(
            models.SaleDispatch.tenant_id == tenant_id,
            models.SaleDispatch.idempotency_key == payload.idempotency_key,
        ).count() == 1


def test_postgres_edit_and_cancel_are_serialized_without_stock_movement(pg_session_factory):
    tenant_id, user_id, invoice_id, line_id = _accepted_invoice(pg_session_factory, "PGEC1")
    with pg_session_factory() as db:
        dispatch, _ = sale_dispatch_service.create_from_invoice(
            db, tenant_id, user_id, _payload(invoice_id, line_id, Decimal("30"), "pg-edit-cancel-0001")
        )
        dispatch_id = dispatch.id
        version = dispatch.version
        inventory_before = db.query(models.InventoryMovement).filter(
            models.InventoryMovement.tenant_id == tenant_id
        ).count()

    update_data = _payload(invoice_id, line_id, Decimal("20"), "unused-update-key").model_dump()
    update_data.pop("fiscal_document_id")
    update_data.pop("idempotency_key")
    update_data["version"] = version
    update_payload = schemas.SaleDispatchUpdate(**update_data)
    results = _run_concurrently(pg_session_factory, [
        lambda db: sale_dispatch_service.update_dispatch(db, tenant_id, dispatch_id, update_payload),
        lambda db: sale_dispatch_service.cancel_dispatch(db, tenant_id, dispatch_id),
    ])
    assert not any(result[0] == "unexpected" for result in results), results

    with pg_session_factory() as db:
        dispatch = sale_dispatch_service.get_dispatch(db, tenant_id, dispatch_id)
        assert dispatch.status == models.DISPATCH_STATUS_CANCELLED
        assert all(line.reservation_status == models.DISPATCH_RESERVATION_RELEASED for line in dispatch.lines)
        inventory_after = db.query(models.InventoryMovement).filter(
            models.InventoryMovement.tenant_id == tenant_id
        ).count()
        assert inventory_after == inventory_before
