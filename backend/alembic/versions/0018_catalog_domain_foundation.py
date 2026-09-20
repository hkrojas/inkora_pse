"""Create the isolated Inkora Catalog domain."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0018_catalog_domain_foundation"
down_revision = "0017_merge_fiscal_inventory_heads"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tenant_product_entitlements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("product_code", sa.String(length=50), nullable=False, server_default="catalog"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="trial"),
        sa.Column("enabled_at", sa.DateTime(), nullable=True),
        sa.Column("disabled_at", sa.DateTime(), nullable=True),
        sa.Column("configured_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("tenant_id", "product_code", name="uq_tenant_product_entitlement"),
    )
    op.create_index("ix_tenant_product_entitlements_tenant_id", "tenant_product_entitlements", ["tenant_id"])
    op.create_index("ix_tenant_product_entitlement_status", "tenant_product_entitlements", ["tenant_id", "product_code", "status"])

    op.create_table(
        "catalog_sites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=180), nullable=False),
        sa.Column("headline", sa.String(length=220), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("business_type", sa.String(length=80), nullable=True),
        sa.Column("whatsapp_number", sa.String(length=32), nullable=True),
        sa.Column("default_whatsapp_message", sa.Text(), nullable=True),
        sa.Column("social_links", sa.JSON(), nullable=True),
        sa.Column("template_key", sa.String(length=50), nullable=False, server_default="modern-grid"),
        sa.Column("theme_schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("theme_config", sa.JSON(), nullable=False),
        sa.Column("seo_title", sa.String(length=180), nullable=True),
        sa.Column("seo_description", sa.String(length=320), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("content_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("tenant_id", name="uq_catalog_site_tenant"),
        sa.UniqueConstraint("public_id", name="uq_catalog_site_public_id"),
        sa.UniqueConstraint("slug", name="uq_catalog_site_slug"),
    )
    op.create_index("ix_catalog_sites_tenant_id", "catalog_sites", ["tenant_id"])
    op.create_index("ix_catalog_sites_public_lookup", "catalog_sites", ["slug", "status", "tenant_id"])

    op.create_table(
        "catalog_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("catalog_id", sa.Integer(), sa.ForeignKey("catalog_sites.id"), nullable=False),
        sa.Column("storage_provider", sa.String(length=30), nullable=False, server_default="supabase"),
        sa.Column("bucket", sa.String(length=120), nullable=False),
        sa.Column("object_key", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("alt_text", sa.String(length=180), nullable=True),
        sa.Column("variants", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("public_id", name="uq_catalog_asset_public_id"),
        sa.UniqueConstraint("storage_provider", "bucket", "object_key", name="uq_catalog_asset_object"),
    )
    op.create_index("ix_catalog_assets_tenant_id", "catalog_assets", ["tenant_id"])
    op.create_index("ix_catalog_assets_catalog_id", "catalog_assets", ["catalog_id"])
    op.create_index("ix_catalog_assets_tenant_catalog", "catalog_assets", ["tenant_id", "catalog_id", "deleted_at"])

    op.create_table(
        "catalog_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("catalog_id", sa.Integer(), sa.ForeignKey("catalog_sites.id"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_asset_id", sa.Integer(), sa.ForeignKey("catalog_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("catalog_id", "slug", name="uq_catalog_category_slug"),
    )
    op.create_index("ix_catalog_categories_tenant_id", "catalog_categories", ["tenant_id"])
    op.create_index("ix_catalog_categories_catalog_id", "catalog_categories", ["catalog_id"])
    op.create_index("ix_catalog_categories_visible", "catalog_categories", ["tenant_id", "catalog_id", "published", "display_order"])

    op.create_table(
        "catalog_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("catalog_id", sa.Integer(), sa.ForeignKey("catalog_sites.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("productos.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("catalog_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("kind", sa.String(length=30), nullable=False, server_default="catalog_product"),
        sa.Column("public_name", sa.String(length=180), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("short_description", sa.String(length=320), nullable=True),
        sa.Column("full_description", sa.Text(), nullable=True),
        sa.Column("price_mode", sa.String(length=30), nullable=False, server_default="quotation"),
        sa.Column("price_source", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("price_amount", sa.Numeric(12, 4), nullable=True),
        sa.Column("price_min", sa.Numeric(12, 4), nullable=True),
        sa.Column("price_max", sa.Numeric(12, 4), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="PEN"),
        sa.Column("availability_source", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("availability_status", sa.String(length=30), nullable=False, server_default="consult"),
        sa.Column("inventory_warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("low_stock_threshold", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("minimum_quantity", sa.Numeric(12, 4), nullable=False, server_default="1"),
        sa.Column("featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("whatsapp_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("minimum_quantity > 0", name="ck_catalog_item_minimum_quantity"),
        sa.CheckConstraint("low_stock_threshold >= 0", name="ck_catalog_item_low_stock_threshold"),
        sa.UniqueConstraint("catalog_id", "slug", name="uq_catalog_item_slug"),
    )
    op.create_index("ix_catalog_items_tenant_id", "catalog_items", ["tenant_id"])
    op.create_index("ix_catalog_items_catalog_id", "catalog_items", ["catalog_id"])
    op.create_index("ix_catalog_items_product_id", "catalog_items", ["product_id"])
    op.create_index("ix_catalog_items_category_id", "catalog_items", ["category_id"])
    op.create_index("ix_catalog_items_visible", "catalog_items", ["tenant_id", "catalog_id", "published", "display_order"])
    op.create_index("ix_catalog_items_category_visible", "catalog_items", ["tenant_id", "category_id", "published", "display_order"])

    op.create_table(
        "catalog_item_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("catalog_assets.id"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="gallery"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("item_id", "asset_id", name="uq_catalog_item_asset"),
    )
    op.create_index("ix_catalog_item_assets_tenant_id", "catalog_item_assets", ["tenant_id"])
    op.create_index("ix_catalog_item_assets_item_id", "catalog_item_assets", ["item_id"])
    op.create_index("ix_catalog_item_assets_asset_id", "catalog_item_assets", ["asset_id"])
    op.create_index("ix_catalog_item_assets_order", "catalog_item_assets", ["tenant_id", "item_id", "role", "display_order"])

    op.create_table(
        "catalog_collections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("catalog_id", sa.Integer(), sa.ForeignKey("catalog_sites.id"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cover_asset_id", sa.Integer(), sa.ForeignKey("catalog_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("catalog_id", "slug", name="uq_catalog_collection_slug"),
    )
    op.create_index("ix_catalog_collections_tenant_id", "catalog_collections", ["tenant_id"])
    op.create_index("ix_catalog_collections_catalog_id", "catalog_collections", ["catalog_id"])
    op.create_index("ix_catalog_collections_visible", "catalog_collections", ["tenant_id", "catalog_id", "published", "display_order"])

    op.create_table(
        "catalog_collection_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("collection_id", sa.Integer(), sa.ForeignKey("catalog_collections.id"), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("collection_id", "item_id", name="uq_catalog_collection_item"),
    )
    op.create_index("ix_catalog_collection_items_tenant_id", "catalog_collection_items", ["tenant_id"])
    op.create_index("ix_catalog_collection_items_collection_id", "catalog_collection_items", ["collection_id"])
    op.create_index("ix_catalog_collection_items_item_id", "catalog_collection_items", ["item_id"])
    op.create_index("ix_catalog_collection_items_order", "catalog_collection_items", ["tenant_id", "collection_id", "display_order"])


def downgrade():
    op.drop_table("catalog_collection_items")
    op.drop_table("catalog_collections")
    op.drop_table("catalog_item_assets")
    op.drop_table("catalog_items")
    op.drop_table("catalog_categories")
    op.drop_table("catalog_assets")
    op.drop_table("catalog_sites")
    op.drop_table("tenant_product_entitlements")
