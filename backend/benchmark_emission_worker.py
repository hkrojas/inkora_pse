"""Local-only homologation: real idle SQL counts, latency probes, 1,000 mock jobs.

Run with INKORA_WORKER_POSTGRES_URL pointing to an exclusive loopback
inkora_worker_* database. Recreates its tables. Never calls any fiscal provider.
"""
import argparse
import json
import multiprocessing as mp
import os
from pathlib import Path
import threading
import time


def boot(url):
    os.environ.update(ENVIRONMENT="test", DATABASE_URL=url, SECRET_KEY="synthetic-worker-benchmark",
                      EMISSION_WORKER_WAKE_MODE="notify", EMISSION_EVENT_TENANT_IDS="*",
                      EMISSION_LISTEN_DATABASE_URL=url+"?sslmode=disable", EMISSION_GLOBAL_CONCURRENCY="4")


def replica(url, stop, reports, synthetic=False):
    boot(url)
    from sqlalchemy import event
    from database import engine, SessionLocal
    import crud
    from services import emission_queue_service as worker, emission_leases as leases
    count = [0]
    @event.listens_for(engine, "before_cursor_execute")
    def sql_count(*args):
        count[0] += 1
    def process(job_id, token):
        with SessionLocal() as db:
            leases.attach(db, job_id, token)
            try:
                crud.mark_emission_job_attempt_started(db, job_id)
                leases.before_provider(db)
                time.sleep(0.005)  # local mock: no HTTP or fiscal document
                crud.mark_emission_job_succeeded(db, job_id, result_snapshot={"synthetic": True})
            finally:
                leases.detach(db)
    if synthetic:
        worker._process_single_job = process
    def stopper():
        stop.wait()
        worker.request_worker_shutdown()
    threading.Thread(target=stopper, daemon=True).start()
    worker.run_worker_loop()
    reports.put(count[0])
    engine.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--idle-seconds", type=int, default=1800)
    parser.add_argument("--jobs", type=int, default=1000)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    boot(os.environ.get("INKORA_WORKER_POSTGRES_URL", ""))
    # Guard before any connection or destructive operation.
    from test_emission_worker_postgres import safe_url, prepare_database, enqueue
    url = safe_url()
    from sqlalchemy import create_engine, event, func
    from sqlalchemy.orm import sessionmaker
    import crud
    import models
    from datetime import datetime, timedelta
    engine = create_engine(url)
    prepare_database(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    baseline = [0]
    @event.listens_for(engine, "before_cursor_execute")
    def sql_count(*ignored):
        baseline[0] += 1
    stop, reports = mp.Event(), mp.Queue()
    process = mp.Process(target=replica, args=(url, stop, reports))
    process.start()
    started = time.monotonic()
    next_recovery = 0
    while time.monotonic()-started < args.idle_seconds:
        now = time.monotonic()
        with factory() as db:
            if now >= next_recovery:
                crud.recover_stale_processing_jobs(db, stale_before=datetime.now()-timedelta(seconds=300))
                crud.recover_pending_fiscal_reconciliations(db)
                next_recovery = now+60
            crud.claim_next_emission_job(db)
        time.sleep(min(2, max(0, args.idle_seconds-(time.monotonic()-started))))
    baseline_queries = baseline[0]
    stop.set()
    process.join(15)
    assert process.exitcode == 0, "Idle worker did not stop cleanly"
    notify_queries = reports.get(timeout=3)
    idle = {"seconds": args.idle_seconds, "baseline_sql": baseline_queries,
            "notify_sql": notify_queries, "reduction_percent": 100*(1-notify_queries/baseline_queries)}
    print(json.dumps({"idle": idle}), flush=True)

    # Four independent processes, each with its own listener and executor.
    stop = mp.Event()
    processes = [mp.Process(target=replica, args=(url, stop, reports, True)) for _ in range(4)]
    for process in processes:
        process.start()
    latencies = []
    time.sleep(3)
    for _ in range(30):
        start = time.monotonic()
        job_id, _ = enqueue(factory)
        deadline = start+10
        while time.monotonic() < deadline:
            with factory() as db:
                job = db.get(models.DocumentEmissionJob, job_id)
                done = job.status == "succeeded"
            if done:
                latencies.append(time.monotonic()-start)
                break
            time.sleep(0.01)
        assert done, "Capacity-available probe was not processed"
    tenants = []
    with factory() as db:
        for index in range(20):
            tenant = models.Tenant(business_name=f"Load tenant {index}", business_ruc=f"BENCH{index:06}", is_active=True)
            db.add(tenant)
            db.flush()
            tenants.append(tenant.id)
        for index in range(args.jobs):
            db.add(models.DocumentEmissionJob(tenant_id=tenants[index%20], resource_type="cotizacion", resource_id=1,
                action="emit_fiscal_document", idempotency_key=f"load-{index}"))
        db.commit()
    start = time.monotonic()
    peak = 0
    while time.monotonic()-start < 300:
        with factory() as db:
            counts = db.query(models.DocumentEmissionJob.tenant_id, func.count()).filter_by(status="processing").group_by(models.DocumentEmissionJob.tenant_id).all()
            total = sum(n for _, n in counts)
            assert total <= 4 and all(n<=1 for _, n in counts)
            peak = max(peak, total)
            done = db.query(models.DocumentEmissionJob).filter(models.DocumentEmissionJob.tenant_id.in_(tenants),
                models.DocumentEmissionJob.status=="succeeded").count()
        if done == args.jobs:
            break
        time.sleep(0.05)
    elapsed = time.monotonic()-start
    stop.set()
    for process in processes:
        process.join(15)
        assert process.exitcode == 0, "Load worker did not drain cleanly"
    assert done == args.jobs
    with factory() as db:
        assert db.query(models.DocumentEmissionAttempt).count() == args.jobs + 30
    result = {"idle": idle, "load": {"jobs": done, "tenants": 20, "replicas": 4,
              "seconds": elapsed, "peak_processing": peak, "attempts_per_job": 1},
              "capacity_available_latency": {"probes": 30, "p95_seconds": sorted(latencies)[28]}}
    Path(args.output).write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result), flush=True)
    assert result["capacity_available_latency"]["p95_seconds"] < 2
    if args.idle_seconds >= 1800:
        assert idle["reduction_percent"] >= 90
    engine.dispose()


if __name__ == "__main__":
    main()
