"""Persist client snapshots on documents."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0008_client_snapshots"
down_revision = "0007_smartpse_company_mgmt"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cotizaciones", sa.Column("cliente_snapshot", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("cotizaciones", "cliente_snapshot")
