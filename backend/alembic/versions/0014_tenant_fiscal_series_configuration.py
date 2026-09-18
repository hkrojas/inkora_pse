"""Persist per-tenant production fiscal series and remote floors.

This revision was referenced by the commercial-inventory chain but absent from
this checkout.  It is intentionally idempotent because the production schema
may already contain these operational columns.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0014_tenant_fiscal_series"
down_revision = "0008_fiscal_doc_provider_trace"
branch_labels = None
depends_on = None


_COLUMNS = (
    ("fiscal_invoice_series", sa.String(length=4)),
    ("fiscal_invoice_series_floor", sa.Integer()),
    ("fiscal_boleta_series", sa.String(length=4)),
    ("fiscal_boleta_series_floor", sa.Integer()),
)


def _tenant_columns() -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns("tenants")}


def upgrade():
    existing = _tenant_columns()
    for name, column_type in _COLUMNS:
        if name not in existing:
            op.add_column("tenants", sa.Column(name, column_type, nullable=True))


def downgrade():
    existing = _tenant_columns()
    for name, _ in reversed(_COLUMNS):
        if name in existing:
            op.drop_column("tenants", name)
