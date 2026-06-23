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
    captured = {"get_bucket": [], "from_bucket": []}

    class FakeBucket:
        def list(self, path="", options=None):
            captured["list_path"] = path
            captured["list_options"] = options
            return []

        def upload(self, *, path, file, file_options):
            captured["probe_path"] = path
            captured["probe_file"] = file
            captured["probe_options"] = file_options

        def download(self, path):
            captured["download_path"] = path
            return b"ok"

        def remove(self, paths):
            captured["remove_paths"] = paths

    class FakeStorage:
        def get_bucket(self, bucket):
            captured["get_bucket"].append(bucket)
            return {"id": bucket}

        def from_(self, bucket):
            captured["from_bucket"].append(bucket)
            return FakeBucket()

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
    assert result["probe_writable"] is True
    assert result["bucket_error"] is None
    assert result["list_error"] is None
    assert result["probe_error"] is None
    assert result["public_assets_bucket_accessible"] is True
    assert result["public_assets_objects_listable"] is True
    assert result["public_assets_bucket_error"] is None
    assert result["public_assets_list_error"] is None
    assert captured["get_bucket"] == ["test-bucket", "public-assets"]
    assert captured["from_bucket"].count("test-bucket") == 4
    assert captured["from_bucket"].count("public-assets") == 1
    assert captured["list_path"] == ""
    assert captured["list_options"] == {"limit": 1}
    assert captured["probe_path"] == "_health/storage-readiness.txt"
    assert captured["probe_file"] == b"ok"
    assert captured["probe_options"] == {"content-type": "text/plain", "upsert": "true"}
    assert captured["download_path"] == "_health/storage-readiness.txt"
    assert captured["remove_paths"] == ["_health/storage-readiness.txt"]


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
