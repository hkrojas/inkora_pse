"""schemas/productos.py — Producto, Insumo, RecetaBOM, Proveedor, OrdenProduccion, Dashboard."""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fiscal_catalogs import (
    PRODUCT_DESCRIPTION_MAX_LENGTH,
    PRODUCT_INTERNAL_CODE_MAX_LENGTH,
    PRODUCT_NAME_MAX_LENGTH,
    normalize_internal_product_code,
    normalize_sunat_unit_code,
    normalize_tax_affectation_code,
)


class ProductoBase(BaseModel):
    codigo_interno: Optional[str] = Field(
        default=None,
        max_length=PRODUCT_INTERNAL_CODE_MAX_LENGTH,
    )
    nombre: str = Field(..., min_length=1, max_length=PRODUCT_NAME_MAX_LENGTH)
    descripcion: Optional[str] = Field(
        default=None,
        max_length=PRODUCT_DESCRIPTION_MAX_LENGTH,
    )
    moneda: str = "PEN"
    unidad_medida: str = "NIU"
    tipo_afectacion_igv: str = "10"
    item_type: str = "inventory"
    inventory_enabled: bool = True

    @field_validator("item_type")
    @classmethod
    def validate_item_type(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in {"unclassified", "inventory", "service"}:
            raise ValueError("El tipo debe ser unclassified, inventory o service")
        return normalized

    @field_validator("nombre")
    @classmethod
    def normalize_nombre(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El nombre del producto es obligatorio")
        return normalized

    @field_validator("codigo_interno", "descripcion", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("codigo_interno")
    @classmethod
    def normalize_codigo(cls, value: Optional[str]) -> Optional[str]:
        return normalize_internal_product_code(value)

    @field_validator("moneda")
    @classmethod
    def validate_moneda(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"PEN", "USD"}:
            raise ValueError("La moneda debe ser PEN o USD")
        return normalized

    @field_validator("unidad_medida")
    @classmethod
    def normalize_unidad_medida(cls, value: str) -> str:
        return normalize_sunat_unit_code(value)

    @field_validator("tipo_afectacion_igv")
    @classmethod
    def validate_tipo_afectacion_igv(cls, value: str) -> str:
        return normalize_tax_affectation_code(value)


class ProductoInventarioInicial(BaseModel):
    warehouse_id: Optional[int] = None
    opening_stock: Decimal = Field(default=Decimal("0"), ge=0)
    minimum_stock: Decimal = Field(default=Decimal("0"), ge=0)


class ProductoCreate(ProductoBase):
    precio_unitario: Decimal = Field(..., gt=0)
    precio_incluye_igv: bool = True
    inventario_inicial: Optional[ProductoInventarioInicial] = None


class ProductoResponse(ProductoBase):
    id: int
    precio_unitario: Decimal
    valor_unitario: Decimal
    model_config = ConfigDict(from_attributes=True)


class ProductoSearchResponse(BaseModel):
    id: int
    codigo_interno: Optional[str] = None
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    precio_unitario: Decimal
    valor_unitario: Decimal
    moneda: str = "PEN"
    unidad_medida: str = "NIU"
    tipo_afectacion_igv: str = "10"
    model_config = ConfigDict(from_attributes=True)


class ProductoPageResponse(BaseModel):
    items: List[ProductoResponse]
    total: int
    skip: int
    limit: int
    counts: Dict[str, int]


class InsumoBase(BaseModel):
    nombre: str
    unidad_compra: str
    unidad_consumo: str
    factor_conversion: Decimal = Field(..., gt=0)
    costo_promedio: Decimal = Decimal("0.00")
    stock_actual: Decimal = Decimal("0.00")
    umbral_minimo: Decimal = Decimal("50.00")


class InsumoCreate(InsumoBase):
    pass


class InsumoResponse(InsumoBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class RecetaBOMBase(BaseModel):
    insumo_id: int
    cantidad_base_necesaria: Decimal = Field(..., gt=0)
    porcentaje_merma_estandar: Decimal = Decimal("0.00")


class RecetaBOMCreate(RecetaBOMBase):
    producto_id: int


class RecetaBOMResponse(RecetaBOMBase):
    id: int
    producto_id: int
    insumo: Optional[InsumoResponse] = None
    model_config = ConfigDict(from_attributes=True)


class AlertaInventarioResponse(BaseModel):
    id: int
    insumo: Optional[InsumoResponse] = None
    mensaje: str
    fecha_creacion: datetime
    resuelta: bool
    model_config = ConfigDict(from_attributes=True)


class DashboardStatsResponse(BaseModel):
    ingresos_totales: Decimal
    saldos_por_cobrar: Decimal
    saldo_vencido: Decimal = Decimal("0.00")
    costos_tercerizacion: Decimal
    documentos_emitidos_mes: int = 0
    documentos_vencidos: int = 0
    top_productos: List[str]


class ProveedorBase(BaseModel):
    razon_social: str
    ruc: str
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    tipo_servicio: str


class ProveedorCreate(ProveedorBase):
    pass


class ProveedorUpdate(BaseModel):
    razon_social: Optional[str] = None
    ruc: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    tipo_servicio: Optional[str] = None


class ProveedorResponse(ProveedorBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class OrdenProduccionDetalleResponse(BaseModel):
    id: int
    insumo_id: int
    insumo: Optional[InsumoResponse] = None
    cantidad_requerida_neta: Decimal
    cantidad_merma: Decimal
    cantidad_total_descontar: Decimal
    model_config = ConfigDict(from_attributes=True)


class OrdenProduccionResponse(BaseModel):
    id: int
    cotizacion_id: int
    estado: str
    fecha_inicio: datetime
    fecha_fin: Optional[datetime] = None
    tipo_produccion: str
    proveedor_id: Optional[int] = None
    proveedor: Optional[ProveedorResponse] = None
    costo_tercerizado: Optional[Decimal] = None
    detalles: List[OrdenProduccionDetalleResponse] = []
    model_config = ConfigDict(from_attributes=True)
