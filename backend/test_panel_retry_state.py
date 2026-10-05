"""Offline retry ledger validation: only a complete causal chain may repeat."""
from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

import models
from config import settings
from services import panel_retry_state as state


NOW = datetime(2026, 10, 5, 12, 0, 0)


@pytest.fixture
def invoice(db_session, monkeypatch):
    monkeypatch.setattr(state.emission_leases, "db_now", lambda db: NOW)
    monkeypatch.setattr(settings, "FISCAL_RECOVERY_FIRST_SECONDS", 900)
    monkeypatch.setattr(settings, "FISCAL_RECOVERY_MAX_SECONDS", 1800)
    tenant = models.Tenant(business_name="Offline ledger", business_ruc="20123456789",
        smartpse_company_id="77", smartpse_environment="demo")
    db_session.add(tenant)
    db_session.flush()
    document = models.Cotizacion(tenant_id=tenant.id, serie="FLED", correlativo=1,
        tipo_comprobante="01", sunat_xml_content="<offline-signed-invoice/>", provider_response={})
    db_session.add(document)
    db_session.flush()
    job = models.DocumentEmissionJob(tenant_id=tenant.id, resource_type="cotizacion", resource_id=document.id,
        action="consult_fiscal_document", provider="smartpse", idempotency_key=str(uuid4()), payload_snapshot={})
    db_session.add(job)
    db_session.commit()
    return SimpleNamespace(db=db_session, tenant=tenant, document=document, job=job, audits=[])


def start_marker(invoice, previous=None, *, job=None, started_at=None):
    job = job or invoice.job
    started_at = started_at or (_time(previous["next_retry_at"]) + timedelta(seconds=1)
        if previous else NOW - timedelta(hours=2))
    return {"version": 1, "id": str(uuid4()), "state": "possible_submission",
        "sequence": previous["sequence"] + 1 if previous else 1,
        "previous_attempt_id": previous["id"] if previous else None, "job_id": job.id,
        "started_at": started_at.isoformat(), "environment": "demo",
        "xml_sha256": hashlib.sha256(invoice.document.sunat_xml_content.encode()).hexdigest(),
        "provider_company_id": "77", "provider_document_id": "444951"}


def _time(value):
    return datetime.fromisoformat(value)


def completed_marker(start):
    completed = _time(start["started_at"]) + timedelta(seconds=10)
    return dict(start, state="confirmed_transient_failure", completed_at=completed.isoformat(),
        next_retry_at=(completed + timedelta(seconds=900 if start["sequence"] == 1 else 1800)).isoformat(),
        outcome={"source": "retry_response", "response_sha256": "a" * 64,
            "message": "HTTP 503 Service Unavailable"})


def write_audit(invoice, action, marker):
    audit = models.AuditLog(action=action, entity_type="cotizacion", entity_id=invoice.document.id,
        details=json.dumps(marker))
    invoice.db.add(audit)
    invoice.db.flush()
    invoice.audits.append(audit)
    return audit


def save_current(invoice, marker, *, job=None):
    job = job or invoice.job
    job.payload_snapshot = dict(job.payload_snapshot, panel_retry_attempt=deepcopy(marker))
    invoice.document.provider_response = {"inkora_evidence": {"panel_retry_attempt": deepcopy(marker)}}
    invoice.db.commit()


def completed_attempt(invoice, previous=None, *, job=None, started_at=None):
    start = start_marker(invoice, previous, job=job, started_at=started_at)
    completed = completed_marker(start)
    write_audit(invoice, state.START_ACTION, start)
    write_audit(invoice, state.COMPLETION_ACTION, completed)
    save_current(invoice, completed, job=job)
    return start, completed


def another_job(invoice):
    job = models.DocumentEmissionJob(tenant_id=invoice.tenant.id, resource_type="cotizacion",
        resource_id=invoice.document.id, action="consult_fiscal_document", provider="smartpse",
        idempotency_key=str(uuid4()), payload_snapshot={})
    invoice.db.add(job)
    invoice.db.commit()
    return job


def test_first_attempt_without_markers_or_history_is_eligible(invoice):
    assert state.eligibility(invoice.db, invoice.job, invoice.document) == (True, None)


def test_complete_due_chain_returns_detached_previous_without_writes(invoice):
    _, previous = completed_attempt(invoice)
    snapshot = deepcopy(invoice.job.payload_snapshot)
    response = deepcopy(invoice.document.provider_response)
    allowed, result = state.eligibility(invoice.db, invoice.job, invoice.document)
    assert allowed and result == previous
    result["outcome"]["message"] = "changed by caller"
    assert invoice.job.payload_snapshot == snapshot and invoice.document.provider_response == response
    assert not invoice.db.dirty and not invoice.db.new


def test_three_completed_attempts_have_no_arbitrary_retry_limit(invoice):
    previous = None
    for _ in range(3):
        _, previous = completed_attempt(invoice, previous)
    assert state.eligibility(invoice.db, invoice.job, invoice.document) == (True, previous)


@pytest.mark.parametrize("offset,expected", [(899, False), (900, True), (901, True)])
def test_retry_uses_database_clock_and_exact_due_boundary(invoice, offset, expected):
    _, previous = completed_attempt(invoice, started_at=NOW - timedelta(seconds=offset + 10))
    assert state.eligibility(invoice.db, invoice.job, invoice.document) == (expected, previous if expected else None)


def test_new_job_can_use_completed_attempt_of_other_job(invoice):
    _, previous = completed_attempt(invoice)
    second = another_job(invoice)
    assert state.eligibility(invoice.db, second, invoice.document) == (True, previous)


def test_historical_job_may_retain_exact_audited_start(invoice):
    first, previous = completed_attempt(invoice)
    invoice.job.payload_snapshot = {"panel_retry_attempt": first}
    second = another_job(invoice)
    _, latest = completed_attempt(invoice, previous, job=second)
    assert state.eligibility(invoice.db, second, invoice.document) == (True, latest)


def test_unfinished_lost_response_does_not_allow_another_attempt(invoice):
    _, previous = completed_attempt(invoice)
    start = start_marker(invoice, previous)
    write_audit(invoice, state.START_ACTION, start)
    save_current(invoice, start)
    assert state.eligibility(invoice.db, invoice.job, invoice.document) == (False, None)


@pytest.mark.parametrize("place", ["document", "snapshot", "audit"])
def test_legacy_or_untracked_markers_block_first_attempt(invoice, place):
    marker = {"id": "old-attempt", "state": "possible_submission"}
    if place == "document":
        invoice.document.provider_response = {"inkora_evidence": {"panel_retry_attempt": marker}}
    elif place == "snapshot":
        invoice.job.payload_snapshot = {"panel_retry_attempt": marker}
    else:
        write_audit(invoice, state.START_ACTION, marker)
    invoice.db.commit()
    assert state.eligibility(invoice.db, invoice.job, invoice.document) == (False, None)


@pytest.mark.parametrize("damage", ["missing_start", "missing_completion", "duplicate_start", "duplicate_completion",
    "unknown_start", "wrong_order", "not_json", "duplicate_json_key", "deleted_document_marker",
    "deleted_job_marker", "unknown_snapshot_marker", "snapshot_tampered", "wrong_snapshot_owner"])
def test_missing_tampered_duplicate_or_reordered_evidence_never_authorizes(invoice, damage):
    start, previous = completed_attempt(invoice)
    if damage == "missing_start":
        invoice.db.delete(invoice.audits[0])
    elif damage == "missing_completion":
        invoice.db.delete(invoice.audits[1])
    elif damage == "duplicate_start":
        write_audit(invoice, state.START_ACTION, start)
    elif damage == "duplicate_completion":
        write_audit(invoice, state.COMPLETION_ACTION, previous)
    elif damage == "unknown_start":
        invoice.audits[0].details = json.dumps(dict(start, job_id=999999))
    elif damage == "wrong_order":
        invoice.audits[0].action, invoice.audits[1].action = state.COMPLETION_ACTION, state.START_ACTION
        invoice.audits[0].details, invoice.audits[1].details = json.dumps(previous), json.dumps(start)
    elif damage == "not_json":
        invoice.audits[0].details = "tenant_id=1; job_id=1; attempt_id=legacy"
    elif damage == "duplicate_json_key":
        invoice.audits[0].details = json.dumps(start)[:-1] + ', "version": 1}'
    elif damage == "deleted_document_marker":
        invoice.document.provider_response = {}
    elif damage == "deleted_job_marker":
        invoice.job.payload_snapshot = {}
    elif damage == "unknown_snapshot_marker":
        invoice.job.payload_snapshot = {"panel_retry_attempt": dict(previous, id=str(uuid4()))}
    elif damage == "snapshot_tampered":
        invoice.job.payload_snapshot = {"panel_retry_attempt": dict(previous, version=True)}
    else:
        second = another_job(invoice)
        second.payload_snapshot = {"panel_retry_attempt": previous}
    invoice.db.commit()
    assert state.eligibility(invoice.db, invoice.job, invoice.document) == (False, None)


@pytest.mark.parametrize("change", [
    {"version": True}, {"version": 1.0}, {"sequence": True}, {"sequence": 2}, {"previous_attempt_id": str(uuid4())},
    {"job_id": "1"}, {"environment": "produccion"}, {"xml_sha256": "b" * 64},
    {"provider_company_id": "78"}, {"provider_document_id": 444951}, {"id": "non-uuid"},
    {"started_at": "not-a-date"}, {"started_at": "2026-10-05T08:00:00+00:00"}, {"extra": "unrecognized"},
])
def test_invalid_start_cannot_become_valid_by_matching_completion(invoice, change):
    valid_start = start_marker(invoice)
    start = dict(valid_start, **change)
    completed = dict(completed_marker(valid_start), **change)
    write_audit(invoice, state.START_ACTION, start)
    write_audit(invoice, state.COMPLETION_ACTION, completed)
    save_current(invoice, completed)
    assert state.eligibility(invoice.db, invoice.job, invoice.document) == (False, None)


@pytest.mark.parametrize("change", [
    {"completed_at": "2026-10-05T09:00:00"}, {"next_retry_at": "2026-10-05T11:59:59"},
    {"state": "response_received"}, {"state": "ambiguous"}, {"extra": "unrecognized"},
    {"outcome": {"source": "panel_listing", "response_sha256": "a" * 64, "message": "HTTP 503"}},
    {"outcome": {"source": "retry_response", "response_sha256": "bad", "message": "HTTP 503"}},
    {"outcome": {"source": "retry_response", "response_sha256": "a" * 64, "message": "Timeout"}},
    {"outcome": {"source": "retry_response", "response_sha256": "a" * 64, "message": "HTTP 503 but processing"}},
    {"outcome": {"source": "retry_response", "response_sha256": "a" * 64, "message": "HTTP 503", "ticket": "123"}},
])
def test_invalid_completion_is_rejected_even_if_all_copies_match(invoice, change):
    start = start_marker(invoice)
    completed = dict(completed_marker(start), **change)
    write_audit(invoice, state.START_ACTION, start)
    write_audit(invoice, state.COMPLETION_ACTION, completed)
    save_current(invoice, completed)
    assert state.eligibility(invoice.db, invoice.job, invoice.document) == (False, None)


@pytest.mark.parametrize("damage", ["predecessor", "sequence", "duplicate_id", "different_provider_id", "too_early"])
def test_second_attempt_requires_contiguous_identity_and_wait(invoice, damage):
    _, previous = completed_attempt(invoice)
    start = start_marker(invoice, previous)
    if damage == "predecessor":
        start["previous_attempt_id"] = str(uuid4())
    elif damage == "sequence":
        start["sequence"] = 3
    elif damage == "duplicate_id":
        start["id"] = previous["id"]
    elif damage == "different_provider_id":
        start["provider_document_id"] = "777"
    else:
        start["started_at"] = previous["completed_at"]
    completed = completed_marker(start)
    write_audit(invoice, state.START_ACTION, start)
    write_audit(invoice, state.COMPLETION_ACTION, completed)
    save_current(invoice, completed)
    assert state.eligibility(invoice.db, invoice.job, invoice.document) == (False, None)


@pytest.mark.parametrize("change", ["foreign_job", "xml", "tenant_company", "tenant_environment", "malformed_other_snapshot"])
def test_current_scope_and_original_xml_must_still_match(invoice, change):
    completed_attempt(invoice)
    job = invoice.job
    if change == "foreign_job":
        job = SimpleNamespace(tenant_id=999, resource_id=invoice.document.id, resource_type="cotizacion", provider="smartpse")
    elif change == "xml":
        invoice.document.sunat_xml_content += "changed"
    elif change == "tenant_company":
        invoice.tenant.smartpse_company_id = "78"
    elif change == "tenant_environment":
        invoice.tenant.smartpse_environment = "produccion"
    else:
        second = another_job(invoice)
        second.payload_snapshot = ["malformed"]
    invoice.db.commit()
    assert state.eligibility(invoice.db, job, invoice.document) == (False, None)


def test_changed_snapshot_from_another_session_is_not_hidden_by_orm_cache(invoice):
    completed_attempt(invoice)
    assert state.eligibility(invoice.db, invoice.job, invoice.document)[0]
    with Session(invoice.db.bind) as other:
        other_job = other.get(models.DocumentEmissionJob, invoice.job.id)
        other_job.payload_snapshot = {}
        other.commit()
    assert "panel_retry_attempt" in invoice.job.payload_snapshot  # Deliberately stale ORM object.
    assert state.eligibility(invoice.db, invoice.job, invoice.document) == (False, None)
