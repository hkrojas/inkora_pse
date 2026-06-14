"""crud/superadmin.py — Operaciones de panel superadmin."""
import random
import string
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

import models
from models.emission_jobs import EMISSION_JOB_STATUS_FAILED
from models.tenants import APISPERU_TOKEN_STATUS_OK, APISPERU_TOKEN_STATUS_INVALID, APISPERU_TOKEN_STATUS_UNCHECKED
from security import get_password_hash
from crud.auth import utc_now_naive


def _current_month_start() -> datetime:
    now = datetime.now()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def get_tenant_users_with_metrics(db: Session, tenant_id: int) -> List[dict]:
    users = (
        db.query(models.User)
        .filter(models.User.tenant_id == tenant_id)
        .order_by(models.User.id)
        .all()
    )
    if not users:
        return []

    month_start = _current_month_start()
    user_ids = [u.id for u in users]

    # Cotizaciones por usuario — totales y mes actual
    cot_total = dict(
        db.query(models.Cotizacion.usuario_id, func.count(models.Cotizacion.id))
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.document_kind == "quotation",
            models.Cotizacion.usuario_id.in_(user_ids),
        )
        .group_by(models.Cotizacion.usuario_id)
        .all()
    )
    cot_mes = dict(
        db.query(models.Cotizacion.usuario_id, func.count(models.Cotizacion.id))
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.document_kind == "quotation",
            models.Cotizacion.usuario_id.in_(user_ids),
            models.Cotizacion.fecha_emision >= month_start,
        )
        .group_by(models.Cotizacion.usuario_id)
        .all()
    )

    # Facturas
    fact_total = dict(
        db.query(models.Cotizacion.usuario_id, func.count(models.Cotizacion.id))
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.document_kind == "fiscal_document",
            models.Cotizacion.serie.like("F%"),
            models.Cotizacion.usuario_id.in_(user_ids),
        )
        .group_by(models.Cotizacion.usuario_id)
        .all()
    )
    fact_mes = dict(
        db.query(models.Cotizacion.usuario_id, func.count(models.Cotizacion.id))
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.document_kind == "fiscal_document",
            models.Cotizacion.serie.like("F%"),
            models.Cotizacion.usuario_id.in_(user_ids),
            models.Cotizacion.fecha_emision >= month_start,
        )
        .group_by(models.Cotizacion.usuario_id)
        .all()
    )

    # Boletas
    bol_total = dict(
        db.query(models.Cotizacion.usuario_id, func.count(models.Cotizacion.id))
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.document_kind == "fiscal_document",
            models.Cotizacion.serie.like("B%"),
            models.Cotizacion.usuario_id.in_(user_ids),
        )
        .group_by(models.Cotizacion.usuario_id)
        .all()
    )
    bol_mes = dict(
        db.query(models.Cotizacion.usuario_id, func.count(models.Cotizacion.id))
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.document_kind == "fiscal_document",
            models.Cotizacion.serie.like("B%"),
            models.Cotizacion.usuario_id.in_(user_ids),
            models.Cotizacion.fecha_emision >= month_start,
        )
        .group_by(models.Cotizacion.usuario_id)
        .all()
    )

    # Notas de crédito
    nc_total = dict(
        db.query(models.Cotizacion.usuario_id, func.count(models.Cotizacion.id))
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.document_kind == "credit_note",
            models.Cotizacion.usuario_id.in_(user_ids),
        )
        .group_by(models.Cotizacion.usuario_id)
        .all()
    )

    # Notas de débito
    nd_total = dict(
        db.query(models.Cotizacion.usuario_id, func.count(models.Cotizacion.id))
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.document_kind == "debit_note",
            models.Cotizacion.usuario_id.in_(user_ids),
        )
        .group_by(models.Cotizacion.usuario_id)
        .all()
    )

    # Guías de remisión — no tienen usuario_id, se asocian por tenant solamente
    # Las guías no tienen campo usuario_id, así que contamos por tenant
    guias_total_count = (
        db.query(func.count(models.GuiaRemision.id))
        .filter(models.GuiaRemision.tenant_id == tenant_id)
        .scalar() or 0
    )
    guias_mes_count = (
        db.query(func.count(models.GuiaRemision.id))
        .filter(
            models.GuiaRemision.tenant_id == tenant_id,
            models.GuiaRemision.fecha_emision >= month_start,
        )
        .scalar() or 0
    )

    # Último documento por usuario
    ultimo_doc = dict(
        db.query(models.Cotizacion.usuario_id, func.max(models.Cotizacion.fecha_emision))
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.usuario_id.in_(user_ids),
        )
        .group_by(models.Cotizacion.usuario_id)
        .all()
    )

    results = []
    for u in users:
        uid = u.id
        is_only_user = len(users) == 1
        results.append({
            "id": uid,
            "email": u.email,
            "nombre_completo": u.nombre_completo,
            "rol": u.rol,
            "is_superadmin": u.is_superadmin,
            "is_active": getattr(u, "is_active", True),
            "must_change_password": getattr(u, "must_change_password", False),
            "tenant_id": u.tenant_id,
            "last_login_at": getattr(u, "last_login_at", None),
            "password_changed_at": getattr(u, "password_changed_at", None),
            "metrics": {
                "cotizaciones_total": cot_total.get(uid, 0),
                "cotizaciones_mes_actual": cot_mes.get(uid, 0),
                "facturas_total": fact_total.get(uid, 0),
                "facturas_mes_actual": fact_mes.get(uid, 0),
                "boletas_total": bol_total.get(uid, 0),
                "boletas_mes_actual": bol_mes.get(uid, 0),
                "notas_credito_total": nc_total.get(uid, 0),
                "notas_debito_total": nd_total.get(uid, 0),
                # Guías se distribuyen al primer usuario (no hay campo usuario_id en guías)
                "guias_total": guias_total_count if is_only_user else 0,
                "guias_mes_actual": guias_mes_count if is_only_user else 0,
                "ultimo_documento_at": ultimo_doc.get(uid),
            },
        })

    return results


def reset_user_password(db: Session, user_id: int) -> Optional[dict]:
    from crud.auth import generate_temp_password
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    temp_password = generate_temp_password()
    user.hashed_password = get_password_hash(temp_password)
    user.must_change_password = True
    user.password_changed_at = utc_now_naive()
    db.commit()
    return {
        "user_id": user.id,
        "email": user.email,
        "temp_password": temp_password,
        "message": "Contraseña reseteada. Comparte esta contraseña de forma segura — no se puede recuperar después.",
    }


def toggle_user_active(db: Session, user_id: int, is_active: bool) -> Optional[models.User]:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    if user.is_active and not is_active:
        user.password_changed_at = utc_now_naive()
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


def get_tenant_emission_errors(db: Session, tenant_id: int, limit: int = 50) -> list:
    jobs = (
        db.query(models.DocumentEmissionJob)
        .filter(
            models.DocumentEmissionJob.tenant_id == tenant_id,
            models.DocumentEmissionJob.status == EMISSION_JOB_STATUS_FAILED,
        )
        .order_by(models.DocumentEmissionJob.finished_at.desc().nullslast())
        .limit(limit)
        .all()
    )
    return jobs


def check_apisperu_token_health(db: Session, tenant_id: int) -> dict:
    from services import facturacion_service
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not tenant:
        return {"tenant_id": tenant_id, "status": "not_found", "checked_at": None, "message": "Tenant no encontrado."}

    if not tenant.apisperu_token:
        status = APISPERU_TOKEN_STATUS_UNCHECKED
        msg = "Sin token configurado."
        db.query(models.Tenant).filter(models.Tenant.id == tenant_id).update({
            "apisperu_token_status": status,
            "apisperu_token_checked_at": datetime.now(),
        })
        db.commit()
        return {"tenant_id": tenant_id, "status": status, "checked_at": datetime.now(), "message": msg}

    result = facturacion_service.validate_apisperu_token(
        token=tenant.apisperu_token,
        api_url=tenant.apisperu_url,
        business_ruc=tenant.business_ruc,
    )
    status = APISPERU_TOKEN_STATUS_OK if result["valid"] else APISPERU_TOKEN_STATUS_INVALID
    msg = result.get("message", "")
    checked_at = datetime.now()
    db.query(models.Tenant).filter(models.Tenant.id == tenant_id).update({
        "apisperu_token_status": status,
        "apisperu_token_checked_at": checked_at,
    })
    db.commit()
    return {"tenant_id": tenant_id, "status": status, "checked_at": checked_at, "message": msg}


def check_all_apisperu_tokens(db: Session) -> List[dict]:
    tenants = db.query(models.Tenant).filter(models.Tenant.apisperu_token.isnot(None)).all()
    results = []
    for t in tenants:
        results.append(check_apisperu_token_health(db, t.id))
    return results
