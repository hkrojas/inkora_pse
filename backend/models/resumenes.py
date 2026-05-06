"""Modelos de lotes fiscales: resumen diario de boletas."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from database import Base


RESUMEN_DIARIO_STATUS_SENT = "sent"
RESUMEN_DIARIO_STATUS_PENDING = "pending"
RESUMEN_DIARIO_STATUS_REJECTED = "rejected"


class ResumenDiario(Base):
    __tablename__ = "resumenes_diarios"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, nullable=False)

    correlativo = Column(String, nullable=False, index=True)
    fec_generacion = Column(DateTime, nullable=False, index=True)
    fec_resumen = Column(DateTime, nullable=False, index=True)
    moneda = Column(String, default="PEN", nullable=False)
    details_count = Column(Integer, default=0, nullable=False)

    status = Column(String, default=RESUMEN_DIARIO_STATUS_PENDING, nullable=False, index=True)
    success = Column(Boolean, default=False, nullable=False)
    ticket = Column(String, nullable=True, index=True)
    sunat_error = Column(Text, nullable=True)
    sunat_hash = Column(String, nullable=True)
    provider_endpoint = Column(String, nullable=True)
    provider_status_code = Column(Integer, nullable=True)
    payload_snapshot = Column(JSON, nullable=True)
    provider_response = Column(JSON, nullable=True)

    tenant = relationship("Tenant", back_populates="resumenes_diarios")
    usuario = relationship("User")
