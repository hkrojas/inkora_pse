"""Persist Smart PSE company management state."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0007_smartpse_company_mgmt"
down_revision = "0006_prod_security_perf"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tenants", sa.Column("smartpse_remote_active", sa.Boolean(), nullable=True))
    op.add_column("tenants", sa.Column("smartpse_remote_estado", sa.String(), nullable=True))
    op.add_column("tenants", sa.Column("smartpse_remote_synced_at", sa.DateTime(), nullable=True))
    op.add_column("tenants", sa.Column("smartpse_start_date", sa.DateTime(), nullable=True))
    op.add_column("tenants", sa.Column("smartpse_end_date", sa.DateTime(), nullable=True))
    op.add_column("tenants", sa.Column("smartpse_firmas_usadas", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("tenants", "smartpse_firmas_usadas")
    op.drop_column("tenants", "smartpse_end_date")
    op.drop_column("tenants", "smartpse_start_date")
    op.drop_column("tenants", "smartpse_remote_synced_at")
    op.drop_column("tenants", "smartpse_remote_estado")
    op.drop_column("tenants", "smartpse_remote_active")
