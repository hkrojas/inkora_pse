"""Add safe draft and adjustment metadata for fiscal notes v2."""
from alembic import op
import sqlalchemy as sa


revision = "0016_fiscal_notes_v2"
down_revision = "0015_commercial_inventory"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    existing_columns = {
        column["name"]
        for column in sa.inspect(bind).get_columns("cotizaciones")
    }
    columns = {
        "nota_ajuste_metadata": sa.Column(
            "nota_ajuste_metadata", sa.JSON(), nullable=True
        ),
        "nota_idempotency_key": sa.Column(
            "nota_idempotency_key", sa.String(), nullable=True
        ),
        "nota_reemplazo_id": sa.Column(
            "nota_reemplazo_id", sa.Integer(), nullable=True
        ),
    }
    for column_name, column in columns.items():
        if column_name not in existing_columns:
            op.add_column("cotizaciones", column)

    foreign_key_names = {
        foreign_key["name"]
        for foreign_key in sa.inspect(bind).get_foreign_keys("cotizaciones")
    }
    if "fk_cotizaciones_nota_reemplazo" not in foreign_key_names:
        op.create_foreign_key(
            "fk_cotizaciones_nota_reemplazo",
            "cotizaciones",
            "cotizaciones",
            ["nota_reemplazo_id"],
            ["id"],
        )

    unique_constraint_names = {
        constraint["name"]
        for constraint in sa.inspect(bind).get_unique_constraints("cotizaciones")
    }
    if (
        "uq_cotizaciones_tenant_note_idempotency"
        not in unique_constraint_names
    ):
        op.create_unique_constraint(
            "uq_cotizaciones_tenant_note_idempotency",
            "cotizaciones",
            ["tenant_id", "nota_idempotency_key"],
        )

    index_names = {
        index["name"]
        for index in sa.inspect(bind).get_indexes("cotizaciones")
    }
    if "ix_cotizaciones_note_reference_status" not in index_names:
        op.create_index(
            "ix_cotizaciones_note_reference_status",
            "cotizaciones",
            ["tenant_id", "nota_referencia_id", "estado"],
        )
    if "ix_cotizaciones_nota_reemplazo_id" not in index_names:
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
