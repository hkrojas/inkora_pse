"""Persist per-tenant production fiscal series and remote floors."""
from __future__ import annotations

from alembic import op


# Alembic stores revision IDs in alembic_version.version_num VARCHAR(32).
revision = "0014_tenant_fiscal_series"
# The production database is currently stamped at this revision. Attach the
# additive series configuration after it so Railway has one unambiguous head.
down_revision = "0008_fiscal_doc_provider_trace"
branch_labels = None
depends_on = None


def upgrade():
    # The columns were applied operationally before this revision was added.
    # Keep pre-deploy idempotent for that production database.
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS fiscal_invoice_series VARCHAR(4)")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS fiscal_invoice_series_floor INTEGER")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS fiscal_boleta_series VARCHAR(4)")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS fiscal_boleta_series_floor INTEGER")


def downgrade():
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS fiscal_boleta_series_floor")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS fiscal_boleta_series")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS fiscal_invoice_series_floor")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS fiscal_invoice_series")
