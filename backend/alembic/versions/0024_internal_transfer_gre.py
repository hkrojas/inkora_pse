"""Add national internal transfers and tenant establishments.

Revision ID: 0024_internal_transfer_gre
Revises: 0023_tenant_gre_series
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0024_internal_transfer_gre"
down_revision = "0023_tenant_gre_series"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("inventory_transfers") as batch:
        batch.add_column(sa.Column(
            "lifecycle_mode",
            sa.String(length=32),
            nullable=False,
            server_default="legacy_immediate",
        ))

    op.create_table(
        "tenant_establishments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("sunat_code", sa.String(length=4), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("ubigeo", sa.String(length=6), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("is_main", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("verified_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("verification_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("tenant_id", "sunat_code", name="uq_tenant_establishments_code"),
    )
    op.create_index("ix_tenant_establishments_active", "tenant_establishments", ["tenant_id", "is_active"])
    op.create_index(
        "uq_tenant_establishments_main",
        "tenant_establishments",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("is_main IS TRUE"),
        sqlite_where=sa.text("is_main = 1"),
    )

    with op.batch_alter_table("warehouses") as batch:
        batch.add_column(sa.Column("establishment_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_warehouses_establishment_id",
            "tenant_establishments",
            ["establishment_id"],
            ["id"],
        )
        batch.create_index("ix_warehouses_establishment_id", ["establishment_id"])

    op.create_table(
        "internal_transfer_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("source_establishment_id", sa.Integer(), sa.ForeignKey("tenant_establishments.id"), nullable=False),
        sa.Column("destination_establishment_id", sa.Integer(), sa.ForeignKey("tenant_establishments.id"), nullable=False),
        sa.Column("source_warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id"), nullable=True),
        sa.Column("destination_warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id"), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("version >= 1", name="ck_internal_transfer_order_version"),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_internal_transfer_order_idempotency"),
    )
    op.create_index(
        "ix_internal_transfer_order_status",
        "internal_transfer_orders",
        ["tenant_id", "status", "created_at"],
    )

    op.create_table(
        "internal_transfer_order_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("transfer_id", sa.Integer(), sa.ForeignKey("internal_transfer_orders.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("productos.id"), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("product_code", sa.String(length=100), nullable=True),
        sa.Column("unit_code", sa.String(length=10), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("cancelled_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("inventory_controlled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint(
            "cancelled_quantity >= 0 AND cancelled_quantity <= quantity",
            name="ck_internal_transfer_order_line_cancelled_quantity",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_internal_transfer_order_line_quantity"),
    )
    op.create_index(
        "ix_internal_transfer_order_line_product",
        "internal_transfer_order_lines",
        ["tenant_id", "product_id"],
    )

    op.create_table(
        "internal_transfer_dispatches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("transfer_id", sa.Integer(), sa.ForeignKey("internal_transfer_orders.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="reserved"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("departure_idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("departure_confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("departure_confirmed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("version >= 1", name="ck_internal_transfer_dispatch_version"),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_internal_transfer_dispatch_idempotency"),
        sa.UniqueConstraint(
            "tenant_id",
            "departure_idempotency_key",
            name="uq_internal_transfer_departure_idempotency",
        ),
    )
    op.create_index(
        "ix_internal_transfer_dispatch_status",
        "internal_transfer_dispatches",
        ["tenant_id", "status", "created_at"],
    )

    op.create_table(
        "internal_transfer_dispatch_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("dispatch_id", sa.Integer(), sa.ForeignKey("internal_transfer_dispatches.id"), nullable=False),
        sa.Column("transfer_line_id", sa.Integer(), sa.ForeignKey("internal_transfer_order_lines.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("reservation_status", sa.String(), nullable=False, server_default="active"),
        sa.Column("reserved_at", sa.DateTime(), nullable=False),
        sa.Column("covered_at", sa.DateTime(), nullable=True),
        sa.Column("released_at", sa.DateTime(), nullable=True),
        sa.Column("departed_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("received_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("source_movement_id", sa.Integer(), sa.ForeignKey("inventory_movements.id"), nullable=True),
        sa.CheckConstraint("quantity > 0", name="ck_internal_transfer_dispatch_line_quantity"),
        sa.UniqueConstraint("dispatch_id", "transfer_line_id", name="uq_internal_transfer_dispatch_line"),
    )

    op.create_table(
        "internal_transfer_receipts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("dispatch_id", sa.Integer(), sa.ForeignKey("internal_transfer_dispatches.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("received_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_internal_transfer_receipt_idempotency"),
    )
    op.create_index(
        "ix_internal_transfer_receipt_dispatch",
        "internal_transfer_receipts",
        ["tenant_id", "dispatch_id", "received_at"],
    )

    op.create_table(
        "internal_transfer_receipt_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("receipt_id", sa.Integer(), sa.ForeignKey("internal_transfer_receipts.id"), nullable=False),
        sa.Column("dispatch_line_id", sa.Integer(), sa.ForeignKey("internal_transfer_dispatch_lines.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("destination_movement_id", sa.Integer(), sa.ForeignKey("inventory_movements.id"), nullable=True),
        sa.CheckConstraint("quantity > 0", name="ck_internal_transfer_receipt_line_quantity"),
    )

    with op.batch_alter_table("guias_remision") as batch:
        batch.add_column(sa.Column("internal_transfer_dispatch_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("partida_codigo_local", sa.String(length=4), nullable=True))
        batch.add_column(sa.Column("llegada_codigo_local", sa.String(length=4), nullable=True))
        batch.create_foreign_key(
            "fk_guias_internal_transfer_dispatch",
            "internal_transfer_dispatches",
            ["internal_transfer_dispatch_id"],
            ["id"],
        )
        batch.create_index("ix_guias_remision_internal_transfer_dispatch_id", ["internal_transfer_dispatch_id"])

    with op.batch_alter_table("guia_remision_items") as batch:
        batch.add_column(sa.Column("internal_transfer_dispatch_line_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_guia_items_internal_transfer_dispatch_line",
            "internal_transfer_dispatch_lines",
            ["internal_transfer_dispatch_line_id"],
            ["id"],
        )
        batch.create_index(
            "ix_guia_remision_items_internal_transfer_dispatch_line_id",
            ["internal_transfer_dispatch_line_id"],
        )


def downgrade():
    with op.batch_alter_table("guia_remision_items") as batch:
        batch.drop_index("ix_guia_remision_items_internal_transfer_dispatch_line_id")
        batch.drop_constraint("fk_guia_items_internal_transfer_dispatch_line", type_="foreignkey")
        batch.drop_column("internal_transfer_dispatch_line_id")
    with op.batch_alter_table("guias_remision") as batch:
        batch.drop_index("ix_guias_remision_internal_transfer_dispatch_id")
        batch.drop_constraint("fk_guias_internal_transfer_dispatch", type_="foreignkey")
        batch.drop_column("llegada_codigo_local")
        batch.drop_column("partida_codigo_local")
        batch.drop_column("internal_transfer_dispatch_id")
    op.drop_table("internal_transfer_receipt_lines")
    op.drop_index("ix_internal_transfer_receipt_dispatch", table_name="internal_transfer_receipts")
    op.drop_table("internal_transfer_receipts")
    op.drop_table("internal_transfer_dispatch_lines")
    op.drop_index("ix_internal_transfer_dispatch_status", table_name="internal_transfer_dispatches")
    op.drop_table("internal_transfer_dispatches")
    op.drop_index("ix_internal_transfer_order_line_product", table_name="internal_transfer_order_lines")
    op.drop_table("internal_transfer_order_lines")
    op.drop_index("ix_internal_transfer_order_status", table_name="internal_transfer_orders")
    op.drop_table("internal_transfer_orders")
    with op.batch_alter_table("warehouses") as batch:
        batch.drop_index("ix_warehouses_establishment_id")
        batch.drop_constraint("fk_warehouses_establishment_id", type_="foreignkey")
        batch.drop_column("establishment_id")
    op.drop_index("uq_tenant_establishments_main", table_name="tenant_establishments")
    op.drop_index("ix_tenant_establishments_active", table_name="tenant_establishments")
    op.drop_table("tenant_establishments")
    with op.batch_alter_table("inventory_transfers") as batch:
        batch.drop_column("lifecycle_mode")
