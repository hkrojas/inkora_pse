"""Bounded shared outage probes and per-document recovery scheduling."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select, or_, and_, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

import fiscal_time
import models
from config import settings
from services import emission_leases


class ProviderPaused(Exception):
    def __init__(self, until):
        super().__init__("El servicio fiscal esta en recuperacion automatica.")
        self.until = until


def enabled(tenant_id: int) -> bool:
    values = settings.FISCAL_CONTINGENCY_TENANT_IDS.strip()
    return values == "*" or str(tenant_id) in {item.strip() for item in values.split(",") if item.strip()}


def enabled_for_job(job) -> bool:
    # Turning off enrollment must not send an already signed job through /procesar.
    return enabled(job.tenant_id) or bool((job.payload_snapshot or {}).get("recovery_flow"))


def scope_for(tenant) -> str:
    environment = getattr(tenant, "smartpse_environment", "demo") or "demo"
    return f"smartpse:{environment}:cpe"


def _circuit(db, scope):
    table = models.FiscalProviderCircuit.__table__
    insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
    db.execute(insert(table).values(scope=scope, failures=0).on_conflict_do_nothing(index_elements=["scope"]))
    return db.execute(select(models.FiscalProviderCircuit).where(
        models.FiscalProviderCircuit.scope == scope).with_for_update().execution_options(populate_existing=True)).scalar_one()


def reserve_probe(db, tenant):
    """Only one replica/document may test an open service. Never hold lock over I/O."""
    circuit = _circuit(db, scope_for(tenant))
    now = emission_leases.db_now(db)
    if circuit.failures:
        if (db.info.get("fiscal_probe") == (scope_for(tenant), circuit.probe_token)
                and circuit.probe_token and circuit.probe_expires_at and circuit.probe_expires_at > now):
            token = circuit.probe_token
            db.commit()
            return token
        blocked_until = circuit.next_probe_at or now
        if circuit.probe_token and circuit.probe_expires_at and circuit.probe_expires_at > now:
            blocked_until = max(blocked_until, circuit.probe_expires_at)
        if blocked_until > now:
            db.commit()
            raise ProviderPaused(blocked_until)
        circuit.probe_token = str(uuid4())
        circuit.probe_expires_at = now + timedelta(seconds=settings.EMISSION_LEASE_SECONDS)
    token = circuit.probe_token
    db.commit()
    db.info["fiscal_probe"] = (scope_for(tenant), token)
    return token


def service_failed(db, tenant, *, token=None):
    token = token or (db.info.get("fiscal_probe") or (None, None))[1]
    circuit = _circuit(db, scope_for(tenant))
    if token and circuit.probe_token != token:
        db.commit()
        return
    now = emission_leases.db_now(db)
    circuit.failures += 1
    seconds = min(settings.FISCAL_RECOVERY_FIRST_SECONDS * (2 ** min(circuit.failures - 1, 5)),
                  settings.FISCAL_RECOVERY_MAX_SECONDS)
    circuit.next_probe_at = now + timedelta(seconds=seconds)
    circuit.probe_token = None
    circuit.probe_expires_at = None
    # Move consult-only work in bulk. Signing jobs remain runnable.
    query = db.query(models.DocumentEmissionJob).filter(
        models.DocumentEmissionJob.provider == "smartpse",
        or_(models.DocumentEmissionJob.action == models.EMISSION_JOB_ACTION_CONSULT_FISCAL,
            and_(models.DocumentEmissionJob.action == models.EMISSION_JOB_ACTION_EMIT_FISCAL,
                 models.DocumentEmissionJob.payload_snapshot["signed_ready"].as_boolean() == True)),
        models.DocumentEmissionJob.status.in_(["queued", "retry"]),
        models.DocumentEmissionJob.tenant_id.in_(select(models.Tenant.id).where(
            models.Tenant.smartpse_environment == tenant.smartpse_environment)),
        models.DocumentEmissionJob.available_at < circuit.next_probe_at,
    )
    if settings.FISCAL_CONTINGENCY_TENANT_IDS.strip() != "*":
        rollout_ids = [int(value.strip()) for value in settings.FISCAL_CONTINGENCY_TENANT_IDS.split(",") if value.strip().isdigit()]
        query = query.filter(or_(models.DocumentEmissionJob.tenant_id.in_(rollout_ids),
                                models.DocumentEmissionJob.payload_snapshot["recovery_flow"].as_boolean() == True))
    query.update({"available_at": circuit.next_probe_at}, synchronize_session=False)
    db.commit()


def service_recovered(db, tenant, *, token=None):
    circuit = _circuit(db, scope_for(tenant))
    if token and circuit.probe_token != token:
        db.commit()
        return
    if not circuit.probe_token or circuit.probe_token == token:
        was_paused = bool(circuit.failures)
        circuit.failures = 0
        circuit.next_probe_at = None
        circuit.probe_token = None
        circuit.probe_expires_at = None
        if was_paused:
            query = db.query(models.DocumentEmissionJob).filter(
                models.DocumentEmissionJob.provider == "smartpse",
                models.DocumentEmissionJob.status.in_(["queued", "retry"]),
                models.DocumentEmissionJob.action.in_([models.EMISSION_JOB_ACTION_EMIT_FISCAL, models.EMISSION_JOB_ACTION_CONSULT_FISCAL]),
                models.DocumentEmissionJob.tenant_id.in_(select(models.Tenant.id).where(models.Tenant.smartpse_environment == tenant.smartpse_environment)))
            if settings.FISCAL_CONTINGENCY_TENANT_IDS.strip() != "*":
                query = query.filter(or_(models.DocumentEmissionJob.tenant_id.in_([
                    int(value.strip()) for value in settings.FISCAL_CONTINGENCY_TENANT_IDS.split(",") if value.strip().isdigit()]),
                    models.DocumentEmissionJob.payload_snapshot["recovery_flow"].as_boolean() == True))
            query.update({"available_at": emission_leases.db_now(db)}, synchronize_session=False)
    db.commit()


def retry_seconds(attempts: int) -> int:
    return min(settings.FISCAL_RECOVERY_FIRST_SECONDS * (2 ** min(max(attempts - 1, 0), 5)),
               settings.FISCAL_RECOVERY_MAX_SECONDS)


def invoice_deadline(document):
    issued = fiscal_time.as_lima(document.fecha_emision)
    # Three following calendar days, not 72 hours after the issue timestamp.
    end = datetime.combine(issued.date() + timedelta(days=4), datetime.min.time(), fiscal_time.LIMA_TZ)
    return end.astimezone(timezone.utc).replace(tzinfo=None)


def note_deadline_alert(db, job, document):
    now = (db.scalar(select(func.clock_timestamp())).astimezone(timezone.utc)
           if db.bind.dialect.name == "postgresql" else datetime.now(timezone.utc))
    if document.tipo_comprobante != "01" or now.replace(tzinfo=None) < invoice_deadline(document):
        return False
    snapshot = dict(job.payload_snapshot or {})
    if not snapshot.get("deadline_alerted"):
        snapshot["deadline_alerted"] = True
        job.payload_snapshot = snapshot
        db.add(models.AuditLog(user_id=job.created_by_user_id, action="fiscal_recovery_deadline",
                               entity_type="cotizacion", entity_id=document.id,
                               details=f"tenant_id={job.tenant_id}; job_id={job.id}; requiere revision fiscal; consulta continua"))
        db.commit()
    return True
