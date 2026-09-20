"""Concurrencia obligatoria de cotizaciones sobre PostgreSQL aislado."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import os
from threading import Barrier

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

import crud
import models
import schemas
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from database import Base


def _postgres_url() -> str:
    value = os.getenv("INKORA_TEST_POSTGRES_URL", "").strip()
    required = os.getenv("INKORA_REQUIRE_POSTGRES_TESTS") == "1"
    if not value:
        if required:
            pytest.fail("INKORA_TEST_POSTGRES_URL es obligatoria para la homologacion PostgreSQL")
        pytest.skip("PostgreSQL de cotizaciones no configurado")
    parsed = make_url(value)
    if not parsed.drivername.startswith("postgresql"):
        pytest.fail("INKORA_TEST_POSTGRES_URL debe usar PostgreSQL")
    if parsed.host not in {"127.0.0.1", "localhost", "::1"}:
        pytest.fail("La suite destructiva solo admite PostgreSQL local aislado")
    if not (parsed.database or "").startswith("inkora_quote_"):
        pytest.fail("La base desechable debe comenzar con inkora_quote_")
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


def test_edit_and_fiscal_creation_share_the_quote_lock(pg_session_factory):
    with pg_session_factory() as db:
        tenant = make_tenant(db, "QPG01")
        user = make_user(db, tenant, email="quote-concurrency@postgres.test")
        client = make_cliente(db, tenant, "QPG01")
        quote = make_quote_via_crud(db, tenant, user, client)
        tenant_id, user_id, client_id, quote_id = tenant.id, user.id, client.id, quote.id

    update_payload = schemas.CotizacionUpdate(
        cliente_id=client_id,
        moneda="PEN",
        tipo_comprobante="00",
        items=[
            schemas.CotizacionItemCreate(
                descripcion="Version editada",
                cantidad=Decimal("2"),
                precio_unitario=Decimal("118"),
            )
        ],
    )
    barrier = Barrier(3)

    def update_quote():
        with pg_session_factory() as db:
            user = crud.get_user_by_id(db, user_id)
            barrier.wait(timeout=10)
            try:
                result = crud.update_cotizacion(db, quote_id, update_payload, user)
                return "updated", result.total_venta
            except ValueError as exc:
                db.rollback()
                return "blocked", str(exc)

    def create_fiscal():
        with pg_session_factory() as db:
            user = crud.get_user_by_id(db, user_id)
            quote = crud.get_cotizacion(db, quote_id, user)
            barrier.wait(timeout=10)
            fiscal = crud.create_fiscal_document_from_quote(db, quote, user_id, "01")
            return "fiscal", fiscal.id

    with ThreadPoolExecutor(max_workers=2) as pool:
        update_future = pool.submit(update_quote)
        fiscal_future = pool.submit(create_fiscal)
        barrier.wait(timeout=10)
        update_result = update_future.result(timeout=30)
        fiscal_result = fiscal_future.result(timeout=30)

    assert fiscal_result[0] == "fiscal"
    assert update_result[0] in {"updated", "blocked"}

    with pg_session_factory() as db:
        quote = db.query(models.Cotizacion).filter(
            models.Cotizacion.id == quote_id,
            models.Cotizacion.tenant_id == tenant_id,
        ).one()
        fiscal = db.query(models.Cotizacion).filter(
            models.Cotizacion.id == fiscal_result[1],
            models.Cotizacion.tenant_id == tenant_id,
        ).one()
        assert fiscal.source_quote_id == quote_id
        assert fiscal.total_venta == quote.total_venta
        assert fiscal.total_venta in {Decimal("118.00"), Decimal("236.00")}
