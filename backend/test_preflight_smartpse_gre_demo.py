from __future__ import annotations

import json

from preflight_smartpse_gre_demo import (
    REQUIRED_GUIDE_COLUMNS,
    REQUIRED_GUIDE_TABLES,
    evaluate_preflight,
)


def _tenant(**overrides):
    data = {
        "id": 5,
        "business_name": "PAPELERIA DEMO SAC",
        "business_ruc": "20606751509",
        "smartpse_environment": "demo",
        "smartpse_usuario_secundaria": "CPE-USER-SECRET",
        "smartpse_token_acceso": "CPE-TOKEN-SECRET",
        "smartpse_gre_sol_username": None,
        "smartpse_gre_sol_password_enc": None,
        "smartpse_gre_client_id": None,
        "smartpse_gre_client_secret_enc": None,
    }
    data.update(overrides)
    return data


def _report(tenant=None, **overrides):
    params = {
        "table_names": set(REQUIRED_GUIDE_TABLES),
        "guide_columns": set(REQUIRED_GUIDE_COLUMNS),
        "alembic_versions": ["0021_sale_dispatch_guides"],
        "runtime_environment": "development",
        "fiscal_environment": "beta",
        "smartpse_base_url": "https://panel.smartpse.pe",
        "has_management_token": True,
    }
    params.update(overrides)
    return evaluate_preflight(tenant or _tenant(), **params)


def test_demo_preflight_is_green_without_optional_gre_credentials():
    report = _report()

    assert report["ready_for_demo_homologation"] is True
    assert report["provider_calls_performed"] is False
    assert report["database_writes_performed"] is False
    assert report["tenant"]["has_cpe_credentials"] is True
    assert report["tenant"]["has_complete_gre_credentials"] is False
    assert report["warnings"]


def test_production_tenant_is_blocked_and_secrets_are_redacted():
    report = _report(
        _tenant(
            smartpse_environment="produccion",
            smartpse_gre_sol_username="SOL-SECRET",
            smartpse_gre_sol_password_enc="PASSWORD-SECRET",
            smartpse_gre_client_id="CLIENT-ID-SECRET",
            smartpse_gre_client_secret_enc="CLIENT-SECRET",
        )
    )
    serialized = json.dumps(report)

    assert report["ready_for_demo_homologation"] is False
    assert any("exactamente" in blocker for blocker in report["blockers"])
    for secret in (
        "CPE-USER-SECRET",
        "CPE-TOKEN-SECRET",
        "SOL-SECRET",
        "PASSWORD-SECRET",
        "CLIENT-ID-SECRET",
        "CLIENT-SECRET",
        "20606751509",
    ):
        assert secret not in serialized


def test_incomplete_0021_schema_is_blocked():
    report = _report(
        table_names={"guias_remision"},
        guide_columns={"tipo_documento"},
        alembic_versions=["0018_access_requests"],
    )

    assert report["ready_for_demo_homologation"] is False
    assert any("0021 incompleto" in blocker for blocker in report["blockers"])


def test_production_runtime_or_unknown_host_is_blocked():
    report = _report(
        runtime_environment="production",
        fiscal_environment="production",
        smartpse_base_url="https://example.invalid",
    )

    assert report["ready_for_demo_homologation"] is False
    assert len(report["blockers"]) >= 3


def test_missing_cpe_credentials_is_blocked():
    report = _report(_tenant(smartpse_token_acceso=None))

    assert report["ready_for_demo_homologation"] is False
    assert any("credenciales CPE" in blocker for blocker in report["blockers"])
