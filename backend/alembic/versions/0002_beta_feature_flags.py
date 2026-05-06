"""Add tenant fiscal beta feature flags.

This revision starts schema changes after the no-op prebeta baseline. It only
adds a JSON column used to gate fiscal modules by tenant during the paid beta.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_beta_feature_flags"
down_revision = "0001_prebeta_baseline"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "subscriptions",
        sa.Column("beta_feature_flags", sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_column("subscriptions", "beta_feature_flags")
