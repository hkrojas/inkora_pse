"""Add tenant-owned production series for electronic transport guides.

Revision ID: 0023_tenant_gre_series
Revises: 0022_gre_sales_documents
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0023_tenant_gre_series"
down_revision = "0022_gre_sales_documents"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tenants") as batch:
        batch.add_column(sa.Column("fiscal_gre_remitente_series", sa.String(length=4), nullable=True))
        batch.add_column(sa.Column("fiscal_gre_remitente_series_floor", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("fiscal_gre_transportista_series", sa.String(length=4), nullable=True))
        batch.add_column(sa.Column("fiscal_gre_transportista_series_floor", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("tenants") as batch:
        batch.drop_column("fiscal_gre_transportista_series_floor")
        batch.drop_column("fiscal_gre_transportista_series")
        batch.drop_column("fiscal_gre_remitente_series_floor")
        batch.drop_column("fiscal_gre_remitente_series")
