from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

import schemas
from api_dependencies import get_current_user, get_db
from conftest import make_tenant, make_user
import security


def _client_with_db(db_session) -> TestClient:
    app = FastAPI()

    @app.get("/users/me/", response_model=schemas.UserResponse)
    async def read_users_me(current_user=Depends(get_current_user)):
        return current_user

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def test_users_me_returns_200_for_legacy_local_email(db_session):
    tenant = make_tenant(db_session, "ME01")
    user = make_user(
        db_session,
        tenant,
        email="e2e-admin@demo.inkora.local",
        rol="admin",
        password="local-pass",
    )
    token = security.create_access_token_with_claims(user)

    response = _client_with_db(db_session).get(
        "/users/me/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "e2e-admin@demo.inkora.local"
    assert data["tenant_id"] == tenant.id
    assert data["is_superadmin"] is False
    assert "hashed_password" not in data
    assert "apisperu_token" not in data


def test_users_me_inactive_tenant_returns_403_not_500(db_session):
    tenant = make_tenant(db_session, "ME02", is_active=False)
    user = make_user(
        db_session,
        tenant,
        email="inactive@test.com",
        rol="admin",
    )
    token = security.create_access_token_with_claims(user)

    response = _client_with_db(db_session).get(
        "/users/me/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert "inactivo" in response.json()["detail"].lower()


def test_users_me_non_superadmin_stays_false(db_session):
    tenant = make_tenant(db_session, "ME03")
    user = make_user(
        db_session,
        tenant,
        email="tenant-admin@test.com",
        rol="admin",
        is_superadmin=False,
    )

    app = FastAPI()

    @app.get("/users/me/", response_model=schemas.UserResponse)
    async def read_users_me(current_user=Depends(get_current_user)):
        return current_user

    app.dependency_overrides[get_current_user] = lambda: user
    response = TestClient(app).get("/users/me/")

    assert response.status_code == 200
    assert response.json()["is_superadmin"] is False
