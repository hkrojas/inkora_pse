import pytest

from seed_demo_tenant import validate_demo_seed_target


def test_demo_seed_accepts_only_local_sqlite_with_explicit_password():
    validate_demo_seed_target(
        "test",
        "sqlite:///C:/temp/inkora_e2e.db",
        "synthetic-password-123",
    )


@pytest.mark.parametrize("environment", ["production", "prod", "staging"])
def test_demo_seed_rejects_non_local_environments(environment):
    with pytest.raises(RuntimeError, match="entorno local o test"):
        validate_demo_seed_target(
            environment,
            "sqlite:///C:/temp/inkora_e2e.db",
            "synthetic-password-123",
        )


def test_demo_seed_rejects_non_sqlite_databases():
    with pytest.raises(RuntimeError, match="solo admite una base SQLite"):
        validate_demo_seed_target(
            "test",
            "postgresql://localhost/inkora_e2e",
            "synthetic-password-123",
        )


def test_demo_seed_rejects_missing_or_weak_passwords():
    with pytest.raises(RuntimeError, match="al menos 12 caracteres"):
        validate_demo_seed_target("test", "sqlite:///test.db", "demo1234")
