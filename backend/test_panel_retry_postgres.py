"""Real PostgreSQL fencing for panel retries; loopback disposable DB, no HTTP."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import threading
from uuid import uuid4

import pytest

import models
from config import settings
from services import emission_leases as leases
from services import emission_queue_service as queue
from services import fiscal_evidence_service as evidence
from services import fiscal_recovery_service as recovery
from services import facturacion_service, smartpse_response
from services.fiscal_submission_state import mark_possible
from test_emission_queue import _make_fiscal_document
from test_emission_worker_postgres import factory, clear_jobs  # noqa: F401
from test_fiscal_contingency_recovery import sign_xml  # noqa: F401
from test_smartpse_response_normalization import _sale_cdr


def prepare(factory, sign_xml, monkeypatch, *, jobs=2):
    monkeypatch.setattr(settings, 'FISCAL_CONTINGENCY_TENANT_IDS', '*')
    with factory() as db:
        tenant, user, document = _make_fiscal_document(db, 'PANELPG'+uuid4().hex[:7])
        tenant.business_ruc = f'20{tenant.id:09d}'
        db.commit()
        monkeypatch.setattr(settings, 'SMARTPSE_PANEL_RETRY_TENANT_IDS', str(tenant.id))
        monkeypatch.setattr(settings, 'SMARTPSE_PANEL_RECOVERY_TENANT_IDS', str(tenant.id))
        first, _ = queue.enqueue_fiscal_document_job(db, document, user, tipo_comprobante='01')
        prepared = first.payload_snapshot['prepared_sale']
        xml = sign_xml(prepared['unsigned_xml'])
        assert evidence.retain_sale_evidence(db, document, {'xml_firmado': xml}, payload=prepared['payload'])
        snapshot = mark_possible(first.payload_snapshot)
        all_jobs = [first]
        for _ in range(jobs-1):
            job = models.DocumentEmissionJob(tenant_id=tenant.id,created_by_user_id=user.id,
                resource_type='cotizacion',resource_id=document.id,provider='smartpse',
                idempotency_key='panel-pg-'+uuid4().hex,action='consult_fiscal_document')
            db.add(job)
            all_jobs.append(job)
        for job in all_jobs:
            job.payload_snapshot = deepcopy(snapshot)
            job.action = 'consult_fiscal_document'
            job.status = 'processing'
            job.worker_owner = uuid4().hex
            job.lease_token = str(uuid4())
            job.lease_expires_at = datetime.now()+timedelta(minutes=3)
        db.commit()
        metadata = {'provider_document_id':'444000','provider_company_id':str(tenant.smartpse_company_id),
            'environment':'demo','state':'error',
            'provider_error_message':'HTTP 503 Service Unavailable',
            'xml_sha256':hashlib.sha256(xml.encode()).hexdigest()}
        return {'tenant_id':tenant.id,'user_id':user.id,'document_id':document.id,
            'jobs':[(job.id,job.lease_token) for job in all_jobs], 'xml':xml,'metadata':metadata}


def test_two_jobs_for_same_invoice_authorize_exactly_one_panel_post(factory, sign_xml, monkeypatch):
    data = prepare(factory, sign_xml, monkeypatch)
    start = threading.Barrier(2)
    def reserve(reservation):
        with factory() as db:
            leases.attach(db, *reservation)
            try:
                start.wait(timeout=10)
                allowed = queue._reserve_panel_retry_attempt(db, reservation[0], data['user_id'],
                    data['xml'], data['metadata'])
                assert not db.in_transaction(), 'No SQL transaction may survive the authorization callback'
                return allowed
            finally:
                db.rollback()
                leases.detach(db)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(reserve, data['jobs']))
    assert sorted(outcomes) == [False, True]
    with factory() as db:
        jobs = db.query(models.DocumentEmissionJob).filter_by(tenant_id=data['tenant_id'],
            resource_type='cotizacion',resource_id=data['document_id']).all()
        assert sum('panel_retry_attempt' in job.payload_snapshot for job in jobs) == 1
        assert db.query(models.AuditLog).filter_by(action='fiscal_panel_retry_started',
            entity_type='cotizacion',entity_id=data['document_id']).count() == 1


def test_append_only_attempt_blocks_new_job_after_evidence_snapshot_replacement(factory, sign_xml, monkeypatch):
    data = prepare(factory, sign_xml, monkeypatch)
    first, second = data['jobs']
    with factory() as db:
        leases.attach(db, *first)
        assert queue._reserve_panel_retry_attempt(db, first[0], data['user_id'],data['xml'],data['metadata']) is True
        assert not db.in_transaction()
        leases.detach(db)
        job = db.get(models.DocumentEmissionJob, first[0])
        snapshot = dict(job.payload_snapshot)
        snapshot.pop('panel_retry_attempt')
        job.payload_snapshot = snapshot
        document = db.get(models.Cotizacion, data['document_id'])
        response = deepcopy(document.provider_response)
        response['inkora_evidence'].pop('panel_retry_attempt')
        document.provider_response = response
        db.commit()
    # A new session/new job must still see the durable audit after a restart.
    with factory() as db:
        leases.attach(db, *second)
        try:
            assert queue._reserve_panel_retry_attempt(db,second[0],data['user_id'],data['xml'],data['metadata']) is False
            assert not db.in_transaction()
        finally:
            leases.detach(db)


def test_expired_lease_cannot_persist_panel_attempt(factory, sign_xml, monkeypatch):
    data = prepare(factory, sign_xml, monkeypatch, jobs=1)
    reservation = data['jobs'][0]
    with factory() as db:
        job=db.get(models.DocumentEmissionJob,reservation[0])
        job.lease_expires_at=datetime.now()-timedelta(seconds=1)
        db.commit()
        leases.attach(db,*reservation)
        try:
            with pytest.raises(leases.LeaseLost):
                queue._reserve_panel_retry_attempt(db,reservation[0],data['user_id'],data['xml'],data['metadata'])
            db.rollback()
        finally:
            leases.detach(db)
    with factory() as db:
        assert db.query(models.AuditLog).filter_by(action='fiscal_panel_retry_started',
            entity_type='cotizacion',entity_id=data['document_id']).count()==0
        assert 'panel_retry_attempt' not in db.get(models.DocumentEmissionJob,reservation[0]).payload_snapshot


@pytest.mark.parametrize('revocation',['user','tenant','subscription','provider_company'])
def test_permissions_revoked_after_probe_commit_veto_post_with_cached_orm(factory, sign_xml, monkeypatch, revocation):
    data=prepare(factory,sign_xml,monkeypatch,jobs=1)
    original=recovery.reserve_probe
    def revoke(db,tenant,**kwargs):
        token=original(db,tenant,**kwargs)
        # Another transaction changes permission after the first check. The
        # factory deliberately uses expire_on_commit=False to expose stale reads.
        with factory() as other:
            if revocation=='user':
                other.get(models.User,data['user_id']).is_active=False
            elif revocation=='tenant':
                other.get(models.Tenant,data['tenant_id']).is_active=False
            elif revocation=='provider_company':
                other.get(models.Tenant,data['tenant_id']).smartpse_company_id='999'
            else:
                other.query(models.Subscription).filter_by(tenant_id=data['tenant_id']).one().status='cancelled'
            other.commit()
        return token
    monkeypatch.setattr(recovery,'reserve_probe',revoke)
    with factory() as db:
        reservation=data['jobs'][0]
        leases.attach(db,*reservation)
        try:
            assert queue._reserve_panel_retry_attempt(db,reservation[0],data['user_id'],data['xml'],data['metadata']) is False
            assert not db.in_transaction()
        finally:
            leases.detach(db)
        assert db.query(models.AuditLog).filter_by(action='fiscal_panel_retry_started',
            entity_type='cotizacion',entity_id=data['document_id']).count()==0


@pytest.mark.parametrize('late_response', ['pending', 'accepted'])
def test_rejection_committed_during_consultation_is_preserved(factory, sign_xml, monkeypatch, late_response):
    data = prepare(factory, sign_xml, monkeypatch, jobs=1)
    with factory() as db:
        job = db.get(models.DocumentEmissionJob, data['jobs'][0][0])
        payload = deepcopy(job.payload_snapshot['prepared_sale']['payload'])
        document = db.get(models.Cotizacion, data['document_id'])
        identity = f'{document.serie}-{document.correlativo}'
        ruc = db.get(models.Tenant, data['tenant_id']).business_ruc
        original_response = deepcopy(document.provider_response)
    rejected_cdr = _sale_cdr(document_id=identity, ruc=ruc, response_code='2335')
    accepted_cdr = _sale_cdr(document_id=identity, ruc=ruc)
    async def noop(*args, **kwargs):
        pass
    monkeypatch.setattr(queue.pdf_storage_service, 'process_pdf_background', noop)
    monkeypatch.setattr(queue.fiscal_artifact_service, 'persist_cdr_artifact', noop)
    active_db = None
    def consult(*args, **kwargs):
        assert not active_db.in_transaction(), 'Another worker must be able to commit while HTTP is in flight'
        with factory() as other:
            document = other.query(models.Cotizacion).filter_by(id=data['document_id'],
                tenant_id=data['tenant_id']).with_for_update().one()
            document.sunat_cdr_content = rejected_cdr
            document.provider_verification_status = 'rejected'
            document.sunat_error = 'SUNAT rechazo acreditado 2335'
            other.commit()
        if late_response == 'pending':
            raise facturacion_service.FacturacionException('Pendiente', {'estado': 202}, partial_result={'pending': True})
        result = smartpse_response.build_smartpse_result(payload, {'cdr': accepted_cdr, 'xml_firmado': data['xml']},
            endpoint='offline', status_code=200, require_cdr=True)
        result['provider_verification_status'] = 'verified'
        return result
    monkeypatch.setattr(facturacion_service, 'consultar_documento_fiscal', consult)
    with factory() as db:
        active_db = db
        assert queue.process_emission_job(data['jobs'][0][0], db_session=db, lease_token=data['jobs'][0][1]) is False
    with factory() as db:
        document = db.get(models.Cotizacion, data['document_id'])
        job = db.get(models.DocumentEmissionJob, data['jobs'][0][0])
        assert job.status == 'failed' and document.provider_verification_status == 'rejected'
        assert document.sunat_cdr_content == rejected_cdr and document.sunat_xml_content == data['xml']
        assert document.provider_response == original_response and not evidence.has_deliverable_xml(document)
        assert db.query(models.Subscription).filter_by(tenant_id=data['tenant_id']).one().documents_used == 0
        assert db.query(models.AuditLog).filter_by(action='fiscal_cdr_conflict', entity_id=document.id).count() == (late_response == 'accepted')


def test_acceptance_committed_before_final_rejection_write_is_immutable(factory, sign_xml, monkeypatch):
    import crud
    data = prepare(factory, sign_xml, monkeypatch, jobs=1)
    with factory() as db:
        job = db.get(models.DocumentEmissionJob, data['jobs'][0][0])
        payload = deepcopy(job.payload_snapshot['prepared_sale']['payload'])
        document = db.get(models.Cotizacion, data['document_id'])
        identity = f'{document.serie}-{document.correlativo}'
        ruc = db.get(models.Tenant, data['tenant_id']).business_ruc
    accepted_cdr = _sale_cdr(document_id=identity, ruc=ruc)
    rejected_cdr = _sale_cdr(document_id=identity, ruc=ruc, response_code='2335')
    pdf_calls = []
    def consult(*args, **kwargs):
        raise facturacion_service.FacturacionRejectedException('SUNAT rechazo acreditado 2335', {'cdr': rejected_cdr})
    async def accept_during_pdf(*args, **kwargs):
        # The rejection worker committed its evidence and released its lock.
        # Another worker confirms acceptance before the final rejection write.
        with factory() as other:
            result = smartpse_response.build_smartpse_result(payload, {'cdr': accepted_cdr, 'xml_firmado': data['xml']},
                endpoint='offline', status_code=200, require_cdr=True)
            result['provider_verification_status'] = 'verified'
            crud.guardar_respuesta_sunat(other, data['document_id'], result, tenant_id=data['tenant_id'])
        pdf_calls.append(True)
    monkeypatch.setattr(facturacion_service, 'consultar_documento_fiscal', consult)
    monkeypatch.setattr(queue.pdf_storage_service, 'process_pdf_background', accept_during_pdf)
    with factory() as db:
        assert queue.process_emission_job(data['jobs'][0][0], db_session=db, lease_token=data['jobs'][0][1]) is True
    with factory() as db:
        document = db.get(models.Cotizacion, data['document_id'])
        job = db.get(models.DocumentEmissionJob, data['jobs'][0][0])
        assert pdf_calls and job.status == 'succeeded'
        assert document.estado == 'facturada' and document.sunat_accepted
        assert document.provider_verification_status == 'verified'
        assert document.sunat_cdr_content == accepted_cdr and document.sunat_xml_content == data['xml']
        assert db.query(models.Subscription).filter_by(tenant_id=data['tenant_id']).one().documents_used == 1
