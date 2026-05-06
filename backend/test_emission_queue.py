"""test_emission_queue.py — pruebas de cola durable de emisión."""
from datetime import datetime, timedelta
from unittest.mock import patch

import crud
import models
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from services import emission_queue_service, facturacion_service


async def _noop_async(*args, **kwargs):
    return None


def _make_fiscal_document(
    db_session,
    suffix: str,
    *,
    subscription_status: str | None = models.SUBSCRIPTION_STATUS_ACTIVE,
):
    tenant = make_tenant(db_session, suffix)
    tenant.smartpse_company_id = "77"
    tenant.smartpse_environment = "demo"
    tenant.smartpse_usuario_secundaria = "AB3KPQR9"
    tenant.smartpse_token_acceso = "MX7TNVQG"
    db_session.commit()
    if subscription_status is not None:
        _set_subscription(db_session, tenant, status=subscription_status)
    user = make_user(db_session, tenant, email=f"{suffix.lower()}@test.com")
    cliente = make_cliente(db_session, tenant, suffix, tipo_documento="6", numero_documento="20191308868")
    quote = make_quote_via_crud(db_session, tenant, user, cliente)
    fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
    return tenant, user, fiscal


def _set_subscription(
    db_session,
    tenant,
    *,
    status: str = models.SUBSCRIPTION_STATUS_ACTIVE,
    max_documents: int | None = None,
    documents_used: int = 0,
):
    subscription = crud.get_subscription_by_tenant(db_session, tenant.id)
    if subscription is None:
        subscription = models.Subscription(tenant_id=tenant.id)
        db_session.add(subscription)
    subscription.status = status
    subscription.max_documents = max_documents
    subscription.documents_used = documents_used
    db_session.commit()
    db_session.refresh(subscription)
    return subscription


def _assert_job_fails_validation_without_provider(db_session, job, expected_error: str):
    crud.claim_next_emission_job(db_session)

    with patch(
        "services.emission_queue_service.facturacion_service.emitir_factura",
    ) as provider_call, patch(
        "services.emission_queue_service.process_direct_sunat_emission_bg",
    ) as direct_sunat_call:
        processed = emission_queue_service.process_emission_job(job.id, db_session=db_session)

    db_session.expire_all()
    updated_job = crud.get_emission_job(db_session, job.id)

    assert processed is False
    assert updated_job.status == models.EMISSION_JOB_STATUS_FAILED
    assert expected_error.lower() in updated_job.last_error.lower()
    provider_call.assert_not_called()
    direct_sunat_call.assert_not_called()


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


def test_enqueue_fiscal_job_usa_smartpse_en_beta_aun_con_direct_sunat_configurado(db_session):
    tenant, user, fiscal = _make_fiscal_document(db_session, "EQ01B")
    tenant.sunat_usuario_sol = "MODDATOS"
    tenant.sunat_clave_sol = "moddatos"
    tenant.sunat_cert_password = "secret"
    tenant.sunat_cert_url = "https://storage.test/cert.p12"
    db_session.commit()

    job, created = emission_queue_service.enqueue_fiscal_document_job(
        db_session,
        fiscal,
        user,
        tipo_comprobante="01",
    )

    assert created is True
    assert job.provider == "smartpse"


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


def test_process_emission_job_fails_without_provider_when_tenant_suspended_after_enqueue(db_session):
    tenant, user, fiscal = _make_fiscal_document(db_session, "EQ06")
    job, _ = emission_queue_service.enqueue_fiscal_document_job(
        db_session,
        fiscal,
        user,
        tipo_comprobante="01",
    )
    _set_subscription(
        db_session,
        tenant,
        status=models.SUBSCRIPTION_STATUS_SUSPENDED,
    )

    _assert_job_fails_validation_without_provider(db_session, job, "suscripción activa")


def test_process_emission_job_fails_without_provider_when_subscription_missing(db_session):
    _, user, fiscal = _make_fiscal_document(
        db_session,
        "EQ10",
        subscription_status=None,
    )
    job, _ = emission_queue_service.enqueue_fiscal_document_job(
        db_session,
        fiscal,
        user,
        tipo_comprobante="01",
    )

    _assert_job_fails_validation_without_provider(
        db_session,
        job,
        "suscripción activa",
    )


def test_process_emission_job_no_falls_back_to_apisperu_when_smartpse_missing(db_session):
    tenant, user, fiscal = _make_fiscal_document(db_session, "EQ11")
    tenant.smartpse_company_id = None
    tenant.smartpse_environment = None
    tenant.smartpse_usuario_secundaria = None
    tenant.smartpse_token_acceso = None
    tenant.apisperu_token = "legacy-token"
    tenant.apisperu_url = "https://facturacion.apisperu.test/api/v1"
    db_session.commit()
    job, _ = emission_queue_service.enqueue_fiscal_document_job(
        db_session,
        fiscal,
        user,
        tipo_comprobante="01",
    )

    _assert_job_fails_validation_without_provider(db_session, job, "Smart PSE")


def test_process_emission_job_allows_explicit_active_trial_and_grace(db_session):
    for index, status in enumerate(
        [models.SUBSCRIPTION_STATUS_ACTIVE, models.SUBSCRIPTION_STATUS_TRIAL, "grace"],
        start=1,
    ):
        _, user, fiscal = _make_fiscal_document(
            db_session,
            f"EQA{index}",
            subscription_status=status,
        )
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
                "correlativo": f"00010{index}",
                "provider_endpoint": "/invoice/send",
                "provider_status_code": 200,
                "sunat_response": {"success": True},
            },
        ), patch(
            "services.emission_queue_service.pdf_storage_service.process_pdf_background",
            side_effect=_noop_async,
        ):
            processed = emission_queue_service.process_emission_job(
                job.id,
                db_session=db_session,
            )

        db_session.expire_all()
        updated_job = crud.get_emission_job(db_session, job.id)
        assert processed is True
        assert updated_job.status == models.EMISSION_JOB_STATUS_SUCCEEDED


def test_process_emission_job_blocks_non_active_subscription_statuses(db_session):
    for index, status in enumerate(
        [
            models.SUBSCRIPTION_STATUS_SUSPENDED,
            "payment_required",
            models.SUBSCRIPTION_STATUS_CANCELLED,
            models.SUBSCRIPTION_STATUS_EXPIRED,
            "desconocido",
        ],
        start=1,
    ):
        _, user, fiscal = _make_fiscal_document(
            db_session,
            f"EQB{index}",
            subscription_status=status,
        )
        job, _ = emission_queue_service.enqueue_fiscal_document_job(
            db_session,
            fiscal,
            user,
            tipo_comprobante="01",
        )
        _assert_job_fails_validation_without_provider(
            db_session,
            job,
            "suscripción activa",
        )


def test_process_emission_job_fails_without_provider_when_user_disabled_after_enqueue(db_session):
    _, user, fiscal = _make_fiscal_document(db_session, "EQ07")
    job, _ = emission_queue_service.enqueue_fiscal_document_job(
        db_session,
        fiscal,
        user,
        tipo_comprobante="01",
    )
    user.is_active = False
    db_session.commit()

    _assert_job_fails_validation_without_provider(db_session, job, "usuario creador")


def test_process_emission_job_fails_without_provider_when_limit_exhausted_after_enqueue(db_session):
    tenant, user, fiscal = _make_fiscal_document(db_session, "EQ08")
    job, _ = emission_queue_service.enqueue_fiscal_document_job(
        db_session,
        fiscal,
        user,
        tipo_comprobante="01",
    )
    _set_subscription(
        db_session,
        tenant,
        status=models.SUBSCRIPTION_STATUS_ACTIVE,
        max_documents=1,
        documents_used=1,
    )

    _assert_job_fails_validation_without_provider(db_session, job, "documentos alcanzado")


def test_process_emission_job_fails_without_provider_when_tenant_inactive_after_enqueue(db_session):
    tenant, user, fiscal = _make_fiscal_document(db_session, "EQ09")
    job, _ = emission_queue_service.enqueue_fiscal_document_job(
        db_session,
        fiscal,
        user,
        tipo_comprobante="01",
    )
    tenant.is_active = False
    db_session.commit()

    _assert_job_fails_validation_without_provider(db_session, job, "tenant inactivo")


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
