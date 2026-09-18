"""Pruebas del modo de contingencia fiscal diferida."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

import crud
import models
from api_dependencies import get_current_user, get_db
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from routers import superadmin as superadmin_router
from services import emission_queue_service


def _make_fiscal_document(db_session, suffix: str):
    tenant = make_tenant(db_session, suffix)
    user = make_user(db_session, tenant, email=f"{suffix.lower()}@test.com")
    cliente = make_cliente(
        db_session,
        tenant,
        suffix,
        tipo_documento="6",
        numero_documento="20191308868",
    )
    quote = make_quote_via_crud(db_session, tenant, user, cliente)
    fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
    return tenant, user, fiscal


def _client_for_user(db_session, user):
    app = FastAPI()
    app.include_router(superadmin_router.router)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def test_contingency_reserves_document_without_claiming_provider_job(db_session):
    tenant, user, fiscal = _make_fiscal_document(db_session, "FC01")
    tenant.fiscal_contingency_mode = True
    tenant.fiscal_contingency_reason = "Incidente Smart PSE"
    db_session.commit()
    db_session.refresh(user)

    job, created = emission_queue_service.enqueue_fiscal_document_job(
        db_session,
        fiscal,
        user,
        tipo_comprobante="01",
    )
    payload = emission_queue_service.build_job_acceptance_payload(
        job,
        message="Documento encolado",
        resource_id=fiscal.id,
        resource_type=models.EMISSION_JOB_RESOURCE_COTIZACION,
    )

    assert created is True
    assert job.status == models.EMISSION_JOB_STATUS_CONTINGENCY_PENDING
    assert crud.claim_next_emission_job(db_session) is None
    assert payload["success"] is True
    assert payload["queued"] is True
    assert payload["deferred"] is True
    assert "contingencia" in payload["message"].lower()


def test_contingency_holds_only_unstarted_cpe_jobs_and_releases_in_order(db_session):
    tenant, user, fiscal = _make_fiscal_document(db_session, "FC02")
    first = crud.create_emission_job(
        db_session,
        tenant_id=tenant.id,
        created_by_user_id=user.id,
        resource_type=models.EMISSION_JOB_RESOURCE_COTIZACION,
        resource_id=fiscal.id,
        action=models.EMISSION_JOB_ACTION_EMIT_FISCAL,
        provider="smartpse",
        idempotency_key=f"contingency:first:{fiscal.id}",
    )
    second = crud.create_emission_job(
        db_session,
        tenant_id=tenant.id,
        created_by_user_id=user.id,
        resource_type=models.EMISSION_JOB_RESOURCE_COTIZACION,
        resource_id=fiscal.id + 1,
        action=models.EMISSION_JOB_ACTION_EMIT_NOTE,
        provider="smartpse",
        idempotency_key=f"contingency:second:{fiscal.id}",
    )
    ambiguous = crud.create_emission_job(
        db_session,
        tenant_id=tenant.id,
        created_by_user_id=user.id,
        resource_type=models.EMISSION_JOB_RESOURCE_COTIZACION,
        resource_id=fiscal.id + 2,
        action=models.EMISSION_JOB_ACTION_EMIT_FISCAL,
        provider="smartpse",
        idempotency_key=f"contingency:ambiguous:{fiscal.id}",
        initial_status=models.EMISSION_JOB_STATUS_PENDING_CONFIRMATION,
    )

    enabled = crud.set_tenant_fiscal_contingency(
        db_session,
        tenant.id,
        enabled=True,
        reason="Smart PSE intermitente",
    )
    db_session.expire_all()

    assert enabled["held_jobs"] == 2
    assert crud.get_emission_job(db_session, first.id).status == models.EMISSION_JOB_STATUS_CONTINGENCY_PENDING
    assert crud.get_emission_job(db_session, second.id).status == models.EMISSION_JOB_STATUS_CONTINGENCY_PENDING
    assert crud.get_emission_job(db_session, ambiguous.id).status == models.EMISSION_JOB_STATUS_PENDING_CONFIRMATION
    enabled_status = crud.get_tenant_fiscal_contingency_status(db_session, tenant.id)
    assert enabled_status["held_jobs"] == 2
    assert enabled_status["processing_jobs"] == 0
    assert enabled_status["pending_confirmation_jobs"] == 1

    disabled = crud.set_tenant_fiscal_contingency(
        db_session,
        tenant.id,
        enabled=False,
        release_interval_seconds=15,
    )
    db_session.expire_all()
    released_first = crud.get_emission_job(db_session, first.id)
    released_second = crud.get_emission_job(db_session, second.id)

    assert disabled["released_jobs"] == 2
    assert released_first.status == models.EMISSION_JOB_STATUS_QUEUED
    assert released_second.status == models.EMISSION_JOB_STATUS_QUEUED
    assert released_second.available_at > released_first.available_at
    assert crud.get_emission_job(db_session, ambiguous.id).status == models.EMISSION_JOB_STATUS_PENDING_CONFIRMATION
    disabled_status = crud.get_tenant_fiscal_contingency_status(db_session, tenant.id)
    assert disabled_status["held_jobs"] == 0
    assert disabled_status["pending_confirmation_jobs"] == 1


def test_fiscal_contingency_endpoint_requires_real_superadmin_and_audits(db_session):
    tenant = make_tenant(db_session, "FC03")
    admin_tenant = make_tenant(db_session, "FC04")
    tenant_admin = make_user(db_session, tenant, email="fc03-admin@test.com")
    superadmin = make_user(
        db_session,
        admin_tenant,
        email="fc04-superadmin@test.com",
        is_superadmin=True,
    )

    forbidden = _client_for_user(db_session, tenant_admin).patch(
        f"/superadmin/tenants/{tenant.id}/fiscal-contingency",
        json={"enabled": True, "reason": "Incidente"},
    )
    response = _client_for_user(db_session, superadmin).patch(
        f"/superadmin/tenants/{tenant.id}/fiscal-contingency",
        json={"enabled": True, "reason": "Incidente Smart PSE"},
    )
    forbidden_status = _client_for_user(db_session, tenant_admin).get(
        f"/superadmin/tenants/{tenant.id}/fiscal-contingency",
    )
    status_response = _client_for_user(db_session, superadmin).get(
        f"/superadmin/tenants/{tenant.id}/fiscal-contingency",
    )

    db_session.expire_all()
    updated_tenant = crud.get_tenant(db_session, tenant.id)
    audit = db_session.query(models.AuditLog).filter(
        models.AuditLog.action == "superadmin.tenant.fiscal_contingency.updated",
    ).one()

    assert forbidden.status_code == 403
    assert forbidden_status.status_code == 403
    assert response.status_code == 200
    assert response.json()["enabled"] is True
    assert status_response.status_code == 200
    assert status_response.json() == {
        "tenant_id": tenant.id,
        "enabled": True,
        "reason": "Incidente Smart PSE",
        "started_at": status_response.json()["started_at"],
        "held_jobs": 0,
        "released_jobs": 0,
        "processing_jobs": 0,
        "pending_confirmation_jobs": 0,
    }
    assert updated_tenant.fiscal_contingency_mode is True
    assert audit.entity_id == tenant.id
    assert "reason=Incidente Smart PSE" in audit.details


def test_fiscal_contingency_endpoint_requires_reason_when_enabling(db_session):
    tenant = make_tenant(db_session, "FC05")
    admin_tenant = make_tenant(db_session, "FC06")
    superadmin = make_user(
        db_session,
        admin_tenant,
        email="fc06-superadmin@test.com",
        is_superadmin=True,
    )

    response = _client_for_user(db_session, superadmin).patch(
        f"/superadmin/tenants/{tenant.id}/fiscal-contingency",
        json={"enabled": True, "reason": "   "},
    )

    assert response.status_code == 422
    db_session.refresh(tenant)
    assert tenant.fiscal_contingency_mode is False
