"""Coordinate fiscal outage probes without storing tenant documents or secrets."""
from alembic import op
import sqlalchemy as sa

revision = "0026_fiscal_provider_circuits"
down_revision = "0025_emission_worker_events"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("fiscal_provider_circuits",
        sa.Column("scope", sa.String(100), primary_key=True),
        sa.Column("failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_probe_at", sa.DateTime(), nullable=True),
        sa.Column("probe_token", sa.String(36), nullable=True),
        sa.Column("probe_expires_at", sa.DateTime(), nullable=True))
    if op.get_bind().dialect.name == "postgresql":
        # Backend-only coordination state; never expose it through the Data API.
        op.execute("ALTER TABLE fiscal_provider_circuits ENABLE ROW LEVEL SECURITY")
        op.execute("REVOKE ALL ON fiscal_provider_circuits FROM PUBLIC")
        op.execute("""DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='anon') THEN
            REVOKE ALL ON fiscal_provider_circuits FROM anon;
          END IF;
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN
            REVOKE ALL ON fiscal_provider_circuits FROM authenticated;
          END IF;
        END $$""")


def downgrade():
    op.drop_table("fiscal_provider_circuits")
