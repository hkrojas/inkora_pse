"""Enable commercial inventory and seed zero balances for existing catalogs."""
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision = "0017_inventory_defaults"
down_revision = "0016_fiscal_notes_v2"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if not {"tenants", "productos", "warehouses", "inventory_balances"}.issubset(tables):
        return

    op.alter_column("tenants", "inventory_enabled", server_default=sa.true())
    op.alter_column("productos", "item_type", server_default="inventory")
    op.alter_column("productos", "inventory_enabled", server_default=sa.true())

    tenants = sa.table(
        "tenants",
        sa.column("id", sa.Integer()),
        sa.column("inventory_enabled", sa.Boolean()),
        sa.column("inventory_started_at", sa.DateTime()),
    )
    productos = sa.table(
        "productos",
        sa.column("id", sa.Integer()),
        sa.column("tenant_id", sa.Integer()),
        sa.column("item_type", sa.String()),
        sa.column("inventory_enabled", sa.Boolean()),
    )
    warehouses = sa.table(
        "warehouses",
        sa.column("id", sa.Integer()),
        sa.column("tenant_id", sa.Integer()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("is_default", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    balances = sa.table(
        "inventory_balances",
        sa.column("tenant_id", sa.Integer()),
        sa.column("warehouse_id", sa.Integer()),
        sa.column("product_id", sa.Integer()),
        sa.column("on_hand", sa.Numeric(18, 4)),
        sa.column("committed", sa.Numeric(18, 4)),
        sa.column("minimum_stock", sa.Numeric(18, 4)),
        sa.column("updated_at", sa.DateTime()),
    )

    now = datetime.utcnow()
    bind.execute(
        tenants.update().values(
            inventory_enabled=True,
            inventory_started_at=sa.func.coalesce(tenants.c.inventory_started_at, now),
        )
    )
    bind.execute(
        productos.update().where(
            sa.or_(
                productos.c.item_type.is_(None),
                productos.c.item_type != "service",
            )
        ).values(item_type="inventory", inventory_enabled=True)
    )

    tenant_ids = [row[0] for row in bind.execute(sa.select(tenants.c.id)).all()]
    default_warehouse_by_tenant = {}
    for tenant_id in tenant_ids:
        default_id = bind.execute(
            sa.select(warehouses.c.id).where(
                warehouses.c.tenant_id == tenant_id,
                warehouses.c.is_default.is_(True),
                warehouses.c.is_active.is_(True),
            ).limit(1)
        ).scalar()
        if default_id is None:
            principal_id = bind.execute(
                sa.select(warehouses.c.id).where(
                    warehouses.c.tenant_id == tenant_id,
                    warehouses.c.code == "PRINCIPAL",
                ).limit(1)
            ).scalar()
            if principal_id is not None:
                bind.execute(
                    warehouses.update().where(warehouses.c.id == principal_id).values(
                        is_default=True,
                        is_active=True,
                        updated_at=now,
                    )
                )
                default_id = principal_id
            else:
                bind.execute(
                    warehouses.insert().values(
                        tenant_id=tenant_id,
                        code="PRINCIPAL",
                        name="Almacén principal",
                        is_default=True,
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                    )
                )
                default_id = bind.execute(
                    sa.select(warehouses.c.id).where(
                        warehouses.c.tenant_id == tenant_id,
                        warehouses.c.code == "PRINCIPAL",
                    ).limit(1)
                ).scalar()
        default_warehouse_by_tenant[tenant_id] = default_id

    inventory_products = bind.execute(
        sa.select(productos.c.id, productos.c.tenant_id).where(
            productos.c.inventory_enabled.is_(True),
            productos.c.item_type == "inventory",
        )
    ).all()
    for product_id, tenant_id in inventory_products:
        warehouse_id = default_warehouse_by_tenant.get(tenant_id)
        if warehouse_id is None:
            continue
        exists = bind.execute(
            sa.select(balances.c.product_id).where(
                balances.c.tenant_id == tenant_id,
                balances.c.warehouse_id == warehouse_id,
                balances.c.product_id == product_id,
            ).limit(1)
        ).first()
        if not exists:
            bind.execute(
                balances.insert().values(
                    tenant_id=tenant_id,
                    warehouse_id=warehouse_id,
                    product_id=product_id,
                    on_hand=0,
                    committed=0,
                    minimum_stock=0,
                    updated_at=now,
                )
            )


def downgrade():
    op.alter_column("productos", "inventory_enabled", server_default=sa.false())
    op.alter_column("productos", "item_type", server_default="unclassified")
    op.alter_column("tenants", "inventory_enabled", server_default=sa.false())
