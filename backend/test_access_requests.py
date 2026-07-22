import asyncio

import models
import schemas
import security
from conftest import make_tenant, make_user
from fastapi import HTTPException
from routers import access_requests as access_requests_router
from services import access_request_service


def _payload(*, ruc="20999999801", email="nuevo@imprenta.pe"):
    return schemas.AccessRequestCreate(
        business_ruc=ruc,
        business_name="Imprenta solicitante SAC",
        business_address="Av. Lima 123",
        business_phone="987654321",
        contact_name="María Administradora",
        email=email,
        password="Segura12345",
        confirm_password="Segura12345",
    )


def _superadmin(db_session):
    tenant = make_tenant(db_session, "981")
    return make_user(
        db_session,
        tenant,
        email="super-access@inkora.pe",
        is_superadmin=True,
    )


def test_public_request_does_not_create_tenant_or_user(db_session):
    before_tenants = db_session.query(models.Tenant).count()
    before_users = db_session.query(models.User).count()

    result = access_request_service.create_access_request(db_session, _payload())

    assert result["status"] == models.ACCESS_REQUEST_PENDING
    assert result["request_token"]
    assert db_session.query(models.Tenant).count() == before_tenants
    assert db_session.query(models.User).count() == before_users
    row = db_session.query(models.AccessRequest).one()
    assert row.password_hash != "Segura12345"
    assert security.verify_password("Segura12345", row.password_hash)
    assert row.public_token_hash != result["request_token"]
    assert access_request_service.get_public_status(db_session, result["request_token"]).id == row.id


def test_duplicate_pending_email_or_ruc_is_blocked(db_session):
    access_request_service.create_access_request(db_session, _payload())
    try:
        access_request_service.create_access_request(
            db_session,
            _payload(ruc="20999999802"),
        )
        assert False, "Se esperaba conflicto por correo pendiente"
    except HTTPException as exc:
        assert exc.status_code == 409


def test_superadmin_approval_atomically_creates_tenant_admin_and_inventory(db_session):
    admin = _superadmin(db_session)
    created = access_request_service.create_access_request(db_session, _payload())
    row = db_session.query(models.AccessRequest).filter_by(status="pending").one()

    approved = access_request_service.approve_access_request(
        db_session,
        row.id,
        admin,
        schemas.AccessRequestReview(review_notes="Identidad validada"),
    )

    assert approved.status == models.ACCESS_REQUEST_APPROVED
    assert approved.password_hash is None
    assert approved.pending_email_key is None
    tenant = db_session.query(models.Tenant).filter_by(id=approved.tenant_id).one()
    user = db_session.query(models.User).filter_by(id=approved.user_id).one()
    warehouse = db_session.query(models.Warehouse).filter_by(
        tenant_id=tenant.id,
        is_default=True,
    ).one()
    assert tenant.is_active is True
    assert tenant.inventory_enabled is True
    assert warehouse.code == "PRINCIPAL"
    assert user.rol == "admin"
    assert user.is_superadmin is False
    assert user.must_change_password is False
    assert security.verify_password("Segura12345", user.hashed_password)
    assert access_request_service.get_public_status(db_session, created["request_token"]).status == "approved"


def test_rejection_scrubs_password_and_allows_a_new_request(db_session):
    admin = _superadmin(db_session)
    access_request_service.create_access_request(db_session, _payload())
    row = db_session.query(models.AccessRequest).filter_by(status="pending").one()

    rejected = access_request_service.reject_access_request(
        db_session,
        row.id,
        admin,
        schemas.AccessRequestReview(review_notes="RUC pendiente de validación"),
    )
    assert rejected.status == models.ACCESS_REQUEST_REJECTED
    assert rejected.password_hash is None
    assert rejected.pending_email_key is None
    assert rejected.pending_ruc_key is None

    retry = access_request_service.create_access_request(db_session, _payload())
    assert retry["status"] == models.ACCESS_REQUEST_PENDING


def test_public_ruc_lookup_returns_only_registration_fields(monkeypatch):
    async def fake_lookup(ruc, token):
        assert ruc == "20606751509"
        assert token == "public-lookup-token"
        return {
            "razon_social": "INKORA DEMO SAC",
            "direccion": "JR. DEMO 123",
            "estado": "ACTIVO",
            "condicion": "HABIDO",
        }

    monkeypatch.setattr(access_requests_router.settings, "DNIRUC_TOKEN", "public-lookup-token")
    monkeypatch.setattr(access_requests_router, "_consultar_documento_con_token", fake_lookup)

    result = asyncio.run(
        access_requests_router.lookup_access_request_ruc.__wrapped__(None, "20606751509")
    )

    assert result == {
        "ruc": "20606751509",
        "business_name": "INKORA DEMO SAC",
        "business_address": "JR. DEMO 123",
    }


def test_public_ruc_lookup_rejects_invalid_ruc():
    try:
        asyncio.run(access_requests_router.lookup_access_request_ruc.__wrapped__(None, "123"))
        assert False, "Se esperaba validación de RUC"
    except HTTPException as exc:
        assert exc.status_code == 400
