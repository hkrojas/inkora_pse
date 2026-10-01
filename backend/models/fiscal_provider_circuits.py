"""One durable outage coordinator per provider, environment and fiscal service."""
from sqlalchemy import Column, DateTime, Integer, String
from database import Base


class FiscalProviderCircuit(Base):
    __tablename__ = "fiscal_provider_circuits"
    scope = Column(String(100), primary_key=True)
    failures = Column(Integer, nullable=False, default=0)
    next_probe_at = Column(DateTime, nullable=True)
    probe_token = Column(String(36), nullable=True)
    probe_expires_at = Column(DateTime, nullable=True)
