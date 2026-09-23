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
        assert db.get(models.DocumentEmissionJob, job_id).status == "pending_confirmation"
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
                "sunat_response":{"success":True,"cdrResponse":{"description":"Aceptado"}}}
    monkeypatch.setattr(worker.facturacion_service, "emitir_factura", provider)
    monkeypatch.setattr(worker.pdf_storage_service, "process_pdf_background", _noop_async)
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
