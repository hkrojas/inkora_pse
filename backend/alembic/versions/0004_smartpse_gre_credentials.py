"""Add Smart PSE GRE credentials and guide fiscal artifacts."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_smartpse_gre_credentials"
down_revision = "0003_smartpse_credentials"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tenants", sa.Column("smartpse_gre_sol_username", sa.String(), nullable=True))
    op.add_column("tenants", sa.Column("smartpse_gre_sol_password_enc", sa.Text(), nullable=True))
    op.add_column("tenants", sa.Column("smartpse_gre_client_id", sa.String(), nullable=True))
    op.add_column("tenants", sa.Column("smartpse_gre_client_secret_enc", sa.Text(), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("smartpse_gre_status", sa.String(), nullable=True, server_default="unchecked"),
    )
    op.add_column("tenants", sa.Column("smartpse_gre_checked_at", sa.DateTime(), nullable=True))

    op.add_column("guias_remision", sa.Column("sunat_xml_content", sa.Text(), nullable=True))
    op.add_column("guias_remision", sa.Column("sunat_hash", sa.String(), nullable=True))
    op.add_column("guias_remision", sa.Column("sunat_ticket", sa.String(), nullable=True))
    op.add_column("guias_remision", sa.Column("provider_response", sa.JSON(), nullable=True))
    op.add_column("guias_remision", sa.Column("provider_endpoint", sa.String(), nullable=True))
    op.add_column("guias_remision", sa.Column("provider_status_code", sa.Integer(), nullable=True))
    op.add_column("guias_remision", sa.Column("sunat_status_checked_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("guias_remision", "sunat_status_checked_at")
    op.drop_column("guias_remision", "provider_status_code")
    op.drop_column("guias_remision", "provider_endpoint")
    op.drop_column("guias_remision", "provider_response")
    op.drop_column("guias_remision", "sunat_ticket")
    op.drop_column("guias_remision", "sunat_hash")
    op.drop_column("guias_remision", "sunat_xml_content")

    op.drop_column("tenants", "smartpse_gre_checked_at")
    op.drop_column("tenants", "smartpse_gre_status")
    op.drop_column("tenants", "smartpse_gre_client_secret_enc")
    op.drop_column("tenants", "smartpse_gre_client_id")
    op.drop_column("tenants", "smartpse_gre_sol_password_enc")
    op.drop_column("tenants", "smartpse_gre_sol_username")
