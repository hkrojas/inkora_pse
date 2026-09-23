"""Tests de resiliencia del worker de emision."""

from sqlalchemy.exc import SQLAlchemyError
import pytest

from services import emission_queue_service as worker
from services import emission_worker_runtime as runtime


class _FakeDb:
    def __init__(self):
        self.closed = False
        self.rolled_back = False

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class _FakeShutdownEvent:
    def __init__(self):
        self.wait_calls = 0

    def wait(self, timeout=None):
        self.wait_calls += 1
        return False


@pytest.mark.parametrize("broken_rollback", [False, True])
def test_worker_loop_retries_database_errors_without_crashing(monkeypatch, broken_rollback):
    fake_db = _FakeDb()
    fake_shutdown = _FakeShutdownEvent()
    if broken_rollback:
        def rollback():
            fake_db.rolled_back = True
            raise SQLAlchemyError("Connection also failed during rollback")
        fake_db.rollback = rollback
    checks = {"count": 0}

    def should_shutdown():
        checks["count"] += 1
        return checks["count"] > 1

    def raise_database_error(db, *, legacy_timeout):
        raise SQLAlchemyError("database pooler refused connection")

    monkeypatch.setattr(worker, "_install_signal_handlers", lambda: None)
    monkeypatch.setattr(worker, "is_shutdown_requested", should_shutdown)
    monkeypatch.setattr(worker, "_shutdown_requested", fake_shutdown)
    monkeypatch.setattr(worker, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(runtime.leases, "recover_coordinator", raise_database_error)

    def wait_after_close(self, generation, timeout):
        assert fake_db.closed, "Never hold the coordinator session while waiting"
        fake_shutdown.wait(timeout)
    monkeypatch.setattr(runtime.WakeSignal, "wait", wait_after_close)
    worker.run_worker_loop()

    assert fake_db.rolled_back is True
    assert fake_db.closed is True
    assert fake_shutdown.wait_calls == 1


def test_worker_loop_retries_when_session_creation_fails(monkeypatch):
    fake_shutdown = _FakeShutdownEvent()
    checks = {"count": 0}

    def should_shutdown():
        checks["count"] += 1
        return checks["count"] > 1

    def raise_database_error():
        raise SQLAlchemyError("database connection unavailable")

    monkeypatch.setattr(worker, "_install_signal_handlers", lambda: None)
    monkeypatch.setattr(worker, "is_shutdown_requested", should_shutdown)
    monkeypatch.setattr(worker, "_shutdown_requested", fake_shutdown)
    monkeypatch.setattr(worker, "SessionLocal", raise_database_error)

    monkeypatch.setattr(runtime.WakeSignal, "wait", lambda self, generation, timeout: fake_shutdown.wait(timeout))
    worker.run_worker_loop()

    assert fake_shutdown.wait_calls == 1
