"""models/emission_jobs.py — Cola durable de emisión fiscal."""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from database import Base

EMISSION_JOB_STATUS_QUEUED = "queued"
EMISSION_JOB_STATUS_PROCESSING = "processing"
EMISSION_JOB_STATUS_RETRY = "retry"
EMISSION_JOB_STATUS_SUCCEEDED = "succeeded"
EMISSION_JOB_STATUS_FAILED = "failed"

EMISSION_JOB_ACTION_EMIT_FISCAL = "emit_fiscal_document"
EMISSION_JOB_ACTION_EMIT_NOTE = "emit_note"
EMISSION_JOB_ACTION_VOID_FISCAL = "void_fiscal_document"
EMISSION_JOB_ACTION_EMIT_GUIDE = "emit_guide"

EMISSION_JOB_RESOURCE_COTIZACION = "cotizacion"
EMISSION_JOB_RESOURCE_GUIA = "guia_remision"


class DocumentEmissionJob(Base):
    __tablename__ = "document_emission_jobs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    tenant = relationship("Tenant", back_populates="emission_jobs")

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_by_user = relationship("User", back_populates="emission_jobs")

    resource_type = Column(String, nullable=False, index=True)
    resource_id = Column(Integer, nullable=False, index=True)
    action = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=True)

    status = Column(String, nullable=False, default=EMISSION_JOB_STATUS_QUEUED, index=True)
    priority = Column(Integer, nullable=False, default=100, index=True)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=5)

    idempotency_key = Column(String, nullable=False, unique=True, index=True)
    payload_snapshot = Column(JSON, nullable=True)
    result_snapshot = Column(JSON, nullable=True)
    provider_ticket = Column(String, nullable=True)
    last_error = Column(Text, nullable=True)

    available_at = Column(DateTime, nullable=False, default=datetime.now, index=True)
    locked_at = Column(DateTime, nullable=True)
    processing_started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

