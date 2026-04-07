"""models/clientes.py — Cliente."""
from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    tipo_documento = Column(String, default="1")  # 1: DNI, 6: RUC
    numero_documento = Column(String, index=True)
    razon_social = Column(String, index=True)
    nombre_comercial = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    ubigeo = Column(String, nullable=True)
    email = Column(String, nullable=True)
    telefono = Column(String, nullable=True)

    whatsapp = Column(String, nullable=True)
    contacto = Column(String, nullable=True)
    condicion_pago = Column(String, nullable=True)
    direccion_entrega = Column(String, nullable=True)
    observaciones = Column(Text, nullable=True)

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="clientes")

    cotizaciones = relationship("Cotizacion", back_populates="cliente")
