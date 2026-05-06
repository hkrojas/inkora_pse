"""Add scalable lookup indexes for Smart PSE GRE operations."""
from __future__ import annotations

from alembic import op


revision = "0005_smartpse_scale_indexes"
down_revision = "0004_smartpse_gre_credentials"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_tenants_scale_lookup",
        "tenants",
        ["id", "business_ruc", "is_active", "smartpse_gre_status"],
        unique=False,
    )
    op.create_index(
        "ix_guias_remision_tenant_estado_fecha",
        "guias_remision",
        ["tenant_id", "estado", "fecha_emision"],
        unique=False,
    )
    op.create_index(
        "ix_guias_remision_tenant_sunat_ticket",
        "guias_remision",
        ["tenant_id", "sunat_ticket"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_guias_remision_tenant_sunat_ticket", table_name="guias_remision")
    op.drop_index("ix_guias_remision_tenant_estado_fecha", table_name="guias_remision")
    op.drop_index("ix_tenants_scale_lookup", table_name="tenants")
