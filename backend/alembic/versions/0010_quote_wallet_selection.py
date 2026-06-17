"""Persist quote wallet selection metadata."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0010_quote_wallet_selection"
down_revision = "0009_quote_payment_methods"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tenants", sa.Column("quote_default_wallet_id", sa.String(), nullable=True))
    op.add_column("cotizaciones", sa.Column("quote_selected_wallet_id", sa.String(), nullable=True))


def downgrade():
    op.drop_column("cotizaciones", "quote_selected_wallet_id")
    op.drop_column("tenants", "quote_default_wallet_id")
