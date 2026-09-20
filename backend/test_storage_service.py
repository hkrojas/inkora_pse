import pytest

from config import Settings
from routers import ops as ops_router
from services import storage_service
import supabase_client


def test_upload_to_storage_does_not_request_upsert(monkeypatch):
    captured = {}

    class FakeBucket:
        def upload(self, *, path, file, file_options):
            captured["path"] = path
            captured["file"] = file
            captured["file_options"] = file_options

        def get_public_url(self, path):
            return f"https://cdn.test/{path}"

    class FakeStorage:
        def from_(self, bucket):
            captured["bucket"] = bucket
            return FakeBucket()

    class FakeClient:
        storage = FakeStorage()

    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: FakeClient())
    monkeypatch.setattr(storage_service.settings, "SUPABASE_STORAGE_BUCKET", "test-bucket")

    result = storage_service.upload_to_storage(
        b"logo-bytes",
        "logos",
        "logo.png",
        "image/png",
        return_public_url=True,
        allow_overwrite=False,
        bucket_name="public-assets",
    )

    assert result == "https://cdn.test/logos/logo.png"
    assert captured["bucket"] == "public-assets"
    assert captured["path"] == "logos/logo.png"
    assert captured["file"] == b"logo-bytes"
    assert captured["file_options"] == {"content-type": "image/png"}
    assert "upsert" not in captured["file_options"]
    assert "x-upsert" not in captured["file_options"]


def test_upload_to_storage_keeps_overwrite_enabled_by_default(monkeypatch):
    captured = {}

    class FakeBucket:
        def upload(self, *, path, file, file_options):
            captured["file_options"] = file_options

    class FakeStorage:
        def from_(self, bucket):
            return FakeBucket()

    class FakeClient:
        storage = FakeStorage()

    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: FakeClient())
    monkeypatch.setattr(storage_service.settings, "SUPABASE_STORAGE_BUCKET", "test-bucket")

    result = storage_service.upload_to_storage(
        b"pdf-bytes",
        "cotizaciones/tenant_1",
        "F001-000001.pdf",
        "application/pdf",
    )

    assert result == "supabase-private://test-bucket/cotizaciones/tenant_1/F001-000001.pdf"
    assert captured["file_options"] == {
        "content-type": "application/pdf",
        "upsert": "true",
    }


def test_check_storage_ready_verifies_bucket_access(monkeypatch):
    captured = {"get_bucket": [], "list_calls": []}

    class FakeBucket:
        def __init__(self, bucket):
            self.bucket = bucket

        def list(self, path="", options=None):
            captured["list_calls"].append((self.bucket, path, options))
            return []

    class FakeStorage:
        def get_bucket(self, bucket):
            captured["get_bucket"].append(bucket)
            return {"id": bucket}

        def from_(self, bucket):
            return FakeBucket(bucket)

    class FakeClient:
        storage = FakeStorage()

    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: FakeClient())
    monkeypatch.setattr(storage_service.settings, "SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setattr(storage_service.settings, "SUPABASE_SERVICE_ROLE_KEY", "server-key")
    monkeypatch.setattr(storage_service.settings, "SUPABASE_STORAGE_BUCKET", "test-bucket")
    monkeypatch.setattr(storage_service.settings, "SUPABASE_PUBLIC_ASSETS_BUCKET", "public-assets")

    result = storage_service.check_storage_ready()

    assert result["ok"] is True
    assert result["configured"] is True
    assert result["bucket"] == "test-bucket"
    assert result["public_assets_bucket"] == "public-assets"
    assert result["uses_server_key"] is True
    assert result["bucket_accessible"] is True
    assert result["objects_listable"] is True
    assert result["bucket_error"] is None
    assert result["list_error"] is None
    assert result["public_assets_bucket_accessible"] is True
    assert result["public_assets_objects_listable"] is True
    assert result["public_assets_bucket_error"] is None
    assert result["public_assets_list_error"] is None
    assert captured["get_bucket"] == ["test-bucket", "public-assets"]
    assert captured["list_calls"] == [
        ("test-bucket", "", {"limit": 1}),
        ("public-assets", "", {"limit": 1}),
    ]


def test_check_storage_ready_reports_sanitized_read_errors(monkeypatch):
    class FakeBucket:
        def list(self, path="", options=None):
            raise PermissionError("sensitive provider response")

    class FakeStorage:
        def get_bucket(self, bucket):
            raise RuntimeError("sensitive provider response")

        def from_(self, bucket):
            return FakeBucket()

    class FakeClient:
        storage = FakeStorage()

    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: FakeClient())
    monkeypatch.setattr(storage_service.settings, "SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setattr(storage_service.settings, "SUPABASE_SERVICE_ROLE_KEY", "server-key")
    monkeypatch.setattr(storage_service.settings, "SUPABASE_STORAGE_BUCKET", "test-bucket")
    monkeypatch.setattr(storage_service.settings, "SUPABASE_PUBLIC_ASSETS_BUCKET", "public-assets")

    result = storage_service.check_storage_ready()

    assert result["ok"] is False
    assert result["bucket_error"] == "RuntimeError"
    assert result["list_error"] == "PermissionError"
    assert result["public_assets_bucket_error"] == "RuntimeError"
    assert result["public_assets_list_error"] == "PermissionError"
    assert "sensitive provider response" not in str(result)


def test_ops_readiness_fails_when_storage_is_configured_but_inaccessible(monkeypatch):
    class FakeDb:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def execute(self, statement):
            return None

    monkeypatch.setattr(ops_router, "SessionLocal", lambda: FakeDb())
    monkeypatch.setattr(
        ops_router.storage_service,
        "check_storage_ready",
        lambda: {
            "ok": False,
            "configured": True,
            "bucket": "private-bucket",
            "public_assets_bucket": "public-bucket",
            "uses_server_key": True,
            "bucket_accessible": False,
            "objects_listable": False,
            "bucket_error": "RuntimeError",
            "list_error": "PermissionError",
            "public_assets_bucket_accessible": False,
            "public_assets_objects_listable": False,
            "public_assets_bucket_error": "RuntimeError",
            "public_assets_list_error": "PermissionError",
        },
    )

    result = ops_router.readiness(None)

    assert result["ok"] is False
    assert result["checks"]["database"]["ok"] is True
    assert result["checks"]["storage"]["ok"] is False
    assert result["checks"]["storage"]["configured"] is True
    assert result["checks"]["storage"]["bucket_error"] == "RuntimeError"


def test_storage_client_requires_service_role_key_outside_local(monkeypatch):
    supabase_client._supabase_client = None
    monkeypatch.setattr(supabase_client.settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(supabase_client.settings, "SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setattr(supabase_client.settings, "SUPABASE_KEY", "anon-key")
    monkeypatch.setattr(supabase_client.settings, "SUPABASE_SERVICE_ROLE_KEY", "")

    try:
        try:
            supabase_client.get_supabase_client()
        except RuntimeError as exc:
            assert "SUPABASE_SERVICE_ROLE_KEY" in str(exc)
        else:
            raise AssertionError("Expected service-role requirement outside local")
    finally:
        supabase_client._supabase_client = None


def test_settings_reject_public_storage_key_outside_local():
    with pytest.raises(ValueError, match="SUPABASE_SERVICE_ROLE_KEY"):
        Settings(
            ENVIRONMENT="staging",
            DATABASE_URL="postgresql://inkora:test@localhost/inkora",
            SECRET_KEY="test-secret",
            BACKEND_URL="https://api.inkora.test",
            FISCAL_ENV="beta",
            SUPABASE_URL="https://project.supabase.co",
            SUPABASE_KEY="anon-key",
            SUPABASE_SERVICE_ROLE_KEY="",
        )


def test_storage_client_allows_public_key_only_in_local(monkeypatch):
    sentinel = object()
    captured = {}
    supabase_client._supabase_client = None

    def fake_create_client(url, key):
        captured["url"] = url
        captured["key"] = key
        return sentinel

    monkeypatch.setattr(supabase_client.settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(supabase_client.settings, "SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setattr(supabase_client.settings, "SUPABASE_KEY", "anon-key")
    monkeypatch.setattr(supabase_client.settings, "SUPABASE_SERVICE_ROLE_KEY", "")
    monkeypatch.setattr(supabase_client, "create_client", fake_create_client)

    try:
        assert supabase_client.get_supabase_client() is sentinel
        assert captured == {
            "url": "https://project.supabase.co",
            "key": "anon-key",
        }
    finally:
        supabase_client._supabase_client = None
