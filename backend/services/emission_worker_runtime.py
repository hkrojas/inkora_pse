"""Bounded executor, PostgreSQL wake listener, timers and batched heartbeats."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import select
import threading
import time
from uuid import uuid4

import psycopg2
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from services import emission_leases as leases
from services.release_identity import release_identity

CHANNEL = "inkora_emission_jobs_changed"


class WakeSignal:
    """Generation avoids clearing a notification received during a queue scan."""
    def __init__(self):
        self.condition = threading.Condition()
        self.generation = 0

    def pulse(self):
        with self.condition:
            self.generation += 1
            self.condition.notify_all()

    def snapshot(self):
        with self.condition:
            return self.generation

    def wait(self, generation, timeout):
        with self.condition:
            self.condition.wait_for(lambda: self.generation != generation, timeout=max(0, timeout))


class Metrics:
    def __init__(self):
        self.lock = threading.Lock()
        self.counts = Counter()

    def add(self, key, value=1):
        with self.lock:
            self.counts[key] += value

    def flush(self, logger, active):
        with self.lock:
            counts, self.counts = self.counts, Counter()
        logger.info("emission_worker_metrics", extra={"event": "emission_worker_metrics",
                    "context": json.dumps(dict(counts, active=active), sort_keys=True)})

    def latency(self, seconds):
        with self.lock:
            self.counts["queue_wait_ms_total"] += round(seconds*1000)
            self.counts["queue_wait_ms_max"] = max(self.counts["queue_wait_ms_max"], round(seconds*1000))
            for limit in (0.1, 0.5, 1, 2, 5, 30, 300):
                if seconds <= limit:
                    self.counts[f"queue_wait_le_{limit}s"] += 1


def listener_options(settings):
    if not settings.EMISSION_LISTEN_DATABASE_URL:
        raise ValueError("EMISSION_LISTEN_DATABASE_URL es obligatoria en modo notify")
    try:
        url = make_url(settings.EMISSION_LISTEN_DATABASE_URL)
        main = make_url(settings.DATABASE_URL)
    except Exception:
        raise ValueError("URL de escucha inválida") from None
    local = url.host in {"localhost", "127.0.0.1", "::1"} and settings.ENVIRONMENT in {"test", "local", "development"}
    if not url.drivername.startswith("postgresql") or url.port == 6543:
        raise ValueError("LISTEN requiere PostgreSQL directo o pooler de sesión, no transaccional")
    if not local and (url.port or 5432) != 5432:
        raise ValueError("LISTEN remoto requiere el puerto de sesión 5432")
    if url.database != main.database:
        raise ValueError("La conexión de escucha debe usar la misma base")
    options = dict(url.translate_connect_args(username="user"))
    options.update(dict(url.query))
    if "pgbouncer" in options:
        raise ValueError("No se admite pgbouncer en la conexión de escucha")
    sslmode = options.get("sslmode", "require")
    if not local and sslmode not in {"require", "verify-ca", "verify-full"}:
        raise ValueError("La conexión de escucha remota requiere TLS")
    options.update(sslmode=sslmode, connect_timeout=5, application_name="inkora-emission-listener",
                   keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=3)
    return options


class Listener(threading.Thread):
    def __init__(self, options, factory, wake, metrics, logger):
        super().__init__(name="emission-listener", daemon=True)
        self.options, self.factory, self.wake = options, factory, wake
        self.metrics, self.logger = metrics, logger
        self.stop_requested = threading.Event()

    def verify_database(self, conn):
        # Challenge via the application connection proves both routes reach the same DB.
        channel = "inkora_check_" + uuid4().hex
        challenge = uuid4().hex
        with conn.cursor() as cursor:
            cursor.execute('LISTEN "' + channel + '"')
        with self.factory() as db:
            db.execute(text("SELECT pg_notify(:channel, :value)"), {"channel": channel, "value": challenge})
            db.commit()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not self.stop_requested.is_set():
            if select.select([conn], [], [], 0.2)[0]:
                conn.poll()
                notices, conn.notifies = conn.notifies, []
                if any(n.channel == channel and n.payload == challenge for n in notices):
                    with conn.cursor() as cursor:
                        cursor.execute('UNLISTEN "' + channel + '"')
                    return
        raise RuntimeError("No se pudo verificar la base de escucha")

    def run(self):
        backoff = 1
        while not self.stop_requested.is_set():
            conn = None
            try:
                conn = psycopg2.connect(**self.options)
                conn.autocommit = True
                with conn.cursor() as cursor:
                    cursor.execute("LISTEN " + CHANNEL)
                self.verify_database(conn)
                self.metrics.add("listener_connections")
                self.wake.pulse()  # LISTEN first, then catch up after every connection.
                backoff = 1
                while not self.stop_requested.is_set():
                    if select.select([conn], [], [], 1)[0]:
                        conn.poll()
                        count = len(conn.notifies)
                        conn.notifies.clear()
                        if count:
                            self.metrics.add("signals", count)
                            self.wake.pulse()
            except (psycopg2.Error, SQLAlchemyError, OSError, RuntimeError):
                self.metrics.add("listener_errors")
                # Never log the DSN or connection exception (may contain credentials).
                self.logger.warning("emission_listener_unavailable", extra={"event": "emission_listener_unavailable"})
            finally:
                if conn:
                    conn.close()
            self.stop_requested.wait(backoff)
            backoff = min(backoff * 2, 30)


def run():
    from services import emission_queue_service as worker
    settings, logger = worker.settings, worker.logger
    poll = max(settings.EMISSION_WORKER_POLL_SECONDS, 1)
    concurrency = max(settings.EMISSION_WORKER_CONCURRENCY, 1)
    fallback = settings.EMISSION_WORKER_FALLBACK_SECONDS
    notify = settings.EMISSION_WORKER_WAKE_MODE == "notify"
    tenant_ids = None if settings.EMISSION_EVENT_TENANT_IDS == "*" else {
        int(value) for value in settings.EMISSION_EVENT_TENANT_IDS.split(",") if value.strip()}
    options = listener_options(settings) if notify else None
    owner = uuid4().hex
    wake, metrics = WakeSignal(), Metrics()
    worker._worker_wakeup = wake
    worker._install_signal_handlers()
    listener = Listener(options, worker.SessionLocal, wake, metrics, logger) if notify else None
    fingerprint = hashlib.sha256(json.dumps({
        "mode": settings.EMISSION_WORKER_WAKE_MODE, "tenants": sorted(tenant_ids) if tenant_ids is not None else "*",
        "local": concurrency, "global": settings.EMISSION_GLOBAL_CONCURRENCY,
        "tenant": settings.EMISSION_TENANT_CONCURRENCY, "fallback": fallback,
        "poll": poll, "recovery": max(settings.EMISSION_STALE_RECOVERY_INTERVAL_SECONDS, 1),
        "lease": settings.EMISSION_LEASE_SECONDS, "heartbeat": settings.EMISSION_HEARTBEAT_SECONDS,
    }, sort_keys=True).encode()).hexdigest()[:16]
    logger.info("emission_worker_started", extra={"event": "emission_worker_started", "context":
        f"owner={owner} config={fingerprint} release={json.dumps(release_identity(), sort_keys=True)} commit={os.getenv('RAILWAY_GIT_COMMIT_SHA', 'local')} mode={settings.EMISSION_WORKER_WAKE_MODE}"})
    if listener:
        listener.start()
    active = {}
    next_recovery = next_poll = next_fallback = next_heartbeat = 0.0
    next_metrics = time.monotonic() + 60
    next_job = float("inf")
    seen = -1
    draining = False
    try:
        with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="emission-worker") as executor:
            while True:
                draining = draining or worker.is_shutdown_requested()
                active = {f: reservation for f, reservation in active.items() if not f.done()}
                if draining and not active:
                    break
                generation = wake.snapshot()
                now = time.monotonic()
                delay = fallback
                db = None
                try:
                    # Heartbeat remains active during graceful draining.
                    if active and now >= next_heartbeat:
                        db = worker.SessionLocal()
                        metrics.add("renewed", leases.renew(db, list(active.values()), owner=owner,
                                                          lease_seconds=settings.EMISSION_LEASE_SECONDS))
                        db.close()
                        db = None
                        next_heartbeat = now + settings.EMISSION_HEARTBEAT_SECONDS
                    if not draining and now >= next_recovery:
                        db = worker.SessionLocal()
                        metrics.add("recovered", leases.recover_coordinator(db,
                            legacy_timeout=max(settings.EMISSION_PROCESSING_TIMEOUT_SECONDS, 30)))
                        db.close()
                        db = None
                        next_recovery = now + max(settings.EMISSION_STALE_RECOVERY_INTERVAL_SECONDS, 1)
                    legacy_due = (now >= next_poll or (not notify and generation != seen)) and (
                        not notify or tenant_ids is not None)
                    fallback_due = now >= next_fallback
                    event_due = notify and (generation != seen or fallback_due or now >= next_job)
                    if not draining and len(active) < concurrency and (legacy_due or event_due):
                        if event_due:
                            next_job = float("inf")
                        if fallback_due:
                            metrics.add("fallbacks")
                            next_fallback = now + fallback
                        # At the legacy deadline compare the whole queue in one
                        # priority order; always serving the pilot first could
                        # starve an older/higher-priority non-pilot job.
                        scopes = [None if legacy_due else tenant_ids]
                        for scope_ids in scopes:
                            while len(active) < concurrency:
                                db = worker.SessionLocal()
                                reservation, scheduled = leases.claim(db, owner=owner, lease_seconds=settings.EMISSION_LEASE_SECONDS,
                                    global_limit=settings.EMISSION_GLOBAL_CONCURRENCY,
                                    tenant_limit=settings.EMISSION_TENANT_CONCURRENCY,
                                    tenant_ids=scope_ids, events=True, include_delay=True)
                                if reservation:
                                    metrics.latency(db.info.get("emission_queue_wait_seconds", 0))
                                db.close()
                                db = None
                                metrics.add("claim_queries")
                                if not reservation:
                                    metrics.add("empty_claims")
                                    if notify and scheduled is not None:
                                        next_job = time.monotonic() + scheduled
                                    break
                                future = executor.submit(worker._process_single_job, *reservation)
                                active[future] = reservation
                                future.add_done_callback(lambda _: wake.pulse())
                                metrics.add("claimed")
                        if legacy_due:
                            next_poll = now + poll
                    # Full capacity must not spin on already-due claim timers.
                    deadlines = [next_metrics]
                    if not draining:
                        deadlines.append(next_recovery)
                        if len(active) < concurrency:
                            deadlines.append(next_fallback if notify else next_poll)
                            if notify:
                                deadlines.append(next_job)
                                if tenant_ids is not None:
                                    deadlines.append(next_poll)
                    if active:
                        deadlines.append(next_heartbeat)
                    delay = max(0.01, min(deadlines) - time.monotonic())
                except SQLAlchemyError:
                    if db is not None:
                        try:
                            db.rollback()
                        except SQLAlchemyError:
                            logger.warning("emission_worker_rollback_failed", extra={"event": "emission_worker_rollback_failed"})
                    metrics.add("database_errors")
                    logger.warning("emission_worker_database_error", extra={"event": "emission_worker_database_error"})
                    delay = min(fallback, poll * 2)
                finally:
                    if db is not None:
                        try:
                            db.close()
                        except SQLAlchemyError:
                            logger.warning("emission_worker_session_close_failed", extra={"event": "emission_worker_session_close_failed"})
                if time.monotonic() >= next_metrics:
                    metrics.flush(logger, len(active))
                    next_metrics = time.monotonic() + 60
                seen = generation
                wake.wait(generation, delay)
    finally:
        if listener:
            listener.stop_requested.set()
            listener.join(timeout=7)
        worker._worker_wakeup = None
        metrics.flush(logger, len(active))
        logger.info("emission_worker_stopped", extra={"event": "emission_worker_stopped"})
