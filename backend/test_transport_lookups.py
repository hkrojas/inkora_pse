from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from api_dependencies import get_current_user
from rate_limit import limiter
from routers.guias import router
from services import transport_lookup_service as svc
from services.factiliza_lookup_service import FactilizaLookupError


@pytest.fixture
def provider(monkeypatch):
    calls = []
    response = {"status": 200, "data": {"placa": "ABC123", "marca": "DEMO", "modelo": "Carga", "color": "Blanco", "vin": "not-exposed"}}
    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=response)
    real_client = httpx.Client
    monkeypatch.setattr(svc.settings, "FACTILIZA_API_TOKEN", "private-provider-token")
    monkeypatch.setattr(svc.settings, "FACTILIZA_API_URL", "https://provider.test/v1")
    monkeypatch.setattr(svc.httpx, "Client", lambda **kwargs: real_client(**kwargs, transport=httpx.MockTransport(handle)))
    return calls, response


def test_plate_normalizes_input_and_limits_returned_data(provider):
    calls, _ = provider
    assert svc.lookup_plate("abc-123") == {"placa": "ABC123", "marca": "DEMO", "modelo": "Carga", "color": "Blanco"}
    assert str(calls[0].url) == "https://provider.test/v1/placa/info/ABC123"
    assert calls[0].headers["authorization"] == "Bearer private-provider-token"


def test_license_is_queried_by_dni_not_license_number(provider):
    calls, payload = provider
    payload["data"] = {"numero_documento": "12345678", "nombre_completo": "PRIVATE NAME", "licencia": {"numero": "Q12345678", "categoria": "A II", "estado": "VIGENTE", "fecha_vencimiento": "2030-01-01"}}
    result = svc.lookup_license("12345678")
    assert result == {"documento": "12345678", "numero": "Q12345678", "categoria": "A II", "estado": "VIGENTE", "fecha_vencimiento": "2030-01-01"}
    assert calls[0].url.path == "/v1/licencia/info/12345678"


@pytest.mark.parametrize("function,value", [(svc.lookup_plate, "a/b"), (svc.lookup_plate, "A" * 50), (svc.lookup_license, "Q12345678"), (svc.lookup_license, "１２３４５６７８")])
def test_invalid_input_never_calls_provider(provider, function, value):
    with pytest.raises(FactilizaLookupError) as caught:
        function(value)
    assert caught.value.status_code == 422
    assert provider[0] == []


@pytest.mark.parametrize("data", [{"placa": "ZZZ999"}, {}, [], None])
def test_plate_rejects_mismatched_or_malformed_data(provider, data):
    provider[1]["data"] = data
    with pytest.raises(FactilizaLookupError):
        svc.lookup_plate("ABC123")


def test_license_rejects_other_person_and_missing_number(provider):
    for data in [{"numero_documento": "87654321", "licencia": {"numero": "Q87654321"}}, {"numero_documento": "12345678", "licencia": {}}]:
        provider[1]["data"] = data
        with pytest.raises(FactilizaLookupError):
            svc.lookup_license("12345678")


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500])
def test_provider_error_envelopes_do_not_leak_provider_messages(provider, status):
    provider[1].update(status=status, message="private-provider-token and private personal details")
    with pytest.raises(FactilizaLookupError) as caught:
        svc.lookup_plate("ABC123")
    assert "private" not in str(caught.value)
    assert caught.value.status_code == (404 if status == 404 else 503)


def test_unconfigured_provider_allows_manual_fallback(monkeypatch):
    monkeypatch.setattr(svc.settings, "FACTILIZA_API_TOKEN", "")
    with pytest.raises(FactilizaLookupError, match="manualmente"):
        svc.lookup_plate("ABC123")


def test_provider_timeout_is_recoverable(monkeypatch):
    monkeypatch.setattr(svc.settings, "FACTILIZA_API_TOKEN", "private")
    real_client = httpx.Client
    def timeout(request):
        raise httpx.ReadTimeout("private", request=request)
    monkeypatch.setattr(svc.httpx, "Client", lambda **kwargs: real_client(**kwargs, transport=httpx.MockTransport(timeout)))
    with pytest.raises(FactilizaLookupError, match="manualmente") as caught:
        svc.lookup_plate("ABC123")
    assert "private" not in str(caught.value)


@pytest.fixture
def lookup_app(monkeypatch):
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.include_router(router)
    limiter.reset()
    monkeypatch.setattr(svc, "lookup_plate", lambda value: {"placa": value})
    monkeypatch.setattr(svc, "lookup_license", lambda value: {"documento": value, "numero": "Q12345678"})
    return app


@pytest.mark.parametrize("path", ["placa/ABC123", "licencia/12345678"])
def test_queries_require_authentication(lookup_app, path):
    assert TestClient(lookup_app).get(f"/guias-remision/consultas/{path}").status_code == 401


@pytest.mark.parametrize("role,active,tenant_id,expected", [("admin", True, 7, 200), ("operador", True, 8, 200), ("vendedor", True, 7, 403), ("admin", False, 7, 403), ("admin", True, None, 403)])
def test_queries_enforce_role_and_active_company(lookup_app, role, active, tenant_id, expected):
    lookup_app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(rol=role, is_superadmin=False, is_active=True, tenant_id=tenant_id, tenant=SimpleNamespace(is_active=active))
    response = TestClient(lookup_app).get("/guias-remision/consultas/placa/ABC123?tenant_id=999")
    assert response.status_code == expected
    if expected == 200:
        assert response.headers["cache-control"] == "no-store"
        assert response.json() == {"placa": "ABC123"}


def test_queries_are_rate_limited(lookup_app):
    lookup_app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(rol="admin", is_superadmin=False, tenant_id=7, tenant=SimpleNamespace(is_active=True))
    client = TestClient(lookup_app)
    responses = [client.get("/guias-remision/consultas/licencia/12345678") for _ in range(21)]
    assert all(response.status_code == 200 for response in responses[:20])
    assert responses[-1].status_code == 429
