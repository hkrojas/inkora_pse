"""Modelos de lotes fiscales: reversiones de retenciones/percepciones."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from database import Base


REVERSION_STATUS_SENT = "sent"
REVERSION_STATUS_PENDING = "pending"
REVERSION_STATUS_REJECTED = "rejected"


class ReversionFiscal(Base):
    __tablename__ = "reversiones_fiscales"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, nullable=False)

    correlativo = Column(String, nullable=False, index=True)
    fec_generacion = Column(DateTime, nullable=False, index=True)
    fec_comunicacion = Column(DateTime, nullable=False, index=True)
    details_count = Column(Integer, default=0, nullable=False)

    status = Column(String, default=REVERSION_STATUS_PENDING, nullable=False, index=True)
    success = Column(Boolean, default=False, nullable=False)
    ticket = Column(String, nullable=True, index=True)
    sunat_error = Column(Text, nullable=True)
    sunat_hash = Column(String, nullable=True)
    provider_endpoint = Column(String, nullable=True)
    provider_status_code = Column(Integer, nullable=True)
    payload_snapshot = Column(JSON, nullable=True)
    provider_response = Column(JSON, nullable=True)

    tenant = relationship("Tenant", back_populates="reversiones_fiscales")
    usuario = relationship("User")
