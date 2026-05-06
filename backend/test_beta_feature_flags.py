from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import crud
import models
from api_dependencies import get_current_user, get_db, get_db_tenant
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from routers import facturacion as facturacion_router
from routers import superadmin as superadmin_router
from services import beta_feature_flags, emission_queue_service, fiscal_provider_service


def _set_subscription(db_session, tenant, *, status="active", flags=None):
    subscription = crud.get_subscription_by_tenant(db_session, tenant.id)
    if subscription is None:
        subscription = models.Subscription(tenant_id=tenant.id)
        db_session.add(subscription)
    subscription.status = status
    subscription.beta_feature_flags = flags
    db_session.commit()
    db_session.refresh(subscription)
    return subscription


def _client_for_user(db_session, user, *routers):
    app = FastAPI()
    for router in routers:
        app.include_router(router.router)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_db_tenant] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def test_sensitive_fiscal_features_default_to_blocked():
    flags = beta_feature_flags.normalize_fiscal_feature_flags(None)

    assert flags
    assert all(enabled is False for enabled in flags.values())
    assert flags[beta_feature_flags.FISCAL_FEATURE_CREDIT_NOTES] is False
    assert flags[beta_feature_flags.FISCAL_FEATURE_DIRECT_SUNAT] is False


def test_superadmin_actualiza_flags_fiscales_y_audita(db_session):
    tenant = make_tenant(db_session, "BF01")
    superadmin = make_user(
        db_session,
        tenant,
        email="flags-superadmin@test.com",
        rol="superadmin",
        is_superadmin=True,
    )
    _set_subscription(db_session, tenant)
    client = _client_for_user(db_session, superadmin, superadmin_router)

    response = client.put(
        f"/superadmin/tenants/{tenant.id}/fiscal-flags",
        json={"flags": {"credit_notes": True, "guides": True}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == tenant.id
    assert body["flags"]["credit_notes"] is True
    assert body["flags"]["guides"] is True
    assert body["flags"]["direct_sunat"] is False
    assert body["definitions"]
    assert (
        db_session.query(models.AuditLog)
        .filter(models.AuditLog.action == "superadmin.subscription.fiscal_flags_updated")
        .count()
        == 1
    )


def test_nota_credito_no_crea_ni_llama_proveedor_si_flag_desactivado(db_session):
    tenant = make_tenant(db_session, "BF02")
    user = make_user(db_session, tenant, email="flags-note@test.com")
    cliente = make_cliente(db_session, tenant, "BF02")
    _set_subscription(db_session, tenant)
    quote = make_quote_via_crud(db_session, tenant, user, cliente)
    fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
    fiscal.estado = "facturada"
    fiscal.sunat_xml_content = "<xml />"
    db_session.commit()
    client = _client_for_user(db_session, user, facturacion_router)

    with patch("routers.facturacion.facturacion_service.emitir_nota") as provider_call:
        response = client.post(
            "/notas/emitir",
            json={
                "comprobante_afectado_id": fiscal.id,
                "tipo_nota": "credito",
                "cod_motivo": "01",
                "descripcion_motivo": "ANULACION DE LA OPERACION",
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FISCAL_FEATURE_DISABLED"
    provider_call.assert_not_called()
    assert (
        db_session.query(models.Cotizacion)
        .filter(
            models.Cotizacion.tenant_id == tenant.id,
            models.Cotizacion.document_kind == "credit_note",
        )
        .count()
        == 0
    )


def test_worker_de_guia_falla_no_retryable_si_flag_desactivado(db_session):
    tenant = make_tenant(db_session, "BF03")
    tenant.apisperu_token = "fake-token"
    user = make_user(db_session, tenant, email="flags-guide@test.com")
    _set_subscription(db_session, tenant)
    guia = models.GuiaRemision(
        tenant_id=tenant.id,
        usuario_id=user.id,
        fecha_traslado=datetime.now(timezone.utc),
        motivo_traslado="01",
        partida_direccion="Av. Partida 1",
        llegada_direccion="Av. Llegada 2",
        serie="T001",
        correlativo=1,
        estado="pendiente",
    )
    db_session.add(guia)
    db_session.flush()
    job = models.DocumentEmissionJob(
        tenant_id=tenant.id,
        created_by_user_id=user.id,
        resource_type=models.EMISSION_JOB_RESOURCE_GUIA,
        resource_id=guia.id,
        action=models.EMISSION_JOB_ACTION_EMIT_GUIDE,
        provider="apisperu",
        idempotency_key="emit:guide:bf03",
    )
    db_session.add(job)
    db_session.commit()

    with patch("services.emission_queue_service.facturacion_service.emitir_guia_remision") as provider_call:
        processed = emission_queue_service.process_emission_job(job.id, db_session=db_session)

    db_session.refresh(job)
    assert processed is False
    assert job.status == models.EMISSION_JOB_STATUS_FAILED
    assert "guides" in job.last_error
    provider_call.assert_not_called()


def test_direct_sunat_requiere_feature_flag_en_production(monkeypatch, db_session):
    tenant = make_tenant(db_session, "BF04")
    subscription = _set_subscription(db_session, tenant, flags={})
    tenant.subscription = subscription
    tenant.sunat_usuario_sol = "MODDATOS"
    tenant.sunat_clave_sol = "moddatos"
    tenant.sunat_cert_password = "secret"
    tenant.sunat_cert_url = "https://storage.test/cert.p12"
    db_session.commit()

    monkeypatch.setattr(fiscal_provider_service.settings, "FISCAL_ENV", "production")

    assert fiscal_provider_service.can_use_direct_sunat(tenant) is False
    assert "feature flag" in fiscal_provider_service.direct_sunat_block_reason(tenant)

    subscription.beta_feature_flags = {"direct_sunat": True}
    assert fiscal_provider_service.can_use_direct_sunat(tenant) is True
