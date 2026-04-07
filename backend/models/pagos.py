"""models/pagos.py — Pago (cliente → tenant)."""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from database import Base


class Pago(Base):
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True)

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="pagos")

    cotizacion_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=False)
    cotizacion = relationship(
        "Cotizacion",
        back_populates="pagos",
        foreign_keys=[cotizacion_id],
    )
    source_quote_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True)
    fiscal_document_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True)
    internal_order_number = Column(String, nullable=True, index=True)

    monto_pagado = Column(Numeric(12, 2), nullable=False)
    metodo_pago = Column(String, nullable=False)
    fecha_pago = Column(DateTime, default=datetime.now)
    referencia_operacion = Column(String, nullable=True)
    tipo = Column(String, default="adelanto")
