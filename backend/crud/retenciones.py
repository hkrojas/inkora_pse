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


def list_retenciones(
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
    query = db.query(models.RetencionFiscal).filter(models.RetencionFiscal.tenant_id == tenant_id)
    if status:
        query = query.filter(models.RetencionFiscal.status == status)
    if desde:
        query = query.filter(models.RetencionFiscal.fecha_emision >= desde)
    if hasta:
        query = query.filter(models.RetencionFiscal.fecha_emision <= hasta)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            (models.RetencionFiscal.serie.ilike(term))
            | (models.RetencionFiscal.correlativo.ilike(term))
            | (models.RetencionFiscal.proveedor_num_doc.ilike(term))
            | (models.RetencionFiscal.proveedor_rzn_social.ilike(term))
            | (models.RetencionFiscal.ticket.ilike(term))
            | (models.RetencionFiscal.sunat_error.ilike(term))
        )
    return query.order_by(desc(models.RetencionFiscal.id)).offset(skip).limit(limit).all()


def create_retencion(
    db: Session,
    *,
    tenant_id: int,
    usuario_id: int | None,
    payload: dict[str, Any],
) -> models.RetencionFiscal:
    proveedor = payload.get("proveedor") or {}
    retencion = models.RetencionFiscal(
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        serie=str(payload.get("serie") or "").strip().upper(),
        correlativo=str(payload.get("correlativo") or "").strip(),
        fecha_emision=_as_datetime(payload["fechaEmision"]),
        proveedor_tipo_doc=str(proveedor.get("tipoDoc") or "").strip(),
        proveedor_num_doc=str(proveedor.get("numDoc") or "").strip(),
        proveedor_rzn_social=str(proveedor.get("rznSocial") or "").strip(),
        regimen=str(payload.get("regimen") or "01").strip(),
        tasa=payload.get("tasa") or 3,
        imp_retenido=payload.get("impRetenido") or 0,
        imp_pagado=payload.get("impPagado") or 0,
        details_count=len(payload.get("details") or []),
        status=models.RETENCION_STATUS_PENDING,
        payload_snapshot=jsonable_encoder(payload),
    )
    db.add(retencion)
    db.commit()
    db.refresh(retencion)
    return retencion


def mark_retencion_sent(
    db: Session,
    retencion_id: int,
    *,
    result: dict[str, Any],
    tenant_id: int,
) -> models.RetencionFiscal | None:
    retencion = (
        db.query(models.RetencionFiscal)
        .filter(models.RetencionFiscal.id == retencion_id, models.RetencionFiscal.tenant_id == tenant_id)
        .first()
    )
    if not retencion:
        return None

    sunat_response = result.get("sunat_response") or result.get("sunatResponse") or {}
    ticket = result.get("ticket") or sunat_response.get("ticket")
    cdr_response = sunat_response.get("cdrResponse") or {}
    is_pending = bool(result.get("pending")) or bool(ticket and not cdr_response)

    retencion.status = models.RETENCION_STATUS_PENDING if is_pending else models.RETENCION_STATUS_SENT
    retencion.success = bool(result.get("success"))
    retencion.ticket = ticket
    retencion.sunat_error = None
    retencion.sunat_hash = result.get("hash")
    retencion.provider_endpoint = result.get("provider_endpoint")
    retencion.provider_status_code = result.get("provider_status_code")
    retencion.provider_response = jsonable_encoder(result.get("provider_response") or result)
    retencion.updated_at = datetime.now()
    db.commit()
    db.refresh(retencion)
    return retencion


def mark_retencion_rejected(
    db: Session,
    retencion_id: int,
    *,
    error: str,
    tenant_id: int,
) -> models.RetencionFiscal | None:
    retencion = (
        db.query(models.RetencionFiscal)
        .filter(models.RetencionFiscal.id == retencion_id, models.RetencionFiscal.tenant_id == tenant_id)
        .first()
    )
    if not retencion:
        return None

    retencion.status = models.RETENCION_STATUS_REJECTED
    retencion.success = False
    retencion.sunat_error = str(error)
    retencion.updated_at = datetime.now()
    db.commit()
    db.refresh(retencion)
    return retencion
