from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import crud
import models
from api_dependencies import get_current_user, get_db, get_db_tenant
from conftest import make_tenant, make_user
from routers import facturacion
from services import document_actions_service as actions
from services import emission_queue_service
from test_emission_queue import _make_fiscal_document


@pytest.fixture(autouse=True)
def isolated_rate_limiter():
    facturacion.limiter.reset()


def client_for(db, user):
    app = FastAPI()
    app.include_router(facturacion.router)
    app.dependency_overrides[get_current_user] = lambda: user
    def session():
        yield db
    app.dependency_overrides[get_db_tenant] = session
    app.dependency_overrides[get_db] = session
    return TestClient(app)


@pytest.mark.parametrize('status,error', [
    ('pending_confirmation', '[1033] informado con otros datos'),
    ('failed', '[1033] informado con otros datos'),
    ('failed', 'timeout'),
    ('failed', 'Error desconocido'),
    ('processing', '[3127] validacion'),
    ('succeeded', '[3127] validacion'),
])
def test_unknown_or_processed_never_requeues(db_session, status, error):
    _, user, doc = _make_fiscal_document(db_session, 'DA1')
    doc.sunat_error = error
    job, _ = emission_queue_service.enqueue_fiscal_document_job(db_session, doc, user, tipo_comprobante='01')
    job.status = status
    job.last_error = error
    db_session.commit()
    client = client_for(db_session, user)
    assert client.get(f'/facturas-emitidas/{doc.id}/acciones').json()['retry_emission'] is False
    with patch.object(emission_queue_service, 'enqueue_fiscal_document_job') as enqueue:
        assert client.post(f'/facturas-emitidas/{doc.id}/reintentar').status_code == 409
        enqueue.assert_not_called()
    assert job.status == status


def test_safe_retry_keeps_identity_and_single_job(db_session):
    _, user, doc = _make_fiscal_document(db_session, 'DA2')
    identity = (doc.id, doc.serie, doc.correlativo)
    job, _ = emission_queue_service.enqueue_fiscal_document_job(db_session, doc, user, tipo_comprobante='01')
    job.status = 'failed'
    job.last_error = '[3127] Error de validación XML'
    doc.sunat_error = job.last_error
    db_session.commit()
    client = client_for(db_session, user)
    with patch.object(facturacion, '_validar_pre_emision'), patch.object(facturacion, '_ensure_emission_credentials'):
        response = client.post(f'/facturas-emitidas/{doc.id}/reintentar')
        assert response.status_code == 202, response.text
        assert response.json()['job_id'] == job.id
        assert client.post(f'/facturas-emitidas/{doc.id}/reintentar').status_code == 409
    assert identity == (doc.id, doc.serie, doc.correlativo)
    assert db_session.query(models.DocumentEmissionJob).count() == 1
    assert db_session.query(models.AuditLog).filter_by(action='fiscal_retry_requested').count() == 1
    assert db_session.query(models.InventoryMovement).count() == 0


def test_retry_obeys_contingency(db_session):
    tenant, user, doc = _make_fiscal_document(db_session, 'DA3')
    tenant.fiscal_contingency_mode = True
    doc.sunat_error = '[3127] Error de validación XML'
    db_session.commit()
    with patch.object(facturacion, '_validar_pre_emision'), patch.object(facturacion, '_ensure_emission_credentials'):
        response = client_for(db_session, user).post(f'/facturas-emitidas/{doc.id}/reintentar')
    assert response.status_code == 202, response.text
    assert response.json()['job_status'] == 'contingency_pending'


@pytest.mark.parametrize('path,method', [
    ('acciones','get'), ('reintentar','post'), ('artifacts/retry','post'),
])
def test_other_tenant_cannot_access_document_actions(db_session, path, method):
    _, _, doc = _make_fiscal_document(db_session, 'DA4')
    other = make_user(db_session, make_tenant(db_session, 'DA5'), email='other@actions.test')
    subscription = models.Subscription(tenant_id=other.tenant_id, status='active')
    db_session.add(subscription)
    db_session.commit()
    prefix = 'facturacion' if path == 'artifacts/retry' else 'facturas-emitidas'
    response = getattr(client_for(db_session, other), method)(f'/{prefix}/{doc.id}/{path}')
    assert response.status_code == 404, response.text


@pytest.mark.parametrize('role,active', [('vendedor',True), ('admin',False)])
def test_permissions_enforced(db_session, role, active):
    tenant, user, doc = _make_fiscal_document(db_session, 'DA6')
    user.rol = role
    tenant.is_active = active
    db_session.commit()
    client = client_for(db_session, user)
    assert client.post(f'/facturas-emitidas/{doc.id}/reintentar').status_code == 403
    assert client.post(f'/facturacion/{doc.id}/artifacts/retry').status_code == 403


def test_artifact_recovery_does_not_emit(db_session):
    _, user, doc = _make_fiscal_document(db_session, 'DA7')
    doc.estado = 'facturada'
    doc.sunat_cdr_content = '<ApplicationResponse />'
    db_session.commit()
    with patch.object(facturacion.fiscal_artifact_service, 'persist_cdr_artifact', return_value='private-cdr'), patch.object(facturacion.pdf_storage_service, 'generate_and_upload_pdf', return_value='private-pdf'), patch.object(facturacion.facturacion_service, 'emitir_factura') as send:
        response = client_for(db_session, user).post(f'/facturacion/{doc.id}/artifacts/retry')
    assert response.status_code == 200, response.text
    send.assert_not_called()


def test_cdr_and_detraction_block_retry():
    doc = SimpleNamespace(document_kind='fiscal_document', tipo_comprobante='01', estado='pendiente', sunat_accepted=False, sunat_cdr_content='cdr', sunat_cdr_url=None)
    assert 'CDR' in actions.retry_block_reason(doc, [])


def test_preserves_prior_ambiguous_history(db_session):
    _, user, doc = _make_fiscal_document(db_session, 'DA8')
    job, _ = emission_queue_service.enqueue_fiscal_document_job(db_session, doc, user, tipo_comprobante='01')
    job.status = 'failed'
    job.last_error = '[3127] XML invalido'
    db_session.add(models.DocumentEmissionAttempt(tenant_id=doc.tenant_id, job_id=job.id, attempt_number=1, status='failed', error_classification='ambiguous'))
    db_session.commit()
    assert actions.available_actions(db_session, doc, user)['retry_emission'] is False
