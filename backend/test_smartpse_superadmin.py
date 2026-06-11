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
