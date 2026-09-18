"""Read-only safety preflight for Smart PSE GRE demo homologation.

This command never calls Smart PSE and never mutates the database. It exists to
prove that the selected tenant and runtime cannot accidentally resolve to the
production endpoint before an operator performs a demo-only homologation.
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import inspect, text

from config import settings
from database import engine


REQUIRED_GUIDE_TABLES = {
    "guias_remision",
    "guide_external_references",
    "sale_dispatches",
    "sale_dispatch_lines",
}
REQUIRED_GUIDE_COLUMNS = {
    "tipo_documento",
    "dispatch_id",
    "external_gre_reference_id",
    "frozen_payload",
    "frozen_xml",
    "emission_environment",
}
TENANT_BASE_COLUMNS = (
    "id",
    "business_name",
    "business_ruc",
    "smartpse_environment",
    "smartpse_usuario_secundaria",
    "smartpse_token_acceso",
)
TENANT_GRE_COLUMNS = (
    "smartpse_gre_sol_username",
    "smartpse_gre_sol_password_enc",
    "smartpse_gre_client_id",
    "smartpse_gre_client_secret_enc",
)


def _present(value: Any) -> bool:
    return bool(str(value or "").strip())


def _masked_ruc(value: Any) -> str | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not digits:
        return None
    return "*" * max(0, len(digits) - 4) + digits[-4:]


def evaluate_preflight(
    tenant: Mapping[str, Any] | None,
    *,
    table_names: set[str],
    guide_columns: set[str],
    alembic_versions: list[str],
    runtime_environment: str,
    fiscal_environment: str,
    smartpse_base_url: str,
    has_management_token: bool,
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    checks: list[str] = []

    runtime = str(runtime_environment or "").strip().lower()
    fiscal = str(fiscal_environment or "").strip().lower()
    parsed_url = urlparse(str(smartpse_base_url or "").strip())

    if fiscal != "beta":
        blockers.append("El runtime debe usar FISCAL_ENV=beta para homologacion demo.")
    else:
        checks.append("Runtime fiscal beta confirmado.")

    if runtime in {"production", "prod"}:
        blockers.append("No se permite homologacion GRE demo desde un runtime de produccion.")
    else:
        checks.append(f"Runtime de aplicacion no productivo: {runtime or 'sin valor'}.")

    if parsed_url.scheme != "https" or parsed_url.hostname != "panel.smartpse.pe":
        blockers.append("SMARTPSE_BASE_URL no apunta al host HTTPS oficial esperado.")
    else:
        checks.append("Host Smart PSE oficial confirmado.")

    missing_tables = sorted(REQUIRED_GUIDE_TABLES - set(table_names))
    missing_columns = sorted(REQUIRED_GUIDE_COLUMNS - set(guide_columns))
    if missing_tables or missing_columns:
        detail = []
        if missing_tables:
            detail.append("tablas=" + ",".join(missing_tables))
        if missing_columns:
            detail.append("columnas_guias=" + ",".join(missing_columns))
        blockers.append("Esquema de guias 0021 incompleto: " + "; ".join(detail) + ".")
    else:
        checks.append("Esquema funcional de 0021 confirmado.")

    if tenant is None:
        blockers.append("No se encontro el tenant solicitado.")
        safe_tenant = None
    else:
        tenant_environment = str(tenant.get("smartpse_environment") or "").strip().lower()
        if tenant_environment != "demo":
            blockers.append(
                "El tenant debe estar configurado exactamente como smartpse_environment=demo."
            )
        else:
            checks.append("Tenant Smart PSE en demo confirmado.")

        has_cpe_credentials = all(
            _present(tenant.get(field))
            for field in ("smartpse_usuario_secundaria", "smartpse_token_acceso")
        )
        if not has_cpe_credentials:
            blockers.append("Faltan credenciales CPE Smart PSE del tenant.")
        else:
            checks.append("Credenciales CPE presentes.")

        has_gre_credentials = all(_present(tenant.get(field)) for field in TENANT_GRE_COLUMNS)
        if has_gre_credentials:
            checks.append("Las cuatro credenciales OAuth/SOL GRE estan presentes.")
        else:
            warnings.append(
                "Las credenciales OAuth/SOL GRE no estan completas; Smart PSE las declara "
                "opcionales en demo, pero la consulta final debe verificarse con evidencia."
            )

        safe_tenant = {
            "id": tenant.get("id"),
            "business_name": tenant.get("business_name"),
            "business_ruc_masked": _masked_ruc(tenant.get("business_ruc")),
            "smartpse_environment": tenant_environment or None,
            "has_cpe_credentials": has_cpe_credentials,
            "has_complete_gre_credentials": has_gre_credentials,
        }

    if not has_management_token:
        warnings.append(
            "SMARTPSE_API_TOKEN no esta configurado; no se podra contrastar la empresa "
            "contra la API de gestion desde este runtime."
        )

    return {
        "ready_for_demo_homologation": not blockers,
        "provider_calls_performed": False,
        "database_writes_performed": False,
        "tenant": safe_tenant,
        "alembic_versions": list(alembic_versions),
        "checks": checks,
        "warnings": warnings,
        "blockers": blockers,
    }


def _load_database_snapshot(*, tenant_id: int | None, ruc: str | None) -> dict[str, Any]:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    tenant_columns = {column["name"] for column in inspector.get_columns("tenants")}
    available_columns = [
        column
        for column in (*TENANT_BASE_COLUMNS, *TENANT_GRE_COLUMNS)
        if column in tenant_columns
    ]
    missing_base = sorted(set(TENANT_BASE_COLUMNS) - tenant_columns)
    if missing_base:
        return {
            "tenant": None,
            "table_names": table_names,
            "guide_columns": set(),
            "alembic_versions": [],
            "schema_error": "Faltan columnas base de tenant: " + ",".join(missing_base),
        }

    where_clause = "id = :value" if tenant_id is not None else "business_ruc = :value"
    lookup_value: Any = tenant_id if tenant_id is not None else str(ruc or "").strip()
    selected = ", ".join(f'"{column}"' for column in available_columns)
    with engine.connect() as connection:
        tenant = connection.execute(
            text(f"SELECT {selected} FROM tenants WHERE {where_clause} LIMIT 1"),
            {"value": lookup_value},
        ).mappings().first()
        alembic_versions = []
        if "alembic_version" in table_names:
            alembic_versions = list(
                connection.execute(text("SELECT version_num FROM alembic_version")).scalars()
            )

    guide_columns = (
        {column["name"] for column in inspector.get_columns("guias_remision")}
        if "guias_remision" in table_names
        else set()
    )
    return {
        "tenant": dict(tenant) if tenant else None,
        "table_names": table_names,
        "guide_columns": guide_columns,
        "alembic_versions": alembic_versions,
        "schema_error": None,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preflight read-only para homologacion Smart PSE GRE exclusivamente demo."
    )
    tenant = parser.add_mutually_exclusive_group(required=True)
    tenant.add_argument("--tenant-id", type=int)
    tenant.add_argument("--ruc")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    snapshot = _load_database_snapshot(tenant_id=args.tenant_id, ruc=args.ruc)
    report = evaluate_preflight(
        snapshot["tenant"],
        table_names=snapshot["table_names"],
        guide_columns=snapshot["guide_columns"],
        alembic_versions=snapshot["alembic_versions"],
        runtime_environment=settings.ENVIRONMENT,
        fiscal_environment=settings.FISCAL_ENV,
        smartpse_base_url=settings.SMARTPSE_BASE_URL,
        has_management_token=_present(settings.SMARTPSE_API_TOKEN),
    )
    if snapshot["schema_error"]:
        report["blockers"].append(snapshot["schema_error"])
        report["ready_for_demo_homologation"] = False
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if report["ready_for_demo_homologation"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
