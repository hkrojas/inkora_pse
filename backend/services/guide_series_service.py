"""Authoritative environment, series and correlativo rules for GRE documents."""
from __future__ import annotations

import re

from sqlalchemy import func
from sqlalchemy.orm import Session

import models


DEMO_SERIES = {"09": "T999", "31": "V999"}
PRODUCTION_SERIES_FIELDS = {
    "09": ("fiscal_gre_remitente_series", "fiscal_gre_remitente_series_floor", "T"),
    "31": ("fiscal_gre_transportista_series", "fiscal_gre_transportista_series_floor", "V"),
}
SERIES_RE = re.compile(r"^[A-Z0-9]{4}$")


class GuideSeriesConfigurationError(ValueError):
    def __init__(self, message: str, *, code: str):
        super().__init__(message)
        self.code = code


def guide_environment(tenant) -> str:
    value = str(getattr(tenant, "smartpse_environment", "") or "").strip().lower()
    if value in {"produccion", "production", "prod"}:
        return "production"
    if value == "demo":
        return "demo"
    raise GuideSeriesConfigurationError(
        "La empresa no tiene un ambiente válido para numerar la guía.",
        code="GUIDE_ENVIRONMENT_REQUIRED",
    )


def guide_series(tenant, document_type: str) -> tuple[str, str]:
    environment = guide_environment(tenant)
    if document_type not in PRODUCTION_SERIES_FIELDS:
        raise GuideSeriesConfigurationError(
            "Tipo de GRE no soportado para asignar serie.",
            code="GUIDE_TYPE_UNSUPPORTED",
        )
    if environment == "demo":
        return environment, DEMO_SERIES[document_type]

    series_field, _, prefix = PRODUCTION_SERIES_FIELDS[document_type]
    series = str(getattr(tenant, series_field, "") or "").strip().upper()
    if not SERIES_RE.fullmatch(series) or not series.startswith(prefix):
        label = "GRE remitente" if document_type == "09" else "GRE transportista"
        raise GuideSeriesConfigurationError(
            f"Configura la serie productiva de {label} antes de crear la guía.",
            code="GUIDE_PRODUCTION_SERIES_REQUIRED",
        )
    return environment, series


def next_guide_correlativo(
    db: Session,
    tenant_id: int,
    document_type: str,
    series: str,
) -> int:
    """Return the next safe number while serializing changes through Tenant.

    The configured floor represents the last number already used externally.
    Existing Inkora documents always win when their maximum is higher.
    """
    tenant = (
        db.query(models.Tenant)
        .filter(models.Tenant.id == tenant_id)
        .with_for_update()
        .first()
    )
    if not tenant or not tenant.is_active:
        raise GuideSeriesConfigurationError(
            "La empresa no está activa para crear guías.",
            code="TENANT_INACTIVE",
        )
    environment, expected_series = guide_series(tenant, document_type)
    if series != expected_series:
        raise GuideSeriesConfigurationError(
            "La serie de la guía ya no coincide con la configuración vigente.",
            code="GUIDE_ENVIRONMENT_CHANGED",
        )

    internal_max = db.query(func.max(models.GuiaRemision.correlativo)).filter(
        models.GuiaRemision.tenant_id == tenant_id,
        models.GuiaRemision.serie == series,
    ).scalar()
    floor = 0
    if environment == "production":
        _, floor_field, _ = PRODUCTION_SERIES_FIELDS[document_type]
        floor = int(getattr(tenant, floor_field, 0) or 0)
    return max(int(internal_max or 0), floor) + 1
