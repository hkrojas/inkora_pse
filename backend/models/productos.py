"""models/productos.py — Producto."""
from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    codigo_interno = Column(String, nullable=True)
    nombre = Column(String, index=True)
    descripcion = Column(Text, nullable=True)
    precio_unitario = Column(Numeric(12, 2))
    valor_unitario = Column(Numeric(12, 2))
    unidad_medida = Column(String, default="NIU")
    tipo_afectacion_igv = Column(String, default="10")

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="productos")

    receta = relationship("RecetaBOM", back_populates="producto", cascade="all, delete-orphan")
