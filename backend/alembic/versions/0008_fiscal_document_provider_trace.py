"""Add fiscal document provider trace fields."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0008_fiscal_doc_provider_trace"
down_revision = "0007_quote_wallet_selection"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cotizaciones", sa.Column("sunat_cdr_content", sa.Text(), nullable=True))
    op.add_column("cotizaciones", sa.Column("provider_response", sa.JSON(), nullable=True))
    op.add_column("cotizaciones", sa.Column("provider_endpoint", sa.String(), nullable=True))
    op.add_column("cotizaciones", sa.Column("provider_status_code", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("cotizaciones", "provider_status_code")
    op.drop_column("cotizaciones", "provider_endpoint")
    op.drop_column("cotizaciones", "provider_response")
    op.drop_column("cotizaciones", "sunat_cdr_content")
