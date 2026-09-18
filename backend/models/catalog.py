"""Tenant-scoped commercial catalog domain.

Catalog records intentionally keep public merchandising data separate from the
operational/fiscal ``Producto`` model.  A catalog item may reference a product,
but that reference is optional and never publishes a product automatically.
"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


CATALOG_PRODUCT_CODE = "catalog"
CATALOG_ENTITLEMENT_STATUSES = ("trial", "active", "suspended", "cancelled")
CATALOG_SITE_STATUSES = ("draft", "published", "suspended")
CATALOG_ITEM_KINDS = ("internal_product", "catalog_product", "service", "solution")
CATALOG_PRICE_MODES = ("fixed", "starting_from", "range", "quotation", "hidden")
CATALOG_PRICE_SOURCES = ("manual", "product")
CATALOG_AVAILABILITY_SOURCES = ("manual", "inventory")
CATALOG_AVAILABILITY_STATUSES = (
    "available",
    "low_stock",
    "out_of_stock",
    "made_to_order",
    "consult",
    "coming_soon",
)


def _public_id() -> str:
    return str(uuid4())


class TenantProductEntitlement(Base):
    __tablename__ = "tenant_product_entitlements"
    __table_args__ = (
        UniqueConstraint("tenant_id", "product_code", name="uq_tenant_product_entitlement"),
        Index("ix_tenant_product_entitlement_status", "tenant_id", "product_code", "status"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    product_code = Column(String(50), nullable=False, default=CATALOG_PRODUCT_CODE)
    status = Column(String(20), nullable=False, default="trial")
    enabled_at = Column(DateTime, nullable=True, default=datetime.now)
    disabled_at = Column(DateTime, nullable=True)
    configured_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    tenant = relationship("Tenant", back_populates="product_entitlements")
    configured_by = relationship("User")


class CatalogSite(Base):
    __tablename__ = "catalog_sites"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_catalog_site_tenant"),
        UniqueConstraint("public_id", name="uq_catalog_site_public_id"),
        UniqueConstraint("slug", name="uq_catalog_site_slug"),
        Index("ix_catalog_sites_public_lookup", "slug", "status", "tenant_id"),
    )

    id = Column(Integer, primary_key=True)
    public_id = Column(String(36), nullable=False, default=_public_id)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    slug = Column(String(120), nullable=False)
    display_name = Column(String(180), nullable=False)
    headline = Column(String(220), nullable=True)
    description = Column(Text, nullable=True)
    business_type = Column(String(80), nullable=True)
    whatsapp_number = Column(String(32), nullable=True)
    default_whatsapp_message = Column(Text, nullable=True)
    social_links = Column(JSON, nullable=True)
    template_key = Column(String(50), nullable=False, default="modern-grid")
    theme_schema_version = Column(Integer, nullable=False, default=1)
    theme_config = Column(JSON, nullable=False, default=dict)
    seo_title = Column(String(180), nullable=True)
    seo_description = Column(String(320), nullable=True)
    status = Column(String(20), nullable=False, default="draft")
    content_version = Column(Integer, nullable=False, default=1)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True)

    tenant = relationship("Tenant", back_populates="catalog_site")
    categories = relationship("CatalogCategory", back_populates="catalog", cascade="all, delete-orphan")
    items = relationship("CatalogItem", back_populates="catalog", cascade="all, delete-orphan")
    assets = relationship("CatalogAsset", back_populates="catalog", cascade="all, delete-orphan")
    collections = relationship("CatalogCollection", back_populates="catalog", cascade="all, delete-orphan")


class CatalogAsset(Base):
    __tablename__ = "catalog_assets"
    __table_args__ = (
        UniqueConstraint("public_id", name="uq_catalog_asset_public_id"),
        UniqueConstraint("storage_provider", "bucket", "object_key", name="uq_catalog_asset_object"),
        Index("ix_catalog_assets_tenant_catalog", "tenant_id", "catalog_id", "deleted_at"),
    )

    id = Column(Integer, primary_key=True)
    public_id = Column(String(36), nullable=False, default=_public_id)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    catalog_id = Column(Integer, ForeignKey("catalog_sites.id"), nullable=False, index=True)
    storage_provider = Column(String(30), nullable=False, default="supabase")
    bucket = Column(String(120), nullable=False)
    object_key = Column(String(500), nullable=False)
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    checksum = Column(String(128), nullable=False)
    alt_text = Column(String(180), nullable=True)
    variants = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True)

    catalog = relationship("CatalogSite", back_populates="assets")


class CatalogCategory(Base):
    __tablename__ = "catalog_categories"
    __table_args__ = (
        UniqueConstraint("catalog_id", "slug", name="uq_catalog_category_slug"),
        Index("ix_catalog_categories_visible", "tenant_id", "catalog_id", "published", "display_order"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    catalog_id = Column(Integer, ForeignKey("catalog_sites.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    image_asset_id = Column(Integer, ForeignKey("catalog_assets.id", ondelete="SET NULL"), nullable=True)
    published = Column(Boolean, nullable=False, default=True)
    display_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True)

    catalog = relationship("CatalogSite", back_populates="categories")
    image_asset = relationship("CatalogAsset", foreign_keys=[image_asset_id])
    items = relationship("CatalogItem", back_populates="category")


class CatalogItem(Base):
    __tablename__ = "catalog_items"
    __table_args__ = (
        UniqueConstraint("catalog_id", "slug", name="uq_catalog_item_slug"),
        CheckConstraint("minimum_quantity > 0", name="ck_catalog_item_minimum_quantity"),
        CheckConstraint("low_stock_threshold >= 0", name="ck_catalog_item_low_stock_threshold"),
        Index("ix_catalog_items_visible", "tenant_id", "catalog_id", "published", "display_order"),
        Index("ix_catalog_items_category_visible", "tenant_id", "category_id", "published", "display_order"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    catalog_id = Column(Integer, ForeignKey("catalog_sites.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("productos.id", ondelete="SET NULL"), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("catalog_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    kind = Column(String(30), nullable=False, default="catalog_product")
    public_name = Column(String(180), nullable=False)
    slug = Column(String(160), nullable=False)
    short_description = Column(String(320), nullable=True)
    full_description = Column(Text, nullable=True)
    price_mode = Column(String(30), nullable=False, default="quotation")
    price_source = Column(String(20), nullable=False, default="manual")
    price_amount = Column(Numeric(12, 4), nullable=True)
    price_min = Column(Numeric(12, 4), nullable=True)
    price_max = Column(Numeric(12, 4), nullable=True)
    currency = Column(String(3), nullable=False, default="PEN")
    availability_source = Column(String(20), nullable=False, default="manual")
    availability_status = Column(String(30), nullable=False, default="consult")
    inventory_warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    low_stock_threshold = Column(Numeric(18, 4), nullable=False, default=0)
    minimum_quantity = Column(Numeric(12, 4), nullable=False, default=1)
    featured = Column(Boolean, nullable=False, default=False)
    published = Column(Boolean, nullable=False, default=False)
    display_order = Column(Integer, nullable=False, default=0)
    whatsapp_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True)

    catalog = relationship("CatalogSite", back_populates="items")
    product = relationship("Producto", back_populates="catalog_items")
    category = relationship("CatalogCategory", back_populates="items")
    assets = relationship("CatalogItemAsset", back_populates="item", cascade="all, delete-orphan")
    collection_links = relationship("CatalogCollectionItem", back_populates="item", cascade="all, delete-orphan")


class CatalogItemAsset(Base):
    __tablename__ = "catalog_item_assets"
    __table_args__ = (
        UniqueConstraint("item_id", "asset_id", name="uq_catalog_item_asset"),
        Index("ix_catalog_item_assets_order", "tenant_id", "item_id", "role", "display_order"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("catalog_items.id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("catalog_assets.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False, default="gallery")
    display_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    item = relationship("CatalogItem", back_populates="assets")
    asset = relationship("CatalogAsset")


class CatalogCollection(Base):
    __tablename__ = "catalog_collections"
    __table_args__ = (
        UniqueConstraint("catalog_id", "slug", name="uq_catalog_collection_slug"),
        Index("ix_catalog_collections_visible", "tenant_id", "catalog_id", "published", "display_order"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    catalog_id = Column(Integer, ForeignKey("catalog_sites.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    cover_asset_id = Column(Integer, ForeignKey("catalog_assets.id", ondelete="SET NULL"), nullable=True)
    published = Column(Boolean, nullable=False, default=True)
    display_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True)

    catalog = relationship("CatalogSite", back_populates="collections")
    cover_asset = relationship("CatalogAsset", foreign_keys=[cover_asset_id])
    item_links = relationship("CatalogCollectionItem", back_populates="collection", cascade="all, delete-orphan")


class CatalogCollectionItem(Base):
    __tablename__ = "catalog_collection_items"
    __table_args__ = (
        UniqueConstraint("collection_id", "item_id", name="uq_catalog_collection_item"),
        Index("ix_catalog_collection_items_order", "tenant_id", "collection_id", "display_order"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    collection_id = Column(Integer, ForeignKey("catalog_collections.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("catalog_items.id"), nullable=False, index=True)
    display_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    collection = relationship("CatalogCollection", back_populates="item_links")
    item = relationship("CatalogItem", back_populates="collection_links")
