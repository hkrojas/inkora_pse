"""Offline crash recovery must distinguish a proven unsent job from uncertainty."""
from copy import deepcopy
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

import crud
import models
from services import emission_leases as leases
from services.fiscal_submission_state import can_submit, initial_state, mark_not_submitted, mark_possible


SUBMISSION_CASES = [
    ("new", initial_state(), True),
    ("authentication_failed_before_post", {"submission_state_version": 1, "submission_phase": "not_submitted"}, True),
    ("false_flags", dict(initial_state(), send_started=False, retry_signed_after_not_found=False), True),
    ("possible", dict(initial_state(), submission_phase="possible_submission", send_started=True), False),
    ("possible_false_flag", dict(initial_state(), submission_phase="possible_submission", send_started=False), False),
    ("legacy_empty", {}, False),
    ("legacy_sign_only", {"sign_only": True, "send_started": False}, False),
    ("no_snapshot", None, False),
    ("array_snapshot", [initial_state()], False),
    ("text_snapshot", "not_started", False),
    ("boolean_snapshot", True, False),
    ("number_snapshot", 1, False),
    ("no_version", {"submission_phase": "not_started"}, False),
    ("no_phase", {"submission_state_version": 1}, False),
    ("boolean_version", dict(initial_state(), submission_state_version=True), False),
    ("float_version", dict(initial_state(), submission_state_version=1.0), False),
    ("string_version", dict(initial_state(), submission_state_version="1"), False),
    ("unsupported_version", dict(initial_state(), submission_state_version=2), False),
    ("null_version", dict(initial_state(), submission_state_version=None), False),
    ("null_phase", dict(initial_state(), submission_phase=None), False),
    ("array_phase", dict(initial_state(), submission_phase=["not_started"]), False),
    ("object_phase", dict(initial_state(), submission_phase={"not_started": True}), False),
    ("wrong_case_phase", dict(initial_state(), submission_phase="NOT_STARTED"), False),
] + [
    (f"{flag}_{name}", dict(initial_state(), **{flag: value}), False)
    for flag in ("send_started", "retry_signed_after_not_found")
    for name, value in (("true", True), ("null", None), ("zero", 0), ("string_false", "false"),
                        ("empty_string", ""), ("array", []), ("object", {}))
]


def _jobs(db, *, mode, action="emit_fiscal_document"):
    tenant = models.Tenant(business_name="Synthetic lease phases", business_ruc=f"20{uuid4().int % 1_000_000_000:09d}", is_active=True)
    db.add(tenant)
    db.flush()
    now = datetime.now()
    jobs = []
    for name, snapshot, safe in SUBMISSION_CASES:
        token = str(uuid4()) if mode == "lease" else None
        job = models.DocumentEmissionJob(
            tenant_id=tenant.id, resource_type="cotizacion", resource_id=1, action=action,
            provider="smartpse", idempotency_key=uuid4().hex, payload_snapshot=deepcopy(snapshot),
            status="pending_confirmation" if mode == "pending" else "processing", attempts=1,
            max_attempts=1, lease_token=token, lease_expires_at=now-timedelta(seconds=60) if token else None,
            execution_started_at=now-timedelta(seconds=90) if token else None,
            locked_at=now-timedelta(seconds=90), processing_started_at=now-timedelta(seconds=90),
        )
        db.add(job)
        db.flush()
        db.add(models.DocumentEmissionAttempt(job_id=job.id, tenant_id=tenant.id, attempt_number=1,
                                              lease_token=token, status="processing"))
        jobs.append((name, job.id, snapshot, safe))
    db.commit()
    return jobs


def _assert_recovered(db, jobs, *, original_action="emit_fiscal_document"):
    db.expire_all()
    for name, job_id, snapshot, safe in jobs:
        job = db.get(models.DocumentEmissionJob, job_id)
        expected_action = original_action if safe else "consult_fiscal_document"
        assert job.action == expected_action, name
        assert job.status == "retry", name
        assert job.finished_at is None, name
        assert job.locked_at is None and job.processing_started_at is None, name
        assert job.attempts == 1 and job.max_attempts == 1, name
        assert job.payload_snapshot == snapshot, name


@pytest.mark.parametrize("mode", ["lease", "legacy", "pending", "coordinator"])
def test_sqlite_recovery_requires_explicit_unsent_evidence(db_session, mode):
    jobs = _jobs(db_session, mode="lease" if mode == "coordinator" else mode)
    if mode == "lease":
        count = leases.recover(db_session)
    elif mode == "legacy":
        count = crud.recover_stale_processing_jobs(db_session, stale_before=datetime.now()-timedelta(seconds=30))
    elif mode == "pending":
        count = crud.recover_pending_fiscal_reconciliations(db_session)
    else:
        count = leases.recover_coordinator(db_session, legacy_timeout=30)
    assert count == len(jobs)
    _assert_recovered(db_session, jobs)


def test_pending_consult_is_never_downgraded_to_emit(db_session):
    jobs = _jobs(db_session, mode="pending", action="consult_fiscal_document")
    assert crud.recover_pending_fiscal_reconciliations(db_session) == len(jobs)
    _assert_recovered(db_session, jobs, original_action="consult_fiscal_document")


def test_crash_after_preauth_failure_preserves_first_send_then_marker_requires_consult(db_session):
    snapshot = mark_not_submitted(mark_possible(initial_state()))
    tenant = models.Tenant(business_name="Synthetic preauth crash", business_ruc="20999999998", is_active=True)
    db_session.add(tenant)
    db_session.flush()
    job = models.DocumentEmissionJob(
        tenant_id=tenant.id, resource_type="cotizacion", resource_id=1, action="emit_fiscal_document",
        provider="smartpse", idempotency_key=uuid4().hex, payload_snapshot=snapshot,
        status="processing", attempts=1, max_attempts=1, lease_token=str(uuid4()),
        lease_expires_at=datetime.now()-timedelta(seconds=1), execution_started_at=datetime.now(),
    )
    db_session.add(job)
    db_session.commit()
    assert leases.recover(db_session) == 1
    db_session.refresh(job)
    assert job.action == "emit_fiscal_document" and can_submit(job.payload_snapshot)
    # A committed marker before the next POST changes crash recovery even if
    # the process dies before it can record an execution timestamp.
    job.payload_snapshot = mark_possible(job.payload_snapshot)
    job.status = "processing"
    job.execution_started_at = None
    db_session.commit()
    assert leases.recover(db_session) == 1
    db_session.refresh(job)
    assert job.action == "consult_fiscal_document" and not can_submit(job.payload_snapshot)


def test_legacy_zero_attempts_is_not_proof_of_no_submission(db_session):
    jobs = _jobs(db_session, mode="lease")
    job = db_session.get(models.DocumentEmissionJob, jobs[5][1])
    job.attempts = 0
    job.execution_started_at = None
    db_session.commit()
    leases.recover(db_session)
    db_session.refresh(job)
    assert job.action == "consult_fiscal_document"


def _boleta_jobs(db, *, mode):
    tenant = models.Tenant(business_name="Synthetic boleta lease", business_ruc=f"20{uuid4().int % 1_000_000_000:09d}", is_active=True)
    db.add(tenant)
    db.flush()
    now = datetime.now()
    cases = [
        ("unexecuted_boleta", {"tipo_comprobante": "03"}, False, 0, mode != "pending"),
        ("executed_boleta", {"tipo_comprobante": "03"}, True, 1, False),
        ("phase_cannot_authorize_executed_boleta", dict(initial_state(), tipo_comprobante="03"), True, 1, False),
        ("missing_type", {}, False, 0, False),
        ("numeric_type", {"tipo_comprobante": 3}, False, 0, False),
    ]
    if mode == "legacy":
        cases.append(("legacy_prior_boleta_attempt", {"tipo_comprobante": "03"}, False, 1, False))
    jobs = []
    for name, snapshot, started, attempts, safe in cases:
        token = str(uuid4()) if mode == "lease" else None
        job = models.DocumentEmissionJob(
            tenant_id=tenant.id, resource_type="cotizacion", resource_id=1, action="emit_fiscal_document",
            provider="smartpse", idempotency_key=uuid4().hex, payload_snapshot=snapshot,
            status="pending_confirmation" if mode == "pending" else "processing", attempts=attempts,
            max_attempts=1, lease_token=token, lease_expires_at=now-timedelta(seconds=60) if token else None,
            execution_started_at=now-timedelta(seconds=90) if started else None,
            locked_at=now-timedelta(seconds=90), processing_started_at=now-timedelta(seconds=90),
        )
        db.add(job)
        db.flush()
        jobs.append((name, job.id, safe))
    db.commit()
    return jobs


@pytest.mark.parametrize("mode", ["lease", "legacy", "pending", "coordinator"])
def test_unexecuted_boleta_keeps_normal_emit_flow(db_session, mode):
    jobs = _boleta_jobs(db_session, mode="lease" if mode == "coordinator" else mode)
    if mode == "lease":
        count = leases.recover(db_session)
    elif mode == "legacy":
        count = crud.recover_stale_processing_jobs(db_session, stale_before=datetime.now()-timedelta(seconds=30))
    elif mode == "pending":
        count = crud.recover_pending_fiscal_reconciliations(db_session)
    else:
        count = leases.recover_coordinator(db_session, legacy_timeout=30)
    assert count == len(jobs)
    db_session.expire_all()
    for name, job_id, safe in jobs:
        job = db_session.get(models.DocumentEmissionJob, job_id)
        assert job.action == ("emit_fiscal_document" if safe else "consult_fiscal_document"), name
        assert job.status == "retry" and job.finished_at is None, name
