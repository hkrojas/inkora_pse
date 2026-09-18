"""Authenticated administration API for the tenant commercial catalog."""
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from access_control import ROLE_ADMIN, ROLE_OPERADOR, assert_user_has_roles
from api_dependencies import get_current_user, get_db_tenant
import models
import schemas
from services import catalog_service
from services import catalog_media_service

router = APIRouter(prefix="/catalog-admin", tags=["catalog-admin"])


def _editor(user: models.User = Depends(get_current_user)):
    return assert_user_has_roles(user, {ROLE_ADMIN, ROLE_OPERADOR}, detail="No tiene permisos para administrar el catálogo.")


@router.get("/catalog")
def read_catalog(user: models.User = Depends(get_current_user), db: Session = Depends(get_db_tenant)):
    catalog_service.require_entitlement(db, user.tenant_id)
    return catalog_service.get_site(db, user.tenant_id)


@router.post("/catalog", response_model=schemas.CatalogSiteResponse, status_code=201)
def create_catalog(data: schemas.CatalogSiteCreate, user: models.User = Depends(_editor), db: Session = Depends(get_db_tenant)):
    assert_user_has_roles(user, {ROLE_ADMIN}, detail="Solo administradores pueden crear el catálogo.")
    return catalog_service.create_site(db, user.tenant_id, data.model_dump(), user.id)


@router.patch("/catalog", response_model=schemas.CatalogSiteResponse)
def patch_catalog(data: schemas.CatalogSiteUpdate, user: models.User = Depends(_editor), db: Session = Depends(get_db_tenant)):
    assert_user_has_roles(user, {ROLE_ADMIN}, detail="Solo administradores pueden cambiar la configuración del catálogo.")
    return catalog_service.update_site(db, user.tenant_id, data.model_dump(exclude_unset=True), user.id)


@router.post("/catalog/publish", response_model=schemas.CatalogSiteResponse)
def publish_catalog(user: models.User = Depends(_editor), db: Session = Depends(get_db_tenant)):
    assert_user_has_roles(user, {ROLE_ADMIN}, detail="Solo administradores pueden publicar el catálogo.")
    return catalog_service.set_published(db, user.tenant_id, True, user.id)


@router.post("/catalog/unpublish", response_model=schemas.CatalogSiteResponse)
def unpublish_catalog(user: models.User = Depends(_editor), db: Session = Depends(get_db_tenant)):
    assert_user_has_roles(user, {ROLE_ADMIN}, detail="Solo administradores pueden despublicar el catálogo.")
    return catalog_service.set_published(db, user.tenant_id, False, user.id)


@router.get("/categories")
def list_categories(user: models.User = Depends(get_current_user), db: Session = Depends(get_db_tenant)):
    site = catalog_service.get_site(db, user.tenant_id)
    return db.query(models.CatalogCategory).filter(models.CatalogCategory.catalog_id == site.id, models.CatalogCategory.deleted_at.is_(None)).order_by(models.CatalogCategory.display_order, models.CatalogCategory.id).all()


@router.post("/categories", status_code=201)
def create_category(data: schemas.CatalogCategoryCreate, user: models.User = Depends(_editor), db: Session = Depends(get_db_tenant)):
    return catalog_service.create_category(db, user.tenant_id, data.model_dump(), user.id)


@router.put("/categories/{category_id}")
def update_category(category_id: int, data: schemas.CatalogCategoryCreate, user: models.User = Depends(_editor), db: Session = Depends(get_db_tenant)):
    return catalog_service.update_category(db, user.tenant_id, category_id, data.model_dump(), user.id)


@router.delete("/categories/{category_id}", status_code=204)
def remove_category(category_id: int, user: models.User = Depends(_editor), db: Session = Depends(get_db_tenant)):
    catalog_service.delete_category(db, user.tenant_id, category_id, user.id)


@router.get("/items")
def list_items(user: models.User = Depends(get_current_user), db: Session = Depends(get_db_tenant)):
    site = catalog_service.get_site(db, user.tenant_id)
    return db.query(models.CatalogItem).filter(models.CatalogItem.catalog_id == site.id, models.CatalogItem.deleted_at.is_(None)).order_by(models.CatalogItem.display_order, models.CatalogItem.id).all()


@router.post("/items", response_model=schemas.CatalogItemResponse, status_code=201)
def create_item(data: schemas.CatalogItemCreate, user: models.User = Depends(_editor), db: Session = Depends(get_db_tenant)):
    return catalog_service.create_item(db, user.tenant_id, data.model_dump(), user.id)


@router.put("/items/{item_id}", response_model=schemas.CatalogItemResponse)
def update_item(item_id: int, data: schemas.CatalogItemCreate, user: models.User = Depends(_editor), db: Session = Depends(get_db_tenant)):
    return catalog_service.update_item(db, user.tenant_id, item_id, data.model_dump(), user.id)


@router.delete("/items/{item_id}", status_code=204)
def remove_item(item_id: int, user: models.User = Depends(_editor), db: Session = Depends(get_db_tenant)):
    catalog_service.delete_item(db, user.tenant_id, item_id, user.id)


@router.get("/collections")
def list_collections(user: models.User = Depends(get_current_user), db: Session = Depends(get_db_tenant)):
    site = catalog_service.get_site(db, user.tenant_id)
    return db.query(models.CatalogCollection).filter(models.CatalogCollection.catalog_id == site.id, models.CatalogCollection.deleted_at.is_(None)).order_by(models.CatalogCollection.display_order, models.CatalogCollection.id).all()


@router.post("/collections", status_code=201)
def create_collection(data: schemas.CatalogCollectionCreate, user: models.User = Depends(_editor), db: Session = Depends(get_db_tenant)):
    return catalog_service.create_collection(db, user.tenant_id, data.model_dump(), user.id)


@router.post("/assets", status_code=201)
async def upload_asset(
    file: UploadFile = File(...), alt_text: str | None = Form(default=None, max_length=180),
    user: models.User = Depends(_editor), db: Session = Depends(get_db_tenant),
):
    catalog_service.require_entitlement(db, user.tenant_id)
    site = catalog_service.get_site(db, user.tenant_id)
    image, original = await catalog_media_service.read_catalog_image(file)
    return catalog_media_service.upload_catalog_asset(db, site, image, original, alt_text)


@router.delete("/assets/{asset_id}", status_code=204)
def remove_asset(asset_id: int, user: models.User = Depends(_editor), db: Session = Depends(get_db_tenant)):
    catalog_service.require_entitlement(db, user.tenant_id)
    catalog_media_service.delete_catalog_asset(db, catalog_service.get_site(db, user.tenant_id), asset_id)


@router.put("/items/{item_id}/assets", status_code=204)
def replace_item_assets(item_id: int, data: schemas.CatalogItemAssetsUpdate, user: models.User = Depends(_editor), db: Session = Depends(get_db_tenant)):
    catalog_service.require_entitlement(db, user.tenant_id)
    catalog_media_service.replace_item_assets(db, catalog_service.get_site(db, user.tenant_id), item_id, data.asset_ids)


@router.put("/collections/{collection_id}")
def update_collection(collection_id: int, data: schemas.CatalogCollectionCreate, user: models.User = Depends(_editor), db: Session = Depends(get_db_tenant)):
    return catalog_service.update_collection(db, user.tenant_id, collection_id, data.model_dump(), user.id)


@router.delete("/collections/{collection_id}", status_code=204)
def remove_collection(collection_id: int, user: models.User = Depends(_editor), db: Session = Depends(get_db_tenant)):
    catalog_service.delete_collection(db, user.tenant_id, collection_id, user.id)


@router.put("/collections/{collection_id}/items")
def replace_collection_items(collection_id: int, data: schemas.CatalogCollectionItemsUpdate, user: models.User = Depends(_editor), db: Session = Depends(get_db_tenant)):
    return catalog_service.replace_collection_items(db, user.tenant_id, collection_id, data.item_ids, user.id)
