"""Add tenant-scoped commercial inventory and immutable kardex."""
from alembic import op
import sqlalchemy as sa

# This migration follows the production migration chain already present on
# main.  The file name is retained for backwards compatibility with the
# development worktree; Alembic keys migrations by ``revision``.
revision = "0015_commercial_inventory"
down_revision = "0014_tenant_fiscal_series"
branch_labels = None
depends_on = None


def _preprovisioned_inventory_schema_is_complete():
    """Detect the production schema that was installed before this revision.

    The initial production rollout used reviewed SQL before the Alembic revision
    was merged.  Returning early lets Alembic record the revision without
    recreating those objects.  New databases still execute the normal DDL below.
    """
    inspector = sa.inspect(op.get_bind())
    required_columns = {
        "tenants": {"inventory_enabled", "inventory_started_at"},
        "productos": {"item_type", "inventory_enabled"},
        "cotizaciones": {
            "warehouse_id",
            "inventory_impact",
            "inventory_return_warehouse_id",
        },
        "cotizacion_items": {"inventory_source_item_id"},
        "guia_remision_items": {"producto_id"},
    }
    required_tables = {
        "warehouses",
        "inventory_balances",
        "inventory_movements",
        "inventory_holds",
        "inventory_transfers",
        "inventory_transfer_items",
        "inventory_returns",
        "inventory_return_items",
    }

    existing_tables = set(inspector.get_table_names())
    if not required_tables.issubset(existing_tables):
        return False

    for table_name, column_names in required_columns.items():
        if table_name not in existing_tables:
            return False
        existing_columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        if not column_names.issubset(existing_columns):
            return False

    return True


def upgrade():
    if _preprovisioned_inventory_schema_is_complete():
        return

    op.add_column("tenants", sa.Column("inventory_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("tenants", sa.Column("inventory_started_at", sa.DateTime(), nullable=True))
    op.add_column("productos", sa.Column("item_type", sa.String(), nullable=False, server_default="unclassified"))
    op.add_column("productos", sa.Column("inventory_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_table(
        "warehouses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("tenant_id", "code", name="uq_warehouses_tenant_code"),
    )
    op.create_index("ix_warehouses_tenant_active", "warehouses", ["tenant_id", "is_active"])

    op.add_column("cotizaciones", sa.Column("warehouse_id", sa.Integer(), nullable=True))
    op.add_column("cotizaciones", sa.Column("inventory_impact", sa.String(), nullable=True))
    op.add_column("cotizaciones", sa.Column("inventory_return_warehouse_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_cotizaciones_warehouse", "cotizaciones", "warehouses", ["warehouse_id"], ["id"])
    op.create_foreign_key("fk_cotizaciones_return_warehouse", "cotizaciones", "warehouses", ["inventory_return_warehouse_id"], ["id"])
    op.create_index("ix_cotizaciones_warehouse_id", "cotizaciones", ["warehouse_id"])
    op.add_column("cotizacion_items", sa.Column("inventory_source_item_id", sa.Integer(), nullable=True))
    op.create_index("ix_cotizacion_items_inventory_source_item_id", "cotizacion_items", ["inventory_source_item_id"])

    op.add_column("guia_remision_items", sa.Column("producto_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_guia_items_producto", "guia_remision_items", "productos", ["producto_id"], ["id"])
    op.create_index("ix_guia_remision_items_producto_id", "guia_remision_items", ["producto_id"])

    op.create_table(
        "inventory_balances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("productos.id"), nullable=False),
        sa.Column("on_hand", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("committed", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("minimum_stock", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("tenant_id", "warehouse_id", "product_id", name="uq_inventory_balance_scope"),
        sa.CheckConstraint("on_hand >= 0 OR on_hand < 0", name="ck_inventory_balance_numeric"),
        sa.CheckConstraint("committed >= 0", name="ck_inventory_committed_nonnegative"),
    )
    op.create_index("ix_inventory_balances_tenant_product", "inventory_balances", ["tenant_id", "product_id"])

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("productos.id"), nullable=False),
        sa.Column("movement_type", sa.String(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("balance_before", sa.Numeric(18, 4), nullable=False),
        sa.Column("balance_after", sa.Numeric(18, 4), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("source_line_id", sa.Integer(), nullable=True),
        sa.Column("related_movement_id", sa.Integer(), sa.ForeignKey("inventory_movements.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_inventory_movement_idempotency"),
        sa.CheckConstraint("quantity <> 0", name="ck_inventory_movement_nonzero"),
    )
    op.create_index("ix_inventory_movements_scope_date", "inventory_movements", ["tenant_id", "warehouse_id", "product_id", "created_at"])
    op.create_index("ix_inventory_movements_source", "inventory_movements", ["tenant_id", "source_type", "source_id"])

    op.create_table(
        "inventory_holds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("productos.id"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("cotizaciones.id"), nullable=False),
        sa.Column("document_item_id", sa.Integer(), sa.ForeignKey("cotizacion_items.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("negative_override", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("tenant_id", "document_id", "document_item_id", name="uq_inventory_hold_document_line"),
        sa.CheckConstraint("quantity > 0", name="ck_inventory_hold_positive"),
    )
    op.create_index("ix_inventory_holds_tenant_status", "inventory_holds", ["tenant_id", "status", "created_at"])

    op.create_table(
        "inventory_transfers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("source_warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("destination_warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="completed"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("source_warehouse_id <> destination_warehouse_id", name="ck_inventory_transfer_distinct_warehouses"),
    )
    op.create_index("ix_inventory_transfers_tenant_date", "inventory_transfers", ["tenant_id", "created_at"])
    op.create_table(
        "inventory_transfer_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transfer_id", sa.Integer(), sa.ForeignKey("inventory_transfers.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("productos.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_inventory_transfer_item_positive"),
    )
    op.create_index("ix_inventory_transfer_items_transfer_id", "inventory_transfer_items", ["transfer_id"])
    op.create_index("ix_inventory_transfer_items_product_id", "inventory_transfer_items", ["product_id"])

    op.create_table(
        "inventory_returns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("credit_note_id", sa.Integer(), sa.ForeignKey("cotizaciones.id"), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=True),
        sa.Column("received_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.UniqueConstraint("tenant_id", "credit_note_id", name="uq_inventory_return_note"),
    )
    op.create_table(
        "inventory_return_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("return_id", sa.Integer(), sa.ForeignKey("inventory_returns.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("productos.id"), nullable=False),
        sa.Column("note_item_id", sa.Integer(), sa.ForeignKey("cotizacion_items.id"), nullable=False),
        sa.Column("authorized_quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("received_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"),
    )
    op.create_index("ix_inventory_return_items_return_id", "inventory_return_items", ["return_id"])
    op.create_index("ix_inventory_return_items_product_id", "inventory_return_items", ["product_id"])


def downgrade():
    op.drop_table("inventory_return_items")
    op.drop_table("inventory_returns")
    op.drop_table("inventory_transfer_items")
    op.drop_table("inventory_transfers")
    op.drop_table("inventory_holds")
    op.drop_table("inventory_movements")
    op.drop_table("inventory_balances")
    op.drop_index("ix_guia_remision_items_producto_id", table_name="guia_remision_items")
    op.drop_constraint("fk_guia_items_producto", "guia_remision_items", type_="foreignkey")
    op.drop_column("guia_remision_items", "producto_id")
    op.drop_index("ix_cotizaciones_warehouse_id", table_name="cotizaciones")
    op.drop_index("ix_cotizacion_items_inventory_source_item_id", table_name="cotizacion_items")
    op.drop_column("cotizacion_items", "inventory_source_item_id")
    op.drop_constraint("fk_cotizaciones_return_warehouse", "cotizaciones", type_="foreignkey")
    op.drop_constraint("fk_cotizaciones_warehouse", "cotizaciones", type_="foreignkey")
    op.drop_column("cotizaciones", "inventory_return_warehouse_id")
    op.drop_column("cotizaciones", "inventory_impact")
    op.drop_column("cotizaciones", "warehouse_id")
    op.drop_table("warehouses")
    op.drop_column("productos", "inventory_enabled")
    op.drop_column("productos", "item_type")
    op.drop_column("tenants", "inventory_started_at")
    op.drop_column("tenants", "inventory_enabled")
