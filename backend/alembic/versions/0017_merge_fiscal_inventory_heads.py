"""Merge the provider-verification and commercial-inventory migration heads."""
from __future__ import annotations


revision = "0017_merge_fiscal_inventory_heads"
down_revision = (
    "0010_smartpse_provider_verification",
    "0016_fiscal_notes_v2",
)
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
