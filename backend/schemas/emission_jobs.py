"""schemas/emission_jobs.py — schemas de cola de emisión."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EmissionJobResponse(BaseModel):
    id: int
    tenant_id: int
    created_by_user_id: Optional[int] = None
    resource_type: str
    resource_id: int
    action: str
    provider: Optional[str] = None
    status: str
    priority: int
    attempts: int
    max_attempts: int
    idempotency_key: str
    payload_snapshot: Optional[dict] = None
    result_snapshot: Optional[dict] = None
    provider_ticket: Optional[str] = None
    last_error: Optional[str] = None
    available_at: datetime
    locked_at: Optional[datetime] = None
    processing_started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
