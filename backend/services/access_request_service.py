"""Safe public signup requests and superadmin approval workflow."""
from datetime import datetime
from hashlib import sha256
from secrets import token_urlsafe

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import crud
import models
import security
from database import without_tenant_filter


ALLOWED_STATUSES = {
    models.ACCESS_REQUEST_PENDING,
    models.ACCESS_REQUEST_APPROVED,
    models.ACCESS_REQUEST_REJECTED,
}


def _token_hash(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def _get_tenant_by_ruc_global(db: Session, business_ruc: str):
    query = db.query(models.Tenant).filter(models.Tenant.business_ruc == business_ruc)
    return without_tenant_filter(query).first()


def create_access_request(db: Session, data, *, ip_address: str | None = None):
    email = str(data.email).strip().lower()
    password_error = security.validate_password_strength(data.password, email)
    if password_error:
        raise HTTPException(422, password_error)
    if crud.get_user_by_email_global(db, email):
        raise HTTPException(409, "Ya existe un usuario registrado con este correo.")
    if _get_tenant_by_ruc_global(db, data.business_ruc):
        raise HTTPException(409, "La empresa ya está registrada. Solicita acceso a su administrador.")

    public_token = token_urlsafe(32)
    request_row = models.AccessRequest(
        business_ruc=data.business_ruc,
        business_name=data.business_name,
        business_address=data.business_address,
        business_phone=data.business_phone,
        contact_name=data.contact_name,
        email=email,
        password_hash=security.get_password_hash(data.password),
        public_token_hash=_token_hash(public_token),
        pending_email_key=email,
        pending_ruc_key=data.business_ruc,
        status=models.ACCESS_REQUEST_PENDING,
    )
    db.add(request_row)
    db.add(models.AuditLog(
        action="access_request.created",
        entity_type="access_request",
        details=f"email={email}; ruc={data.business_ruc}",
        ip_address=ip_address,
    ))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Ya existe una solicitud pendiente para este correo o RUC.") from exc
    return {
        "status": request_row.status,
        "request_token": public_token,
        "message": "Solicitud enviada. El superadministrador revisará el alta.",
    }


def get_public_status(db: Session, public_token: str):
    row = db.query(models.AccessRequest).filter(
        models.AccessRequest.public_token_hash == _token_hash(public_token),
    ).first()
    if not row:
        raise HTTPException(404, "Solicitud no encontrada.")
    return row


def list_access_requests(db: Session, *, status: str | None, skip: int, limit: int):
    query = db.query(models.AccessRequest)
    if status:
        normalized = status.strip().lower()
        if normalized not in ALLOWED_STATUSES:
            raise HTTPException(422, "Estado de solicitud inválido.")
        query = query.filter(models.AccessRequest.status == normalized)
    total = query.count()
    items = query.order_by(
        models.AccessRequest.created_at.desc(),
        models.AccessRequest.id.desc(),
    ).offset(skip).limit(limit).all()
    return {"items": items, "total": total, "skip": skip, "limit": limit}


def _pending_for_review(db: Session, request_id: int):
    row = db.query(models.AccessRequest).filter(
        models.AccessRequest.id == request_id,
    ).with_for_update().first()
    if not row:
        raise HTTPException(404, "Solicitud no encontrada.")
    if row.status != models.ACCESS_REQUEST_PENDING:
        raise HTTPException(409, "La solicitud ya fue revisada.")
    return row


def approve_access_request(db: Session, request_id: int, admin: models.User, data):
    row = _pending_for_review(db, request_id)
    if crud.get_user_by_email_global(db, row.email):
        raise HTTPException(409, "El correo ya pertenece a un usuario activo.")
    if _get_tenant_by_ruc_global(db, row.business_ruc):
        raise HTTPException(409, "El RUC ya pertenece a un tenant existente.")
    if not row.password_hash:
        raise HTTPException(409, "La solicitud no conserva credenciales válidas.")

    now = datetime.now()
    tenant = models.Tenant(
        business_name=row.business_name,
        business_ruc=row.business_ruc,
        business_address=row.business_address,
        business_phone=row.business_phone,
        is_active=True,
        inventory_enabled=True,
        inventory_started_at=now,
    )
    db.add(tenant)
    db.flush()
    db.add(models.Warehouse(
        tenant_id=tenant.id,
        code="PRINCIPAL",
        name="Almacén principal",
        is_default=True,
        is_active=True,
    ))
    db.add(models.Subscription(
        tenant_id=tenant.id,
        status=models.SUBSCRIPTION_STATUS_TRIAL,
    ))
    user = models.User(
        email=row.email,
        hashed_password=row.password_hash,
        nombre_completo=row.contact_name,
        rol="admin",
        is_superadmin=False,
        is_active=True,
        tenant_id=tenant.id,
        must_change_password=False,
        password_changed_at=now,
    )
    db.add(user)
    db.flush()

    row.status = models.ACCESS_REQUEST_APPROVED
    row.review_notes = data.review_notes
    row.reviewed_by_user_id = admin.id
    row.reviewed_at = now
    row.tenant_id = tenant.id
    row.user_id = user.id
    row.password_hash = None
    row.pending_email_key = None
    row.pending_ruc_key = None
    db.add(models.AuditLog(
        user_id=admin.id,
        action="access_request.approved",
        entity_type="access_request",
        entity_id=row.id,
        details=f"tenant_id={tenant.id}; user_id={user.id}; ruc={row.business_ruc}",
    ))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "No se pudo aprobar porque el correo o RUC ya fue utilizado.") from exc
    db.refresh(row)
    return row


def reject_access_request(db: Session, request_id: int, admin: models.User, data):
    row = _pending_for_review(db, request_id)
    row.status = models.ACCESS_REQUEST_REJECTED
    row.review_notes = data.review_notes or "Solicitud denegada por revisión administrativa."
    row.reviewed_by_user_id = admin.id
    row.reviewed_at = datetime.now()
    row.password_hash = None
    row.pending_email_key = None
    row.pending_ruc_key = None
    db.add(models.AuditLog(
        user_id=admin.id,
        action="access_request.rejected",
        entity_type="access_request",
        entity_id=row.id,
        details=f"ruc={row.business_ruc}",
    ))
    db.commit()
    db.refresh(row)
    return row
