"""Add Smart PSE provider verification trace fields."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0010_smartpse_provider_verification"
down_revision = "0009_widen_unit_price_precision"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cotizaciones", sa.Column("provider_document_name", sa.String(), nullable=True))
    op.add_column("cotizaciones", sa.Column("provider_verification_status", sa.String(), nullable=True))
    op.add_column("cotizaciones", sa.Column("provider_verified_at", sa.DateTime(), nullable=True))
    op.add_column("cotizaciones", sa.Column("provider_verification_error", sa.Text(), nullable=True))
    op.create_index(
        "ix_cotizaciones_provider_document_name",
        "cotizaciones",
        ["provider_document_name"],
    )
    op.create_index(
        "ix_cotizaciones_provider_verification_status",
        "cotizaciones",
        ["provider_verification_status"],
    )


def downgrade():
    op.drop_index("ix_cotizaciones_provider_verification_status", table_name="cotizaciones")
    op.drop_index("ix_cotizaciones_provider_document_name", table_name="cotizaciones")
    op.drop_column("cotizaciones", "provider_verification_error")
    op.drop_column("cotizaciones", "provider_verified_at")
    op.drop_column("cotizaciones", "provider_verification_status")
    op.drop_column("cotizaciones", "provider_document_name")
