import os
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import crud
import models
from access_control import ROLE_ADMIN, ROLE_SUPERADMIN, ROLE_VENDEDOR
from api_dependencies import get_current_user, get_db, get_db_tenant, require_admin
from conftest import make_tenant, make_user
from routers import superadmin as superadmin_router
from routers import tenants as tenants_router


ROOT = Path(__file__).resolve().parents[1]


def _client_for_user(db_session, user, *routers):
    app = FastAPI()
    for router in routers:
        app.include_router(router.router)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_db_tenant] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _audit_actions(db_session):
    return [row.action for row in db_session.query(models.AuditLog).all()]


def test_tenant_admin_no_puede_crear_rol_superadmin(db_session):
    tenant = make_tenant(db_session, "SA01")
    admin = make_user(db_session, tenant, email="tenant-admin@test.com", rol=ROLE_ADMIN)
    client = _client_for_user(db_session, admin, tenants_router)

    response = client.post(
        "/users/",
        json={
            "email": "tenant-superadmin@test.com",
            "nombre_completo": "Tenant Superadmin",
            "rol": ROLE_SUPERADMIN,
        },
    )

    assert response.status_code == 403
    assert "superadmin" in response.json()["detail"].lower()


def test_rol_superadmin_sin_flag_no_accede_a_superadmin_ni_admin_tenant(db_session):
    tenant = make_tenant(db_session, "SA02")
    user = make_user(
        db_session,
        tenant,
        email="fake-superadmin@test.com",
        rol=ROLE_SUPERADMIN,
        is_superadmin=False,
    )
    client = _client_for_user(db_session, user, superadmin_router)

    response = client.get("/superadmin/tenants")

    assert response.status_code == 403
    with pytest.raises(HTTPException) as exc:
        require_admin(user)
    assert exc.value.status_code == 403


def test_global_user_routes_no_son_accesibles_por_tenant_user(db_session):
    tenant = make_tenant(db_session, "SA03")
    admin = make_user(db_session, tenant, email="admin-sa03@test.com", rol=ROLE_ADMIN)
    target = make_user(db_session, tenant, email="target-sa03@test.com", rol=ROLE_VENDEDOR)
    client = _client_for_user(db_session, admin, superadmin_router)

    patch_response = client.patch(
        f"/users/{target.id}",
        json={"nombre_completo": "Cambio no permitido"},
    )
    delete_response = client.delete(f"/users/{target.id}")

    assert patch_response.status_code == 403
    assert delete_response.status_code == 403


def test_global_user_routes_quedan_ocultas_del_openapi(db_session):
    tenant = make_tenant(db_session, "SA04")
    superadmin = make_user(
        db_session,
        tenant,
        email="superadmin-sa04@test.com",
        rol=ROLE_SUPERADMIN,
        is_superadmin=True,
    )
    client = _client_for_user(db_session, superadmin, superadmin_router)

    paths = client.get("/openapi.json").json()["paths"]

    assert "/users/{user_id}" not in paths
    assert "/superadmin/users/{user_id}" in paths


def test_patch_superadmin_users_funciona_solo_con_superadmin_real_y_audita(db_session):
    tenant = make_tenant(db_session, "SA05")
    target = make_user(db_session, tenant, email="target-sa05@test.com", rol=ROLE_VENDEDOR)
    fake_superadmin = make_user(
        db_session,
        tenant,
        email="fake-sa05@test.com",
        rol=ROLE_SUPERADMIN,
        is_superadmin=False,
    )
    real_superadmin = make_user(
        db_session,
        tenant,
        email="real-sa05@test.com",
        rol=ROLE_SUPERADMIN,
        is_superadmin=True,
    )

    forbidden_client = _client_for_user(db_session, fake_superadmin, superadmin_router)
    assert forbidden_client.patch(
        f"/superadmin/users/{target.id}",
        json={"nombre_completo": "Nope"},
    ).status_code == 403

    client = _client_for_user(db_session, real_superadmin, superadmin_router)
    response = client.patch(
        f"/superadmin/users/{target.id}",
        json={"nombre_completo": "Usuario Actualizado", "rol": "operador"},
    )

    assert response.status_code == 200
    assert response.json()["nombre_completo"] == "Usuario Actualizado"
    assert response.json()["rol"] == "operador"
    assert "superadmin.user.updated" in _audit_actions(db_session)


def test_patch_superadmin_users_no_acepta_is_superadmin_en_update_generico(db_session):
    tenant = make_tenant(db_session, "SA06")
    target = make_user(db_session, tenant, email="target-sa06@test.com", rol=ROLE_VENDEDOR)
    superadmin = make_user(
        db_session,
        tenant,
        email="real-sa06@test.com",
        rol=ROLE_SUPERADMIN,
        is_superadmin=True,
    )
    client = _client_for_user(db_session, superadmin, superadmin_router)

    response = client.patch(
        f"/superadmin/users/{target.id}",
        json={"is_superadmin": True},
    )

    assert response.status_code == 422


def test_delete_superadmin_users_funciona_solo_con_superadmin_real_y_audita(db_session):
    tenant = make_tenant(db_session, "SA07")
    target = make_user(db_session, tenant, email="target-sa07@test.com", rol=ROLE_VENDEDOR)
    fake_superadmin = make_user(
        db_session,
        tenant,
        email="fake-sa07@test.com",
        rol=ROLE_SUPERADMIN,
        is_superadmin=False,
    )
    real_superadmin = make_user(
        db_session,
        tenant,
        email="real-sa07@test.com",
        rol=ROLE_SUPERADMIN,
        is_superadmin=True,
    )

    forbidden_client = _client_for_user(db_session, fake_superadmin, superadmin_router)
    assert forbidden_client.delete(f"/superadmin/users/{target.id}").status_code == 403

    client = _client_for_user(db_session, real_superadmin, superadmin_router)
    response = client.delete(f"/superadmin/users/{target.id}")

    assert response.status_code == 200
    assert crud.get_user_by_id(db_session, target.id) is None
    assert "superadmin.user.deleted" in _audit_actions(db_session)


def test_frontend_superadmin_visibility_usa_solo_is_superadmin():
    files = [
        ROOT / "frontend" / "src" / "pages" / "SuperadminPage.jsx",
        ROOT / "frontend" / "src" / "components" / "Sidebar.jsx",
        ROOT / "frontend" / "src" / "layouts" / "AppLayout.jsx",
        ROOT / "frontend" / "src" / "pages" / "ConfiguracionPage.jsx",
    ]
    forbidden_patterns = [
        "user?.is_superadmin || user?.rol === 'superadmin'",
        "user?.rol !== 'superadmin' && !user?.is_superadmin",
        "['admin', 'superadmin'].includes(user?.rol)",
    ]

    for file_path in files:
        text = file_path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert pattern not in text


def test_superadmin_tenants_page_escala_filtra_y_no_expone_secretos_gre(db_session):
    tenant = make_tenant(db_session, "PG00")
    tenant.business_name = "Empresa Demo 0000 SAC"
    tenant.business_ruc = "20000000000"
    tenant.smartpse_gre_sol_username = "SOL0000"
    tenant.smartpse_gre_sol_password_enc = "enc:v1:secret-pass-0000"
    tenant.smartpse_gre_client_id = "client-0000"
    tenant.smartpse_gre_client_secret_enc = "enc:v1:secret-client-0000"
    tenant.smartpse_gre_status = models.SMARTPSE_GRE_STATUS_OK
    superadmin = make_user(
        db_session,
        tenant,
        email="page-superadmin@test.com",
        rol=ROLE_SUPERADMIN,
        is_superadmin=True,
    )

    for idx in range(1, 1000):
        gre_configured = idx % 3 == 0
        db_session.add(
            models.Tenant(
                business_name=f"Empresa Demo {idx:04d} SAC",
                business_ruc=f"20{idx:09d}",
                business_address=f"Av. Escala {idx}",
                is_active=idx % 7 != 0,
                plan_type="founder" if idx % 2 == 0 else "free",
                smartpse_gre_sol_username=f"SOL{idx:04d}" if gre_configured else None,
                smartpse_gre_sol_password_enc=(
                    f"enc:v1:secret-pass-{idx:04d}" if gre_configured else None
                ),
                smartpse_gre_client_id=f"client-{idx:04d}" if gre_configured else None,
                smartpse_gre_client_secret_enc=(
                    f"enc:v1:secret-client-{idx:04d}" if gre_configured else None
                ),
                smartpse_gre_status=(
                    models.SMARTPSE_GRE_STATUS_INVALID
                    if gre_configured and idx % 5 == 0
                    else models.SMARTPSE_GRE_STATUS_UNCHECKED
                ),
            )
        )
    db_session.commit()

    client = _client_for_user(db_session, superadmin, superadmin_router)

    response = client.get("/superadmin/tenants-page", params={"skip": 25, "limit": 25})

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1000
    assert data["skip"] == 25
    assert data["limit"] == 25
    assert len(data["items"]) == 25
    assert data["metrics"]["total"] == 1000
    assert data["metrics"]["active"] == db_session.query(models.Tenant).filter(models.Tenant.is_active.is_(True)).count()
    assert data["metrics"]["smartpse_gre"] == 334
    assert data["metrics"]["smartpse_gre_pending"] == 666
    assert "secret-pass" not in response.text
    assert "secret-client" not in response.text
    assert "smartpse_gre_sol_username" not in response.text
    assert "smartpse_gre_client_secret" not in response.text

    search_response = client.get(
        "/superadmin/tenants-page",
        params={"q": "Empresa Demo 0999", "limit": 25},
    )
    assert search_response.status_code == 200
    search_data = search_response.json()
    assert search_data["total"] == 1
    assert search_data["items"][0]["business_ruc"] == "20000000999"

    configured_response = client.get(
        "/superadmin/tenants-page",
        params={"gre_status": "configured", "limit": 100},
    )
    assert configured_response.status_code == 200
    configured_data = configured_response.json()
    assert configured_data["total"] == 334
    assert all(item["has_smartpse_gre_credentials"] for item in configured_data["items"])

    inactive_response = client.get(
        "/superadmin/tenants-page",
        params={"active_status": "inactive", "limit": 100},
    )
    assert inactive_response.status_code == 200
    assert inactive_response.json()["total"] == db_session.query(models.Tenant).filter(models.Tenant.is_active.is_(False)).count()
    assert all(not item["is_active"] for item in inactive_response.json()["items"])

    too_large = client.get("/superadmin/tenants-page", params={"limit": 101})
    assert too_large.status_code == 422
