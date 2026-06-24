"""Preserve decimal quantity precision in quote line items."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0013_quote_quantity_precision"
down_revision = "0012_fiscal_provider_evidence"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "cotizacion_items",
        "cantidad",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Numeric(18, 4),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "cotizacion_items",
        "cantidad",
        existing_type=sa.Numeric(18, 4),
        type_=sa.Numeric(12, 2),
        existing_nullable=True,
    )
