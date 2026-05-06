import sys
import types

from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from config import settings


if "slowapi" not in sys.modules:
    slowapi_module = types.ModuleType("slowapi")
    slowapi_errors_module = types.ModuleType("slowapi.errors")
    slowapi_util_module = types.ModuleType("slowapi.util")

    class RateLimitExceeded(Exception):
        pass

    class Limiter:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def limit(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

    async def _rate_limit_exceeded_handler(request, exc):
        return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)

    def get_remote_address(request):
        return "test-client"

    slowapi_module.Limiter = Limiter
    slowapi_module._rate_limit_exceeded_handler = _rate_limit_exceeded_handler
    slowapi_errors_module.RateLimitExceeded = RateLimitExceeded
    slowapi_util_module.get_remote_address = get_remote_address

    sys.modules["slowapi"] = slowapi_module
    sys.modules["slowapi.errors"] = slowapi_errors_module
    sys.modules["slowapi.util"] = slowapi_util_module

from main import create_app


FROZEN_ROUTE = "/proveedores/"
FROZEN_TAG = "frozen-non-launch"
LAUNCH_ROUTE = "/health"
FISCAL_LEGACY_ROUTE = "/retenciones/emitir-legacy"


def _client_for_environment(monkeypatch, environment: str) -> TestClient:
    monkeypatch.setattr(settings, "ENVIRONMENT", environment)
    return TestClient(create_app())


def _openapi_paths(client: TestClient) -> dict:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    return response.json()["paths"]


def _has_frozen_tag(paths: dict) -> bool:
    return any(
        FROZEN_TAG in operation.get("tags", [])
        for methods in paths.values()
        for operation in methods.values()
    )


def test_legacy_frozen_routes_are_available_in_local(monkeypatch):
    client = _client_for_environment(monkeypatch, "development")
    paths = _openapi_paths(client)

    assert FROZEN_ROUTE in paths
    assert _has_frozen_tag(paths)

    response = client.get(FROZEN_ROUTE)
    assert response.status_code == 401


def test_legacy_frozen_routes_are_available_in_test(monkeypatch):
    client = _client_for_environment(monkeypatch, "test")
    paths = _openapi_paths(client)

    assert FROZEN_ROUTE in paths
    assert _has_frozen_tag(paths)


def test_legacy_frozen_routes_are_not_registered_in_staging(monkeypatch):
    client = _client_for_environment(monkeypatch, "staging")
    paths = _openapi_paths(client)

    assert FROZEN_ROUTE not in paths
    assert not _has_frozen_tag(paths)
    assert client.get(FROZEN_ROUTE).status_code == 404
    assert client.get(LAUNCH_ROUTE).status_code == 200


def test_legacy_frozen_routes_are_not_registered_in_production(monkeypatch):
    client = _client_for_environment(monkeypatch, "production")
    paths = _openapi_paths(client)

    assert FROZEN_ROUTE not in paths
    assert not _has_frozen_tag(paths)
    assert client.get(FROZEN_ROUTE).status_code == 404
    assert client.get(LAUNCH_ROUTE).status_code == 200


def test_legacy_frozen_routes_are_not_registered_in_launch_mode(monkeypatch):
    client = _client_for_environment(monkeypatch, "launch")
    paths = _openapi_paths(client)

    assert FROZEN_ROUTE not in paths
    assert not _has_frozen_tag(paths)
    assert client.get(FROZEN_ROUTE).status_code == 404
    assert client.get(LAUNCH_ROUTE).status_code == 200


def test_removed_fiscal_legacy_endpoint_does_not_return_with_frozen_local(monkeypatch):
    client = _client_for_environment(monkeypatch, "development")

    response = client.post(FISCAL_LEGACY_ROUTE, json={})

    assert response.status_code == 410
