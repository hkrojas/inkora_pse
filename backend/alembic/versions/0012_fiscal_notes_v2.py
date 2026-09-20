"""Add safe draft and adjustment metadata for fiscal notes v2."""
from alembic import op
import sqlalchemy as sa


revision = "0016_fiscal_notes_v2"
down_revision = "0015_commercial_inventory"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cotizaciones", sa.Column("nota_ajuste_metadata", sa.JSON(), nullable=True))
    op.add_column("cotizaciones", sa.Column("nota_idempotency_key", sa.String(), nullable=True))
    op.add_column("cotizaciones", sa.Column("nota_reemplazo_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_cotizaciones_nota_reemplazo",
        "cotizaciones",
        "cotizaciones",
        ["nota_reemplazo_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_cotizaciones_tenant_note_idempotency",
        "cotizaciones",
        ["tenant_id", "nota_idempotency_key"],
    )
    op.create_index(
        "ix_cotizaciones_note_reference_status",
        "cotizaciones",
        ["tenant_id", "nota_referencia_id", "estado"],
    )
    op.create_index(
        "ix_cotizaciones_nota_reemplazo_id",
        "cotizaciones",
        ["nota_reemplazo_id"],
    )


def downgrade():
    op.drop_index("ix_cotizaciones_nota_reemplazo_id", table_name="cotizaciones")
    op.drop_index("ix_cotizaciones_note_reference_status", table_name="cotizaciones")
    op.drop_constraint("uq_cotizaciones_tenant_note_idempotency", "cotizaciones", type_="unique")
    op.drop_constraint("fk_cotizaciones_nota_reemplazo", "cotizaciones", type_="foreignkey")
    op.drop_column("cotizaciones", "nota_reemplazo_id")
    op.drop_column("cotizaciones", "nota_idempotency_key")
    op.drop_column("cotizaciones", "nota_ajuste_metadata")
