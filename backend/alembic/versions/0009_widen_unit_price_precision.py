"""Widen precio_unitario, valor_unitario and cantidad to 4 decimal places.

SUNAT UBL 2.1 allows high-precision unit prices (PriceAmount up to 10 decimals).
Storing at least 4 decimals prevents premature rounding that causes large
discrepancies when multiplied by high quantities (e.g. 0.365 × 1000).

Totals (total_base_igv, total_igv, total_item, total_venta, etc.) remain at
Numeric(12, 2) because SUNAT requires 2-decimal totals.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0009_widen_unit_price_precision"
down_revision = "0008_fiscal_doc_provider_trace"
branch_labels = None
depends_on = None


def upgrade():
    # -- productos --
    op.alter_column(
        "productos",
        "precio_unitario",
        type_=sa.Numeric(12, 4),
        existing_type=sa.Numeric(12, 2),
        existing_nullable=True,
    )
    op.alter_column(
        "productos",
        "valor_unitario",
        type_=sa.Numeric(12, 4),
        existing_type=sa.Numeric(12, 2),
        existing_nullable=True,
    )

    # -- cotizacion_items --
    op.alter_column(
        "cotizacion_items",
        "cantidad",
        type_=sa.Numeric(12, 4),
        existing_type=sa.Numeric(12, 2),
        existing_nullable=True,
    )
    op.alter_column(
        "cotizacion_items",
        "precio_unitario",
        type_=sa.Numeric(12, 4),
        existing_type=sa.Numeric(12, 2),
        existing_nullable=True,
    )
    op.alter_column(
        "cotizacion_items",
        "valor_unitario",
        type_=sa.Numeric(12, 4),
        existing_type=sa.Numeric(12, 2),
        existing_nullable=True,
    )


def downgrade():
    # Revert to 2 decimal places (may truncate data)
    op.alter_column(
        "cotizacion_items",
        "valor_unitario",
        type_=sa.Numeric(12, 2),
        existing_type=sa.Numeric(12, 4),
        existing_nullable=True,
    )
    op.alter_column(
        "cotizacion_items",
        "precio_unitario",
        type_=sa.Numeric(12, 2),
        existing_type=sa.Numeric(12, 4),
        existing_nullable=True,
    )
    op.alter_column(
        "cotizacion_items",
        "cantidad",
        type_=sa.Numeric(12, 2),
        existing_type=sa.Numeric(12, 4),
        existing_nullable=True,
    )
    op.alter_column(
        "productos",
        "valor_unitario",
        type_=sa.Numeric(12, 2),
        existing_type=sa.Numeric(12, 4),
        existing_nullable=True,
    )
    op.alter_column(
        "productos",
        "precio_unitario",
        type_=sa.Numeric(12, 2),
        existing_type=sa.Numeric(12, 4),
        existing_nullable=True,
    )
