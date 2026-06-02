from services import storage_service


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
    )

    assert result == "https://cdn.test/logos/logo.png"
    assert captured["bucket"] == "test-bucket"
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
    captured = {}

    class FakeBucket:
        def list(self, path="", options=None):
            captured["list_path"] = path
            captured["list_options"] = options
            return []

    class FakeStorage:
        def get_bucket(self, bucket):
            captured["bucket"] = bucket
            return {"id": bucket}

        def from_(self, bucket):
            captured["from_bucket"] = bucket
            return FakeBucket()

    class FakeClient:
        storage = FakeStorage()

    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: FakeClient())
    monkeypatch.setattr(storage_service.settings, "SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setattr(storage_service.settings, "SUPABASE_SERVICE_ROLE_KEY", "server-key")
    monkeypatch.setattr(storage_service.settings, "SUPABASE_STORAGE_BUCKET", "test-bucket")

    result = storage_service.check_storage_ready()

    assert result["ok"] is True
    assert result["configured"] is True
    assert result["bucket"] == "test-bucket"
    assert result["uses_server_key"] is True
    assert result["bucket_accessible"] is True
    assert result["objects_listable"] is True
    assert result["bucket_error"] is None
    assert result["list_error"] is None
    assert captured["bucket"] == "test-bucket"
    assert captured["list_path"] == ""
    assert captured["list_options"] == {"limit": 1}
