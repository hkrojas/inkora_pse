"""Migration/rollback evidence for revision 0024 on isolated PostgreSQL."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

import models
from conftest import make_tenant, make_user
from database import Base
from schemas.inventory import WarehouseCreate
from services import inventory_service


def _load_migration():
    path = Path(__file__).parent / "alembic" / "versions" / "0024_internal_transfer_gre.py"
    spec = importlib.util.spec_from_file_location("migration_0024_internal_transfer_gre", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _postgres_url():
    value = os.getenv("INKORA_TEST_POSTGRES_URL", "").strip()
    required = os.getenv("INKORA_REQUIRE_POSTGRES_TESTS") == "1"
    if not value:
        if required:
            pytest.fail("INKORA_TEST_POSTGRES_URL es obligatoria para probar la migración 0024")
        pytest.skip("PostgreSQL de migración no configurado")
    parsed = make_url(value)
    if not parsed.drivername.startswith("postgresql") or parsed.host not in {"127.0.0.1", "localhost", "::1"}:
        pytest.fail("La migración destructiva solo admite PostgreSQL local")
    if not (parsed.database or "").startswith("inkora_gre_"):
        pytest.fail("La base desechable debe comenzar con inkora_gre_")
    return value


def _column_names(connection, table):
    return {row["name"] for row in sa.inspect(connection).get_columns(table)}


def _prepare_0023_shape(connection):
    """Remove only 0024 objects from current metadata, preserving legacy data."""
    for table in (
        "internal_transfer_receipt_lines",
        "internal_transfer_receipts",
        "internal_transfer_dispatch_lines",
        "internal_transfer_dispatches",
        "internal_transfer_order_lines",
        "internal_transfer_orders",
        "tenant_establishments",
    ):
        connection.execute(sa.text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
    connection.execute(sa.text("ALTER TABLE guia_remision_items DROP COLUMN IF EXISTS internal_transfer_dispatch_line_id"))
    connection.execute(sa.text("ALTER TABLE guias_remision DROP COLUMN IF EXISTS internal_transfer_dispatch_id"))
    connection.execute(sa.text("ALTER TABLE guias_remision DROP COLUMN IF EXISTS partida_codigo_local"))
    connection.execute(sa.text("ALTER TABLE guias_remision DROP COLUMN IF EXISTS llegada_codigo_local"))
    connection.execute(sa.text("ALTER TABLE warehouses DROP COLUMN IF EXISTS establishment_id"))
    connection.execute(sa.text("ALTER TABLE inventory_transfers DROP COLUMN IF EXISTS lifecycle_mode"))


def test_0024_upgrade_and_rollback_preserve_legacy_transfer():
    engine = sa.create_engine(_postgres_url(), pool_pre_ping=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            tenant = make_tenant(db, "MIG24")
            user = make_user(db, tenant, email="migration-0024@test.pe")
            source = inventory_service.create_warehouse(db, tenant.id, WarehouseCreate(code="MIG-O", name="Origen", is_default=True))
            destination = inventory_service.create_warehouse(db, tenant.id, WarehouseCreate(code="MIG-D", name="Destino"))
            legacy = models.InventoryTransfer(
                tenant_id=tenant.id,
                source_warehouse_id=source.id,
                destination_warehouse_id=destination.id,
                status="completed",
                lifecycle_mode="legacy_immediate",
                reason="Movimiento histórico",
                created_by_user_id=user.id,
            )
            db.add(legacy)
            db.commit()
            legacy_id = legacy.id

        migration = _load_migration()
        with engine.begin() as connection:
            _prepare_0023_shape(connection)
            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()

            assert "lifecycle_mode" in _column_names(connection, "inventory_transfers")
            assert "departure_idempotency_key" in _column_names(
                connection,
                "internal_transfer_dispatches",
            )
            assert {"internal_transfer_orders", "internal_transfer_dispatches", "internal_transfer_receipts"} <= set(sa.inspect(connection).get_table_names())
            establishment_indexes = {
                index["name"]: index
                for index in sa.inspect(connection).get_indexes("tenant_establishments")
            }
            assert establishment_indexes["uq_tenant_establishments_main"]["unique"] is True
            dispatch_constraints = {
                constraint["name"]
                for constraint in sa.inspect(connection).get_unique_constraints(
                    "internal_transfer_dispatches"
                )
            }
            assert "uq_internal_transfer_departure_idempotency" in dispatch_constraints
            row = connection.execute(sa.text(
                "SELECT status, lifecycle_mode, reason FROM inventory_transfers WHERE id = :id"
            ), {"id": legacy_id}).mappings().one()
            assert row == {"status": "completed", "lifecycle_mode": "legacy_immediate", "reason": "Movimiento histórico"}

            migration.downgrade()
            assert "lifecycle_mode" not in _column_names(connection, "inventory_transfers")
            assert connection.execute(sa.text(
                "SELECT count(*) FROM inventory_transfers WHERE id = :id"
            ), {"id": legacy_id}).scalar_one() == 1

            migration.upgrade()
            assert connection.execute(sa.text(
                "SELECT lifecycle_mode FROM inventory_transfers WHERE id = :id"
            ), {"id": legacy_id}).scalar_one() == "legacy_immediate"
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_0024_revision_chain_is_linear_and_fits_alembic_column():
    migration = _load_migration()
    assert migration.down_revision == "0023_tenant_gre_series"
    assert len(migration.revision) <= 32
