"""Public tenant access requests reviewed by Inkora superadmins."""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint

from database import Base


ACCESS_REQUEST_PENDING = "pending"
ACCESS_REQUEST_APPROVED = "approved"
ACCESS_REQUEST_REJECTED = "rejected"


class AccessRequest(Base):
    __tablename__ = "access_requests"
    __table_args__ = (
        UniqueConstraint("public_token_hash", name="uq_access_requests_public_token"),
        UniqueConstraint("pending_email_key", name="uq_access_requests_pending_email"),
        UniqueConstraint("pending_ruc_key", name="uq_access_requests_pending_ruc"),
        Index("ix_access_requests_status_created", "status", "created_at"),
    )

    id = Column(Integer, primary_key=True)
    business_ruc = Column(String(11), nullable=False)
    business_name = Column(String(255), nullable=False)
    business_address = Column(String(500), nullable=True)
    business_phone = Column(String(20), nullable=True)
    contact_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(Text, nullable=True)
    public_token_hash = Column(String(64), nullable=False)
    pending_email_key = Column(String(255), nullable=True)
    pending_ruc_key = Column(String(11), nullable=True)
    status = Column(String(20), nullable=False, default=ACCESS_REQUEST_PENDING)
    review_notes = Column(Text, nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
