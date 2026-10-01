"""Local superadmin histories expose every page without provider side effects."""
from datetime import datetime

import pytest

import models
from conftest import make_tenant, make_user
from routers import superadmin as router
from test_superadmin_hardening import _client_for_user


@pytest.fixture
def history(db_session):
    tenant = make_tenant(db_session, "PAGE01")
    other = make_tenant(db_session, "PAGE02")
    admin = make_user(db_session, tenant, email="pagination-root@test.com", rol="superadmin", is_superadmin=True)
    user = make_user(db_session, tenant, email="pagination-tenant@test.com", rol="admin")
    for selected, count in [(tenant, 67), (other, 2)]:
        for index in range(count):
            db_session.add(models.DocumentEmissionJob(
                tenant_id=selected.id, resource_type="cotizacion", resource_id=index + 1,
                action="emit_fiscal_document", status="failed", attempts=2,
                last_error="special error" if index == 10 else "provider unavailable",
                idempotency_key=f"pagination-{selected.id}-{index}", finished_at=datetime(2026, 9, 1),
            ))
            db_session.add(models.AuditLog(entity_type="tenant", entity_id=selected.id,
                action="superadmin.tenant.smartpse.special" if index == 10 else "superadmin.tenant.smartpse.checked",
                timestamp=datetime(2026, 9, 1)))
        db_session.add(models.AuditLog(entity_type="tenant", entity_id=selected.id, action="other.action"))
        db_session.add(models.DocumentEmissionJob(tenant_id=selected.id, resource_type="cotizacion", resource_id=999,
            action="emit_fiscal_document", status="succeeded", idempotency_key=f"success-{selected.id}"))
    db_session.commit()
    return tenant, other, admin, user


@pytest.mark.parametrize("suffix,key", [("emission-errors/page", "job_id"), ("smartpse/audit-logs/page", "id")])
def test_superadmin_history_pages_cover_more_than_fifty_records(db_session, history, suffix, key):
    tenant, other, admin, _ = history
    client = _client_for_user(db_session, admin, router)
    path = f"/superadmin/tenants/{tenant.id}/{suffix}"
    ids = []
    for skip, expected in [(0, 15), (15, 15), (30, 15), (45, 15), (60, 7)]:
        response = client.get(path, params={"skip": skip, "limit": 15})
        assert response.status_code == 200
        payload = response.json()
        assert (payload["total"], payload["skip"], payload["limit"]) == (67, skip, 15)
        assert len(payload["items"]) == expected
        ids.extend(row[key] for row in payload["items"])
    assert len(set(ids)) == 67
    assert ids == sorted(ids, reverse=True)
    assert client.get(path, params={"skip": 100}).json()["items"] == []
    filtered = client.get(path, params={"q": "special"}).json()
    assert filtered["total"] == len(filtered["items"]) == 1
    other_payload = client.get(f"/superadmin/tenants/{other.id}/{suffix}").json()
    assert other_payload["total"] == 2
    assert not set(ids).intersection(row[key] for row in other_payload["items"])


@pytest.mark.parametrize("suffix", ["emission-errors/page", "smartpse/audit-logs/page"])
def test_superadmin_history_authorization_and_validation(db_session, history, suffix):
    tenant, _, admin, user = history
    path = f"/superadmin/tenants/{tenant.id}/{suffix}"
    assert _client_for_user(db_session, user, router).get(path).status_code == 403
    client = _client_for_user(db_session, admin, router)
    assert client.get(f"/superadmin/tenants/999999/{suffix}").status_code == 404
    for params in [{"skip": -1}, {"limit": 0}, {"limit": 101}]:
        assert client.get(path, params=params).status_code == 422


def test_smartpse_companies_page_uses_provider_metadata_and_mock_only(db_session, history, monkeypatch):
    _, _, admin, user = history
    calls = []
    class Provider:
        def list_companies(self, **params):
            calls.append(params)
            skip = (params["page"] - 1) * params["per_page"]
            return {"data": [{"id": str(index), "ruc": f"20{index:09d}", "razon_social": f"Empresa {index}"}
                             for index in range(skip, min(skip + params["per_page"], 37))],
                    "total": 37, "current_page": params["page"], "last_page": 3}
    monkeypatch.setattr(router.smartpse_client, "get_default_client", lambda: Provider())
    client = _client_for_user(db_session, admin, router)
    ids = []
    for page, expected in [(1, 15), (2, 15), (3, 7)]:
        response = client.get("/superadmin/smartpse/companies", params={"page": page, "per_page": 15, "search": "Empresa"})
        assert response.status_code == 200
        assert response.json()["total"] == 37
        assert len(response.json()["data"]) == expected
        ids.extend(row["id"] for row in response.json()["data"])
    assert len(set(ids)) == 37
    assert calls == [{"search": "Empresa", "page": page, "per_page": 15} for page in (1, 2, 3)]
    assert _client_for_user(db_session, user, router).get("/superadmin/smartpse/companies").status_code == 403
    assert len(calls) == 3


def test_smartpse_legacy_history_contract_remains_a_bounded_list(db_session, history):
    tenant, _, admin, _ = history
    response = _client_for_user(db_session, admin, router).get(f"/superadmin/tenants/{tenant.id}/smartpse/audit-logs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 50
