"""Destructive tests ONLY on loopback inkora_worker_* databases; no provider calls."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import importlib.util
import os
from pathlib import Path
import select
import threading
import time
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
import psycopg2
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

import crud
import models
from database import Base
from services import emission_leases as leases
from services.fiscal_submission_state import can_submit, initial_state, mark_not_submitted, mark_possible
from services.emission_worker_runtime import CHANNEL, Listener, Metrics, WakeSignal


def safe_url():
    value = os.getenv("INKORA_WORKER_POSTGRES_URL", "")
    if not value:
        if os.getenv("INKORA_REQUIRE_POSTGRES_TESTS") == "1":
            pytest.fail("INKORA_WORKER_POSTGRES_URL es obligatoria")
        pytest.skip("PostgreSQL worker local no configurado")
    url = make_url(value)
    assert url.drivername.startswith("postgresql")
    assert url.host in {"localhost", "127.0.0.1", "::1"}
    assert (url.database or "").startswith("inkora_worker_")
    return value


def migration():
    path = Path(__file__).parent / "alembic/versions/0025_emission_worker_events.py"
    spec = importlib.util.spec_from_file_location("worker_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def circuit_migration():
    path = Path(__file__).parent / "alembic/versions/0026_fiscal_provider_circuits.py"
    spec = importlib.util.spec_from_file_location("circuit_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("service", ["cpe", "cpe:sign"])
def test_shared_outage_allows_only_one_probe_across_ten_companies(factory, monkeypatch, service):
    from config import settings
    from services import fiscal_recovery_service as recovery
    monkeypatch.setattr(settings, "FISCAL_CONTINGENCY_TENANT_IDS", "*")
    with factory() as db:
        db.query(models.FiscalProviderCircuit).delete()
        tenants = [models.Tenant(business_name=f"Synthetic outage {i}", business_ruc=uuid4().hex[:11],
                                smartpse_environment="demo", is_active=True) for i in range(10)]
        db.add_all(tenants)
        db.commit()
        ids = [tenant.id for tenant in tenants]
        recovery.service_failed(db, tenants[0], service=service)
        circuit = db.get(models.FiscalProviderCircuit, recovery.scope_for(tenants[0], service=service))
        circuit.next_probe_at = leases.db_now(db) - timedelta(seconds=1)
        db.commit()
    def probe(tenant_id):
        with factory() as db:
            tenant = db.get(models.Tenant, tenant_id)
            try:
                return recovery.reserve_probe(db, tenant, service=service)
            except recovery.ProviderPaused:
                return None
    with ThreadPoolExecutor(max_workers=10) as executor:
        tokens = list(executor.map(probe, ids))
    assert sum(token is not None for token in tokens) == 1
    with factory() as db:
        tenant = db.get(models.Tenant, ids[0])
        winning = next(token for token in tokens if token)
        recovery.service_failed(db, tenant, token=winning, service=service)
        circuit = db.get(models.FiscalProviderCircuit, recovery.scope_for(tenant, service=service))
        assert circuit.failures == 2
        assert 1790 < (circuit.next_probe_at - leases.db_now(db)).total_seconds() <= 1800
        recovery.service_recovered(db, tenant, token="stale-token", service=service)
        # A stale result from an expired probe cannot close an active newer probe.
        circuit.probe_token = "new-probe"
        db.commit()
        recovery.service_recovered(db, tenant, token="stale-token", service=service)
        assert circuit.probe_token == "new-probe"


@pytest.mark.parametrize("service", ["cpe", "cpe:sign"])
@pytest.mark.parametrize("rollout", ["*", ""])
def test_circuit_bulk_survives_malformed_snapshot_flags(factory, monkeypatch, service, rollout):
    from config import settings
    from services import fiscal_recovery_service as recovery
    monkeypatch.setattr(settings, "FISCAL_CONTINGENCY_TENANT_IDS", rollout)
    with factory() as db:
        db.query(models.FiscalProviderCircuit).delete()
        tenant = models.Tenant(business_name="Synthetic circuit flags", business_ruc=uuid4().hex[:11],
                               smartpse_environment="demo", is_active=True)
        db.add(tenant)
        db.commit()
        tenant_id = tenant.id
    ready = service == "cpe"
    valid, _ = enqueue(factory, tenant_id, provider="smartpse",
                       payload_snapshot={**initial_state(), "signed_ready": ready, "recovery_flow": True})
    for malformed in ("broken", {"value": True}, [True], 7):
        enqueue(factory, tenant_id, provider="smartpse",
                payload_snapshot={"signed_ready": malformed, "recovery_flow": True})
        enqueue(factory, tenant_id, provider="smartpse",
                payload_snapshot={"signed_ready": ready, "recovery_flow": malformed})
    with factory() as db:
        tenant = db.get(models.Tenant, tenant_id)
        recovery.service_failed(db, tenant, service=service)
        db.expire_all()
        assert db.get(models.DocumentEmissionJob, valid).available_at > leases.db_now(db) + timedelta(minutes=14)
        recovery.service_recovered(db, tenant, service=service)
        db.expire_all()
        assert db.get(models.DocumentEmissionJob, valid).available_at <= leases.db_now(db)


def test_submission_evidence_sql_matches_python_for_malformed_json(factory):
    import json
    from test_fiscal_submission_leases import SUBMISSION_CASES
    samples = [(name, json.dumps(snapshot), safe) for name, snapshot, safe in SUBMISSION_CASES]
    samples += [("exponent_version", '{"submission_state_version":1e0,"submission_phase":"not_started"}', False),
                ("positive_exponent_version", '{"submission_state_version":1E+0,"submission_phase":"not_started"}', False)]
    with factory() as db:
        for name, encoded, expected in samples:
            python_result = can_submit(json.loads(encoded))
            sql_result = db.scalar(text(f"SELECT {leases._CAN_SUBMIT_SQL} "
                                        "FROM (SELECT CAST(:snapshot AS json) AS payload_snapshot) j"), {"snapshot": encoded})
            assert python_result is expected, name
            assert sql_result is python_result, name


@pytest.mark.parametrize("mode", ["lease_sql", "lease_python", "legacy_sql", "legacy_python", "pending_sql", "pending_python"])
def test_submission_phase_recovery_matches_all_coordinators(factory, mode):
    from test_fiscal_submission_leases import _assert_recovered, _jobs
    with factory() as db:
        kind = "pending" if mode.startswith("pending") else "legacy" if mode.startswith("legacy") else "lease"
        jobs = _jobs(db, mode=kind)
        if mode.endswith("sql"):
            count = leases.recover_coordinator(db, legacy_timeout=30)
        elif kind == "pending":
            count = crud.recover_pending_fiscal_reconciliations(db)
        elif kind == "legacy":
            count = crud.recover_stale_processing_jobs(db, stale_before=datetime.now()-timedelta(seconds=30))
        else:
            count = leases.recover(db)
        assert count == len(jobs)
        _assert_recovered(db, jobs)
        if kind != "pending":
            for name, job_id, _, _ in jobs:
                job = db.get(models.DocumentEmissionJob, job_id)
                attempt = db.query(models.DocumentEmissionAttempt).filter_by(job_id=job_id).one()
                assert attempt.status == "retry", name
                expected = "ambiguous" if job.action == "consult_fiscal_document" else "transient"
                assert attempt.error_classification == expected, name


def test_preauth_failure_then_crash_preserves_emit_until_new_submission_marker(factory):
    job_id, _ = enqueue(factory, provider="smartpse", payload_snapshot=initial_state(), max_attempts=1)
    reservation = claim(factory)
    with factory() as db:
        leases.attach(db, *reservation)
        crud.mark_emission_job_attempt_started(db, job_id)
        job = db.get(models.DocumentEmissionJob, job_id)
        # The typed client pre-auth failure is represented by this transition.
        job.payload_snapshot = mark_not_submitted(mark_possible(job.payload_snapshot))
        db.commit()
        leases.detach(db)
        job.lease_expires_at = datetime.now()-timedelta(seconds=1)
        db.commit()
        assert leases.recover_coordinator(db, legacy_timeout=30) == 1
        db.refresh(job)
        assert job.action == "emit_fiscal_document" and can_submit(job.payload_snapshot)
        first = db.query(models.DocumentEmissionAttempt).filter_by(job_id=job_id, attempt_number=1).one()
        assert first.status == "retry" and first.error_classification == "transient"
    new_reservation = claim(factory)
    with factory() as db:
        leases.attach(db, *new_reservation)
        crud.mark_emission_job_attempt_started(db, job_id)
        job = db.get(models.DocumentEmissionJob, job_id)
        job.payload_snapshot = mark_possible(job.payload_snapshot)
        leases.before_provider(db)  # commit before an unobserved POST
        leases.detach(db)
        job.lease_expires_at = datetime.now()-timedelta(seconds=1)
        db.commit()
        assert leases.recover_coordinator(db, legacy_timeout=30) == 1
        db.refresh(job)
        assert job.action == "consult_fiscal_document" and not can_submit(job.payload_snapshot)
        second = db.query(models.DocumentEmissionAttempt).filter_by(job_id=job_id, attempt_number=2).one()
        assert second.status == "retry" and second.error_classification == "ambiguous"
        leases.attach(db, *new_reservation)
        with pytest.raises(leases.LeaseLost):
            crud.mark_emission_job_succeeded(db, job_id, result_snapshot={"success": True})
        db.rollback()
        leases.detach(db)


@pytest.mark.parametrize("sql", [False, True])
def test_pending_consult_action_never_becomes_emit(factory, sql):
    from test_fiscal_submission_leases import _assert_recovered, _jobs
    with factory() as db:
        jobs = _jobs(db, mode="pending", action="consult_fiscal_document")
        count = leases.recover_coordinator(db, legacy_timeout=30) if sql else crud.recover_pending_fiscal_reconciliations(db)
        assert count == len(jobs)
        _assert_recovered(db, jobs, original_action="consult_fiscal_document")


@pytest.mark.parametrize("mode", ["lease_sql", "lease_python", "legacy_sql", "legacy_python", "pending_sql", "pending_python"])
def test_boleta_recovery_preserves_unexecuted_normal_flow(factory, mode):
    from test_fiscal_submission_leases import _boleta_jobs
    kind = "pending" if mode.startswith("pending") else "legacy" if mode.startswith("legacy") else "lease"
    with factory() as db:
        jobs = _boleta_jobs(db, mode=kind)
        if mode.endswith("sql"):
            count = leases.recover_coordinator(db, legacy_timeout=30)
        elif kind == "pending":
            count = crud.recover_pending_fiscal_reconciliations(db)
        elif kind == "legacy":
            count = crud.recover_stale_processing_jobs(db, stale_before=datetime.now()-timedelta(seconds=30))
        else:
            count = leases.recover(db)
        assert count == len(jobs)
        db.expire_all()
        for name, job_id, safe in jobs:
            job = db.get(models.DocumentEmissionJob, job_id)
            assert job.action == ("emit_fiscal_document" if safe else "consult_fiscal_document"), name
            assert job.status == "retry" and job.finished_at is None, name


def test_circuit_migration_is_private_and_reversible(factory):
    engine = factory.kw["bind"]
    with engine.begin() as conn:
        assert conn.scalar(text("SELECT relrowsecurity FROM pg_class WHERE oid='fiscal_provider_circuits'::regclass"))
        assert conn.scalar(text("""SELECT count(*) FROM pg_class c,
          LATERAL aclexplode(coalesce(c.relacl, acldefault('r',c.relowner))) a
          WHERE c.oid='fiscal_provider_circuits'::regclass AND a.grantee=0""")) == 0
        with Operations.context(MigrationContext.configure(conn)):
            circuit_migration().downgrade()
            circuit_migration().upgrade()


def test_duplicate_cdr_callbacks_charge_document_usage_only_once(factory):
    from test_emission_queue import _make_fiscal_document
    from test_smartpse_response_normalization import _sale_cdr
    with factory() as db:
        tenant, _, document = _make_fiscal_document(db, "DUPLICATECDR")
        tenant_id, document_id = tenant.id, document.id
        result = {"success": True, "cdr_xml": _sale_cdr(
            document_id=f"{document.serie}-{document.correlativo}", ruc=tenant.business_ruc),
            "provider_verification_status": "verified"}
    barrier = threading.Barrier(2)
    def callback(_):
        with factory() as db:
            # Both callbacks deliberately begin with a stale pending ORM instance.
            assert db.get(models.Cotizacion, document_id).estado == "pendiente"
            barrier.wait(timeout=5)
            persisted = crud.guardar_respuesta_sunat(db, document_id, result, tenant_id=tenant_id)
            return persisted.estado
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert list(executor.map(callback, range(2))) == ["facturada", "facturada"]
    with factory() as db:
        subscription = db.query(models.Subscription).filter_by(tenant_id=tenant_id).one()
        assert subscription.documents_used == 1


def prepare_database(engine):
    # Build the prior schema in a disposable database, then run the actual migration.
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        for name in ("worker_owner", "lease_token", "lease_expires_at", "execution_started_at"):
            conn.execute(text(f"ALTER TABLE document_emission_jobs DROP COLUMN {name}"))
        for name in ("lease_token", "late_result_snapshot"):
            conn.execute(text(f"ALTER TABLE document_emission_attempts DROP COLUMN {name}"))
        with Operations.context(MigrationContext.configure(conn)):
            migration().upgrade()
            conn.execute(text("DROP TABLE fiscal_provider_circuits"))
            circuit_migration().upgrade()


@pytest.fixture(scope="module")
def factory():
    engine = create_engine(safe_url(), pool_size=8, max_overflow=8)
    prepare_database(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def clear_jobs(factory):
    with factory() as db:
        db.query(models.DocumentEmissionAttempt).delete()
        db.query(models.DocumentEmissionJob).delete()
        db.commit()


def enqueue(factory, tenant_id=None, **values):
    with factory() as db:
        if tenant_id is None:
            tenant = models.Tenant(business_name="Worker synthetic", business_ruc=uuid4().hex[:11], is_active=True)
            db.add(tenant)
            db.flush()
            tenant_id = tenant.id
        job = models.DocumentEmissionJob(tenant_id=tenant_id, resource_type="cotizacion", resource_id=1,
            action="emit_fiscal_document", idempotency_key=uuid4().hex, **values)
        db.add(job)
        db.commit()
        return job.id, tenant_id


def claim(factory, **overrides):
    options = dict(owner="test-worker", lease_seconds=300, global_limit=4, tenant_limit=1)
    options.update(overrides)
    with factory() as db:
        return leases.claim(db, **options)


def connect():
    conn = psycopg2.connect(safe_url())
    conn.autocommit = True
    return conn


def notice(conn, timeout=0.25):
    if select.select([conn], [], [], timeout)[0]:
        conn.poll()
    result = list(conn.notifies)
    conn.notifies.clear()
    return result


def test_transactional_notifications_and_heartbeat_silence(factory):
    conn = connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute("LISTEN " + CHANNEL)
        job_id, _ = enqueue(factory)
        messages = notice(conn)
        assert len(messages) == 1 and messages[0].payload == ""
        with factory() as db:
            db.execute(text("UPDATE document_emission_jobs SET priority=priority+1 WHERE id=:id"), {"id": job_id})
            assert not notice(conn)
            db.rollback()
        assert not notice(conn)
        reservation = claim(factory)
        assert not notice(conn)
        with factory() as db:
            assert leases.renew(db, [reservation], owner="test-worker", lease_seconds=300) == 1
        assert not notice(conn)
        with factory() as db:
            db.execute(text("UPDATE document_emission_jobs SET status='succeeded' WHERE id=:id"), {"id": job_id})
            db.commit()
        assert len(notice(conn)) == 1
    finally:
        conn.close()


def test_four_replicas_global_and_tenant_caps(factory):
    tenants = [enqueue(factory)[1] for _ in range(20)]
    for tenant in tenants:
        for _ in range(4):
            enqueue(factory, tenant)
    barrier = threading.Barrier(12)
    def reserve(i):
        barrier.wait()
        return claim(factory, owner=str(i))
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(reserve, range(12)))
    claims = [r for r in results if r]
    assert len(claims) == len(set(claims)) == 4
    with factory() as db:
        rows = db.query(models.DocumentEmissionJob).filter_by(status="processing").all()
        assert len({row.tenant_id for row in rows}) == 4


def test_crashes_before_and_after_start_and_fenced_late_evidence(factory):
    job_id, _ = enqueue(factory)
    reservation = claim(factory)
    with factory() as db:
        job = db.get(models.DocumentEmissionJob, job_id)
        job.lease_expires_at = datetime.now() - timedelta(seconds=1)
        db.commit()
        assert leases.recover(db) == 1
        assert db.get(models.DocumentEmissionJob, job_id).status == "retry"
    new = claim(factory)
    assert new[1] != reservation[1]
    with factory() as db:
        leases.attach(db, *reservation)
        with pytest.raises(leases.LeaseLost):
            crud.mark_emission_job_attempt_started(db, job_id)
        db.rollback()
        leases.detach(db)
        leases.attach(db, *new)
        crud.mark_emission_job_attempt_started(db, job_id)
        with pytest.raises(leases.LeaseLost):
            crud.mark_emission_job_attempt_started(db, job_id)
        db.rollback()
        leases.detach(db)
    with factory() as db:
        db.query(models.DocumentEmissionJob).filter_by(id=job_id).update({"lease_expires_at": datetime.now()-timedelta(seconds=1)})
        db.commit()
        assert leases.recover(db) == 1
        assert db.get(models.DocumentEmissionJob, job_id).status == "pending_confirmation"
        assert claim(factory) is None
        leases.attach(db, *new)
        with pytest.raises(leases.LeaseLost):
            crud.mark_emission_job_succeeded(db, job_id, result_snapshot={"success": True})
        db.rollback()
        leases.detach(db)
        leases.record_late_result(db, *new, {"success": True, "source": "late_mock"})
        assert db.get(models.DocumentEmissionJob, job_id).status == "pending_confirmation"
        attempt = db.query(models.DocumentEmissionAttempt).filter_by(job_id=job_id).one()
        assert attempt.late_result_snapshot["source"] == "late_mock"


def test_scheduled_retry_scope_and_order(factory):
    future, tenant = enqueue(factory, available_at=datetime.now()+timedelta(seconds=15))
    due, other = enqueue(factory, priority=5)
    with factory() as db:
        delay = leases.next_available_delay(db, tenant_ids={tenant})
        assert 10 < delay <= 15
    assert claim(factory, tenant_ids={tenant}) is None
    assert claim(factory, tenant_ids={tenant}, events=False)[0] == due
    with factory() as db:
        job = db.get(models.DocumentEmissionJob, future)
        job.available_at = datetime.now()-timedelta(seconds=1)
        db.commit()
    assert claim(factory, tenant_ids={tenant})[0] == future


def test_listener_startup_reconnect_and_notifications(factory):
    import logging
    options = make_url(safe_url()).translate_connect_args(username="user")
    options["application_name"] = "inkora-emission-test-listener"
    wake, metrics = WakeSignal(), Metrics()
    listener = Listener(options, factory, wake, metrics, logging.getLogger(__name__))
    def until(predicate, timeout=6):
        deadline = time.monotonic()+timeout
        while not predicate() and time.monotonic()<deadline:
            time.sleep(0.02)
        assert predicate()
    enqueue(factory)  # exists before LISTEN: startup pulse must catch it
    listener.start()
    try:
        until(lambda: wake.snapshot() > 0)
        first = wake.snapshot()
        enqueue(factory)
        until(lambda: wake.snapshot() > first)
        with factory() as db:
            db.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE application_name='inkora-emission-test-listener'"))
            db.commit()
        until(lambda: metrics.counts["listener_errors"] > 0)
        gap = wake.snapshot()
        enqueue(factory)
        until(lambda: metrics.counts["listener_connections"] >= 2)
        assert wake.snapshot() > gap
    finally:
        listener.stop_requested.set()
        listener.join(7)
    assert not listener.is_alive()


def test_migration_down_up_preserves_jobs(factory):
    job_id, _ = enqueue(factory)
    with factory.kw["bind"].begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            migration().downgrade()
            assert conn.scalar(text("SELECT count(*) FROM document_emission_jobs WHERE id=:id"), {"id":job_id}) == 1
            migration().upgrade()
    assert claim(factory)[0] == job_id


def test_production_recovery_and_heartbeat_protect_started_job(factory):
    job_id, _ = enqueue(factory)
    reservation = claim(factory)
    with factory() as db:
        leases.attach(db, *reservation)
        crud.mark_emission_job_attempt_started(db, job_id)
        leases.detach(db)
        assert leases.renew(db, [reservation], owner="wrong-worker", lease_seconds=300) == 0
        assert leases.renew(db, [reservation], owner="test-worker", lease_seconds=300) == 1
        assert leases.recover_coordinator(db, legacy_timeout=30) == 0
        db.query(models.DocumentEmissionJob).filter_by(id=job_id).update({"lease_expires_at":datetime.now()-timedelta(seconds=1)})
        db.commit()
        assert leases.renew(db, [reservation], owner="test-worker", lease_seconds=300) == 0
        assert leases.recover_coordinator(db, legacy_timeout=30) == 1
        db.expire_all()
        assert db.get(models.DocumentEmissionJob, job_id).status == "pending_confirmation"
        assert db.query(models.DocumentEmissionAttempt).filter_by(job_id=job_id).one().status == "pending_confirmation"


def test_late_provider_response_cannot_change_fiscal_document(factory, monkeypatch):
    from services import emission_queue_service as worker
    from test_emission_queue import _make_fiscal_document
    with factory() as db:
        _, user, document = _make_fiscal_document(db, "LEASELATE")
        job, _ = worker.enqueue_fiscal_document_job(db, document, user, tipo_comprobante="01")
        job_id, document_id, original = job.id, document.id, document.estado
    reservation = claim(factory)
    def late_provider(*args, **kwargs):
        with factory() as db:
            db.query(models.DocumentEmissionJob).filter_by(id=job_id).update({"lease_expires_at":datetime.now()-timedelta(seconds=1)})
            db.commit()
            leases.recover_coordinator(db, legacy_timeout=30)
        return {"success":True, "ticket":"synthetic-late-ticket"}
    monkeypatch.setattr(worker.facturacion_service, "emitir_factura", late_provider)
    with factory() as db:
        assert not worker.process_emission_job(job_id, db_session=db, lease_token=reservation[1])
        db.expire_all()
        assert db.get(models.Cotizacion, document_id).estado == original
        assert db.get(models.DocumentEmissionJob, job_id).status == "retry"
        assert db.get(models.DocumentEmissionJob, job_id).action == "consult_fiscal_document"
        attempt = db.query(models.DocumentEmissionAttempt).filter_by(job_id=job_id).one()
        assert attempt.late_result_snapshot["ticket"] == "synthetic-late-ticket"


def test_runtime_capacity_and_heartbeats_continue_during_shutdown(factory, monkeypatch):
    from services import emission_queue_service as worker
    started, release = threading.Event(), threading.Event()
    shutdown = threading.Event()
    monkeypatch.setattr(worker, "_shutdown_requested", shutdown)
    monkeypatch.setattr(worker, "SessionLocal", factory)
    monkeypatch.setattr(worker, "_install_signal_handlers", lambda: None)
    monkeypatch.setattr(worker.settings, "EMISSION_WORKER_WAKE_MODE", "poll")
    monkeypatch.setattr(worker.settings, "EMISSION_WORKER_CONCURRENCY", 1)
    monkeypatch.setattr(worker.settings, "EMISSION_LEASE_SECONDS", 1)
    monkeypatch.setattr(worker.settings, "EMISSION_HEARTBEAT_SECONDS", 0.15)
    monkeypatch.setattr(worker.settings, "EMISSION_STALE_RECOVERY_INTERVAL_SECONDS", 0.2)
    for _ in range(4):
        enqueue(factory)
    def slow(job_id, token):
        with factory() as db:
            leases.attach(db, job_id, token)
            crud.mark_emission_job_attempt_started(db, job_id)
            leases.before_provider(db)
            started.set()
            assert release.wait(6)
            crud.mark_emission_job_succeeded(db, job_id, result_snapshot={"synthetic":True})
            leases.detach(db)
    monkeypatch.setattr(worker, "_process_single_job", slow)
    thread = threading.Thread(target=worker.run_worker_loop)
    thread.start()
    try:
        assert started.wait(4)
        worker.request_worker_shutdown()
        time.sleep(1.5)  # deliberately longer than the initial lease
        with factory() as db:
            rows = db.query(models.DocumentEmissionJob).filter_by(status="processing").all()
            assert len(rows) == 1
            assert rows[0].lease_expires_at > datetime.now()
            assert db.query(models.DocumentEmissionJob).filter_by(status="queued").count() == 3
    finally:
        release.set()
        worker.request_worker_shutdown()
        thread.join(7)
    assert not thread.is_alive()
    with factory() as db:
        assert db.query(models.DocumentEmissionJob).filter_by(status="succeeded").count() == 1


def test_runtime_fallback_and_scheduled_retry_without_listener(factory, monkeypatch):
    from services import emission_queue_service as worker, emission_worker_runtime as runtime
    shutdown = threading.Event()
    monkeypatch.setattr(worker, "_shutdown_requested", shutdown)
    monkeypatch.setattr(worker, "SessionLocal", factory)
    monkeypatch.setattr(worker, "_install_signal_handlers", lambda: None)
    monkeypatch.setattr(worker.settings, "EMISSION_WORKER_WAKE_MODE", "notify")
    monkeypatch.setattr(worker.settings, "EMISSION_EVENT_TENANT_IDS", "*")
    monkeypatch.setattr(worker.settings, "EMISSION_WORKER_FALLBACK_SECONDS", 0.3)
    monkeypatch.setattr(runtime, "listener_options", lambda settings: {})
    monkeypatch.setattr(runtime.Listener, "run", lambda self: None)
    processed = threading.Event()
    when = []
    def process(job_id, token):
        when.append(time.monotonic())
        with factory() as db:
            leases.attach(db, job_id, token)
            crud.mark_emission_job_attempt_started(db, job_id)
            crud.mark_emission_job_succeeded(db, job_id)
            leases.detach(db)
        processed.set()
    monkeypatch.setattr(worker, "_process_single_job", process)
    thread = threading.Thread(target=worker.run_worker_loop)
    thread.start()
    try:
        time.sleep(0.1)
        start = time.monotonic()
        enqueue(factory, available_at=datetime.now()+timedelta(seconds=0.6))
        assert processed.wait(3)
        assert 0.55 <= when[0]-start < 1.5
    finally:
        worker.request_worker_shutdown()
        thread.join(7)
    assert not thread.is_alive()


@pytest.mark.parametrize("blocked", [False, True])
def test_owned_execution_preserves_fiscal_result_and_suspended_tenant_guard(factory, monkeypatch, blocked):
    from services import emission_queue_service as worker
    from test_emission_queue import _make_fiscal_document, _noop_async
    suffix = "LEASEBLOCK" if blocked else "LEASEOK"
    with factory() as db:
        tenant, user, document = _make_fiscal_document(db, suffix)
        job, _ = worker.enqueue_fiscal_document_job(db, document, user, tipo_comprobante="01")
        job_id, document_id = job.id, document.id
        if blocked:
            tenant.is_active = False
            db.commit()
    reservation = claim(factory)
    calls = []
    def provider(*args, **kwargs):
        calls.append(1)
        return {"success":True,"serie":"F001","correlativo":"000001",
                "cdr_xml":"<ApplicationResponse>offline accepted fixture</ApplicationResponse>",
                "sunat_response":{"success":True,"cdrResponse":{"description":"Aceptado"}}}
    monkeypatch.setattr(worker.facturacion_service, "emitir_factura", provider)
    monkeypatch.setattr(worker.pdf_storage_service, "process_pdf_background", _noop_async)
    monkeypatch.setattr(worker.fiscal_artifact_service, "persist_cdr_artifact", _noop_async)
    with factory() as db:
        assert worker.process_emission_job(job_id, db_session=db, lease_token=reservation[1]) is (not blocked)
        db.expire_all()
        assert bool(calls) is (not blocked)
        assert db.get(models.DocumentEmissionJob, job_id).status == ("failed" if blocked else "succeeded")
        if not blocked:
            assert db.get(models.Cotizacion, document_id).estado == "facturada"


def test_duplicate_execution_token_cannot_create_second_attempt_or_provider_call(factory, monkeypatch):
    from services import emission_queue_service as worker
    from test_emission_queue import _make_fiscal_document
    with factory() as db:
        _, user, document = _make_fiscal_document(db, "LEASEDUP")
        job, _ = worker.enqueue_fiscal_document_job(db, document, user, tipo_comprobante="01")
        job_id = job.id
    reservation = claim(factory)
    with factory() as db:
        leases.attach(db, *reservation)
        crud.mark_emission_job_attempt_started(db, job_id)
        leases.detach(db)
    def forbidden(*args, **kwargs):
        pytest.fail("Un token ya iniciado no debe invocar al proveedor de nuevo")
    monkeypatch.setattr(worker.facturacion_service, "emitir_factura", forbidden)
    with factory() as db:
        assert not worker.process_emission_job(job_id, db_session=db, lease_token=reservation[1])
        assert db.query(models.DocumentEmissionAttempt).filter_by(job_id=job_id).count() == 1
        assert db.get(models.DocumentEmissionJob, job_id).status == "processing"
        assert db.query(models.DocumentEmissionAttempt).filter_by(job_id=job_id).one().late_result_snapshot is None


def test_pilot_does_not_starve_higher_priority_legacy_job(factory, monkeypatch):
    from services import emission_queue_service as worker, emission_worker_runtime as runtime
    _, pilot = enqueue(factory, priority=100)
    legacy_job, _ = enqueue(factory, priority=1)
    monkeypatch.setattr(worker, "_shutdown_requested", threading.Event())
    monkeypatch.setattr(worker, "SessionLocal", factory)
    monkeypatch.setattr(worker, "_install_signal_handlers", lambda: None)
    monkeypatch.setattr(worker.settings, "EMISSION_WORKER_WAKE_MODE", "notify")
    monkeypatch.setattr(worker.settings, "EMISSION_EVENT_TENANT_IDS", str(pilot))
    monkeypatch.setattr(worker.settings, "EMISSION_WORKER_CONCURRENCY", 1)
    monkeypatch.setattr(runtime, "listener_options", lambda settings: {})
    monkeypatch.setattr(runtime.Listener, "run", lambda self: None)
    processed = []
    def process(job_id, token):
        processed.append(job_id)
        worker.request_worker_shutdown()
    monkeypatch.setattr(worker, "_process_single_job", process)
    thread = threading.Thread(target=worker.run_worker_loop)
    thread.start()
    thread.join(5)
    if thread.is_alive():
        worker.request_worker_shutdown()
        thread.join(5)
    assert not thread.is_alive()
    assert processed == [legacy_job]


def test_poll_mode_drains_ready_work_immediately_on_local_completion(factory, monkeypatch):
    from services import emission_queue_service as worker
    for _ in range(2):
        enqueue(factory)
    monkeypatch.setattr(worker, "_shutdown_requested", threading.Event())
    monkeypatch.setattr(worker, "SessionLocal", factory)
    monkeypatch.setattr(worker, "_install_signal_handlers", lambda: None)
    monkeypatch.setattr(worker.settings, "EMISSION_WORKER_WAKE_MODE", "poll")
    monkeypatch.setattr(worker.settings, "EMISSION_WORKER_POLL_SECONDS", 30)
    monkeypatch.setattr(worker.settings, "EMISSION_WORKER_CONCURRENCY", 1)
    processed = []
    def process(job_id, token):
        with factory() as db:
            leases.attach(db, job_id, token)
            crud.mark_emission_job_attempt_started(db, job_id)
            crud.mark_emission_job_succeeded(db, job_id)
            leases.detach(db)
        processed.append(job_id)
        if len(processed) == 2:
            worker.request_worker_shutdown()
    monkeypatch.setattr(worker, "_process_single_job", process)
    thread = threading.Thread(target=worker.run_worker_loop)
    thread.start()
    thread.join(3)
    completed = not thread.is_alive()
    if not completed:
        worker.request_worker_shutdown()
        thread.join(3)
    assert completed and len(processed) == 2
