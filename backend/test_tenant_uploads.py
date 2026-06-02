from fastapi import FastAPI
from fastapi.testclient import TestClient

from api_dependencies import get_current_user, get_db, get_db_tenant
from conftest import make_tenant, make_user
from routers import tenants as tenants_router


def _client_for_user(db_session, user):
    app = FastAPI()
    app.include_router(tenants_router.router)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_db_tenant] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def test_upload_payment_qr_updates_tenant_payment_qr_without_500(db_session, monkeypatch):
    tenant = make_tenant(db_session, "QR01")
    admin = make_user(db_session, tenant, email="qr-admin@test.com", rol="admin")
    client = _client_for_user(db_session, admin)
    captured = {}

    def fake_upload_to_storage(
        file_bytes,
        folder_name,
        filename,
        content_type,
        *,
        return_public_url=False,
        allow_overwrite=True,
    ):
        captured.update(
            {
                "file_bytes": file_bytes,
                "folder_name": folder_name,
                "filename": filename,
                "content_type": content_type,
                "return_public_url": return_public_url,
                "allow_overwrite": allow_overwrite,
            }
        )
        return f"https://cdn.test/{folder_name}/{filename}"

    monkeypatch.setattr(tenants_router.storage_service, "upload_to_storage", fake_upload_to_storage)

    response = client.post(
        "/users/upload-payment-qr",
        files={"file": ("qr-cobro.png", b"\x89PNG\r\n\x1a\nqr", "image/png")},
    )

    assert response.status_code == 200
    assert captured["folder_name"] == "payment_qrs"
    assert captured["filename"].startswith("payment_qr_")
    assert captured["content_type"] == "image/png"
    assert captured["return_public_url"] is True
    assert captured["allow_overwrite"] is False

    body = response.json()
    db_session.refresh(tenant)
    assert body["url"].startswith("https://cdn.test/payment_qrs/payment_qr_")
    assert tenant.payment_qr_filename == body["url"]


def test_upload_logo_updates_tenant_logo_without_500(db_session, monkeypatch):
    tenant = make_tenant(db_session, "LG01")
    admin = make_user(db_session, tenant, email="logo-admin@test.com", rol="admin")
    client = _client_for_user(db_session, admin)
    captured = {}

    def fake_upload_to_storage(
        file_bytes,
        folder_name,
        filename,
        content_type,
        *,
        return_public_url=False,
        allow_overwrite=True,
    ):
        captured.update(
            {
                "file_bytes": file_bytes,
                "folder_name": folder_name,
                "filename": filename,
                "content_type": content_type,
                "return_public_url": return_public_url,
                "allow_overwrite": allow_overwrite,
            }
        )
        return f"https://cdn.test/{folder_name}/{filename}"

    monkeypatch.setattr(tenants_router.storage_service, "upload_to_storage", fake_upload_to_storage)

    response = client.post(
        "/users/upload-logo",
        files={"file": ("logo.png", b"\x89PNG\r\n\x1a\nlogo", "image/png")},
    )

    assert response.status_code == 200
    assert captured["folder_name"] == "logos"
    assert captured["filename"].startswith("logo_")
    assert captured["content_type"] == "image/png"
    assert captured["return_public_url"] is True
    assert captured["allow_overwrite"] is False

    body = response.json()
    db_session.refresh(tenant)
    assert body["url"].startswith("https://cdn.test/logos/logo_")
    assert tenant.logo_filename == body["url"]
