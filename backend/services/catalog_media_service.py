"""Server-only validation and immutable WebP variants for catalog assets."""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from uuid import uuid4
from datetime import datetime

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from config import settings
from supabase_client import get_supabase_client
import models

ALLOWED_TYPES = {"JPEG", "PNG", "WEBP"}
VARIANT_WIDTHS = (480, 960, 1600)


def _invalid(detail: str):
    raise HTTPException(status_code=422, detail=detail)


async def read_catalog_image(upload: UploadFile) -> tuple[Image.Image, bytes]:
    payload = await upload.read(settings.MAX_CATALOG_UPLOAD_BYTES + 1)
    if not payload or len(payload) > settings.MAX_CATALOG_UPLOAD_BYTES:
        _invalid("La imagen debe pesar como máximo 5 MB.")
    try:
        image = Image.open(BytesIO(payload)); image.verify()
        image = Image.open(BytesIO(payload)); image = ImageOps.exif_transpose(image)
    except (UnidentifiedImageError, OSError, ValueError):
        _invalid("El archivo no es una imagen válida.")
    if image.format not in ALLOWED_TYPES or image.width > 6000 or image.height > 6000:
        _invalid("Solo se aceptan JPEG, PNG o WebP de hasta 6000×6000 px.")
    return image.convert("RGB"), payload


def _webp_variants(image: Image.Image) -> dict[int, bytes]:
    variants = {}
    for width in VARIANT_WIDTHS:
        copy = image.copy(); copy.thumbnail((width, width * 4), Image.Resampling.LANCZOS)
        output = BytesIO(); copy.save(output, "WEBP", quality=84, method=6)
        variants[width] = output.getvalue()
    return variants


def upload_catalog_asset(db: Session, site: models.CatalogSite, image: Image.Image, original: bytes, alt_text: str | None):
    asset_public_id = str(uuid4())
    variants = _webp_variants(image)
    client = get_supabase_client(); bucket = settings.CATALOG_PUBLIC_STORAGE_BUCKET
    metadata: dict[str, dict] = {}
    try:
        for width, content in variants.items():
            path = f"catalogs/{site.public_id}/{asset_public_id}/{width}.webp"
            client.storage.from_(bucket).upload(path, content, {"content-type": "image/webp", "x-upsert": "false", "cache-control": "public, max-age=31536000, immutable"})
            metadata[str(width)] = {"object_key": path, "width": min(width, image.width), "height": round(image.height * min(width, image.width) / image.width)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail="No se pudo guardar la imagen del catálogo.") from exc
    largest = metadata["1600"]
    asset = models.CatalogAsset(
        public_id=asset_public_id, tenant_id=site.tenant_id, catalog_id=site.id, storage_provider="supabase", bucket=bucket,
        object_key=largest["object_key"], content_type="image/webp", size_bytes=len(variants[1600]), width=image.width, height=image.height,
        checksum=sha256(original).hexdigest(), alt_text=alt_text, variants=metadata,
    )
    db.add(asset); site.content_version += 1; db.commit(); db.refresh(asset)
    return asset


def delete_catalog_asset(db: Session, site: models.CatalogSite, asset_id: int) -> None:
    asset = db.query(models.CatalogAsset).filter(models.CatalogAsset.id == asset_id, models.CatalogAsset.catalog_id == site.id, models.CatalogAsset.deleted_at.is_(None)).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset no encontrado.")
    asset.deleted_at = datetime.now(); site.content_version += 1; db.commit()


def replace_item_assets(db: Session, site: models.CatalogSite, item_id: int, asset_ids: list[int]) -> None:
    item = db.query(models.CatalogItem).filter(models.CatalogItem.id == item_id, models.CatalogItem.catalog_id == site.id, models.CatalogItem.deleted_at.is_(None)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Ítem no encontrado.")
    assets = db.query(models.CatalogAsset).filter(models.CatalogAsset.catalog_id == site.id, models.CatalogAsset.id.in_(asset_ids), models.CatalogAsset.deleted_at.is_(None)).all()
    if len(assets) != len(asset_ids):
        raise HTTPException(status_code=404, detail="Una o más imágenes no pertenecen al catálogo.")
    db.query(models.CatalogItemAsset).filter(models.CatalogItemAsset.item_id == item.id).delete(synchronize_session=False)
    for order, asset_id in enumerate(asset_ids):
        db.add(models.CatalogItemAsset(tenant_id=site.tenant_id, item_id=item.id, asset_id=asset_id, role="cover" if order == 0 else "gallery", display_order=order))
    site.content_version += 1; db.commit()
