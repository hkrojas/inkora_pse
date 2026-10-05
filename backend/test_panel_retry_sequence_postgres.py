"""Real PostgreSQL serialization of a confirmed panel attempt's successor."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta
import threading

import pytest

import models
from services import emission_leases as leases
from services import emission_queue_service as queue
from test_panel_retry_postgres import factory, clear_jobs, prepare, sign_xml  # noqa: F401
from test_panel_retry_sequence import confirmed_failure


def reserve_and_complete(factory, data):
    reservation = data["jobs"][0]
    receipt = {}
    with factory() as db:
        leases.attach(db, *reservation)
        try:
            assert queue._reserve_panel_retry_attempt(db, reservation[0], data["user_id"],
                data["xml"], data["metadata"], receipt=receipt) is True
            assert receipt and not db.in_transaction()
            completed = queue._complete_panel_retry_attempt(
                db, reservation[0], receipt, confirmed_failure())
            assert completed and not db.in_transaction()
            return receipt, completed
        finally:
            db.rollback()
            leases.detach(db)


def advance_past_cooldown(factory, data, completed, monkeypatch):
    clock = datetime.fromisoformat(completed["next_retry_at"]) + timedelta(seconds=1)
    with factory() as db:
        for job_id, _ in data["jobs"]:
            db.get(models.DocumentEmissionJob, job_id).lease_expires_at = clock + timedelta(minutes=3)
        db.commit()
    monkeypatch.setattr(leases, "db_now", lambda db: clock)


def test_two_jobs_race_for_exactly_one_successor(factory, sign_xml, monkeypatch):
    data = prepare(factory, sign_xml, monkeypatch)
    _, completed = reserve_and_complete(factory, data)
    advance_past_cooldown(factory, data, completed, monkeypatch)
    start = threading.Barrier(2)

    def authorize(reservation):
        receipt = {}
        with factory() as db:
            leases.attach(db, *reservation)
            try:
                start.wait(timeout=10)
                allowed = queue._reserve_panel_retry_attempt(db, reservation[0], data["user_id"],
                    data["xml"], data["metadata"], expected_previous_id=completed["id"], receipt=receipt)
                assert not db.in_transaction()
                assert bool(receipt) == allowed
                return allowed, receipt
            finally:
                db.rollback()
                leases.detach(db)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(authorize, data["jobs"]))
    assert sorted(allowed for allowed, _ in outcomes) == [False, True]
    successor = next(receipt for allowed, receipt in outcomes if allowed)
    assert successor["sequence"] == 2 and successor["previous_attempt_id"] == completed["id"]
    with factory() as db:
        document = db.get(models.Cotizacion, data["document_id"])
        assert document.provider_response["inkora_evidence"]["panel_retry_attempt"] == successor
        assert document.sunat_xml_content == data["xml"] and not document.sunat_cdr_content
        assert db.query(models.AuditLog).filter_by(action="fiscal_panel_retry_started",
            entity_type="cotizacion", entity_id=document.id).count() == 2
        assert db.query(models.AuditLog).filter_by(action="fiscal_panel_retry_completed",
            entity_type="cotizacion", entity_id=document.id).count() == 1


def test_late_prior_response_cannot_overwrite_successor(factory, sign_xml, monkeypatch):
    data = prepare(factory, sign_xml, monkeypatch, jobs=1)
    old_receipt, completed = reserve_and_complete(factory, data)
    advance_past_cooldown(factory, data, completed, monkeypatch)
    reservation = data["jobs"][0]
    successor = {}
    with factory() as db:
        leases.attach(db, *reservation)
        try:
            assert queue._reserve_panel_retry_attempt(db, reservation[0], data["user_id"],
                data["xml"], data["metadata"], expected_previous_id=completed["id"], receipt=successor)
            assert not db.in_transaction()
            original_successor = deepcopy(successor)
            assert queue._complete_panel_retry_attempt(
                db, reservation[0], old_receipt, confirmed_failure()) is None
            db.rollback()
        finally:
            leases.detach(db)
    with factory() as db:
        assert db.get(models.DocumentEmissionJob, reservation[0]).payload_snapshot["panel_retry_attempt"] == original_successor
        document = db.get(models.Cotizacion, data["document_id"])
        assert document.provider_response["inkora_evidence"]["panel_retry_attempt"] == original_successor
        assert db.query(models.AuditLog).filter_by(action="fiscal_panel_retry_completed",
            entity_type="cotizacion", entity_id=document.id).count() == 1


def test_expired_lease_cannot_complete_confirmed_response(factory, sign_xml, monkeypatch):
    data = prepare(factory, sign_xml, monkeypatch, jobs=1)
    reservation = data["jobs"][0]
    receipt = {}
    with factory() as db:
        leases.attach(db, *reservation)
        try:
            assert queue._reserve_panel_retry_attempt(db, reservation[0], data["user_id"],
                data["xml"], data["metadata"], receipt=receipt)
            assert not db.in_transaction()
            # Expire the durable lease from another session while HTTP is in flight.
            with factory() as other:
                other.get(models.DocumentEmissionJob, reservation[0]).lease_expires_at = datetime.now() - timedelta(seconds=1)
                other.commit()
            with pytest.raises(leases.LeaseLost):
                queue._complete_panel_retry_attempt(db, reservation[0], receipt, confirmed_failure())
            db.rollback()
        finally:
            leases.detach(db)
    with factory() as db:
        assert db.get(models.DocumentEmissionJob, reservation[0]).payload_snapshot["panel_retry_attempt"] == receipt
        document = db.get(models.Cotizacion, data["document_id"])
        assert document.provider_response["inkora_evidence"]["panel_retry_attempt"] == receipt
        assert db.query(models.AuditLog).filter_by(action="fiscal_panel_retry_completed",
            entity_type="cotizacion", entity_id=document.id).count() == 0
