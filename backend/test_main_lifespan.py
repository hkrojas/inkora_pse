import pytest
from fastapi.testclient import TestClient

import main


class _SessionContext:
    def __init__(self, *, error=None):
        self.error = error
        self.queries = []

    def __enter__(self):
        if self.error is not None:
            raise self.error
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, query):
        self.queries.append(str(query))


def test_lifespan_pings_database_before_serving(monkeypatch):
    session = _SessionContext()
    monkeypatch.setattr(main, "SessionLocal", lambda: session)

    with TestClient(main.create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert session.queries == ["SELECT 1"]


def test_lifespan_fails_fast_when_database_is_unreachable(monkeypatch):
    session = _SessionContext(error=OSError("database unavailable"))
    monkeypatch.setattr(main, "SessionLocal", lambda: session)

    with pytest.raises(RuntimeError, match="No se pudo conectar a la base de datos"):
        with TestClient(main.create_app()):
            pass
