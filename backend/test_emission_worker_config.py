from config import Settings
import pytest
from services.emission_worker_runtime import WakeSignal, listener_options


def test_emission_worker_defaults_preserve_low_latency_and_limit_stale_recovery():
    settings = Settings(
        ENVIRONMENT="test",
        DATABASE_URL="sqlite:///worker-config-test.db",
        SECRET_KEY="worker-config-test-secret",
    )

    assert settings.EMISSION_WORKER_POLL_SECONDS == 3
    assert settings.EMISSION_STALE_RECOVERY_INTERVAL_SECONDS == 60
    assert settings.EMISSION_WORKER_WAKE_MODE == "poll"
    assert settings.EMISSION_GLOBAL_CONCURRENCY == settings.EMISSION_TENANT_CONCURRENCY == 1


@pytest.mark.parametrize("overrides", [
    {"EMISSION_WORKER_WAKE_MODE": "realtime"}, {"EMISSION_EVENT_TENANT_IDS": "1,-2"},
    {"EMISSION_EVENT_TENANT_IDS": "1,x"}, {"EMISSION_HEARTBEAT_SECONDS": 100},
    {"EMISSION_GLOBAL_CONCURRENCY": 0},
])
def test_invalid_worker_settings_fail_closed(overrides):
    with pytest.raises(ValueError):
        Settings(_env_file=None, DATABASE_URL="sqlite://", SECRET_KEY="test", **overrides)


@pytest.mark.parametrize("dsn", [
    "postgresql://postgres@db.example:6543/postgres", "postgresql://postgres@db.example:5432/postgres?sslmode=disable",
    "postgresql://postgres@db.example:5432/wrong_database", "",
])
def test_listener_rejects_unsafe_connection_modes(dsn):
    settings = Settings(_env_file=None, DATABASE_URL="postgresql://postgres@db.example/postgres",
                        SECRET_KEY="test", EMISSION_LISTEN_DATABASE_URL=dsn)
    with pytest.raises(ValueError):
        listener_options(settings)


def test_wakeup_during_scan_is_not_lost():
    import time
    wake = WakeSignal()
    generation = wake.snapshot()
    for _ in range(100):
        wake.pulse()
    start = time.monotonic()
    wake.wait(generation, 1)
    assert time.monotonic()-start < 0.1
