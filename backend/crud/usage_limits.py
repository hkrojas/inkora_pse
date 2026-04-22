"""crud/usage_limits.py — Limites de emision por tenant/usuario y consulta de uso."""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

import models
from models.tenants import (
    USAGE_LIMIT_KIND_BOLETA,
    USAGE_LIMIT_KIND_FACTURA,
    USAGE_LIMIT_KIND_GUIA,
    USAGE_LIMIT_KIND_NOTA_CREDITO,
    USAGE_LIMIT_KIND_NOTA_DEBITO,
    USAGE_LIMIT_PERIOD_DAY,
    USAGE_LIMIT_PERIOD_MONTH,
    USAGE_LIMIT_PERIOD_TOTAL,
)


def _period_start(period: str) -> Optional[datetime]:
    now = datetime.now()
    if period == USAGE_LIMIT_PERIOD_MONTH:
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if period == USAGE_LIMIT_PERIOD_DAY:
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    return None  # total => sin filtro


def get_tenant_limits(db: Session, tenant_id: int) -> List[models.UsageLimit]:
    return (
        db.query(models.UsageLimit)
        .filter(models.UsageLimit.tenant_id == tenant_id)
        .order_by(
            models.UsageLimit.user_id.asc().nullsfirst(),
            models.UsageLimit.document_kind,
            models.UsageLimit.period,
        )
        .all()
    )


def get_limit_by_id(db: Session, limit_id: int) -> Optional[models.UsageLimit]:
    return db.query(models.UsageLimit).filter(models.UsageLimit.id == limit_id).first()


def upsert_tenant_limits(
    db: Session,
    tenant_id: int,
    payload_items: List[dict],
) -> List[models.UsageLimit]:
    """
    Bulk upsert: para cada item (user_id, document_kind, period) reemplaza el limite existente
    o crea uno nuevo. max_count <= 0 elimina el limite.
    """
    result: List[models.UsageLimit] = []
    for item in payload_items:
        user_id = item.get("user_id")
        document_kind = item["document_kind"]
        period = item.get("period", USAGE_LIMIT_PERIOD_MONTH)
        max_count = int(item["max_count"])

        existing = (
            db.query(models.UsageLimit)
            .filter(
                models.UsageLimit.tenant_id == tenant_id,
                models.UsageLimit.user_id == user_id,
                models.UsageLimit.document_kind == document_kind,
                models.UsageLimit.period == period,
            )
            .first()
        )

        if max_count <= 0:
            if existing:
                db.delete(existing)
            continue

        if existing:
            existing.max_count = max_count
            existing.notify_at_pct = item.get("notify_at_pct", existing.notify_at_pct)
            existing.enabled = item.get("enabled", existing.enabled)
            result.append(existing)
        else:
            new_limit = models.UsageLimit(
                tenant_id=tenant_id,
                user_id=user_id,
                document_kind=document_kind,
                period=period,
                max_count=max_count,
                notify_at_pct=item.get("notify_at_pct", 80),
                enabled=item.get("enabled", True),
            )
            db.add(new_limit)
            result.append(new_limit)

    db.commit()
    for lim in result:
        db.refresh(lim)
    return result


def delete_limit(db: Session, limit_id: int) -> bool:
    lim = get_limit_by_id(db, limit_id)
    if not lim:
        return False
    db.delete(lim)
    db.commit()
    return True


def count_usage_for_kind(
    db: Session,
    tenant_id: int,
    user_id: Optional[int],
    document_kind: str,
    period: str,
) -> int:
    """
    Cuenta cuantos documentos del tipo indicado se emitieron en el periodo.
    Solo cuenta los que estan efectivamente emitidos (estado='facturada' o 'emitida' para guia).
    """
    start = _period_start(period)

    if document_kind == USAGE_LIMIT_KIND_GUIA:
        q = db.query(func.count(models.GuiaRemision.id)).filter(
            models.GuiaRemision.tenant_id == tenant_id,
            models.GuiaRemision.estado == "emitida",
        )
        if start is not None:
            q = q.filter(models.GuiaRemision.fecha_emision >= start)
        # user_id no existe en GuiaRemision; si viene user_id, la cuenta aplica al tenant completo
        return q.scalar() or 0

    q = db.query(func.count(models.Cotizacion.id)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.estado == "facturada",
    )

    if document_kind == USAGE_LIMIT_KIND_FACTURA:
        q = q.filter(
            models.Cotizacion.document_kind == "fiscal_document",
            models.Cotizacion.serie.like("F%"),
        )
    elif document_kind == USAGE_LIMIT_KIND_BOLETA:
        q = q.filter(
            models.Cotizacion.document_kind == "fiscal_document",
            models.Cotizacion.serie.like("B%"),
        )
    elif document_kind == USAGE_LIMIT_KIND_NOTA_CREDITO:
        q = q.filter(models.Cotizacion.document_kind == "credit_note")
    elif document_kind == USAGE_LIMIT_KIND_NOTA_DEBITO:
        q = q.filter(models.Cotizacion.document_kind == "debit_note")
    else:
        return 0

    if user_id is not None:
        q = q.filter(models.Cotizacion.usuario_id == user_id)
    if start is not None:
        q = q.filter(models.Cotizacion.fecha_emision >= start)

    return q.scalar() or 0


def get_active_limits(
    db: Session,
    tenant_id: int,
    user_id: int,
    document_kind: str,
) -> List[models.UsageLimit]:
    """
    Retorna los limites aplicables a un (tenant, user, document_kind):
    - limites a nivel tenant (user_id NULL)
    - limites especificos del usuario
    Solo devuelve los enabled.
    """
    return (
        db.query(models.UsageLimit)
        .filter(
            models.UsageLimit.tenant_id == tenant_id,
            models.UsageLimit.document_kind == document_kind,
            models.UsageLimit.enabled == True,  # noqa: E712
            (
                (models.UsageLimit.user_id.is_(None))
                | (models.UsageLimit.user_id == user_id)
            ),
        )
        .all()
    )


def build_tenant_usage_report(
    db: Session,
    tenant_id: int,
) -> List[dict]:
    """Devuelve uso actual para cada limite configurado del tenant."""
    limits = get_tenant_limits(db, tenant_id)
    result = []
    for lim in limits:
        used = count_usage_for_kind(
            db,
            tenant_id=tenant_id,
            user_id=lim.user_id,
            document_kind=lim.document_kind,
            period=lim.period,
        )
        pct = int(min(100, (used / lim.max_count) * 100)) if lim.max_count > 0 else 0
        result.append({
            "limit_id": lim.id,
            "tenant_id": tenant_id,
            "user_id": lim.user_id,
            "document_kind": lim.document_kind,
            "period": lim.period,
            "max_count": lim.max_count,
            "used": used,
            "pct": pct,
            "would_block": lim.enabled and used >= lim.max_count,
            "enabled": lim.enabled,
        })
    return result


class QuotaExceededError(Exception):
    """Se lanza cuando una emision excede una cuota configurada."""
    def __init__(self, limit: models.UsageLimit, used: int):
        self.limit = limit
        self.used = used
        super().__init__(
            f"Cuota excedida: {used}/{limit.max_count} ({limit.document_kind}, {limit.period})"
        )


def check_emission_quota(
    db: Session,
    tenant_id: int,
    user_id: int,
    document_kind: str,
) -> None:
    """
    Verifica los limites configurados y lanza QuotaExceededError si alguno se excede.
    Las cotizaciones (document_kind='quotation') nunca se limitan.
    """
    if document_kind == "quotation":
        return
    limits = get_active_limits(db, tenant_id, user_id, document_kind)
    for lim in limits:
        used = count_usage_for_kind(
            db,
            tenant_id=tenant_id,
            user_id=lim.user_id,
            document_kind=document_kind,
            period=lim.period,
        )
        if used >= lim.max_count:
            raise QuotaExceededError(lim, used)
