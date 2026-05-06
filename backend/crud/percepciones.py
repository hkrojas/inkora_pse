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


def list_percepciones(
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
    query = db.query(models.PercepcionFiscal).filter(models.PercepcionFiscal.tenant_id == tenant_id)
    if status:
        query = query.filter(models.PercepcionFiscal.status == status)
    if desde:
        query = query.filter(models.PercepcionFiscal.fecha_emision >= desde)
    if hasta:
        query = query.filter(models.PercepcionFiscal.fecha_emision <= hasta)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            (models.PercepcionFiscal.serie.ilike(term))
            | (models.PercepcionFiscal.correlativo.ilike(term))
            | (models.PercepcionFiscal.cliente_num_doc.ilike(term))
            | (models.PercepcionFiscal.cliente_rzn_social.ilike(term))
            | (models.PercepcionFiscal.ticket.ilike(term))
            | (models.PercepcionFiscal.sunat_error.ilike(term))
        )
    return query.order_by(desc(models.PercepcionFiscal.id)).offset(skip).limit(limit).all()


def create_percepcion(
    db: Session,
    *,
    tenant_id: int,
    usuario_id: int | None,
    payload: dict[str, Any],
) -> models.PercepcionFiscal:
    cliente = payload.get("proveedor") or {}
    percepcion = models.PercepcionFiscal(
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        serie=str(payload.get("serie") or "").strip().upper(),
        correlativo=str(payload.get("correlativo") or "").strip(),
        fecha_emision=_as_datetime(payload["fechaEmision"]),
        cliente_tipo_doc=str(cliente.get("tipoDoc") or "").strip(),
        cliente_num_doc=str(cliente.get("numDoc") or "").strip(),
        cliente_rzn_social=str(cliente.get("rznSocial") or "").strip(),
        regimen=str(payload.get("regimen") or "01").strip(),
        tasa=payload.get("tasa") or 2,
        imp_percibido=payload.get("impPercibido") or 0,
        imp_cobrado=payload.get("impCobrado") or 0,
        details_count=len(payload.get("details") or []),
        status=models.PERCEPCION_STATUS_PENDING,
        payload_snapshot=jsonable_encoder(payload),
    )
    db.add(percepcion)
    db.commit()
    db.refresh(percepcion)
    return percepcion


def mark_percepcion_sent(
    db: Session,
    percepcion_id: int,
    *,
    result: dict[str, Any],
    tenant_id: int,
) -> models.PercepcionFiscal | None:
    percepcion = (
        db.query(models.PercepcionFiscal)
        .filter(models.PercepcionFiscal.id == percepcion_id, models.PercepcionFiscal.tenant_id == tenant_id)
        .first()
    )
    if not percepcion:
        return None

    sunat_response = result.get("sunat_response") or result.get("sunatResponse") or {}
    ticket = result.get("ticket") or sunat_response.get("ticket")
    cdr_response = sunat_response.get("cdrResponse") or {}
    is_pending = bool(result.get("pending")) or bool(ticket and not cdr_response)

    percepcion.status = models.PERCEPCION_STATUS_PENDING if is_pending else models.PERCEPCION_STATUS_SENT
    percepcion.success = bool(result.get("success"))
    percepcion.ticket = ticket
    percepcion.sunat_error = None
    percepcion.sunat_hash = result.get("hash")
    percepcion.provider_endpoint = result.get("provider_endpoint")
    percepcion.provider_status_code = result.get("provider_status_code")
    percepcion.provider_response = jsonable_encoder(result.get("provider_response") or result)
    percepcion.updated_at = datetime.now()
    db.commit()
    db.refresh(percepcion)
    return percepcion


def mark_percepcion_rejected(
    db: Session,
    percepcion_id: int,
    *,
    error: str,
    tenant_id: int,
) -> models.PercepcionFiscal | None:
    percepcion = (
        db.query(models.PercepcionFiscal)
        .filter(models.PercepcionFiscal.id == percepcion_id, models.PercepcionFiscal.tenant_id == tenant_id)
        .first()
    )
    if not percepcion:
        return None

    percepcion.status = models.PERCEPCION_STATUS_REJECTED
    percepcion.success = False
    percepcion.sunat_error = str(error)
    percepcion.updated_at = datetime.now()
    db.commit()
    db.refresh(percepcion)
    return percepcion
