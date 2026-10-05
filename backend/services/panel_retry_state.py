"""Validate durable panel retry history before reserving another attempt.

This module never writes, commits, acquires locks or calls a provider. The
reservation caller must hold the document lock and a valid execution lease.
Only a complete, consistent response-backed chain can permit another attempt.
"""
from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import json
import re
from uuid import UUID

import models
from services import emission_leases, fiscal_recovery_service, smartpse_panel_client


START_ACTION = "fiscal_panel_retry_started"
COMPLETION_ACTION = "fiscal_panel_retry_completed"
POSSIBLE_SUBMISSION = "possible_submission"
CONFIRMED_TRANSIENT_FAILURE = "confirmed_transient_failure"
START_KEYS = frozenset({"version", "id", "state", "sequence", "previous_attempt_id", "job_id",
    "started_at", "environment", "xml_sha256", "provider_company_id", "provider_document_id"})
COMPLETION_KEYS = START_KEYS | {"completed_at", "next_retry_at", "outcome"}


def _uuid(value):
    if not isinstance(value, str):
        return False
    try:
        return str(UUID(value)) == value
    except ValueError:
        return False


def _timestamp(value):
    if not isinstance(value, str) or "T" not in value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is None else None


def _digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _provider_id(value):
    return isinstance(value, str) and re.fullmatch(r"[1-9][0-9]{0,19}", value) is not None


def _valid_start(marker):
    return (isinstance(marker, dict) and set(marker) == START_KEYS
        and type(marker["version"]) is int and marker["version"] == 1
        and marker["state"] == POSSIBLE_SUBMISSION and _uuid(marker["id"])
        and type(marker["sequence"]) is int and marker["sequence"] > 0
        and (marker["previous_attempt_id"] is None or _uuid(marker["previous_attempt_id"]))
        and type(marker["job_id"]) is int and marker["job_id"] > 0
        and _timestamp(marker["started_at"]) is not None
        and marker["environment"] in ("demo", "produccion") and _digest(marker["xml_sha256"])
        and _provider_id(marker["provider_company_id"]) and _provider_id(marker["provider_document_id"]))


def _start_from_completion(marker):
    return {key: POSSIBLE_SUBMISSION if key == "state" else marker[key] for key in START_KEYS}


def _valid_completion(marker):
    if (not isinstance(marker, dict) or set(marker) != COMPLETION_KEYS
            or marker["state"] != CONFIRMED_TRANSIENT_FAILURE
            or not _valid_start(_start_from_completion(marker))):
        return False
    completed = _timestamp(marker["completed_at"])
    retry_at = _timestamp(marker["next_retry_at"])
    outcome = marker["outcome"]
    if (completed is None or retry_at is None or completed < _timestamp(marker["started_at"])
            or not isinstance(outcome, dict) or set(outcome) != {"source", "response_sha256", "message"}
            or outcome["source"] != "retry_response" or not _digest(outcome["response_sha256"])
            or not smartpse_panel_client.confirmed_transient_retry_error(outcome["message"])):
        return False
    try:
        return retry_at == completed + timedelta(seconds=fiscal_recovery_service.retry_seconds(marker["sequence"]))
    except OverflowError:
        return False


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Repeated JSON key")
        result[key] = value
    return result


def _audit_marker(details):
    if not isinstance(details, str) or len(details) > 16000:
        return None
    try:
        return json.loads(details, object_pairs_hook=_unique_object)
    except (ValueError, TypeError, RecursionError):
        return None


def eligibility(db, job, document):
    """Return (allowed, previous completed marker or None), without mutation.

    A new job may inherit the latest completed attempt from another job of the
    same invoice. Historical snapshots may retain either exact audited version;
    they cannot introduce, alter or erase an attempt that their job started.
    Legacy markers and incomplete attempts remain eligible for consultation only.
    """
    if (job.tenant_id != document.tenant_id or job.resource_id != document.id
            or job.resource_type != models.EMISSION_JOB_RESOURCE_COTIZACION or job.provider != "smartpse"):
        return False, None
    jobs = db.query(models.DocumentEmissionJob.id, models.DocumentEmissionJob.payload_snapshot).filter_by(tenant_id=job.tenant_id,
        resource_type=models.EMISSION_JOB_RESOURCE_COTIZACION, resource_id=document.id).all()
    scoped_jobs = {item.id: item.payload_snapshot for item in jobs}
    if job.id not in scoped_jobs or any(not isinstance(item.payload_snapshot, dict) for item in jobs):
        return False, None
    response = document.provider_response
    if response is None:
        response = {}
    if not isinstance(response, dict):
        return False, None
    evidence = response.get("inkora_evidence", {})
    if not isinstance(evidence, dict):
        return False, None
    audits = db.query(models.AuditLog.action, models.AuditLog.details).filter(models.AuditLog.entity_type == "cotizacion",
        models.AuditLog.entity_id == document.id,
        models.AuditLog.action.in_((START_ACTION, COMPLETION_ACTION))).order_by(models.AuditLog.id).all()
    snapshot_markers = {item.id: item.payload_snapshot["panel_retry_attempt"] for item in jobs
        if "panel_retry_attempt" in item.payload_snapshot}
    if not audits:
        return (False, None) if snapshot_markers or "panel_retry_attempt" in evidence else (True, None)

    tenant = db.query(models.Tenant.smartpse_environment, models.Tenant.smartpse_company_id).filter_by(id=job.tenant_id).first()
    xml = document.sunat_xml_content
    if not tenant or not isinstance(xml, str) or not xml:
        return False, None
    expected_identity = (tenant.smartpse_environment, str(tenant.smartpse_company_id or ""),
        hashlib.sha256(xml.encode("utf-8")).hexdigest())
    known = []
    started_jobs = set()
    last = pending = None
    provider_document_id = None
    for audit in audits:
        marker = _audit_marker(audit.details)
        if audit.action == START_ACTION:
            if pending is not None or not _valid_start(marker):
                return False, None
            if (marker["sequence"] != (last["sequence"] + 1 if last else 1)
                    or marker["previous_attempt_id"] != (last["id"] if last else None)
                    or marker["job_id"] not in scoped_jobs
                    or any(prior["id"] == marker["id"] for prior in known)
                    or (marker["environment"], marker["provider_company_id"], marker["xml_sha256"]) != expected_identity
                    or (last and _timestamp(marker["started_at"]) < _timestamp(last["next_retry_at"]))):
                return False, None
            if provider_document_id is None:
                provider_document_id = marker["provider_document_id"]
            elif provider_document_id != marker["provider_document_id"]:
                return False, None
            pending = marker
            known.append(marker)
            started_jobs.add(marker["job_id"])
        else:
            if (pending is None or not _valid_completion(marker)
                    or _start_from_completion(marker) != pending):
                return False, None
            last, pending = marker, None
            known.append(marker)
    if pending is not None or last is None or not _valid_completion(evidence.get("panel_retry_attempt")):
        return False, None
    if evidence["panel_retry_attempt"] != last or not started_jobs.issubset(snapshot_markers):
        return False, None
    for owner_id, marker in snapshot_markers.items():
        if (not (_valid_start(marker) or _valid_completion(marker))
                or marker["job_id"] != owner_id or not any(marker == prior for prior in known)):
            return False, None
    if emission_leases.db_now(db) < _timestamp(last["next_retry_at"]):
        return False, None
    return True, deepcopy(last)
