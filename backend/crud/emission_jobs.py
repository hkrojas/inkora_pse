"""crud/emission_jobs.py — Operaciones de cola durable de emisión."""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

import models

ACTIVE_JOB_STATUSES = {
    models.EMISSION_JOB_STATUS_QUEUED,
    models.EMISSION_JOB_STATUS_PROCESSING,
    models.EMISSION_JOB_STATUS_RETRY,
}


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
        status=models.EMISSION_JOB_STATUS_QUEUED,
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
    db.commit()
    db.refresh(job)
    return job


def mark_emission_job_retry(
    db: Session,
    job_id: int,
    *,
    error_message: str,
    retry_in_seconds: int,
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
):
    job = get_emission_job(db, job_id)
    if not job:
        return None
    now = datetime.now()
    job.status = models.EMISSION_JOB_STATUS_QUEUED
    job.last_error = None
    job.result_snapshot = None
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
    if reset_attempts:
        job.attempts = 0
    db.commit()
    db.refresh(job)
    return job


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
        else:
            job.status = models.EMISSION_JOB_STATUS_RETRY
            job.available_at = now
            job.finished_at = None
            job.last_error = "Job recuperado tras interrupcion del worker."
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
    db.commit()
    db.refresh(job)
    return job
