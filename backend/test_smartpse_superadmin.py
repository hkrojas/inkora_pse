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
