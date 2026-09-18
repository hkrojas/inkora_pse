"""Tenant-safe write operations for the commercial catalog."""
from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
from database import without_tenant_filter


def _not_found(name: str):
    raise HTTPException(status_code=404, detail=f"{name} no encontrado.")


def _touch(site: models.CatalogSite) -> None:
    site.content_version += 1


def _audit(db: Session, user_id: int, action: str, entity_type: str, entity_id: int | None) -> None:
    db.add(models.AuditLog(user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id))


def get_entitlement(db: Session, tenant_id: int):
    return without_tenant_filter(db.query(models.TenantProductEntitlement)).filter(
        models.TenantProductEntitlement.tenant_id == tenant_id,
        models.TenantProductEntitlement.product_code == models.CATALOG_PRODUCT_CODE,
    ).first()


def require_entitlement(db: Session, tenant_id: int):
    entitlement = get_entitlement(db, tenant_id)
    if not entitlement or entitlement.status not in {"trial", "active"}:
        raise HTTPException(status_code=403, detail="El producto Catálogo no está habilitado para este tenant.")
    return entitlement


def upsert_entitlement(db: Session, tenant_id: int, status: str, actor_id: int):
    tenant = without_tenant_filter(db.query(models.Tenant)).filter(models.Tenant.id == tenant_id).first()
    if not tenant:
        _not_found("Tenant")
    entitlement = get_entitlement(db, tenant_id)
    if not entitlement:
        entitlement = models.TenantProductEntitlement(
            tenant_id=tenant_id, product_code=models.CATALOG_PRODUCT_CODE, status=status,
            enabled_at=datetime.now() if status in {"trial", "active"} else None,
            configured_by_user_id=actor_id,
        )
        db.add(entitlement)
    else:
        entitlement.status = status
        entitlement.configured_by_user_id = actor_id
        if status in {"trial", "active"}:
            entitlement.enabled_at = entitlement.enabled_at or datetime.now()
            entitlement.disabled_at = None
        else:
            entitlement.disabled_at = datetime.now()
    _audit(db, actor_id, "catalog.entitlement.updated", "tenant", tenant_id)
    db.commit(); db.refresh(entitlement)
    return entitlement


def get_site(db: Session, tenant_id: int, *, required: bool = True):
    site = db.query(models.CatalogSite).filter(
        models.CatalogSite.tenant_id == tenant_id, models.CatalogSite.deleted_at.is_(None)
    ).first()
    if required and not site:
        _not_found("Catálogo")
    return site


def create_site(db: Session, tenant_id: int, data: dict, actor_id: int):
    require_entitlement(db, tenant_id)
    if get_site(db, tenant_id, required=False):
        raise HTTPException(status_code=409, detail="El tenant ya tiene un catálogo.")
    duplicate = without_tenant_filter(db.query(models.CatalogSite)).filter(
        models.CatalogSite.slug == data["slug"], models.CatalogSite.deleted_at.is_(None)
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Ese slug ya está en uso.")
    data["theme_config"] = data["theme_config"] if isinstance(data["theme_config"], dict) else data["theme_config"].model_dump()
    site = models.CatalogSite(tenant_id=tenant_id, **data)
    db.add(site); _audit(db, actor_id, "catalog.site.created", "catalog_site", None)
    try:
        db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(status_code=409, detail="Ese slug ya está en uso.")
    db.refresh(site)
    return site


def update_site(db: Session, tenant_id: int, changes: dict, actor_id: int):
    site = get_site(db, tenant_id); require_entitlement(db, tenant_id)
    if "theme_config" in changes and changes["theme_config"] is not None:
        changes["theme_config"] = changes["theme_config"] if isinstance(changes["theme_config"], dict) else changes["theme_config"].model_dump()
    for key, value in changes.items(): setattr(site, key, value)
    _touch(site); _audit(db, actor_id, "catalog.site.updated", "catalog_site", site.id)
    db.commit(); db.refresh(site)
    return site


def set_published(db: Session, tenant_id: int, published: bool, actor_id: int):
    site = get_site(db, tenant_id); require_entitlement(db, tenant_id)
    if published and not db.query(models.CatalogItem).filter(
        models.CatalogItem.catalog_id == site.id, models.CatalogItem.published.is_(True), models.CatalogItem.deleted_at.is_(None)
    ).first():
        raise HTTPException(status_code=422, detail="Publique al menos un ítem antes de publicar el catálogo.")
    site.status = "published" if published else "draft"
    site.published_at = datetime.now() if published else None
    _touch(site); _audit(db, actor_id, "catalog.site.published" if published else "catalog.site.unpublished", "catalog_site", site.id)
    db.commit(); db.refresh(site)
    return site


def _asset(db: Session, site, asset_id: int | None):
    if asset_id is None: return None
    asset = db.query(models.CatalogAsset).filter(models.CatalogAsset.id == asset_id, models.CatalogAsset.catalog_id == site.id, models.CatalogAsset.deleted_at.is_(None)).first()
    if not asset: _not_found("Asset")
    return asset


def _category(db: Session, site, category_id: int | None):
    if category_id is None: return None
    category = db.query(models.CatalogCategory).filter(models.CatalogCategory.id == category_id, models.CatalogCategory.catalog_id == site.id, models.CatalogCategory.deleted_at.is_(None)).first()
    if not category: _not_found("Categoría")
    return category


def _product(db: Session, tenant_id: int, product_id: int | None):
    if product_id is None: return None
    product = db.query(models.Producto).filter(models.Producto.id == product_id, models.Producto.tenant_id == tenant_id).first()
    if not product: _not_found("Producto interno")
    return product


def _warehouse(db: Session, tenant_id: int, warehouse_id: int | None):
    if warehouse_id is None: return None
    warehouse = db.query(models.Warehouse).filter(models.Warehouse.id == warehouse_id, models.Warehouse.tenant_id == tenant_id, models.Warehouse.is_active.is_(True)).first()
    if not warehouse: _not_found("Almacén")
    return warehouse


def create_category(db: Session, tenant_id: int, data: dict, actor_id: int):
    site = get_site(db, tenant_id); require_entitlement(db, tenant_id); _asset(db, site, data.get("image_asset_id"))
    category = models.CatalogCategory(tenant_id=tenant_id, catalog_id=site.id, **data)
    db.add(category); _touch(site); _audit(db, actor_id, "catalog.category.created", "catalog_category", None)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(status_code=409, detail="Ese slug de categoría ya está en uso.")
    db.refresh(category); return category


def update_category(db: Session, tenant_id: int, category_id: int, data: dict, actor_id: int):
    site = get_site(db, tenant_id); require_entitlement(db, tenant_id); category = _category(db, site, category_id); _asset(db, site, data.get("image_asset_id"))
    for key, value in data.items(): setattr(category, key, value)
    _touch(site); _audit(db, actor_id, "catalog.category.updated", "catalog_category", category.id)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(status_code=409, detail="Ese slug de categoría ya está en uso.")
    db.refresh(category); return category


def delete_category(db: Session, tenant_id: int, category_id: int, actor_id: int):
    site = get_site(db, tenant_id); require_entitlement(db, tenant_id); category = _category(db, site, category_id)
    category.deleted_at = datetime.now(); category.published = False
    db.query(models.CatalogItem).filter(models.CatalogItem.category_id == category.id).update({"category_id": None})
    _touch(site); _audit(db, actor_id, "catalog.category.deleted", "catalog_category", category.id); db.commit()


def _validate_item(db: Session, site, tenant_id: int, data: dict):
    _product(db, tenant_id, data.get("product_id")); _category(db, site, data.get("category_id")); _warehouse(db, tenant_id, data.get("inventory_warehouse_id"))


def create_item(db: Session, tenant_id: int, data: dict, actor_id: int):
    site = get_site(db, tenant_id); require_entitlement(db, tenant_id); _validate_item(db, site, tenant_id, data)
    item = models.CatalogItem(tenant_id=tenant_id, catalog_id=site.id, **data)
    db.add(item); _touch(site); _audit(db, actor_id, "catalog.item.created", "catalog_item", None)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(status_code=409, detail="Ese slug de ítem ya está en uso.")
    db.refresh(item); return item


def update_item(db: Session, tenant_id: int, item_id: int, data: dict, actor_id: int):
    site = get_site(db, tenant_id); require_entitlement(db, tenant_id)
    item = db.query(models.CatalogItem).filter(models.CatalogItem.id == item_id, models.CatalogItem.catalog_id == site.id, models.CatalogItem.deleted_at.is_(None)).first()
    if not item: _not_found("Ítem")
    merged = {field: getattr(item, field) for field in ("product_id", "category_id", "inventory_warehouse_id")}; merged.update(data); _validate_item(db, site, tenant_id, merged)
    for key, value in data.items(): setattr(item, key, value)
    _touch(site); _audit(db, actor_id, "catalog.item.updated", "catalog_item", item.id)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(status_code=409, detail="Ese slug de ítem ya está en uso.")
    db.refresh(item); return item


def delete_item(db: Session, tenant_id: int, item_id: int, actor_id: int):
    site = get_site(db, tenant_id); require_entitlement(db, tenant_id); item = db.query(models.CatalogItem).filter(models.CatalogItem.id == item_id, models.CatalogItem.catalog_id == site.id, models.CatalogItem.deleted_at.is_(None)).first()
    if not item: _not_found("Ítem")
    item.deleted_at = datetime.now(); item.published = False; _touch(site); _audit(db, actor_id, "catalog.item.deleted", "catalog_item", item.id); db.commit()


def create_collection(db: Session, tenant_id: int, data: dict, actor_id: int):
    site = get_site(db, tenant_id); require_entitlement(db, tenant_id); _asset(db, site, data.get("cover_asset_id"))
    collection = models.CatalogCollection(tenant_id=tenant_id, catalog_id=site.id, **data)
    db.add(collection); _touch(site); _audit(db, actor_id, "catalog.collection.created", "catalog_collection", None)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(status_code=409, detail="Ese slug de colección ya está en uso.")
    db.refresh(collection); return collection


def update_collection(db: Session, tenant_id: int, collection_id: int, data: dict, actor_id: int):
    site = get_site(db, tenant_id); require_entitlement(db, tenant_id)
    collection = db.query(models.CatalogCollection).filter(models.CatalogCollection.id == collection_id, models.CatalogCollection.catalog_id == site.id, models.CatalogCollection.deleted_at.is_(None)).first()
    if not collection: _not_found("Colección")
    _asset(db, site, data.get("cover_asset_id"))
    for key, value in data.items(): setattr(collection, key, value)
    _touch(site); _audit(db, actor_id, "catalog.collection.updated", "catalog_collection", collection.id)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(status_code=409, detail="Ese slug de colección ya está en uso.")
    db.refresh(collection); return collection


def delete_collection(db: Session, tenant_id: int, collection_id: int, actor_id: int):
    site = get_site(db, tenant_id); require_entitlement(db, tenant_id)
    collection = db.query(models.CatalogCollection).filter(models.CatalogCollection.id == collection_id, models.CatalogCollection.catalog_id == site.id, models.CatalogCollection.deleted_at.is_(None)).first()
    if not collection: _not_found("Colección")
    collection.deleted_at = datetime.now(); collection.published = False
    _touch(site); _audit(db, actor_id, "catalog.collection.deleted", "catalog_collection", collection.id); db.commit()


def replace_collection_items(db: Session, tenant_id: int, collection_id: int, item_ids: list[int], actor_id: int):
    site = get_site(db, tenant_id); require_entitlement(db, tenant_id)
    collection = db.query(models.CatalogCollection).filter(models.CatalogCollection.id == collection_id, models.CatalogCollection.catalog_id == site.id, models.CatalogCollection.deleted_at.is_(None)).first()
    if not collection: _not_found("Colección")
    items = db.query(models.CatalogItem).filter(models.CatalogItem.catalog_id == site.id, models.CatalogItem.id.in_(item_ids), models.CatalogItem.deleted_at.is_(None)).all() if item_ids else []
    if len(items) != len(item_ids): _not_found("Ítem")
    db.query(models.CatalogCollectionItem).filter(models.CatalogCollectionItem.collection_id == collection.id).delete(synchronize_session=False)
    for order, item_id in enumerate(item_ids): db.add(models.CatalogCollectionItem(tenant_id=tenant_id, collection_id=collection.id, item_id=item_id, display_order=order))
    _touch(site); _audit(db, actor_id, "catalog.collection.items_replaced", "catalog_collection", collection.id); db.commit(); return collection
