"""Concurrency contracts for internal transfers on an isolated PostgreSQL database."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
import os
from threading import Barrier

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

import models
from conftest import make_producto, make_tenant, make_user
from database import Base
from schemas.internal_transfers import (
    EstablishmentCreate,
    EstablishmentVerify,
    InternalTransferCreate,
    InternalTransferDispatchCreate,
    InternalTransferDispatchLineCreate,
    InternalTransferLineCreate,
)
from schemas.inventory import ProductInventoryConfig, WarehouseCreate
from services import internal_transfer_service, inventory_service


def _postgres_url():
    value = os.getenv("INKORA_TEST_POSTGRES_URL", "").strip()
    required = os.getenv("INKORA_REQUIRE_POSTGRES_TESTS") == "1"
    if not value:
        if required:
            pytest.fail("INKORA_TEST_POSTGRES_URL es obligatoria para la homologación PostgreSQL")
        pytest.skip("PostgreSQL interno no configurado")
    parsed = make_url(value)
    if not parsed.drivername.startswith("postgresql"):
        pytest.fail("INKORA_TEST_POSTGRES_URL debe usar PostgreSQL")
    if parsed.host not in {"127.0.0.1", "localhost", "::1"}:
        pytest.fail("La suite destructiva solo admite PostgreSQL local aislado")
    if not (parsed.database or "").startswith("inkora_gre_"):
        pytest.fail("La base desechable debe comenzar con inkora_gre_")
    return value


@pytest.fixture(scope="module")
def pg_factory():
    engine = create_engine(_postgres_url(), pool_pre_ping=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    try:
        yield factory
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def _setup(factory, suffix):
    with factory() as db:
        tenant = make_tenant(db, suffix)
        user = make_user(db, tenant, email=f"internal-{suffix}@postgres.test")
        tenant.inventory_enabled = True
        source = internal_transfer_service.create_establishment(db, tenant.id, user.id, EstablishmentCreate(
            sunat_code="0000", name="Principal", ubigeo="150101", address="Av. Principal 100", is_main=True,
        ))
        destination = internal_transfer_service.create_establishment(db, tenant.id, user.id, EstablishmentCreate(
            sunat_code="0001", name="Sucursal", ubigeo="150132", address="Av. Sucursal 200",
        ))
        for row in (source, destination):
            internal_transfer_service.verify_establishment(
                db, tenant.id, row.id, user.id,
                EstablishmentVerify(note="Contrastado con establecimientos SUNAT"),
            )
        source_wh = inventory_service.create_warehouse(db, tenant.id, WarehouseCreate(
            code="ORIGEN", name="Origen", is_default=True, establishment_id=source.id,
        ))
        destination_wh = inventory_service.create_warehouse(db, tenant.id, WarehouseCreate(
            code="DESTINO", name="Destino", establishment_id=destination.id,
        ))
        product = make_producto(db, tenant, suffix)
        inventory_service.configure_product(db, tenant.id, product.id, ProductInventoryConfig(
            item_type="inventory", inventory_enabled=True, warehouse_id=source_wh.id,
            opening_stock=Decimal("100"), minimum_stock=Decimal("0"),
        ), user.id)
        transfer, _ = internal_transfer_service.create_transfer(db, tenant.id, user.id, InternalTransferCreate(
            source_establishment_id=source.id,
            destination_establishment_id=destination.id,
            source_warehouse_id=source_wh.id,
            destination_warehouse_id=destination_wh.id,
            reason="Reposición concurrente",
            idempotency_key=f"pg-transfer-{suffix}",
            lines=[InternalTransferLineCreate(product_id=product.id, quantity=Decimal("100"))],
        ))
        return tenant.id, user.id, transfer.id, transfer.lines[0].id, source_wh.id, product.id


def _dispatch_payload(line_id, quantity, key):
    return InternalTransferDispatchCreate(
        idempotency_key=key,
        lines=[InternalTransferDispatchLineCreate(transfer_line_id=line_id, quantity=Decimal(quantity))],
    )


def _concurrent(factory, operations):
    barrier = Barrier(len(operations) + 1)

    def execute(operation):
        with factory() as db:
            barrier.wait(timeout=10)
            try:
                return "ok", operation(db)
            except internal_transfer_service.InternalTransferError as exc:
                db.rollback()
                return "domain_error", exc.code
            except Exception as exc:  # pragma: no cover - diagnostic evidence
                db.rollback()
                return "unexpected", f"{type(exc).__name__}: {exc}"

    with ThreadPoolExecutor(max_workers=len(operations)) as pool:
        futures = [pool.submit(execute, operation) for operation in operations]
        barrier.wait(timeout=10)
        return [future.result(timeout=30) for future in futures]


def test_two_simultaneous_reservations_of_60_cannot_overallocate(pg_factory):
    tenant_id, user_id, transfer_id, line_id, warehouse_id, product_id = _setup(pg_factory, "IT601")
    payloads = [_dispatch_payload(line_id, "60", "it-pg-60-a"), _dispatch_payload(line_id, "60", "it-pg-60-b")]
    results = _concurrent(pg_factory, [
        lambda db, payload=payload: internal_transfer_service.create_dispatch(db, tenant_id, transfer_id, user_id, payload)
        for payload in payloads
    ])
    assert sorted(row[0] for row in results) == ["domain_error", "ok"], results
    assert any(row == ("domain_error", "TRANSFER_QUANTITY_EXCEEDED") for row in results)
    with pg_factory() as db:
        balance = inventory_service._balance(db, tenant_id, warehouse_id, product_id, lock=False)
        assert balance.committed == Decimal("60.0000")
        assert balance.on_hand == Decimal("100.0000")


def test_simultaneous_40_and_60_reserve_exact_total(pg_factory):
    tenant_id, user_id, transfer_id, line_id, warehouse_id, product_id = _setup(pg_factory, "IT406")
    payloads = [_dispatch_payload(line_id, "40", "it-pg-40"), _dispatch_payload(line_id, "60", "it-pg-60")]
    results = _concurrent(pg_factory, [
        lambda db, payload=payload: internal_transfer_service.create_dispatch(db, tenant_id, transfer_id, user_id, payload)
        for payload in payloads
    ])
    assert [row[0] for row in results].count("ok") == 2, results
    with pg_factory() as db:
        context = internal_transfer_service.transfer_context(db, tenant_id, transfer_id)
        assert context["lines"][0]["pending_assignment"] == Decimal("0.0000")
        balance = inventory_service._balance(db, tenant_id, warehouse_id, product_id, lock=False)
        assert balance.committed == Decimal("100.0000")
        assert db.query(func.count(models.InventoryMovement.id)).filter(
            models.InventoryMovement.tenant_id == tenant_id,
            models.InventoryMovement.movement_type.in_(["transfer_out", "transfer_in"]),
        ).scalar() == 0


def test_simultaneous_same_idempotency_key_creates_one_dispatch(pg_factory):
    tenant_id, user_id, transfer_id, line_id, _warehouse_id, _product_id = _setup(pg_factory, "ITID1")
    payload = _dispatch_payload(line_id, "25", "it-pg-same-key")
    results = _concurrent(pg_factory, [
        lambda db: internal_transfer_service.create_dispatch(db, tenant_id, transfer_id, user_id, payload),
        lambda db: internal_transfer_service.create_dispatch(db, tenant_id, transfer_id, user_id, payload),
    ])
    assert [row[0] for row in results].count("ok") == 2, results
    assert sorted(row[1][1] for row in results) == [False, True]
    with pg_factory() as db:
        assert db.query(models.InternalTransferDispatch).filter(
            models.InternalTransferDispatch.tenant_id == tenant_id,
            models.InternalTransferDispatch.idempotency_key == payload.idempotency_key,
        ).count() == 1


def test_departure_idempotency_key_cannot_confirm_two_dispatches(pg_factory):
    tenant_id, user_id, transfer_id, line_id, warehouse_id, product_id = _setup(
        pg_factory,
        "ITDEP",
    )
    with pg_factory() as db:
        first, _ = internal_transfer_service.create_dispatch(
            db,
            tenant_id,
            transfer_id,
            user_id,
            _dispatch_payload(line_id, "40", "it-pg-departure-first"),
        )
        second, _ = internal_transfer_service.create_dispatch(
            db,
            tenant_id,
            transfer_id,
            user_id,
            _dispatch_payload(line_id, "60", "it-pg-departure-second"),
        )
        for correlativo, dispatch in enumerate((first, second), start=1):
            db.add(models.GuiaRemision(
                tenant_id=tenant_id,
                usuario_id=user_id,
                internal_transfer_dispatch_id=dispatch.id,
                tipo_documento="09",
                serie="TI01",
                correlativo=correlativo,
                fecha_emision=datetime.now(),
                estado="emitida",
                motivo_traslado="04",
                modalidad_traslado="02",
            ))
        db.commit()
        dispatch_ids = (first.id, second.id)

    shared_key = "it-pg-shared-departure-key"
    results = _concurrent(pg_factory, [
        lambda db, dispatch_id=dispatch_id: internal_transfer_service.confirm_departure(
            db,
            tenant_id,
            dispatch_id,
            user_id,
            shared_key,
        )
        for dispatch_id in dispatch_ids
    ])

    assert sorted(row[0] for row in results) == ["domain_error", "ok"], results
    assert any(row == ("domain_error", "IDEMPOTENCY_CONFLICT") for row in results)
    with pg_factory() as db:
        departed = db.query(models.InternalTransferDispatch).filter(
            models.InternalTransferDispatch.id.in_(dispatch_ids),
            models.InternalTransferDispatch.departure_confirmed_at.is_not(None),
        ).count()
        movements = db.query(models.InventoryMovement).filter(
            models.InventoryMovement.tenant_id == tenant_id,
            models.InventoryMovement.source_type == "internal_transfer_dispatch",
        ).count()
        balance = inventory_service._balance(
            db,
            tenant_id,
            warehouse_id,
            product_id,
            lock=False,
        )
        assert departed == 1
        assert movements == 1
        assert balance.on_hand in {Decimal("40.0000"), Decimal("60.0000")}
