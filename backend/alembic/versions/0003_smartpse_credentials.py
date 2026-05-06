"""Add Smart PSE tenant credentials.

Stores per-tenant CPE credentials issued by Smart PSE. The global management
API token remains in environment variables only.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_smartpse_credentials"
down_revision = "0002_beta_feature_flags"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tenants", sa.Column("smartpse_company_id", sa.String(), nullable=True))
    op.add_column("tenants", sa.Column("smartpse_environment", sa.String(), nullable=True, server_default="demo"))
    op.add_column("tenants", sa.Column("smartpse_usuario_secundaria", sa.String(), nullable=True))
    op.add_column("tenants", sa.Column("smartpse_token_acceso", sa.String(), nullable=True))
    op.add_column("tenants", sa.Column("smartpse_status", sa.String(), nullable=True, server_default="unchecked"))
    op.add_column("tenants", sa.Column("smartpse_checked_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("tenants", "smartpse_checked_at")
    op.drop_column("tenants", "smartpse_status")
    op.drop_column("tenants", "smartpse_token_acceso")
    op.drop_column("tenants", "smartpse_usuario_secundaria")
    op.drop_column("tenants", "smartpse_environment")
    op.drop_column("tenants", "smartpse_company_id")
