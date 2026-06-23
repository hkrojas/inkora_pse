"""Persist fiscal provider verification and artifact status."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0012_fiscal_provider_evidence"
down_revision = "0011_extended_unit_price_precision"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cotizaciones", sa.Column("provider_document_name", sa.String(), nullable=True))
    op.add_column("cotizaciones", sa.Column("provider_verified_at", sa.DateTime(), nullable=True))
    op.add_column("cotizaciones", sa.Column("provider_verification_status", sa.String(), nullable=True))
    op.add_column("cotizaciones", sa.Column("cdr_artifact_status", sa.String(), nullable=True))
    op.add_column("cotizaciones", sa.Column("pdf_artifact_status", sa.String(), nullable=True))


def downgrade():
    op.drop_column("cotizaciones", "pdf_artifact_status")
    op.drop_column("cotizaciones", "cdr_artifact_status")
    op.drop_column("cotizaciones", "provider_verification_status")
    op.drop_column("cotizaciones", "provider_verified_at")
    op.drop_column("cotizaciones", "provider_document_name")
