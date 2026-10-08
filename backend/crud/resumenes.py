from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import desc
from sqlalchemy.orm import Session

import models
from services import smartpse_response


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _preserve_confirmed_summary(db: Session, resumen: models.ResumenDiario) -> bool:
    status = smartpse_response.summary_cdr_status(resumen.payload_snapshot, resumen.provider_response)
    if status is None:
        return False
    resumen.status = models.RESUMEN_DIARIO_STATUS_SENT if status == "accepted" else models.RESUMEN_DIARIO_STATUS_REJECTED
    resumen.success = status == "accepted"
    if resumen.success:
        resumen.sunat_error = None
    db.commit()
    db.refresh(resumen)
    return True


def list_resumenes_diarios(
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
    query = db.query(models.ResumenDiario).filter(models.ResumenDiario.tenant_id == tenant_id)
    if status:
        query = query.filter(models.ResumenDiario.status == status)
    if desde:
        query = query.filter(models.ResumenDiario.fec_resumen >= desde)
    if hasta:
        query = query.filter(models.ResumenDiario.fec_resumen <= hasta)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            (models.ResumenDiario.correlativo.ilike(term))
            | (models.ResumenDiario.ticket.ilike(term))
            | (models.ResumenDiario.sunat_error.ilike(term))
        )
    return query.order_by(desc(models.ResumenDiario.id)).offset(skip).limit(limit).all()


def create_resumen_diario(
    db: Session,
    *,
    tenant_id: int,
    usuario_id: int | None,
    payload: dict[str, Any],
) -> models.ResumenDiario:
    resumen = models.ResumenDiario(
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        correlativo=str(payload.get("correlativo") or "").strip(),
        fec_generacion=_as_datetime(payload["fecGeneracion"]),
        fec_resumen=_as_datetime(payload["fecResumen"]),
        moneda=payload.get("moneda") or "PEN",
        details_count=len(payload.get("details") or []),
        status=models.RESUMEN_DIARIO_STATUS_PENDING,
        payload_snapshot=jsonable_encoder(payload),
    )
    db.add(resumen)
    db.commit()
    db.refresh(resumen)
    return resumen


def mark_resumen_diario_sent(
    db: Session,
    resumen_id: int,
    *,
    result: dict[str, Any],
    tenant_id: int,
) -> models.ResumenDiario | None:
    resumen = (
        db.query(models.ResumenDiario)
        .filter(models.ResumenDiario.id == resumen_id, models.ResumenDiario.tenant_id == tenant_id)
        .populate_existing().with_for_update()
        .first()
    )
    if not resumen:
        return None

    sunat_response = result.get("sunat_response") or result.get("sunatResponse") or {}
    ticket = result.get("ticket") or sunat_response.get("ticket")
    # Do not let a slower pending consultation erase an accepted CDR.
    if _preserve_confirmed_summary(db, resumen):
        return resumen
    cdr = smartpse_response.extract_cdr_xml(result)
    if cdr:
        smartpse_response.validate_summary_cdr(cdr, resumen.payload_snapshot or {})
    is_pending = not bool(cdr)

    resumen.status = (
        models.RESUMEN_DIARIO_STATUS_PENDING
        if is_pending
        else models.RESUMEN_DIARIO_STATUS_SENT
    )
    resumen.success = not is_pending
    resumen.ticket = ticket or resumen.ticket
    resumen.sunat_error = None
    resumen.sunat_hash = result.get("hash")
    resumen.provider_endpoint = result.get("provider_endpoint")
    resumen.provider_status_code = result.get("provider_status_code")
    resumen.provider_response = jsonable_encoder(result)
    resumen.updated_at = datetime.now()
    db.commit()
    db.refresh(resumen)
    return resumen


def mark_resumen_diario_rejected(
    db: Session,
    resumen_id: int,
    *,
    error: str,
    tenant_id: int,
    provider_response: dict | None = None,
    pending: bool = False,
) -> models.ResumenDiario | None:
    resumen = (
        db.query(models.ResumenDiario)
        .filter(models.ResumenDiario.id == resumen_id, models.ResumenDiario.tenant_id == tenant_id)
        .populate_existing().with_for_update()
        .first()
    )
    if not resumen:
        return None

    if _preserve_confirmed_summary(db, resumen):
        return resumen
    resumen.status = models.RESUMEN_DIARIO_STATUS_PENDING if pending else models.RESUMEN_DIARIO_STATUS_REJECTED
    resumen.success = False
    resumen.sunat_error = str(error)
    if provider_response:
        resumen.provider_response = jsonable_encoder(provider_response)
    resumen.updated_at = datetime.now()
    db.commit()
    db.refresh(resumen)
    return resumen
