"""Focused contract tests for the additive GRE sales-document migration."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from urllib.parse import urlsplit

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def _load_migration():
    path = Path(__file__).parent / "alembic" / "versions" / "0022_gre_sales_documents.py"
    spec = importlib.util.spec_from_file_location("migration_0022_gre_sales_documents", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_0022_adds_traceability_and_blocks_historical_receipts():
    database_url = os.getenv("INKORA_GRE_MIGRATION_TEST_URL", "sqlite://")
    if not database_url.startswith("sqlite"):
        parsed = urlsplit(database_url)
        assert parsed.hostname in {"127.0.0.1", "localhost"}
        assert parsed.path.lstrip("/").startswith("inkora_gre_")
    engine = sa.create_engine(database_url)
    metadata = sa.MetaData()
    sa.Table("tenants", metadata, sa.Column("id", sa.Integer, primary_key=True))
    sa.Table("users", metadata, sa.Column("id", sa.Integer, primary_key=True))
    sa.Table("warehouses", metadata, sa.Column("id", sa.Integer, primary_key=True))
    sa.Table("resumenes_diarios", metadata, sa.Column("id", sa.Integer, primary_key=True))
    sa.Table(
        "cotizaciones",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("document_kind", sa.String, nullable=False),
        sa.Column("tipo_comprobante", sa.String, nullable=False),
        sa.Column("dispatch_reconciliation_status", sa.String, nullable=False),
    )
    sa.Table(
        "sale_dispatches",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("fiscal_document_id", sa.Integer, sa.ForeignKey("cotizaciones.id"), nullable=False),
    )
    sa.Table(
        "guias_remision",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(sa.text("INSERT INTO tenants (id) VALUES (1)"))
        connection.execute(
            sa.text(
                "INSERT INTO cotizaciones "
                "(id, document_kind, tipo_comprobante, dispatch_reconciliation_status) "
                "VALUES (10, 'fiscal_document', '01', 'required'), "
                "(11, 'fiscal_document', '03', 'not_required'), "
                "(12, 'quotation', '00', 'not_required')"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO sale_dispatches (id, tenant_id, fiscal_document_id) "
                "VALUES (20, 1, 10)"
            )
        )

        migration = _load_migration()
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()

        dispatch = connection.execute(
            sa.text(
                "SELECT source_document_type, source_summary_id, source_acceptance_evidence "
                "FROM sale_dispatches WHERE id = 20"
            )
        ).mappings().one()
        assert dispatch["source_document_type"] == "01"
        assert dispatch["source_summary_id"] is None
        assert dispatch["source_acceptance_evidence"] is None

        statuses = dict(
            connection.execute(
                sa.text("SELECT id, dispatch_reconciliation_status FROM cotizaciones")
            ).all()
        )
        assert statuses == {10: "required", 11: "required", 12: "not_required"}

        guide_columns = {column["name"] for column in sa.inspect(connection).get_columns("guias_remision")}
        assert {
            "observaciones",
            "transportista_acuerdo_confirmado_at",
            "transportista_acuerdo_confirmado_by_user_id",
        } <= guide_columns
