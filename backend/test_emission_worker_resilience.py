"""Tests de resiliencia del worker de emision."""

from sqlalchemy.exc import SQLAlchemyError

from services import emission_queue_service as worker


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


def test_worker_loop_retries_database_errors_without_crashing(monkeypatch):
    fake_db = _FakeDb()
    fake_shutdown = _FakeShutdownEvent()
    checks = {"count": 0}

    def should_shutdown():
        checks["count"] += 1
        return checks["count"] > 1

    def raise_database_error(db, *, stale_before):
        raise SQLAlchemyError("database pooler refused connection")

    monkeypatch.setattr(worker, "_install_signal_handlers", lambda: None)
    monkeypatch.setattr(worker, "is_shutdown_requested", should_shutdown)
    monkeypatch.setattr(worker, "_shutdown_requested", fake_shutdown)
    monkeypatch.setattr(worker, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(worker.crud, "recover_stale_processing_jobs", raise_database_error)

    worker.run_worker_loop()

    assert fake_db.rolled_back is True
    assert fake_db.closed is True
    assert fake_shutdown.wait_calls == 1
