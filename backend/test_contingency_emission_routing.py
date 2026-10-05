"""An enrolled invoice cannot bypass the durable worker with mode=sync."""
import json
from unittest.mock import patch

import pytest
from fastapi import BackgroundTasks
from starlette.requests import Request

import models
import schemas
from config import settings
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from routers import facturacion
from services import emission_queue_service as queue


@pytest.mark.parametrize("requested", ["sync", "async", None])
def test_enrolled_invoice_route_enqueues_without_provider(db_session, monkeypatch, requested):
    tenant = make_tenant(db_session, "CR01")
    tenant.business_ruc = "20123456789"
    tenant.smartpse_company_id = "77"
    tenant.smartpse_environment = "demo"
    tenant.smartpse_usuario_secundaria = "local-demo-user"
    tenant.smartpse_token_acceso = "local-demo-token"
    user = make_user(db_session, tenant, email="routing@test.com")
    db_session.add(models.Subscription(tenant_id=tenant.id, status="active"))
    db_session.commit()
    client = make_cliente(db_session, tenant, "CR01", tipo_documento="6", numero_documento="20191308868")
    quote = make_quote_via_crud(db_session, tenant, user, client)
    monkeypatch.setattr(settings, "FISCAL_CONTINGENCY_TENANT_IDS", str(tenant.id))
    monkeypatch.setattr(settings, "EMISSION_MODE_DEFAULT", "sync")
    request = Request({"type": "http", "method": "POST", "path": "/cotizaciones/facturar",
                       "headers": [], "client": ("127.0.0.1", 1234)})
    with patch.object(queue.facturacion_service, "emitir_factura") as provider:
        response = facturacion.emitir_comprobante(request, quote.id,
            schemas.FacturarPayload(tipo_comprobante="01"), BackgroundTasks(),
            db=db_session, current_user=user, _emission_check=user, mode=requested)
    assert response.status_code == 202
    data = json.loads(response.body)
    job = db_session.query(models.DocumentEmissionJob).one()
    assert data["queued"] is True
    assert job.tenant_id == tenant.id and job.created_by_user_id == user.id
    assert job.payload_snapshot["recovery_flow"] is True
    assert job.payload_snapshot["submission_phase"] == "not_started"
    assert db_session.query(models.Cotizacion).filter_by(source_quote_id=quote.id).count() == 1
    provider.assert_not_called()


@pytest.mark.parametrize("tipo,enrolled", [("01", False), ("03", True), ("07", True), (None, True)])
def test_sync_remains_available_outside_enrolled_invoice_scope(monkeypatch, tipo, enrolled):
    monkeypatch.setattr(settings, "FISCAL_CONTINGENCY_TENANT_IDS", "5" if enrolled else "6")
    assert queue.resolve_emission_mode("sync", tenant_id=5, tipo_comprobante=tipo) == "sync"


def test_unknown_mode_remains_invalid_for_enrolled_invoice(monkeypatch):
    monkeypatch.setattr(settings, "FISCAL_CONTINGENCY_TENANT_IDS", "5")
    with pytest.raises(ValueError):
        queue.resolve_emission_mode("unknown", tenant_id=5, tipo_comprobante="01")
