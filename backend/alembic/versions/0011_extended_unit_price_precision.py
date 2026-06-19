"""Allow extended unit price precision."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0011_extended_unit_price_precision"
down_revision = "0010_quote_wallet_selection"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "cotizacion_items",
        "precio_unitario",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Numeric(18, 4),
        existing_nullable=True,
    )
    op.alter_column(
        "cotizacion_items",
        "valor_unitario",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Numeric(18, 10),
        existing_nullable=True,
    )
    op.alter_column(
        "productos",
        "precio_unitario",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Numeric(18, 4),
        existing_nullable=True,
    )
    op.alter_column(
        "productos",
        "valor_unitario",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Numeric(18, 10),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "productos",
        "valor_unitario",
        existing_type=sa.Numeric(18, 10),
        type_=sa.Numeric(12, 2),
        existing_nullable=True,
    )
    op.alter_column(
        "productos",
        "precio_unitario",
        existing_type=sa.Numeric(18, 4),
        type_=sa.Numeric(12, 2),
        existing_nullable=True,
    )
    op.alter_column(
        "cotizacion_items",
        "valor_unitario",
        existing_type=sa.Numeric(18, 10),
        type_=sa.Numeric(12, 2),
        existing_nullable=True,
    )
    op.alter_column(
        "cotizacion_items",
        "precio_unitario",
        existing_type=sa.Numeric(18, 4),
        type_=sa.Numeric(12, 2),
        existing_nullable=True,
    )
