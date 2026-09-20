"""Validated contracts for the Inkora Catalog domain."""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from schemas._base import StrictInputModel


CatalogEntitlementStatus = Literal["trial", "active", "suspended", "cancelled"]
CatalogSiteStatus = Literal["draft", "published", "suspended"]
CatalogItemKind = Literal["internal_product", "catalog_product", "service", "solution"]
CatalogPriceMode = Literal["fixed", "starting_from", "range", "quotation", "hidden"]
CatalogPriceSource = Literal["manual", "product"]
CatalogAvailabilitySource = Literal["manual", "inventory"]
CatalogAvailabilityStatus = Literal[
    "available", "low_stock", "out_of_stock", "made_to_order", "consult", "coming_soon"
]

_SLUG_INVALID = re.compile(r"[^a-z0-9]+")


def normalize_catalog_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    normalized = _SLUG_INVALID.sub("-", normalized.lower()).strip("-")
    if not normalized:
        raise ValueError("El slug debe incluir letras o numeros.")
    return normalized


class CatalogEntitlementUpdate(StrictInputModel):
    status: CatalogEntitlementStatus


class CatalogThemeConfig(StrictInputModel):
    primaryColor: str = Field(default="#2563EB", pattern=r"^#[0-9A-Fa-f]{6}$")
    secondaryColor: str = Field(default="#0F172A", pattern=r"^#[0-9A-Fa-f]{6}$")
    backgroundColor: str = Field(default="#FFFFFF", pattern=r"^#[0-9A-Fa-f]{6}$")
    fontFamily: Literal["Inter", "Manrope", "Poppins"] = "Inter"
    cardRadius: int = Field(default=16, ge=0, le=32)
    buttonStyle: Literal["rounded", "pill", "square"] = "rounded"
    showHero: bool = True
    showPrices: bool = True
    showAvailability: bool = True


class CatalogSiteCreate(StrictInputModel):
    slug: str = Field(..., min_length=2, max_length=120)
    display_name: str = Field(..., min_length=2, max_length=180)
    headline: Optional[str] = Field(default=None, max_length=220)
    description: Optional[str] = None
    business_type: Optional[str] = Field(default=None, max_length=80)
    whatsapp_number: Optional[str] = Field(default=None, max_length=32)
    default_whatsapp_message: Optional[str] = None
    social_links: dict[str, str] = Field(default_factory=dict)
    template_key: Literal["modern-grid", "minimal", "commercial"] = "modern-grid"
    theme_config: CatalogThemeConfig = Field(default_factory=CatalogThemeConfig)
    seo_title: Optional[str] = Field(default=None, max_length=180)
    seo_description: Optional[str] = Field(default=None, max_length=320)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        return normalize_catalog_slug(value)


class CatalogSiteUpdate(StrictInputModel):
    display_name: Optional[str] = Field(default=None, min_length=2, max_length=180)
    headline: Optional[str] = Field(default=None, max_length=220)
    description: Optional[str] = None
    business_type: Optional[str] = Field(default=None, max_length=80)
    whatsapp_number: Optional[str] = Field(default=None, max_length=32)
    default_whatsapp_message: Optional[str] = None
    social_links: Optional[dict[str, str]] = None
    template_key: Optional[Literal["modern-grid", "minimal", "commercial"]] = None
    theme_config: Optional[CatalogThemeConfig] = None
    seo_title: Optional[str] = Field(default=None, max_length=180)
    seo_description: Optional[str] = Field(default=None, max_length=320)


class CatalogCategoryCreate(StrictInputModel):
    name: str = Field(..., min_length=2, max_length=120)
    slug: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = None
    image_asset_id: Optional[int] = Field(default=None, gt=0)
    published: bool = True
    display_order: int = Field(default=0, ge=0)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        return normalize_catalog_slug(value)


class CatalogItemCreate(StrictInputModel):
    product_id: Optional[int] = Field(default=None, gt=0)
    category_id: Optional[int] = Field(default=None, gt=0)
    kind: CatalogItemKind = "catalog_product"
    public_name: str = Field(..., min_length=2, max_length=180)
    slug: str = Field(..., min_length=2, max_length=160)
    short_description: Optional[str] = Field(default=None, max_length=320)
    full_description: Optional[str] = None
    price_mode: CatalogPriceMode = "quotation"
    price_source: CatalogPriceSource = "manual"
    price_amount: Optional[Decimal] = Field(default=None, gt=0)
    price_min: Optional[Decimal] = Field(default=None, gt=0)
    price_max: Optional[Decimal] = Field(default=None, gt=0)
    currency: Literal["PEN", "USD"] = "PEN"
    availability_source: CatalogAvailabilitySource = "manual"
    availability_status: CatalogAvailabilityStatus = "consult"
    inventory_warehouse_id: Optional[int] = Field(default=None, gt=0)
    low_stock_threshold: Decimal = Field(default=Decimal("0"), ge=0)
    minimum_quantity: Decimal = Field(default=Decimal("1"), gt=0)
    featured: bool = False
    published: bool = False
    display_order: int = Field(default=0, ge=0)
    whatsapp_message: Optional[str] = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        return normalize_catalog_slug(value)

    @model_validator(mode="after")
    def validate_pricing(self):
        if self.price_source == "product" and not self.product_id:
            raise ValueError("El precio sincronizado requiere un producto interno.")
        if self.price_mode == "fixed" and self.price_source == "manual" and not self.price_amount:
            raise ValueError("El precio fijo requiere price_amount.")
        if self.price_mode == "starting_from" and self.price_source == "manual" and not (self.price_min or self.price_amount):
            raise ValueError("El precio desde requiere price_min o price_amount.")
        if self.price_mode == "range":
            if not self.price_min or not self.price_max:
                raise ValueError("El rango requiere price_min y price_max.")
            if self.price_min > self.price_max:
                raise ValueError("price_min no puede ser mayor que price_max.")
        if self.price_mode in {"quotation", "hidden"} and any(
            value is not None for value in (self.price_amount, self.price_min, self.price_max)
        ):
            raise ValueError("Los precios quotation y hidden no aceptan importes publicos.")
        if self.availability_source == "inventory" and not self.product_id:
            raise ValueError("La disponibilidad de inventario requiere un producto interno.")
        return self


class CatalogCollectionCreate(StrictInputModel):
    name: str = Field(..., min_length=2, max_length=120)
    slug: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = None
    cover_asset_id: Optional[int] = Field(default=None, gt=0)
    published: bool = True
    display_order: int = Field(default=0, ge=0)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        return normalize_catalog_slug(value)


class CatalogCollectionItemsUpdate(StrictInputModel):
    item_ids: list[int] = Field(default_factory=list, max_length=100)

    @field_validator("item_ids")
    @classmethod
    def validate_unique_items(cls, value: list[int]) -> list[int]:
        if any(item_id <= 0 for item_id in value) or len(value) != len(set(value)):
            raise ValueError("Los ítems de una colección deben ser IDs positivos y únicos.")
        return value


class CatalogItemAssetsUpdate(StrictInputModel):
    asset_ids: list[int] = Field(..., min_length=1, max_length=8)

    @field_validator("asset_ids")
    @classmethod
    def validate_unique_assets(cls, value: list[int]) -> list[int]:
        if any(asset_id <= 0 for asset_id in value) or len(value) != len(set(value)):
            raise ValueError("Las imágenes deben ser IDs positivos y únicos.")
        return value


class CatalogEntitlementResponse(BaseModel):
    product_code: str
    status: CatalogEntitlementStatus
    enabled_at: Optional[datetime] = None
    disabled_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CatalogSiteResponse(BaseModel):
    id: int
    public_id: str
    tenant_id: int
    slug: str
    display_name: str
    status: CatalogSiteStatus
    content_version: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CatalogItemResponse(BaseModel):
    id: int
    tenant_id: int
    catalog_id: int
    product_id: Optional[int]
    public_name: str
    slug: str
    price_mode: CatalogPriceMode
    price_source: CatalogPriceSource
    availability_source: CatalogAvailabilitySource
    availability_status: CatalogAvailabilityStatus
    published: bool
    model_config = ConfigDict(from_attributes=True)


class CatalogPublicItemResponse(BaseModel):
    slug: str
    public_name: str
    short_description: Optional[str] = None
    price_mode: CatalogPriceMode
    currency: str
    availability_status: CatalogAvailabilityStatus
    minimum_quantity: Decimal
    featured: bool
    image: Optional[dict[str, Any]] = None
