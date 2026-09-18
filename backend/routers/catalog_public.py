"""Unauthenticated, published-only catalog endpoints."""
from contextlib import contextmanager

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db, reset_tenant_context
import models
from services import catalog_public_service as public

router = APIRouter(prefix="/public/catalogs", tags=["catalog-public"])


@contextmanager
def _catalog_scope(db: Session, slug: str):
    site, token = public.resolve_published_catalog(db, slug)
    try: yield site
    finally: reset_tenant_context(token)


def _response(site, data):
    return JSONResponse(data, headers={"Cache-Control": "public, s-maxage=60, stale-while-revalidate=300", "ETag": f'W/"catalog-{site.content_version}"'})


@router.get("/{catalog_slug}")
def get_catalog(catalog_slug: str, db: Session = Depends(get_db)):
    with _catalog_scope(db, catalog_slug) as site:
        return _response(site, public.public_site(site))


@router.get("/{catalog_slug}/items")
def list_items(catalog_slug: str, page: int = Query(1, ge=1), limit: int = Query(15, ge=1, le=50), q: str | None = Query(None, max_length=80), category: str | None = None, collection: str | None = None, featured: bool | None = None, db: Session = Depends(get_db)):
    with _catalog_scope(db, catalog_slug) as site:
        query = db.query(models.CatalogItem).filter(models.CatalogItem.catalog_id == site.id, models.CatalogItem.published.is_(True), models.CatalogItem.deleted_at.is_(None))
        if q: query = query.filter(or_(models.CatalogItem.public_name.ilike(f"%{q.strip()}%"), models.CatalogItem.short_description.ilike(f"%{q.strip()}%")))
        if category:
            query = query.join(models.CatalogCategory).filter(models.CatalogCategory.slug == category, models.CatalogCategory.published.is_(True), models.CatalogCategory.deleted_at.is_(None))
        if collection:
            query = query.join(models.CatalogCollectionItem).join(models.CatalogCollection).filter(models.CatalogCollection.slug == collection, models.CatalogCollection.published.is_(True), models.CatalogCollection.deleted_at.is_(None))
        if featured is not None: query = query.filter(models.CatalogItem.featured == featured)
        total = query.count(); rows = query.order_by(models.CatalogItem.display_order, models.CatalogItem.id).offset((page - 1) * limit).limit(limit).all()
        return _response(site, {"items": [public.public_item(db, item) for item in rows], "page": page, "limit": limit, "total": total})


@router.get("/{catalog_slug}/items/{item_slug}")
def get_item(catalog_slug: str, item_slug: str, db: Session = Depends(get_db)):
    with _catalog_scope(db, catalog_slug) as site:
        item = db.query(models.CatalogItem).filter(models.CatalogItem.catalog_id == site.id, models.CatalogItem.slug == item_slug, models.CatalogItem.published.is_(True), models.CatalogItem.deleted_at.is_(None)).first()
        if not item: from fastapi import HTTPException; raise HTTPException(404, "Ítem no encontrado.")
        return _response(site, public.public_item(db, item))


@router.get("/{catalog_slug}/categories/{category_slug}")
def get_category(catalog_slug: str, category_slug: str, db: Session = Depends(get_db)):
    with _catalog_scope(db, catalog_slug) as site:
        category = db.query(models.CatalogCategory).filter(models.CatalogCategory.catalog_id == site.id, models.CatalogCategory.slug == category_slug, models.CatalogCategory.published.is_(True), models.CatalogCategory.deleted_at.is_(None)).first()
        if not category: from fastapi import HTTPException; raise HTTPException(404, "Categoría no encontrada.")
        return _response(site, {"slug": category.slug, "name": category.name, "description": category.description, "image": public.asset_view(category.image_asset)})


@router.get("/{catalog_slug}/collections/{collection_slug}")
def get_collection(catalog_slug: str, collection_slug: str, db: Session = Depends(get_db)):
    with _catalog_scope(db, catalog_slug) as site:
        collection = db.query(models.CatalogCollection).filter(models.CatalogCollection.catalog_id == site.id, models.CatalogCollection.slug == collection_slug, models.CatalogCollection.published.is_(True), models.CatalogCollection.deleted_at.is_(None)).first()
        if not collection: from fastapi import HTTPException; raise HTTPException(404, "Colección no encontrada.")
        return _response(site, {"slug": collection.slug, "name": collection.name, "description": collection.description, "image": public.asset_view(collection.cover_asset)})
