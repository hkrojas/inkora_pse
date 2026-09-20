"""Focused contract test for the additive tenant GRE-series migration."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def _load_migration():
    path = Path(__file__).parent / "alembic" / "versions" / "0023_tenant_gre_series_configuration.py"
    spec = importlib.util.spec_from_file_location("migration_0023_tenant_gre_series", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_0023_adds_nullable_gre_series_without_changing_existing_tenants():
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    sa.Table(
        "tenants",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("business_name", sa.String, nullable=False),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(sa.text("INSERT INTO tenants (id, business_name) VALUES (1, 'Empresa')"))
        migration = _load_migration()
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()

        row = connection.execute(sa.text(
            "SELECT fiscal_gre_remitente_series, fiscal_gre_remitente_series_floor, "
            "fiscal_gre_transportista_series, fiscal_gre_transportista_series_floor "
            "FROM tenants WHERE id = 1"
        )).mappings().one()
        assert set(row.values()) == {None}

        columns = {column["name"] for column in sa.inspect(connection).get_columns("tenants")}
        assert {
            "fiscal_gre_remitente_series",
            "fiscal_gre_remitente_series_floor",
            "fiscal_gre_transportista_series",
            "fiscal_gre_transportista_series_floor",
        } <= columns


def test_0023_revision_fits_production_alembic_version_column():
    migration = _load_migration()

    assert len(migration.revision) <= 32
    assert migration.down_revision == "0022_gre_sales_documents"
