"""Add tenant-controlled deferred fiscal contingency mode.

Revision ID: 0020_tenant_fiscal_contingency
Revises: 0019_emission_attempt_history
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0020_tenant_fiscal_contingency"
down_revision = "0019_emission_attempt_history"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "tenants",
        sa.Column(
            "fiscal_contingency_mode",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "tenants",
        sa.Column("fiscal_contingency_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("fiscal_contingency_started_at", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_column("tenants", "fiscal_contingency_started_at")
    op.drop_column("tenants", "fiscal_contingency_reason")
    op.drop_column("tenants", "fiscal_contingency_mode")
