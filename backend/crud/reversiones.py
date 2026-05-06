from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import desc
from sqlalchemy.orm import Session

import models


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def list_reversiones(
    db: Session,
    tenant_id: int,
    *,
    skip: int = 0,
    limit: int = 15,
    status: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    q: str | None = None,
):
    query = db.query(models.ReversionFiscal).filter(models.ReversionFiscal.tenant_id == tenant_id)
    if status:
        query = query.filter(models.ReversionFiscal.status == status)
    if desde:
        query = query.filter(models.ReversionFiscal.fec_comunicacion >= desde)
    if hasta:
        query = query.filter(models.ReversionFiscal.fec_comunicacion <= hasta)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            (models.ReversionFiscal.correlativo.ilike(term))
            | (models.ReversionFiscal.ticket.ilike(term))
            | (models.ReversionFiscal.sunat_error.ilike(term))
        )
    return query.order_by(desc(models.ReversionFiscal.id)).offset(skip).limit(limit).all()


def create_reversion(
    db: Session,
    *,
    tenant_id: int,
    usuario_id: int | None,
    payload: dict[str, Any],
) -> models.ReversionFiscal:
    reversion = models.ReversionFiscal(
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        correlativo=str(payload.get("correlativo") or "").strip(),
        fec_generacion=_as_datetime(payload["fecGeneracion"]),
        fec_comunicacion=_as_datetime(payload["fecComunicacion"]),
        details_count=len(payload.get("details") or []),
        status=models.REVERSION_STATUS_PENDING,
        payload_snapshot=jsonable_encoder(payload),
    )
    db.add(reversion)
    db.commit()
    db.refresh(reversion)
    return reversion


def mark_reversion_sent(
    db: Session,
    reversion_id: int,
    *,
    result: dict[str, Any],
    tenant_id: int,
) -> models.ReversionFiscal | None:
    reversion = (
        db.query(models.ReversionFiscal)
        .filter(models.ReversionFiscal.id == reversion_id, models.ReversionFiscal.tenant_id == tenant_id)
        .first()
    )
    if not reversion:
        return None

    sunat_response = result.get("sunat_response") or result.get("sunatResponse") or {}
    ticket = result.get("ticket") or sunat_response.get("ticket")
    cdr_response = sunat_response.get("cdrResponse") or {}
    is_pending = bool(result.get("pending")) or bool(ticket and not cdr_response)

    reversion.status = models.REVERSION_STATUS_PENDING if is_pending else models.REVERSION_STATUS_SENT
    reversion.success = bool(result.get("success"))
    reversion.ticket = ticket
    reversion.sunat_error = None
    reversion.sunat_hash = result.get("hash")
    reversion.provider_endpoint = result.get("provider_endpoint")
    reversion.provider_status_code = result.get("provider_status_code")
    reversion.provider_response = jsonable_encoder(result.get("provider_response") or result)
    reversion.updated_at = datetime.now()
    db.commit()
    db.refresh(reversion)
    return reversion


def mark_reversion_rejected(
    db: Session,
    reversion_id: int,
    *,
    error: str,
    tenant_id: int,
) -> models.ReversionFiscal | None:
    reversion = (
        db.query(models.ReversionFiscal)
        .filter(models.ReversionFiscal.id == reversion_id, models.ReversionFiscal.tenant_id == tenant_id)
        .first()
    )
    if not reversion:
        return None

    reversion.status = models.REVERSION_STATUS_REJECTED
    reversion.success = False
    reversion.sunat_error = str(error)
    reversion.updated_at = datetime.now()
    db.commit()
    db.refresh(reversion)
    return reversion
