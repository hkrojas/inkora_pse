"""test_emission_queue.py — pruebas de cola durable de emisión."""
from datetime import datetime, timedelta
from unittest.mock import patch

import crud
import models
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from services import emission_queue_service, facturacion_service


async def _noop_async(*args, **kwargs):
    return None


def _make_fiscal_document(db_session, suffix: str):
    tenant = make_tenant(db_session, suffix)
    tenant.apisperu_token = "fake-token"
    tenant.apisperu_url = "https://facturacion.test/api/v1"
    db_session.commit()
    user = make_user(db_session, tenant, email=f"{suffix.lower()}@test.com")
    cliente = make_cliente(db_session, tenant, suffix, tipo_documento="6", numero_documento="20191308868")
    quote = make_quote_via_crud(db_session, tenant, user, cliente)
    fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
    return tenant, user, fiscal


def test_enqueue_fiscal_job_is_idempotent_for_active_job(db_session):
    _, user, fiscal = _make_fiscal_document(db_session, "EQ01")

    job_1, created_1 = emission_queue_service.enqueue_fiscal_document_job(
        db_session,
        fiscal,
        user,
        tipo_comprobante="01",
    )
    job_2, created_2 = emission_queue_service.enqueue_fiscal_document_job(
        db_session,
        fiscal,
        user,
        tipo_comprobante="01",
    )

    assert created_1 is True
    assert created_2 is False
    assert job_1.id == job_2.id
    assert job_1.status == models.EMISSION_JOB_STATUS_QUEUED


def test_process_emission_job_marks_success_and_updates_document(db_session):
    _, user, fiscal = _make_fiscal_document(db_session, "EQ02")
    job, _ = emission_queue_service.enqueue_fiscal_document_job(
        db_session,
        fiscal,
        user,
        tipo_comprobante="01",
    )
    crud.claim_next_emission_job(db_session)

    with patch(
        "services.emission_queue_service.facturacion_service.emitir_factura",
        return_value={
            "success": True,
            "serie": "F001",
            "correlativo": "000001",
            "provider_endpoint": "/invoice/send",
            "provider_status_code": 200,
            "sunat_response": {"success": True, "cdrResponse": {"description": "Aceptado"}},
        },
    ), patch(
        "services.emission_queue_service.pdf_storage_service.process_pdf_background",
        side_effect=_noop_async,
    ):
        processed = emission_queue_service.process_emission_job(job.id, db_session=db_session)

    db_session.expire_all()
    updated_job = crud.get_emission_job(db_session, job.id)
    updated_doc = crud.get_cotizacion(db_session, fiscal.id, user)

    assert processed is True
    assert updated_job.status == models.EMISSION_JOB_STATUS_SUCCEEDED
    assert updated_doc.estado == "facturada"
    assert updated_job.result_snapshot["success"] is True


def test_process_emission_job_schedules_retry_for_timeout(db_session):
    _, user, fiscal = _make_fiscal_document(db_session, "EQ03")
    job, _ = emission_queue_service.enqueue_fiscal_document_job(
        db_session,
        fiscal,
        user,
        tipo_comprobante="01",
    )
    crud.claim_next_emission_job(db_session)

    with patch(
        "services.emission_queue_service.facturacion_service.emitir_factura",
        side_effect=facturacion_service.FacturacionException("Timeout enviando documento a /invoice/send."),
    ):
        processed = emission_queue_service.process_emission_job(job.id, db_session=db_session)

    db_session.expire_all()
    updated_job = crud.get_emission_job(db_session, job.id)

    assert processed is False
    assert updated_job.status == models.EMISSION_JOB_STATUS_RETRY
    assert "Timeout" in updated_job.last_error


def test_enqueue_fiscal_job_requeues_failed_job_instead_of_creating_duplicate(db_session):
    _, user, fiscal = _make_fiscal_document(db_session, "EQ04")
    job, _ = emission_queue_service.enqueue_fiscal_document_job(
        db_session,
        fiscal,
        user,
        tipo_comprobante="01",
    )
    crud.mark_emission_job_failed(db_session, job.id, error_message="fallo terminal")

    reused_job, created = emission_queue_service.enqueue_fiscal_document_job(
        db_session,
        fiscal,
        user,
        tipo_comprobante="01",
    )

    db_session.expire_all()
    updated_job = crud.get_emission_job(db_session, job.id)

    assert created is False
    assert reused_job.id == job.id
    assert updated_job.status == models.EMISSION_JOB_STATUS_QUEUED
    assert updated_job.attempts == 0
    assert updated_job.last_error is None


def test_process_next_available_job_recovers_stale_processing_job(db_session):
    _, user, fiscal = _make_fiscal_document(db_session, "EQ05")
    job, _ = emission_queue_service.enqueue_fiscal_document_job(
        db_session,
        fiscal,
        user,
        tipo_comprobante="01",
    )
    claimed = crud.claim_next_emission_job(db_session)
    assert claimed.id == job.id

    stale_job = crud.get_emission_job(db_session, job.id)
    stale_job.processing_started_at = datetime.now() - timedelta(hours=1)
    stale_job.locked_at = datetime.now() - timedelta(hours=1)
    db_session.commit()

    with patch(
        "services.emission_queue_service.facturacion_service.emitir_factura",
        return_value={
            "success": True,
            "serie": "F001",
            "correlativo": "000002",
            "provider_endpoint": "/invoice/send",
            "provider_status_code": 200,
            "sunat_response": {"success": True, "cdrResponse": {"description": "Aceptado"}},
        },
    ), patch(
        "services.emission_queue_service.pdf_storage_service.process_pdf_background",
        side_effect=_noop_async,
    ), patch(
        "services.emission_queue_service.settings.EMISSION_PROCESSING_TIMEOUT_SECONDS",
        30,
    ):
        processed = emission_queue_service.process_next_available_job(db_session=db_session)

    db_session.expire_all()
    updated_job = crud.get_emission_job(db_session, job.id)

    assert processed is True
    assert updated_job.status == models.EMISSION_JOB_STATUS_SUCCEEDED
    assert updated_job.attempts == 1
