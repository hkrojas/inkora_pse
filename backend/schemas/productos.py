"""schemas/productos.py — Producto, Insumo, RecetaBOM, Proveedor, OrdenProduccion, Dashboard."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductoBase(BaseModel):
    codigo_interno: Optional[str] = None
    nombre: str
    descripcion: Optional[str] = None
    precio_unitario: Decimal = Field(..., gt=0)
    unidad_medida: str = "NIU"
    tipo_afectacion_igv: str = "10"


class ProductoCreate(ProductoBase):
    pass


class ProductoResponse(ProductoBase):
    id: int
    valor_unitario: Decimal
    model_config = ConfigDict(from_attributes=True)


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
