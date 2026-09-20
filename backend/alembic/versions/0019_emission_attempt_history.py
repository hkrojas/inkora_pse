"""Add append-only fiscal emission attempt history.

Revision ID: 0019_emission_attempt_history
Revises: 0018_catalog_domain_foundation
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0019_emission_attempt_history"
down_revision = "0018_catalog_domain_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "document_emission_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("document_emission_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_classification", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("provider_endpoint", sa.String(), nullable=True),
        sa.Column("provider_status_code", sa.Integer(), nullable=True),
        sa.Column("result_snapshot", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("job_id", "attempt_number", name="uq_emission_attempt_job_number"),
    )
    op.create_index(
        "ix_document_emission_attempts_job_id",
        "document_emission_attempts",
        ["job_id"],
    )
    op.create_index(
        "ix_document_emission_attempts_tenant_id",
        "document_emission_attempts",
        ["tenant_id"],
    )
    op.create_index(
        "ix_document_emission_attempts_status",
        "document_emission_attempts",
        ["status"],
    )
    op.create_index(
        "ix_document_emission_attempts_error_classification",
        "document_emission_attempts",
        ["error_classification"],
    )


def downgrade():
    op.drop_index(
        "ix_document_emission_attempts_error_classification",
        table_name="document_emission_attempts",
    )
    op.drop_index(
        "ix_document_emission_attempts_status",
        table_name="document_emission_attempts",
    )
    op.drop_index(
        "ix_document_emission_attempts_tenant_id",
        table_name="document_emission_attempts",
    )
    op.drop_index(
        "ix_document_emission_attempts_job_id",
        table_name="document_emission_attempts",
    )
    op.drop_table("document_emission_attempts")
