"""Extend sale dispatch GRE traceability to invoices and receipts.

Revision ID: 0022_gre_sales_documents
Revises: 0021_sale_dispatch_guides
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0022_gre_sales_documents"
down_revision = "0021_sale_dispatch_guides"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("sale_dispatches") as batch:
        batch.add_column(sa.Column("source_document_type", sa.String(), nullable=True))
        batch.add_column(sa.Column("source_summary_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("source_acceptance_evidence", sa.JSON(), nullable=True))
        batch.create_foreign_key(
            "fk_sale_dispatches_source_summary",
            "resumenes_diarios",
            ["source_summary_id"],
            ["id"],
        )

    op.execute(
        "UPDATE sale_dispatches "
        "SET source_document_type = ("
        "SELECT cotizaciones.tipo_comprobante FROM cotizaciones "
        "WHERE cotizaciones.id = sale_dispatches.fiscal_document_id"
        ")"
    )
    op.execute(
        "UPDATE sale_dispatches SET source_document_type = '01' "
        "WHERE source_document_type IS NULL"
    )

    with op.batch_alter_table("sale_dispatches") as batch:
        batch.alter_column(
            "source_document_type",
            existing_type=sa.String(),
            nullable=False,
            server_default="01",
        )
        batch.create_check_constraint(
            "ck_sale_dispatches_source_document_type",
            "source_document_type IN ('01', '03')",
        )
        batch.create_index(
            "ix_sale_dispatches_source_summary",
            ["tenant_id", "source_summary_id"],
        )

    with op.batch_alter_table("guias_remision") as batch:
        batch.add_column(sa.Column("observaciones", sa.Text(), nullable=True))
        batch.add_column(sa.Column("transportista_acuerdo_confirmado_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("transportista_acuerdo_confirmado_by_user_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_guias_transportista_acuerdo_user",
            "users",
            ["transportista_acuerdo_confirmado_by_user_id"],
            ["id"],
        )

    # Existing receipt history cannot be assumed to have no prior dispatches.
    op.execute(
        "UPDATE cotizaciones SET dispatch_reconciliation_status = 'required' "
        "WHERE document_kind = 'fiscal_document' AND tipo_comprobante = '03'"
    )


def downgrade():
    with op.batch_alter_table("guias_remision") as batch:
        batch.drop_constraint("fk_guias_transportista_acuerdo_user", type_="foreignkey")
        batch.drop_column("transportista_acuerdo_confirmado_by_user_id")
        batch.drop_column("transportista_acuerdo_confirmado_at")
        batch.drop_column("observaciones")

    with op.batch_alter_table("sale_dispatches") as batch:
        batch.drop_index("ix_sale_dispatches_source_summary")
        batch.drop_constraint("ck_sale_dispatches_source_document_type", type_="check")
        batch.drop_constraint("fk_sale_dispatches_source_summary", type_="foreignkey")
        batch.drop_column("source_acceptance_evidence")
        batch.drop_column("source_summary_id")
        batch.drop_column("source_document_type")

    # Downgrading restores the 0021 behavior: only invoices require reconciliation.
    op.execute(
        "UPDATE cotizaciones SET dispatch_reconciliation_status = 'not_required' "
        "WHERE document_kind = 'fiscal_document' AND tipo_comprobante = '03'"
    )
