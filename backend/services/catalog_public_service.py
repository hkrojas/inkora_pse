"""Read-only public catalog projection; never returns internal tenant data."""
from __future__ import annotations

from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy.orm import Session

from config import settings
from database import activate_tenant_context, reset_tenant_context, without_tenant_filter
import models


def resolve_published_catalog(db: Session, slug: str):
    """Use one intentional global lookup, then activate the resolved tenant."""
    site = without_tenant_filter(db.query(models.CatalogSite)).join(models.Tenant).join(
        models.TenantProductEntitlement,
        (models.TenantProductEntitlement.tenant_id == models.CatalogSite.tenant_id)
        & (models.TenantProductEntitlement.product_code == models.CATALOG_PRODUCT_CODE),
    ).filter(
        models.CatalogSite.slug == slug,
        models.CatalogSite.status == "published",
        models.CatalogSite.deleted_at.is_(None),
        models.Tenant.is_active.is_(True),
        models.TenantProductEntitlement.status.in_(("trial", "active")),
    ).first()
    if not site:
        raise HTTPException(status_code=404, detail="Catálogo no encontrado.")
    return site, activate_tenant_context(site.tenant_id)


def asset_view(asset: models.CatalogAsset | None):
    if not asset: return None
    variants = asset.variants or {}
    return {
        "alt": asset.alt_text or "",
        "width": asset.width,
        "height": asset.height,
        "variants": {
            width: f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/public/{quote(asset.bucket)}/{quote(data['object_key'])}"
            for width, data in variants.items()
        },
    }


def public_item(db: Session, item: models.CatalogItem):
    price_amount = item.price_amount
    price_min = item.price_min
    price_max = item.price_max
    if item.price_source == "product" and item.product:
        price_amount = item.product.precio_unitario
        price_min = None; price_max = None
    availability = item.availability_status
    if item.availability_source == "inventory":
        if not item.product or not item.catalog.tenant.inventory_enabled:
            availability = "consult"
        else:
            balances = db.query(models.InventoryBalance).filter(
                models.InventoryBalance.product_id == item.product_id,
                *([models.InventoryBalance.warehouse_id == item.inventory_warehouse_id] if item.inventory_warehouse_id else []),
            ).all()
            available = sum((balance.available or 0) for balance in balances)
            availability = "out_of_stock" if available <= 0 else ("low_stock" if available <= item.low_stock_threshold else "available")
    cover_link = db.query(models.CatalogItemAsset).filter(models.CatalogItemAsset.item_id == item.id).order_by(models.CatalogItemAsset.display_order).first()
    return {
        "slug": item.slug, "public_name": item.public_name, "short_description": item.short_description,
        "full_description": item.full_description, "kind": item.kind, "price_mode": item.price_mode,
        "price_amount": price_amount, "price_min": price_min, "price_max": price_max, "currency": item.currency,
        "availability_status": availability, "minimum_quantity": item.minimum_quantity, "featured": item.featured,
        "image": asset_view(cover_link.asset if cover_link else None),
    }


def public_site(site: models.CatalogSite):
    return {
        "slug": site.slug, "display_name": site.display_name, "headline": site.headline, "description": site.description,
        "business_type": site.business_type, "whatsapp_number": site.whatsapp_number,
        "default_whatsapp_message": site.default_whatsapp_message, "social_links": site.social_links or {},
        "template_key": site.template_key, "theme_config": site.theme_config, "seo_title": site.seo_title,
        "seo_description": site.seo_description, "content_version": site.content_version,
    }
