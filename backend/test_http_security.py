import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from api_dependencies import get_db_tenant
from database import activate_tenant_context, current_tenant_id, reset_tenant_context
from http_security import CORS_ALLOWED_HEADERS, SECURITY_HEADERS
from main import create_app


def test_api_responses_include_security_headers_and_request_id():
    response = TestClient(create_app()).get(
        "/health",
        headers={"X-Request-Id": "security-test-request"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "security-test-request"
    for name, value in SECURITY_HEADERS.items():
        assert response.headers[name] == value


def test_cors_preflight_accepts_known_headers_and_rejects_unknown_header():
    client = TestClient(create_app())
    origin = "http://localhost:5173"

    accepted = client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,idempotency-key,x-request-id",
        },
    )
    rejected = client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-unexpected-privileged-header",
        },
    )

    assert accepted.status_code == 200
    assert accepted.headers["access-control-allow-origin"] == origin
    assert rejected.status_code == 400
    assert "Authorization" in CORS_ALLOWED_HEADERS
    assert "Idempotency-Key" in CORS_ALLOWED_HEADERS


def test_get_db_tenant_restores_nested_context():
    outer_token = activate_tenant_context(91)
    dependency = get_db_tenant(
        current_user=SimpleNamespace(tenant_id=92),
        db=SimpleNamespace(),
    )
    try:
        assert next(dependency) is not None
        assert current_tenant_id.get() == 92
        dependency.close()
        assert current_tenant_id.get() == 91
    finally:
        reset_tenant_context(outer_token)


def test_tenant_context_is_isolated_between_concurrent_tasks():
    async def scenario():
        ready = 0
        ready_lock = asyncio.Lock()
        release = asyncio.Event()

        async def worker(tenant_id: int):
            nonlocal ready
            token = activate_tenant_context(tenant_id)
            try:
                async with ready_lock:
                    ready += 1
                    if ready == 2:
                        release.set()
                await release.wait()
                await asyncio.sleep(0)
                return current_tenant_id.get()
            finally:
                reset_tenant_context(token)

        return await asyncio.gather(worker(101), worker(202))

    assert asyncio.run(scenario()) == [101, 202]
    assert current_tenant_id.get() is None


def test_vercel_configs_apply_the_same_browser_security_policy():
    repository_root = Path(__file__).resolve().parents[1]
    expected = {
        "Content-Security-Policy",
        "Permissions-Policy",
        "Referrer-Policy",
        "X-Content-Type-Options",
        "X-Frame-Options",
    }

    for relative_path in ("vercel.json", "frontend/vercel.json"):
        config = json.loads((repository_root / relative_path).read_text(encoding="utf-8"))
        configured = {
            item["key"]
            for rule in config["headers"]
            for item in rule["headers"]
        }
        assert configured == expected
