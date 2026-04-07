"""models/frozen.py — MRP: Insumo, RecetaBOM, Proveedor, OrdenProduccion, OrdenProduccionDetalle, AlertaInventario."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from database import Base


class Insumo(Base):
    __tablename__ = "insumos"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="insumos")

    nombre = Column(String, index=True)
    unidad_compra = Column(String)
    unidad_consumo = Column(String)
    factor_conversion = Column(Numeric(12, 4))
    costo_promedio = Column(Numeric(12, 2), default=0)
    stock_actual = Column(Numeric(12, 2), default=0)
    umbral_minimo = Column(Numeric(12, 2), default=50.0)

    recetas = relationship("RecetaBOM", back_populates="insumo")


class RecetaBOM(Base):
    __tablename__ = "recetas_bom"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="recetas")

    producto_id = Column(Integer, ForeignKey("productos.id"))
    producto = relationship("Producto", back_populates="receta")

    insumo_id = Column(Integer, ForeignKey("insumos.id"))
    insumo = relationship("Insumo", back_populates="recetas")

    cantidad_base_necesaria = Column(Numeric(12, 4))
    porcentaje_merma_estandar = Column(Numeric(5, 2), default=0.0)


class Proveedor(Base):
    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="proveedores")

    razon_social = Column(String, index=True)
    ruc = Column(String, index=True)
    direccion = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    email = Column(String, nullable=True)
    tipo_servicio = Column(String, index=True)


class OrdenProduccion(Base):
    __tablename__ = "ordenes_produccion"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="ordenes_produccion")

    cotizacion_id = Column(Integer, ForeignKey("cotizaciones.id"))
    cotizacion = relationship("Cotizacion")

    estado = Column(String, default="en_cola")
    fecha_inicio = Column(DateTime, default=datetime.now)
    fecha_fin = Column(DateTime, nullable=True)

    tipo_produccion = Column(String, default="interna")
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True)
    proveedor = relationship("Proveedor")
    costo_tercerizado = Column(Numeric(12, 2), nullable=True)

    detalles = relationship("OrdenProduccionDetalle", back_populates="orden", cascade="all, delete-orphan")


class OrdenProduccionDetalle(Base):
    __tablename__ = "ordenes_produccion_detalle"

    id = Column(Integer, primary_key=True, index=True)
    orden_id = Column(Integer, ForeignKey("ordenes_produccion.id"))
    orden = relationship("OrdenProduccion", back_populates="detalles")

    insumo_id = Column(Integer, ForeignKey("insumos.id"))
    insumo = relationship("Insumo")

    cantidad_requerida_neta = Column(Numeric(12, 4))
    cantidad_merma = Column(Numeric(12, 4))
    cantidad_total_descontar = Column(Numeric(12, 4))


class AlertaInventario(Base):
    __tablename__ = "alertas_inventario"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant")

    insumo_id = Column(Integer, ForeignKey("insumos.id"))
    insumo = relationship("Insumo")

    mensaje = Column(String)
    fecha_creacion = Column(DateTime, default=datetime.now)
    resuelta = Column(Boolean, default=False)
