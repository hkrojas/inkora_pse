from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import models
from api_dependencies import get_current_user, get_db, get_db_tenant
from conftest import make_tenant, make_user
from routers import superadmin as superadmin_router


def _client_for_user(db_session, user):
    app = FastAPI()
    app.include_router(superadmin_router.router)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_db_tenant] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def test_superadmin_provisions_smartpse_company_and_hides_cpe_secret(db_session):
    tenant = make_tenant(db_session, "SP01")
    superadmin = make_user(
        db_session,
        tenant,
        email="smartpse-superadmin@test.com",
        rol="superadmin",
        is_superadmin=True,
    )
    client = _client_for_user(db_session, superadmin)
    fake_client = MagicMock()
    fake_client.provision_company.return_value = {
        "id": 77,
        "ruc": tenant.business_ruc,
        "environment": "demo",
        "active": True,
        "estado": "ACTIVO",
        "credenciales_cpe": {
            "usuario_secundaria": "AB3KPQR9",
            "token_acceso": "MX7TNVQG",
        },
    }

    with patch("routers.superadmin.smartpse_client.get_default_client", return_value=fake_client):
        response = client.post(
            f"/superadmin/tenants/{tenant.id}/smartpse/provision",
            json={"environment": "demo"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["has_smartpse_credentials"] is True
    assert body["smartpse_status"] == "ok"
    assert "smartpse_token_acceso" not in body
    assert "token_acceso" not in str(body)

    db_session.refresh(tenant)
    assert tenant.smartpse_company_id == "77"
    assert tenant.smartpse_environment == "demo"
    assert tenant.smartpse_usuario_secundaria == "AB3KPQR9"
    assert tenant.smartpse_token_acceso == "MX7TNVQG"
    assert (
        db_session.query(models.AuditLog)
        .filter(models.AuditLog.action == "superadmin.tenant.smartpse_provisioned")
        .count()
        == 1
    )


def test_superadmin_check_smartpse_credentials_updates_status(db_session):
    tenant = make_tenant(db_session, "SP02")
    tenant.smartpse_company_id = "77"
    tenant.smartpse_environment = "demo"
    tenant.smartpse_usuario_secundaria = "AB3KPQR9"
    tenant.smartpse_token_acceso = "MX7TNVQG"
    superadmin = make_user(
        db_session,
        tenant,
        email="smartpse-check@test.com",
        rol="superadmin",
        is_superadmin=True,
    )
    db_session.commit()
    client = _client_for_user(db_session, superadmin)
    fake_client = MagicMock()
    fake_client.validate_tenant_credentials.return_value = {
        "valid": True,
        "message": "Credenciales Smart PSE aceptadas.",
        "provider_status_code": 200,
        "provider_detail": "ok",
    }

    with patch("routers.superadmin.smartpse_client.get_default_client", return_value=fake_client):
        response = client.post(f"/superadmin/tenants/{tenant.id}/smartpse/check")

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["provider_status_code"] == 200
    db_session.refresh(tenant)
    assert tenant.smartpse_status == "ok"
    assert tenant.smartpse_checked_at is not None


def test_superadmin_syncs_smartpse_company_without_exposing_cpe_secret(db_session):
    tenant = make_tenant(db_session, "SP03")
    tenant.smartpse_company_id = "88"
    tenant.smartpse_environment = "demo"
    tenant.smartpse_usuario_secundaria = "AB3KPQR9"
    tenant.smartpse_token_acceso = "MX7TNVQG"
    superadmin = make_user(
        db_session,
        tenant,
        email="smartpse-sync@test.com",
        rol="superadmin",
        is_superadmin=True,
    )
    db_session.commit()
    client = _client_for_user(db_session, superadmin)
    fake_client = MagicMock()
    fake_client.get_company.return_value = {
        "id": 88,
        "ruc": tenant.business_ruc,
        "razon_social": tenant.business_name,
        "environment": "produccion",
        "active": False,
        "estado": "INACTIVO",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "firmas_usadas": 12,
        "credenciales_cpe": {
            "usuario_secundaria": "AB3KPQR9",
            "token_acceso": "MX7TNVQG",
        },
    }

    with patch("routers.superadmin.smartpse_client.get_default_client", return_value=fake_client):
        response = client.post(f"/superadmin/tenants/{tenant.id}/smartpse/sync")

    assert response.status_code == 200
    body = response.json()
    assert body["smartpse_company_id"] == "88"
    assert body["smartpse_environment"] == "produccion"
    assert body["smartpse_remote_active"] is False
    assert body["smartpse_remote_estado"] == "INACTIVO"
    assert body["smartpse_firmas_usadas"] == 12
    assert "token_acceso" not in str(body)
    assert "usuario_secundaria" not in str(body)

    db_session.refresh(tenant)
    assert tenant.smartpse_remote_active is False
    assert tenant.smartpse_remote_estado == "INACTIVO"
    assert tenant.smartpse_remote_synced_at is not None
    assert tenant.smartpse_start_date is not None
    assert tenant.smartpse_end_date is not None


def test_superadmin_updates_and_toggles_smartpse_company(db_session):
    tenant = make_tenant(db_session, "SP04")
    tenant.smartpse_company_id = "89"
    tenant.smartpse_environment = "demo"
    tenant.smartpse_usuario_secundaria = "AB3KPQR9"
    tenant.smartpse_token_acceso = "MX7TNVQG"
    superadmin = make_user(
        db_session,
        tenant,
        email="smartpse-update@test.com",
        rol="superadmin",
        is_superadmin=True,
    )
    db_session.commit()
    client = _client_for_user(db_session, superadmin)
    fake_client = MagicMock()
    fake_client.update_company.return_value = {
        "id": 89,
        "ruc": tenant.business_ruc,
        "razon_social": "NUEVO NOMBRE SAC",
        "environment": "produccion",
        "active": True,
        "estado": "ACTIVO",
        "start_date": "2026-01-01",
        "end_date": None,
        "firmas_usadas": 13,
    }
    fake_client.toggle_company_activation.return_value = {
        "id": 89,
        "ruc": tenant.business_ruc,
        "environment": "produccion",
        "active": False,
        "estado": "INACTIVO",
        "firmas_usadas": 13,
    }

    with patch("routers.superadmin.smartpse_client.get_default_client", return_value=fake_client):
        update_response = client.patch(
            f"/superadmin/tenants/{tenant.id}/smartpse/company",
            json={
                "razon_social": "NUEVO NOMBRE SAC",
                "environment": "produccion",
                "start_date": "2026-01-01",
                "end_date": None,
            },
        )
        activation_response = client.post(f"/superadmin/tenants/{tenant.id}/smartpse/activation")

    assert update_response.status_code == 200
    assert activation_response.status_code == 200
    fake_client.update_company.assert_called_once_with(
        "89",
        {
            "razon_social": "NUEVO NOMBRE SAC",
            "environment": "produccion",
            "start_date": "2026-01-01",
            "end_date": None,
        },
    )
    fake_client.toggle_company_activation.assert_called_once_with("89")
    db_session.refresh(tenant)
    assert tenant.smartpse_environment == "produccion"
    assert tenant.smartpse_remote_active is False
    assert tenant.smartpse_remote_estado == "INACTIVO"
    assert (
        db_session.query(models.AuditLog)
        .filter(models.AuditLog.action == "superadmin.tenant.smartpse_company_updated")
        .count()
        == 1
    )
    assert (
        db_session.query(models.AuditLog)
        .filter(models.AuditLog.action == "superadmin.tenant.smartpse_activation_toggled")
        .count()
        == 1
    )


def test_superadmin_creates_independent_smartpse_company(db_session):
    tenant = make_tenant(db_session, "SP05")
    superadmin = make_user(
        db_session,
        tenant,
        email="smartpse-create-remote@test.com",
        rol="superadmin",
        is_superadmin=True,
    )
    client = _client_for_user(db_session, superadmin)
    fake_client = MagicMock()
    fake_client.provision_company.return_value = {
        "id": 90,
        "ruc": "20999999991",
        "razon_social": "REMOTE ONLY SAC",
        "environment": "demo",
        "active": True,
        "estado": "ACTIVO",
        "credenciales_cpe": {
            "usuario_secundaria": "AB3KPQR9",
            "token_acceso": "MX7TNVQG",
        },
    }

    with patch("routers.superadmin.smartpse_client.get_default_client", return_value=fake_client):
        response = client.post(
            "/superadmin/smartpse/companies",
            json={
                "ruc": "20999999991",
                "razon_social": "REMOTE ONLY SAC",
                "environment": "demo",
                "start_date": "2026-01-01",
                "end_date": None,
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == "90"
    assert body["ruc"] == "20999999991"
    assert "token_acceso" not in str(body)
    fake_client.provision_company.assert_called_once_with(
        ruc="20999999991",
        razon_social="REMOTE ONLY SAC",
        environment="demo",
        start_date="2026-01-01",
        end_date=None,
    )
    assert (
        db_session.query(models.AuditLog)
        .filter(models.AuditLog.action == "superadmin.smartpse_company.created")
        .count()
        == 1
    )


def test_superadmin_rotates_manual_cpe_credentials_without_exposing_secret(db_session):
    tenant = make_tenant(db_session, "SP06")
    superadmin = make_user(
        db_session,
        tenant,
        email="smartpse-rotate@test.com",
        rol="superadmin",
        is_superadmin=True,
    )
    db_session.commit()
    client = _client_for_user(db_session, superadmin)

    response = client.put(
        f"/superadmin/tenants/{tenant.id}/smartpse/credentials",
        json={
            "company_id": "99",
            "environment": "produccion",
            "usuario_secundaria": "NEWUSER1",
            "token_acceso": "NEWTOKEN1",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["smartpse_company_id"] == "99"
    assert body["smartpse_environment"] == "produccion"
    assert body["has_smartpse_credentials"] is True
    assert "NEWTOKEN1" not in str(body)
    assert "NEWUSER1" not in str(body)
    db_session.refresh(tenant)
    assert tenant.smartpse_usuario_secundaria == "NEWUSER1"
    assert tenant.smartpse_token_acceso == "NEWTOKEN1"
    assert tenant.smartpse_status == "unchecked"
    assert (
        db_session.query(models.AuditLog)
        .filter(models.AuditLog.action == "superadmin.tenant.smartpse_credentials_rotated")
        .count()
        == 1
    )


def test_superadmin_deletes_tenant_smartpse_company_with_confirmation(db_session):
    tenant = make_tenant(db_session, "SP07")
    tenant.smartpse_company_id = "91"
    tenant.smartpse_environment = "demo"
    tenant.smartpse_usuario_secundaria = "AB3KPQR9"
    tenant.smartpse_token_acceso = "MX7TNVQG"
    superadmin = make_user(
        db_session,
        tenant,
        email="smartpse-delete@test.com",
        rol="superadmin",
        is_superadmin=True,
    )
    db_session.commit()
    client = _client_for_user(db_session, superadmin)
    fake_client = MagicMock()
    fake_client.delete_company.return_value = {"id": "91", "deleted": True}

    with patch("routers.superadmin.smartpse_client.get_default_client", return_value=fake_client):
        missing_confirmation = client.delete(f"/superadmin/tenants/{tenant.id}/smartpse/company")
        response = client.delete(
            f"/superadmin/tenants/{tenant.id}/smartpse/company",
            params={"confirm_company_id": "91"},
        )

    assert missing_confirmation.status_code == 422
    assert response.status_code == 200
    fake_client.delete_company.assert_called_once_with("91")
    db_session.refresh(tenant)
    assert tenant.smartpse_company_id is None
    assert tenant.smartpse_usuario_secundaria is None
    assert tenant.smartpse_token_acceso is None
    assert tenant.smartpse_status == "unchecked"
    assert (
        db_session.query(models.AuditLog)
        .filter(models.AuditLog.action == "superadmin.tenant.smartpse_company_deleted")
        .count()
        == 1
    )


def test_superadmin_syncs_all_smartpse_companies_and_reports_failures(db_session):
    tenant_ok = make_tenant(db_session, "SP08")
    tenant_ok.smartpse_company_id = "92"
    tenant_fail = make_tenant(db_session, "SP09")
    tenant_fail.smartpse_company_id = "93"
    superadmin = make_user(
        db_session,
        tenant_ok,
        email="smartpse-sync-all@test.com",
        rol="superadmin",
        is_superadmin=True,
    )
    db_session.commit()
    client = _client_for_user(db_session, superadmin)
    fake_client = MagicMock()

    def fake_get_company(company_id):
        if str(company_id) == "93":
            raise Exception("provider down")
        return {
            "id": 92,
            "ruc": tenant_ok.business_ruc,
            "environment": "demo",
            "active": True,
            "estado": "ACTIVO",
        }

    fake_client.get_company.side_effect = fake_get_company

    with patch("routers.superadmin.smartpse_client.get_default_client", return_value=fake_client):
        response = client.post("/superadmin/smartpse/sync-all")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 2
    assert body["synced"] == 1
    assert body["failed"] == 1
    assert any(item["tenant_id"] == tenant_fail.id and item["status"] == "failed" for item in body["items"])
    db_session.refresh(tenant_ok)
    assert tenant_ok.smartpse_remote_estado == "ACTIVO"


def test_superadmin_lists_tenant_smartpse_audit_timeline(db_session):
    tenant = make_tenant(db_session, "SP10")
    superadmin = make_user(
        db_session,
        tenant,
        email="smartpse-audit@test.com",
        rol="superadmin",
        is_superadmin=True,
    )
    db_session.add(
        models.AuditLog(
            user_id=superadmin.id,
            action="superadmin.tenant.smartpse_synced",
            entity_type="tenant",
            entity_id=tenant.id,
            details="company_id=100",
        )
    )
    db_session.add(
        models.AuditLog(
            user_id=superadmin.id,
            action="superadmin.tenant.updated",
            entity_type="tenant",
            entity_id=tenant.id,
            details="not smartpse",
        )
    )
    db_session.commit()
    client = _client_for_user(db_session, superadmin)

    response = client.get(f"/superadmin/tenants/{tenant.id}/smartpse/audit-logs")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["action"] == "superadmin.tenant.smartpse_synced"
