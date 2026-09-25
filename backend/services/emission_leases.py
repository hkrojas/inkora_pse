"""Short PostgreSQL coordination transactions and per-execution fencing.

No advisory/row lock is held while calling a fiscal provider. An expired send is
ambiguous, never automatically sent again. Database fencing cannot cancel HTTP.
"""
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import event, func, or_, select, text, update

import models

Job = models.DocumentEmissionJob
Attempt = models.DocumentEmissionAttempt
RUNNABLE = ("queued", "retry")
CLAIM_LOCK = 482190317  # stable across every replica / mode


class LeaseLost(RuntimeError):
    def __init__(self, result=None):
        super().__init__("La ejecución ya no posee una reserva vigente")
        self.result = result


def db_now(db):
    if db.bind.dialect.name == "postgresql":
        # Same naive convention as existing timestamps, but shared database clock.
        return db.scalar(select(func.clock_timestamp())).replace(tzinfo=None)
    return datetime.now()


def tenant_scope(query, tenant_ids, *, events):
    if tenant_ids is None:  # '*' means all
        return query if events else query.filter(False)
    return query.filter(Job.tenant_id.in_(tenant_ids) if events else ~Job.tenant_id.in_(tenant_ids))


def claim(db, *, owner, lease_seconds, global_limit, tenant_limit, tenant_ids=None, events=True,
          include_delay=False):
    if db.bind.dialect.name == "postgresql":
        # Separate statement: the capacity snapshot MUST be taken after acquiring
        # the lock. A lock inside the same CTE would allow a stale MVCC snapshot.
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": CLAIM_LOCK})
        scope = ("TRUE" if events else "FALSE") if tenant_ids is None else (
            "(j.tenant_id = ANY(CAST(:tenant_ids AS integer[])))" if events else
            "NOT (j.tenant_id = ANY(CAST(:tenant_ids AS integer[])))")
        row = db.execute(text(f"""
            WITH active AS MATERIALIZED (
                SELECT tenant_id, count(*) AS n FROM document_emission_jobs
                WHERE status='processing' GROUP BY tenant_id
            ), candidate AS (
                SELECT j.id FROM document_emission_jobs j
                WHERE j.status IN ('queued','retry') AND j.available_at <= clock_timestamp()::timestamp
                  AND {scope}
                  AND (SELECT coalesce(sum(n),0) FROM active) < :global_limit
                  AND NOT EXISTS (SELECT 1 FROM active a WHERE a.tenant_id=j.tenant_id AND a.n >= :tenant_limit)
                ORDER BY j.priority,j.created_at,j.id LIMIT 1 FOR UPDATE SKIP LOCKED
            ), claimed AS (
                UPDATE document_emission_jobs j SET status='processing', worker_owner=:owner,
                  lease_token=:token, lease_expires_at=clock_timestamp()::timestamp + :lease_seconds * interval '1 second',
                  locked_at=clock_timestamp()::timestamp, processing_started_at=clock_timestamp()::timestamp,
                  execution_started_at=NULL, updated_at=clock_timestamp()::timestamp
                FROM candidate c WHERE j.id=c.id RETURNING j.id,j.lease_token,j.available_at
            )
            SELECT c.id,c.lease_token,c.available_at,
              (SELECT min(j.available_at) FROM document_emission_jobs j
               WHERE j.status IN ('queued','retry') AND j.available_at > clock_timestamp()::timestamp
                 AND {scope}) AS next_at, clock_timestamp()::timestamp AS now
            FROM (VALUES (1)) AS singleton(x) LEFT JOIN claimed c ON TRUE
        """), dict(owner=owner, token=str(uuid4()), lease_seconds=lease_seconds,
                    global_limit=global_limit, tenant_limit=tenant_limit,
                    tenant_ids=sorted(tenant_ids or []))).one()
        reservation = (row.id, row.lease_token) if row.id is not None else None
        if reservation:
            db.info["emission_queue_wait_seconds"] = max(0, (row.now-row.available_at).total_seconds())
        delay = max(0.01, (row.next_at - row.now).total_seconds()) if row.next_at else None
        db.commit()
        return (reservation, delay) if include_delay else reservation
    # Count every processing reservation, including expired ones until recovery.
    active = db.query(Job.tenant_id, func.count(Job.id)).filter(Job.status == "processing").group_by(Job.tenant_id).all()
    if sum(count for _, count in active) >= global_limit:
        db.rollback()
        return (None, None) if include_delay else None
    blocked = [tenant for tenant, count in active if count >= tenant_limit]
    now = db_now(db)
    query = db.query(Job).filter(Job.status.in_(RUNNABLE), Job.available_at <= now,
                                ~Job.tenant_id.in_(blocked))
    job = tenant_scope(query, tenant_ids, events=events).order_by(
        Job.priority, Job.created_at, Job.id).with_for_update(skip_locked=True).first()
    if not job:
        db.rollback()
        delay = next_available_delay(db, tenant_ids=tenant_ids) if include_delay else None
        return (None, delay) if include_delay else None
    job.status = "processing"
    job.worker_owner = owner
    job.lease_token = str(uuid4())
    job.lease_expires_at = now + timedelta(seconds=lease_seconds)
    job.locked_at = job.processing_started_at = now
    job.execution_started_at = None
    job.updated_at = now
    # Return only the reservation, never a session-bound payload to another thread.
    reservation = (job.id, job.lease_token)
    db.commit()
    return (reservation, None) if include_delay else reservation


def recover_coordinator(db, *, legacy_timeout):
    """One maintenance statement per minute, including existing fiscal reconciliation."""
    if db.bind.dialect.name != "postgresql":
        from crud.emission_jobs import recover_stale_processing_jobs, recover_pending_fiscal_reconciliations
        count = recover_stale_processing_jobs(db, stale_before=datetime.now()-timedelta(seconds=legacy_timeout))
        count += recover_pending_fiscal_reconciliations(db)
        return count + recover(db)
    row = db.execute(text("""
        WITH expired AS (
          SELECT id FROM document_emission_jobs WHERE status='processing' AND (
            (lease_token IS NOT NULL AND lease_expires_at <= clock_timestamp()::timestamp) OR
            (lease_token IS NULL AND coalesce(processing_started_at,locked_at) <=
              clock_timestamp()::timestamp - :timeout * interval '1 second'))
          FOR UPDATE SKIP LOCKED
        ), recovered AS (
          UPDATE document_emission_jobs j SET
            status=CASE WHEN j.lease_token IS NOT NULL AND j.execution_started_at IS NOT NULL
                         THEN 'pending_confirmation'
                        WHEN j.lease_token IS NULL AND j.attempts >= j.max_attempts THEN 'failed'
                        ELSE 'retry' END,
            last_error=CASE WHEN j.lease_token IS NOT NULL AND j.execution_started_at IS NOT NULL
                         THEN 'Reserva vencida tras iniciar ejecución; conciliar antes de reenviar.'
                        ELSE 'Reserva recuperada tras interrupción del worker.' END,
            locked_at=NULL, processing_started_at=NULL,
            finished_at=CASE WHEN j.execution_started_at IS NOT NULL OR j.attempts >= j.max_attempts
                         THEN clock_timestamp()::timestamp ELSE NULL END,
            available_at=clock_timestamp()::timestamp,updated_at=clock_timestamp()::timestamp
          FROM expired e WHERE j.id=e.id RETURNING j.id,j.attempts,j.status,j.last_error,j.lease_token
        ), attempts AS (
          UPDATE document_emission_attempts a SET status=r.status,error_message=r.last_error,
            error_classification=CASE WHEN r.status='pending_confirmation' THEN 'ambiguous' ELSE 'transient' END,
            finished_at=clock_timestamp()::timestamp
          FROM recovered r WHERE a.job_id=r.id AND a.attempt_number=r.attempts
            AND a.lease_token IS NOT DISTINCT FROM r.lease_token RETURNING a.id
        ), reconciled AS (
          UPDATE document_emission_jobs SET action='consult_fiscal_document',status='retry',
            available_at=clock_timestamp()::timestamp,finished_at=NULL,locked_at=NULL,
            processing_started_at=NULL,updated_at=clock_timestamp()::timestamp
          WHERE id IN (SELECT id FROM document_emission_jobs WHERE provider='smartpse'
            AND action='emit_fiscal_document' AND status='pending_confirmation'
            AND last_error ILIKE '%Smart PSE remote verification missing:%'
            FOR UPDATE SKIP LOCKED) RETURNING id
        ) SELECT (SELECT count(*) FROM recovered) + (SELECT count(*) FROM reconciled) AS n
    """), {"timeout": legacy_timeout}).one()
    db.commit()
    return row.n


def next_available_delay(db, *, tenant_ids):
    now = db_now(db)
    query = db.query(func.min(Job.available_at)).filter(
        Job.status.in_(RUNNABLE), Job.available_at > now)
    value = tenant_scope(query, tenant_ids, events=True).scalar()
    return max(0.01, (value - now).total_seconds()) if value else None


def renew(db, reservations, *, owner, lease_seconds):
    if not reservations:
        return 0
    now = db_now(db)
    predicates = [((Job.id == job_id) & (Job.lease_token == token)) for job_id, token in reservations]
    count = db.query(Job).filter(
        Job.status == "processing", Job.worker_owner == owner,
        Job.lease_expires_at > now, or_(*predicates),
    ).update({Job.lease_expires_at: now + timedelta(seconds=lease_seconds)}, synchronize_session=False)
    db.commit()
    return count


def recover(db):
    now = db_now(db)
    jobs = db.query(Job).filter(Job.status == "processing", Job.lease_token.isnot(None),
                               Job.lease_expires_at <= now).with_for_update(skip_locked=True).all()
    for job in jobs:
        started = job.execution_started_at is not None
        job.status = "pending_confirmation" if started else "retry"
        job.last_error = ("Reserva vencida tras iniciar ejecución; conciliar antes de reenviar."
                          if started else "Reserva vencida antes de iniciar ejecución.")
        job.available_at = now
        job.finished_at = now if started else None
        job.locked_at = None
        job.updated_at = now
        if started:
            db.query(Attempt).filter(Attempt.job_id == job.id, Attempt.lease_token == job.lease_token).update({
                Attempt.status: "pending_confirmation", Attempt.error_classification: "ambiguous",
                Attempt.error_message: job.last_error, Attempt.finished_at: now,
            }, synchronize_session=False)
    if jobs:
        db.commit()
    return len(jobs)


def check(db, result=None):
    """Lock/fence the current write transaction using database values, not ORM cache."""
    ownership = db.info.get("emission_lease")
    if not ownership:
        return
    if result is not None:
        db.info["emission_result"] = result
    job_id, token = ownership
    table = Job.__table__
    now = db_now(db)
    valid = db.execute(select(table.c.id).where(
        table.c.id == job_id, table.c.lease_token == token,
        table.c.status == "processing", table.c.lease_expires_at > now,
    ).with_for_update()).first()
    if not valid:
        raise LeaseLost(db.info.get("emission_result"))


def before_provider(db):
    check(db)
    db.commit()  # release the fence before network I/O


def _before_flush(db, flush_context, instances):
    if db.new or db.dirty or db.deleted:
        check(db)


def attach(db, job_id, token):
    db.info["emission_lease"] = (job_id, token)
    event.listen(db, "before_flush", _before_flush)


def detach(db):
    db.info.pop("emission_lease", None)
    db.info.pop("emission_result", None)
    if event.contains(db, "before_flush", _before_flush):
        event.remove(db, "before_flush", _before_flush)


def record_late_result(db, job_id, token, result):
    # Only append evidence to this old attempt; never modify the job/document.
    if result is None:
        return
    db.execute(update(Attempt).where(Attempt.job_id == job_id, Attempt.lease_token == token,
                                    Attempt.late_result_snapshot.is_(None)).values(
        late_result_snapshot=result))
    db.commit()
