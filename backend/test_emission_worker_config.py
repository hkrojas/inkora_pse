from config import Settings


def test_emission_worker_defaults_preserve_low_latency_and_limit_stale_recovery():
    settings = Settings(
        ENVIRONMENT="test",
        DATABASE_URL="sqlite:///worker-config-test.db",
        SECRET_KEY="worker-config-test-secret",
    )

    assert settings.EMISSION_WORKER_POLL_SECONDS == 3
    assert settings.EMISSION_STALE_RECOVERY_INTERVAL_SECONDS == 60
