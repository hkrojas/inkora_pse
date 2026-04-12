"""crud/tenants.py — Tenants, suscripciones SaaS, superadmin, beta."""
from sqlalchemy import delete
from sqlalchemy.orm import Session, joinedload

import models
import schemas


# ==========================================
# TENANTS
# ==========================================

def get_tenant(db: Session, tenant_id: int):
    return db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()


def get_tenant_by_ruc(db: Session, business_ruc: str):
    return db.query(models.Tenant).filter(models.Tenant.business_ruc == business_ruc).first()


def create_tenant(db: Session, tenant: schemas.TenantCreate):
    if get_tenant_by_ruc(db, tenant.business_ruc):
        raise ValueError("Ya existe una empresa registrada con ese RUC.")

    db_tenant = models.Tenant(**tenant.model_dump())
    try:
        db.add(db_tenant)
        db.flush()
        sub = models.Subscription(tenant_id=db_tenant.id)
        db.add(sub)
        db.commit()
        db.refresh(db_tenant)
        return db_tenant
    except Exception as e:
        db.rollback()
        raise e


def update_tenant(db: Session, tenant_id: int, data: schemas.TenantUpdate):
    db_tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if db_tenant:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(db_tenant, key, value)
        db.commit()
        db.refresh(db_tenant)
    return db_tenant


def get_all_tenants(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Tenant).order_by(models.Tenant.id.desc()).offset(skip).limit(limit).all()


def update_tenant_saas(db: Session, tenant_id: int, updates: dict):
    db_tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not db_tenant:
        return None
    for key, value in updates.items():
        if value is not None:
            setattr(db_tenant, key, value)
    db.commit()
    db.refresh(db_tenant)
    return db_tenant


def delete_tenant(db: Session, tenant_id: int):
    db_tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not db_tenant:
        return None
    try:
        related_counts = {
            "clientes": db.query(models.Cliente).filter(models.Cliente.tenant_id == tenant_id).count(),
            "productos": db.query(models.Producto).filter(models.Producto.tenant_id == tenant_id).count(),
            "cotizaciones": db.query(models.Cotizacion).filter(models.Cotizacion.tenant_id == tenant_id).count(),
            "guias": db.query(models.GuiaRemision).filter(models.GuiaRemision.tenant_id == tenant_id).count(),
            "pagos": db.query(models.Pago).filter(models.Pago.tenant_id == tenant_id).count(),
            "proveedores": db.query(models.Proveedor).filter(models.Proveedor.tenant_id == tenant_id).count(),
            "insumos": db.query(models.Insumo).filter(models.Insumo.tenant_id == tenant_id).count(),
            "recetas": db.query(models.RecetaBOM).filter(models.RecetaBOM.tenant_id == tenant_id).count(),
            "ordenes_produccion": db.query(models.OrdenProduccion).filter(models.OrdenProduccion.tenant_id == tenant_id).count(),
            "pagos_saas": db.query(models.SubscriptionPayment).filter(
                models.SubscriptionPayment.tenant_id == tenant_id
            ).count(),
        }
        blocking_relations = [name for name, count in related_counts.items() if count > 0]
        if blocking_relations:
            joined = ", ".join(blocking_relations)
            raise ValueError(
                "No se puede eliminar el tenant porque tiene datos relacionados: "
                f"{joined}. Desactívelo si necesita conservar el historial."
            )

        user_ids = [
            row[0]
            for row in db.query(models.User.id).filter(models.User.tenant_id == tenant_id).all()
        ]
        if user_ids:
            db.execute(delete(models.AuditLog).where(models.AuditLog.user_id.in_(user_ids)))
            db.execute(delete(models.User).where(models.User.tenant_id == tenant_id))

        db.execute(delete(models.Subscription).where(models.Subscription.tenant_id == tenant_id))
        db.delete(db_tenant)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e


def get_all_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).options(joinedload(models.User.tenant)).order_by(models.User.id.desc()).offset(skip).limit(limit).all()


def create_audit_log(db: Session, user_id: int, action: str, entity_type: str = None, entity_id: int = None, details: str = None, ip_address: str = None):
    log = models.AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address
    )
    db.add(log)
    db.commit()
    return log


def get_audit_logs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).offset(skip).limit(limit).all()


# ==========================================
# SUBSCRIPCIONES SAAS
# ==========================================

def get_subscription_by_tenant(db: Session, tenant_id: int) -> models.Subscription | None:
    return (
        db.query(models.Subscription)
        .filter(models.Subscription.tenant_id == tenant_id)
        .first()
    )


def get_or_create_subscription(db: Session, tenant_id: int) -> models.Subscription:
    sub = get_subscription_by_tenant(db, tenant_id)
    if sub:
        return sub
    sub = models.Subscription(tenant_id=tenant_id)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def update_subscription_fields(
    db: Session,
    tenant_id: int,
    updates: dict,
) -> models.Subscription:
    sub = get_or_create_subscription(db, tenant_id)
    for key, value in updates.items():
        setattr(sub, key, value)
    db.commit()
    db.refresh(sub)
    return sub


def register_subscription_payment(
    db: Session,
    tenant_id: int,
    data: schemas.SubscriptionPaymentCreate,
    validated_by_user_id: int,
) -> models.SubscriptionPayment:
    from datetime import datetime as dt
    payment = models.SubscriptionPayment(
        tenant_id=tenant_id,
        amount=data.amount,
        currency=data.currency,
        method=data.method,
        reference=data.reference,
        paid_at=data.paid_at or dt.now(),
        validated_by_user_id=validated_by_user_id,
        notes=data.notes,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def get_subscription_payments(
    db: Session,
    tenant_id: int,
    skip: int = 0,
    limit: int = 50,
) -> list[models.SubscriptionPayment]:
    return (
        db.query(models.SubscriptionPayment)
        .filter(models.SubscriptionPayment.tenant_id == tenant_id)
        .order_by(models.SubscriptionPayment.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_all_tenants_with_subscription(
    db: Session,
    skip: int = 0,
    limit: int = 100,
) -> list[models.Tenant]:
    return (
        db.query(models.Tenant)
        .options(joinedload(models.Tenant.subscription))
        .order_by(models.Tenant.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def check_document_limit(db: Session, tenant_id: int) -> None:
    sub = get_subscription_by_tenant(db, tenant_id)
    if sub is None:
        return
    if sub.max_documents is None:
        return
    used = sub.documents_used or 0
    if used >= sub.max_documents:
        raise ValueError(
            f"Límite de documentos alcanzado: {used}/{sub.max_documents}. "
            "Contacte al administrador para ampliar su plan."
        )


# ==========================================
# FASE 9: BETA CERRADA — MÉTRICAS OPERATIVAS
# ==========================================

def get_tenant_actividad(db: Session, tenant_id: int) -> dict:
    from datetime import datetime as _dt, timedelta
    from sqlalchemy import func

    tenant = get_tenant(db, tenant_id)
    if not tenant:
        return {}

    sub = get_subscription_by_tenant(db, tenant_id)

    clientes_count = db.query(func.count(models.Cliente.id)).filter(
        models.Cliente.tenant_id == tenant_id
    ).scalar() or 0

    productos_count = db.query(func.count(models.Producto.id)).filter(
        models.Producto.tenant_id == tenant_id
    ).scalar() or 0

    usuarios_count = db.query(func.count(models.User.id)).filter(
        models.User.tenant_id == tenant_id
    ).scalar() or 0

    cotizaciones_count = db.query(func.count(models.Cotizacion.id)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind == "quotation",
    ).scalar() or 0

    documentos_fiscales_count = db.query(func.count(models.Cotizacion.id)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind.in_(["fiscal_document", "credit_note", "debit_note"]),
    ).scalar() or 0

    hace_30_dias = _dt.now() - timedelta(days=30)
    documentos_fiscales_ultimo_mes = db.query(func.count(models.Cotizacion.id)).filter(
        models.Cotizacion.tenant_id == tenant_id,
        models.Cotizacion.document_kind.in_(["fiscal_document", "credit_note", "debit_note"]),
        models.Cotizacion.fecha_emision >= hace_30_dias,
    ).scalar() or 0

    guias_count = db.query(func.count(models.GuiaRemision.id)).filter(
        models.GuiaRemision.tenant_id == tenant_id
    ).scalar() or 0

    pagos_count = db.query(func.count(models.Pago.id)).filter(
        models.Pago.tenant_id == tenant_id
    ).scalar() or 0

    ultimo_fiscal = (
        db.query(models.Cotizacion)
        .filter(
            models.Cotizacion.tenant_id == tenant_id,
            models.Cotizacion.document_kind.in_(["fiscal_document", "credit_note", "debit_note"]),
        )
        .order_by(models.Cotizacion.fecha_emision.desc())
        .first()
    )

    return {
        "tenant_id": tenant_id,
        "business_name": tenant.business_name,
        "business_ruc": tenant.business_ruc,
        "clientes_count": clientes_count,
        "productos_count": productos_count,
        "usuarios_count": usuarios_count,
        "cotizaciones_count": cotizaciones_count,
        "documentos_fiscales_count": documentos_fiscales_count,
        "documentos_fiscales_ultimo_mes": documentos_fiscales_ultimo_mes,
        "guias_count": guias_count,
        "pagos_count": pagos_count,
        "ultimo_documento_fiscal_fecha": getattr(ultimo_fiscal, "fecha_emision", None),
        "subscription_status": getattr(sub, "status", None),
        "onboarding_status": getattr(sub, "onboarding_status", None),
        "documents_used": getattr(sub, "documents_used", 0),
        "max_documents": getattr(sub, "max_documents", None),
    }


def get_beta_resumen_data(db: Session) -> list[dict]:
    from sqlalchemy import func

    tenants = db.query(models.Tenant).order_by(models.Tenant.id.desc()).all()
    result = []

    for tenant in tenants:
        sub = get_subscription_by_tenant(db, tenant.id)

        clientes_count = db.query(func.count(models.Cliente.id)).filter(
            models.Cliente.tenant_id == tenant.id
        ).scalar() or 0

        productos_count = db.query(func.count(models.Producto.id)).filter(
            models.Producto.tenant_id == tenant.id
        ).scalar() or 0

        usuarios_count = db.query(func.count(models.User.id)).filter(
            models.User.tenant_id == tenant.id
        ).scalar() or 0

        ultimo_pago = (
            db.query(models.SubscriptionPayment)
            .filter(models.SubscriptionPayment.tenant_id == tenant.id)
            .order_by(models.SubscriptionPayment.paid_at.desc())
            .first()
        )

        result.append({
            "tenant_id": tenant.id,
            "business_name": tenant.business_name,
            "business_ruc": tenant.business_ruc,
            "is_active": tenant.is_active,
            "is_pilot": getattr(sub, "is_pilot", False) if sub else False,
            "subscription_status": getattr(sub, "status", None),
            "onboarding_status": getattr(sub, "onboarding_status", None),
            "plan_code": getattr(sub, "plan_code", None),
            "current_price": getattr(sub, "current_price", None),
            "founder_price": getattr(sub, "founder_price", None),
            "billing_due_at": getattr(sub, "billing_due_at", None),
            "documents_used": getattr(sub, "documents_used", 0),
            "max_documents": getattr(sub, "max_documents", None),
            "clientes_count": clientes_count,
            "productos_count": productos_count,
            "usuarios_count": usuarios_count,
            "ultimo_pago_saas_fecha": getattr(ultimo_pago, "paid_at", None) if ultimo_pago else None,
            "ultimo_pago_saas_monto": getattr(ultimo_pago, "amount", None) if ultimo_pago else None,
            "notes_internal": getattr(sub, "notes_internal", None),
        })

    return result
