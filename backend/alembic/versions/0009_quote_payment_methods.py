"""Persist selected bank methods snapshot on quotes."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0009_quote_payment_methods"
down_revision = "0008_client_snapshots"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cotizaciones", sa.Column("quote_payment_methods", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("cotizaciones", "quote_payment_methods")
