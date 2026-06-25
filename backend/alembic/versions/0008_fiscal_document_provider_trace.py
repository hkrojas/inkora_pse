"""Add fiscal document provider trace fields.

This migration was originally created with a stale down_revision that did not
exist in the deployed Alembic graph. Keep the revision id to preserve history,
but attach it after the current quote precision head.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0008_fiscal_doc_provider_trace"
down_revision = "0013_quote_quantity_precision"
branch_labels = None
depends_on = None


def _existing_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade():
    columns = _existing_columns("cotizaciones")
    if "sunat_cdr_content" not in columns:
        op.add_column("cotizaciones", sa.Column("sunat_cdr_content", sa.Text(), nullable=True))
    if "provider_response" not in columns:
        op.add_column("cotizaciones", sa.Column("provider_response", sa.JSON(), nullable=True))
    if "provider_endpoint" not in columns:
        op.add_column("cotizaciones", sa.Column("provider_endpoint", sa.String(), nullable=True))
    if "provider_status_code" not in columns:
        op.add_column("cotizaciones", sa.Column("provider_status_code", sa.Integer(), nullable=True))


def downgrade():
    columns = _existing_columns("cotizaciones")
    if "provider_status_code" in columns:
        op.drop_column("cotizaciones", "provider_status_code")
    if "provider_endpoint" in columns:
        op.drop_column("cotizaciones", "provider_endpoint")
    if "provider_response" in columns:
        op.drop_column("cotizaciones", "provider_response")
    if "sunat_cdr_content" in columns:
        op.drop_column("cotizaciones", "sunat_cdr_content")
