"""Persist per-tenant production fiscal series and remote floors."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0013_tenant_fiscal_series_configuration"
down_revision = "0012_fiscal_provider_evidence"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tenants", sa.Column("fiscal_invoice_series", sa.String(length=4), nullable=True))
    op.add_column("tenants", sa.Column("fiscal_invoice_series_floor", sa.Integer(), nullable=True))
    op.add_column("tenants", sa.Column("fiscal_boleta_series", sa.String(length=4), nullable=True))
    op.add_column("tenants", sa.Column("fiscal_boleta_series_floor", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("tenants", "fiscal_boleta_series_floor")
    op.drop_column("tenants", "fiscal_boleta_series")
    op.drop_column("tenants", "fiscal_invoice_series_floor")
    op.drop_column("tenants", "fiscal_invoice_series")
