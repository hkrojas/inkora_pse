"""crud/emission_jobs.py — Operaciones de cola durable de emisión."""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

import models

ACTIVE_JOB_STATUSES = {
    models.EMISSION_JOB_STATUS_QUEUED,
    models.EMISSION_JOB_STATUS_PROCESSING,
    models.EMISSION_JOB_STATUS_RETRY,
    models.EMISSION_JOB_STATUS_PENDING_CONFIRMATION,
    models.EMISSION_JOB_STATUS_CONTINGENCY_PENDING,
}

CONTINGENCY_ACTIONS = {
    models.EMISSION_JOB_ACTION_EMIT_FISCAL,
    models.EMISSION_JOB_ACTION_EMIT_NOTE,
    models.EMISSION_JOB_ACTION_EMIT_GUIDE,
}


def _get_current_attempt(db: Session, job_id: int, attempt_number: int):
    return db.query(models.DocumentEmissionAttempt).filter(
        models.DocumentEmissionAttempt.job_id == job_id,
        models.DocumentEmissionAttempt.attempt_number == attempt_number,
    ).first()


def get_emission_attempts(db: Session, job_id: int, tenant_id: int | None = None):
    query = db.query(models.DocumentEmissionAttempt).filter(
        models.DocumentEmissionAttempt.job_id == job_id,
    )
    if tenant_id is not None:
        query = query.filter(models.DocumentEmissionAttempt.tenant_id == tenant_id)
    return query.order_by(models.DocumentEmissionAttempt.attempt_number.asc()).all()


def _finish_current_attempt(
    db: Session,
    job,
    *,
    status: str,
    error_classification: str | None = None,
    error_message: str | None = None,
    result_snapshot: dict | None = None,
):
    attempt = _get_current_attempt(db, job.id, job.attempts or 0)
    if not attempt:
        return None
    attempt.status = status
    attempt.error_classification = error_classification
    attempt.error_message = error_message
    attempt.result_snapshot = result_snapshot
    if result_snapshot:
        attempt.provider_endpoint = result_snapshot.get("provider_endpoint")
        attempt.provider_status_code = result_snapshot.get("provider_status_code")
    attempt.finished_at = datetime.now()
    return attempt


def get_emission_job(
    db: Session,
    job_id: int,
    tenant_id: int | None = None,
):
    query = db.query(models.DocumentEmissionJob).filter(models.DocumentEmissionJob.id == job_id)
    if tenant_id is not None:
        query = query.filter(models.DocumentEmissionJob.tenant_id == tenant_id)
    return query.first()


def get_emission_jobs(
    db: Session,
    tenant_id: int,
    *,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
):
    query = db.query(models.DocumentEmissionJob).filter(
        models.DocumentEmissionJob.tenant_id == tenant_id,
    ).order_by(models.DocumentEmissionJob.created_at.desc())
    if status:
        query = query.filter(models.DocumentEmissionJob.status == status)
    return query.offset(skip).limit(limit).all()


def get_active_emission_job_by_key(
    db: Session,
    tenant_id: int,
    idempotency_key: str,
):
    return db.query(models.DocumentEmissionJob).filter(
        models.DocumentEmissionJob.tenant_id == tenant_id,
        models.DocumentEmissionJob.idempotency_key == idempotency_key,
        models.DocumentEmissionJob.status.in_(ACTIVE_JOB_STATUSES),
    ).first()


def get_emission_job_by_key(
    db: Session,
    tenant_id: int,
    idempotency_key: str,
):
    return db.query(models.DocumentEmissionJob).filter(
        models.DocumentEmissionJob.tenant_id == tenant_id,
        models.DocumentEmissionJob.idempotency_key == idempotency_key,
    ).first()


def create_emission_job(
    db: Session,
    *,
    tenant_id: int,
    created_by_user_id: int | None,
    resource_type: str,
    resource_id: int,
    action: str,
    provider: str | None,
    idempotency_key: str,
    payload_snapshot: dict | None = None,
    priority: int = 100,
    max_attempts: int = 5,
    initial_status: str = models.EMISSION_JOB_STATUS_QUEUED,
):
    job = models.DocumentEmissionJob(
        tenant_id=tenant_id,
        created_by_user_id=created_by_user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        provider=provider,
        idempotency_key=idempotency_key,
        payload_snapshot=payload_snapshot,
        priority=priority,
        max_attempts=max_attempts,
        status=initial_status,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def claim_next_emission_job(db: Session):
    now = datetime.now()
    query = db.query(models.DocumentEmissionJob).filter(
        models.DocumentEmissionJob.status.in_(
            [
                models.EMISSION_JOB_STATUS_QUEUED,
                models.EMISSION_JOB_STATUS_RETRY,
            ]
        ),
        models.DocumentEmissionJob.available_at <= now,
    ).order_by(
        models.DocumentEmissionJob.priority.asc(),
        models.DocumentEmissionJob.created_at.asc(),
    )

    try:
        job = query.with_for_update(skip_locked=True).first()
    except TypeError:
        job = query.with_for_update().first()

    if not job:
        return None

    job.status = models.EMISSION_JOB_STATUS_PROCESSING
    job.locked_at = now
    job.processing_started_at = now
    job.updated_at = now
    db.commit()
    db.refresh(job)
    return job


def mark_emission_job_attempt_started(
    db: Session,
    job_id: int,
):
    job = get_emission_job(db, job_id)
    if not job:
        return None
    job.attempts = (job.attempts or 0) + 1
    db.add(
        models.DocumentEmissionAttempt(
            job_id=job.id,
            tenant_id=job.tenant_id,
            attempt_number=job.attempts,
            status=models.EMISSION_ATTEMPT_STATUS_PROCESSING,
        )
    )
    job.updated_at = datetime.now()
    db.commit()
    db.refresh(job)
    return job


def mark_emission_job_succeeded(
    db: Session,
    job_id: int,
    *,
    result_snapshot: dict | None = None,
    provider_ticket: str | None = None,
):
    job = get_emission_job(db, job_id)
    if not job:
        return None
    now = datetime.now()
    job.status = models.EMISSION_JOB_STATUS_SUCCEEDED
    job.result_snapshot = result_snapshot
    job.provider_ticket = provider_ticket
    job.last_error = None
    job.locked_at = None
    job.finished_at = now
    job.updated_at = now
    _finish_current_attempt(
        db,
        job,
        status=models.EMISSION_ATTEMPT_STATUS_SUCCEEDED,
        result_snapshot=result_snapshot,
    )
    db.commit()
    db.refresh(job)
    return job


def mark_emission_job_retry(
    db: Session,
    job_id: int,
    *,
    error_message: str,
    retry_in_seconds: int,
    error_classification: str | None = None,
):
    job = get_emission_job(db, job_id)
    if not job:
        return None
    now = datetime.now()
    job.status = models.EMISSION_JOB_STATUS_RETRY
    job.last_error = error_message
    job.locked_at = None
    job.finished_at = None
    job.available_at = now + timedelta(seconds=retry_in_seconds)
    job.updated_at = now
    _finish_current_attempt(
        db,
        job,
        status=models.EMISSION_ATTEMPT_STATUS_RETRY,
        error_classification=error_classification,
        error_message=error_message,
    )
    db.commit()
    db.refresh(job)
    return job


def requeue_emission_job(
    db: Session,
    job_id: int,
    *,
    payload_snapshot: dict | None = None,
    provider: str | None = None,
    reset_attempts: bool = False,
    target_status: str = models.EMISSION_JOB_STATUS_QUEUED,
):
    job = get_emission_job(db, job_id)
    if not job:
        return None
    now = datetime.now()
    job.status = target_status
    # Conservar evidencia forense. Un nuevo intento no debe borrar la causa
    # anterior ni el resultado parcial almacenado.
    job.provider_ticket = None
    job.locked_at = None
    job.processing_started_at = None
    job.finished_at = None
    job.available_at = now
    job.updated_at = now
    if payload_snapshot is not None:
        job.payload_snapshot = payload_snapshot
    if provider is not None:
        job.provider = provider
    # `reset_attempts` se conserva en la firma por compatibilidad, pero los
    # contadores fiscales son acumulativos y nunca se reinician.
    db.commit()
    db.refresh(job)
    return job


def set_tenant_fiscal_contingency(
    db: Session,
    tenant_id: int,
    *,
    enabled: bool,
    reason: str | None = None,
    release_interval_seconds: int = 15,
):
    """Retiene o libera envíos CPE sin tocar jobs en curso o ambiguos."""
    tenant = db.query(models.Tenant).filter(
        models.Tenant.id == tenant_id,
    ).with_for_update().first()
    if not tenant:
        return None

    now = datetime.now()
    processing_jobs = db.query(models.DocumentEmissionJob).filter(
        models.DocumentEmissionJob.tenant_id == tenant_id,
        models.DocumentEmissionJob.action.in_(CONTINGENCY_ACTIONS),
        models.DocumentEmissionJob.status == models.EMISSION_JOB_STATUS_PROCESSING,
    ).count()
    held_jobs = 0
    released_jobs = 0

    if enabled:
        normalized_reason = (reason or "").strip() or "Incidente del proveedor fiscal"
        tenant.fiscal_contingency_mode = True
        tenant.fiscal_contingency_reason = normalized_reason
        tenant.fiscal_contingency_started_at = tenant.fiscal_contingency_started_at or now
        jobs = db.query(models.DocumentEmissionJob).filter(
            models.DocumentEmissionJob.tenant_id == tenant_id,
            models.DocumentEmissionJob.action.in_(CONTINGENCY_ACTIONS),
            models.DocumentEmissionJob.status.in_([
                models.EMISSION_JOB_STATUS_QUEUED,
                models.EMISSION_JOB_STATUS_RETRY,
            ]),
        ).with_for_update().all()
        for job in jobs:
            job.status = models.EMISSION_JOB_STATUS_CONTINGENCY_PENDING
            job.locked_at = None
            job.processing_started_at = None
            job.finished_at = None
            job.updated_at = now
            held_jobs += 1
    else:
        tenant.fiscal_contingency_mode = False
        tenant.fiscal_contingency_reason = None
        tenant.fiscal_contingency_started_at = None
        jobs = db.query(models.DocumentEmissionJob).filter(
            models.DocumentEmissionJob.tenant_id == tenant_id,
            models.DocumentEmissionJob.action.in_(CONTINGENCY_ACTIONS),
            models.DocumentEmissionJob.status == models.EMISSION_JOB_STATUS_CONTINGENCY_PENDING,
        ).order_by(
            models.DocumentEmissionJob.created_at.asc(),
        ).with_for_update().all()
        interval = max(release_interval_seconds, 1)
        for index, job in enumerate(jobs):
            job.status = models.EMISSION_JOB_STATUS_QUEUED
            job.available_at = now + timedelta(seconds=index * interval)
            job.locked_at = None
            job.processing_started_at = None
            job.finished_at = None
            job.updated_at = now
            released_jobs += 1

    db.commit()
    db.refresh(tenant)
    return {
        "tenant": tenant,
        "held_jobs": held_jobs,
        "released_jobs": released_jobs,
        "processing_jobs": processing_jobs,
    }


def get_tenant_fiscal_contingency_status(db: Session, tenant_id: int):
    """Devuelve el estado y los conteos CPE actuales sin mutar la cola."""
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not tenant:
        return None

    base_filters = (
        models.DocumentEmissionJob.tenant_id == tenant_id,
        models.DocumentEmissionJob.action.in_(CONTINGENCY_ACTIONS),
    )
    held_jobs = db.query(models.DocumentEmissionJob).filter(
        *base_filters,
        models.DocumentEmissionJob.status == models.EMISSION_JOB_STATUS_CONTINGENCY_PENDING,
    ).count()
    processing_jobs = db.query(models.DocumentEmissionJob).filter(
        *base_filters,
        models.DocumentEmissionJob.status == models.EMISSION_JOB_STATUS_PROCESSING,
    ).count()
    pending_confirmation_jobs = db.query(models.DocumentEmissionJob).filter(
        *base_filters,
        models.DocumentEmissionJob.status == models.EMISSION_JOB_STATUS_PENDING_CONFIRMATION,
    ).count()

    return {
        "tenant": tenant,
        "held_jobs": held_jobs,
        "processing_jobs": processing_jobs,
        "pending_confirmation_jobs": pending_confirmation_jobs,
    }


def recover_stale_processing_jobs(
    db: Session,
    *,
    stale_before: datetime,
):
    jobs = db.query(models.DocumentEmissionJob).filter(
        models.DocumentEmissionJob.status == models.EMISSION_JOB_STATUS_PROCESSING,
        (
            (models.DocumentEmissionJob.processing_started_at.isnot(None))
            & (models.DocumentEmissionJob.processing_started_at <= stale_before)
        ) | (
            (models.DocumentEmissionJob.processing_started_at.is_(None))
            & (models.DocumentEmissionJob.locked_at.isnot(None))
            & (models.DocumentEmissionJob.locked_at <= stale_before)
        ),
    ).all()

    now = datetime.now()
    recovered = 0
    for job in jobs:
        if (job.attempts or 0) >= (job.max_attempts or 1):
            job.status = models.EMISSION_JOB_STATUS_FAILED
            job.finished_at = now
            job.last_error = (
                "Job marcado como fallido tras quedar colgado y superar el maximo de intentos."
            )
            _finish_current_attempt(
                db,
                job,
                status=models.EMISSION_ATTEMPT_STATUS_FAILED,
                error_classification="transient",
                error_message=job.last_error,
            )
        else:
            job.status = models.EMISSION_JOB_STATUS_RETRY
            job.available_at = now
            job.finished_at = None
            job.last_error = "Job recuperado tras interrupcion del worker."
            _finish_current_attempt(
                db,
                job,
                status=models.EMISSION_ATTEMPT_STATUS_RETRY,
                error_classification="transient",
                error_message=job.last_error,
            )
        job.locked_at = None
        job.processing_started_at = None
        job.updated_at = now
        recovered += 1

    if recovered:
        db.commit()

    return recovered


def mark_emission_job_failed(
    db: Session,
    job_id: int,
    *,
    error_message: str,
    error_classification: str | None = None,
):
    job = get_emission_job(db, job_id)
    if not job:
        return None
    now = datetime.now()
    job.status = models.EMISSION_JOB_STATUS_FAILED
    job.last_error = error_message
    job.locked_at = None
    job.finished_at = now
    job.updated_at = now
    _finish_current_attempt(
        db,
        job,
        status=models.EMISSION_ATTEMPT_STATUS_FAILED,
        error_classification=error_classification,
        error_message=error_message,
    )
    db.commit()
    db.refresh(job)
    return job


def mark_emission_job_pending_confirmation(
    db: Session,
    job_id: int,
    *,
    error_message: str,
    error_classification: str,
    result_snapshot: dict | None = None,
    provider_ticket: str | None = None,
):
    job = get_emission_job(db, job_id)
    if not job:
        return None
    now = datetime.now()
    job.status = models.EMISSION_JOB_STATUS_PENDING_CONFIRMATION
    job.last_error = error_message
    if result_snapshot is not None:
        job.result_snapshot = result_snapshot
    if provider_ticket is not None:
        job.provider_ticket = provider_ticket
    job.locked_at = None
    job.finished_at = now
    job.updated_at = now
    _finish_current_attempt(
        db,
        job,
        status=models.EMISSION_ATTEMPT_STATUS_PENDING_CONFIRMATION,
        error_classification=error_classification,
        error_message=error_message,
        result_snapshot=result_snapshot,
    )
    db.commit()
    db.refresh(job)
    return job
