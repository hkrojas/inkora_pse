"""Modelos de comprobantes fiscales: percepciones SUNAT/APISPeru."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import relationship

from database import Base


PERCEPCION_STATUS_SENT = "sent"
PERCEPCION_STATUS_PENDING = "pending"
PERCEPCION_STATUS_REJECTED = "rejected"


class PercepcionFiscal(Base):
    __tablename__ = "percepciones_fiscales"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, nullable=False)

    serie = Column(String, nullable=False, index=True)
    correlativo = Column(String, nullable=False, index=True)
    fecha_emision = Column(DateTime, nullable=False, index=True)
    cliente_tipo_doc = Column(String, nullable=False)
    cliente_num_doc = Column(String, nullable=False, index=True)
    cliente_rzn_social = Column(String, nullable=False)
    regimen = Column(String, default="01", nullable=False)
    tasa = Column(Numeric(5, 2), default=2, nullable=False)
    imp_percibido = Column(Numeric(12, 2), default=0, nullable=False)
    imp_cobrado = Column(Numeric(12, 2), default=0, nullable=False)
    details_count = Column(Integer, default=0, nullable=False)

    status = Column(String, default=PERCEPCION_STATUS_PENDING, nullable=False, index=True)
    success = Column(Boolean, default=False, nullable=False)
    ticket = Column(String, nullable=True, index=True)
    sunat_error = Column(Text, nullable=True)
    sunat_hash = Column(String, nullable=True)
    provider_endpoint = Column(String, nullable=True)
    provider_status_code = Column(Integer, nullable=True)
    payload_snapshot = Column(JSON, nullable=True)
    provider_response = Column(JSON, nullable=True)

    tenant = relationship("Tenant", back_populates="percepciones_fiscales")
    usuario = relationship("User")
