"""Feature flags fiscales por tenant para la beta pagada controlada."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

import models


FISCAL_FEATURE_CREDIT_NOTES = "credit_notes"
FISCAL_FEATURE_DEBIT_NOTES = "debit_notes"
FISCAL_FEATURE_GUIDES = "guides"
FISCAL_FEATURE_DAILY_SUMMARY = "daily_summary"
FISCAL_FEATURE_VOIDING = "voiding"
FISCAL_FEATURE_REVERSIONS = "reversions"
FISCAL_FEATURE_RETENTIONS = "retentions"
FISCAL_FEATURE_PERCEPTIONS = "perceptions"
FISCAL_FEATURE_DIRECT_SUNAT = "direct_sunat"


@dataclass(frozen=True)
class FiscalFeatureDefinition:
    key: str
    label: str
    category: str
    default_enabled: bool
    control: str


FISCAL_FEATURE_DEFINITIONS: tuple[FiscalFeatureDefinition, ...] = (
    FiscalFeatureDefinition(
        key=FISCAL_FEATURE_CREDIT_NOTES,
        label="Notas de credito",
        category="notas",
        default_enabled=False,
        control="Feature flag por tenant + limite acumulado",
    ),
    FiscalFeatureDefinition(
        key=FISCAL_FEATURE_DEBIT_NOTES,
        label="Notas de debito",
        category="notas",
        default_enabled=False,
        control="Feature flag por tenant",
    ),
    FiscalFeatureDefinition(
        key=FISCAL_FEATURE_GUIDES,
        label="Guias de remision",
        category="guias",
        default_enabled=False,
        control="Feature flag por tenant + datos logisticos completos",
    ),
    FiscalFeatureDefinition(
        key=FISCAL_FEATURE_DAILY_SUMMARY,
        label="Resumen diario",
        category="boletas",
        default_enabled=False,
        control="Feature flag por tenant + soporte inicial",
    ),
    FiscalFeatureDefinition(
        key=FISCAL_FEATURE_VOIDING,
        label="Bajas",
        category="operaciones_sensibles",
        default_enabled=False,
        control="Confirmacion soporte/superadmin",
    ),
    FiscalFeatureDefinition(
        key=FISCAL_FEATURE_REVERSIONS,
        label="Reversiones",
        category="operaciones_sensibles",
        default_enabled=False,
        control="Confirmacion soporte/superadmin",
    ),
    FiscalFeatureDefinition(
        key=FISCAL_FEATURE_RETENTIONS,
        label="Retenciones",
        category="documentos_especializados",
        default_enabled=False,
        control="Soporte/superadmin inicial",
    ),
    FiscalFeatureDefinition(
        key=FISCAL_FEATURE_PERCEPTIONS,
        label="Percepciones",
        category="documentos_especializados",
        default_enabled=False,
        control="Soporte/superadmin inicial",
    ),
    FiscalFeatureDefinition(
        key=FISCAL_FEATURE_DIRECT_SUNAT,
        label="SUNAT directo",
        category="proveedor",
        default_enabled=False,
        control="Solo soporte/lab controlado",
    ),
)

FISCAL_FEATURE_KEYS = {definition.key for definition in FISCAL_FEATURE_DEFINITIONS}
DEFAULT_FISCAL_FEATURE_FLAGS = {
    definition.key: definition.default_enabled
    for definition in FISCAL_FEATURE_DEFINITIONS
}


def feature_definitions_payload() -> list[dict[str, Any]]:
    return [
        {
            "key": definition.key,
            "label": definition.label,
            "category": definition.category,
            "default_enabled": definition.default_enabled,
            "control": definition.control,
        }
        for definition in FISCAL_FEATURE_DEFINITIONS
    ]


def normalize_fiscal_feature_flags(raw_flags: Any) -> dict[str, bool]:
    """Devuelve todos los flags conocidos, aplicando defaults seguros."""
    flags = dict(DEFAULT_FISCAL_FEATURE_FLAGS)
    if isinstance(raw_flags, dict):
        for key, value in raw_flags.items():
            if key in FISCAL_FEATURE_KEYS:
                flags[key] = bool(value)
    return flags


def validate_fiscal_feature_flags(raw_flags: Any) -> dict[str, bool]:
    if not isinstance(raw_flags, dict):
        raise ValueError("Los flags fiscales deben enviarse como objeto JSON.")

    unknown_keys = sorted(set(raw_flags) - FISCAL_FEATURE_KEYS)
    if unknown_keys:
        raise ValueError(
            "Flags fiscales no soportados: " + ", ".join(unknown_keys)
        )
    return normalize_fiscal_feature_flags(raw_flags)


def subscription_feature_flags(subscription: models.Subscription | None) -> dict[str, bool]:
    return normalize_fiscal_feature_flags(
        getattr(subscription, "beta_feature_flags", None) if subscription else None
    )


def is_feature_enabled_for_subscription(
    subscription: models.Subscription | None,
    feature_key: str,
) -> bool:
    if feature_key not in FISCAL_FEATURE_KEYS:
        return False
    return subscription_feature_flags(subscription).get(feature_key, False)


def is_feature_enabled_for_tenant(tenant: models.Tenant | None, feature_key: str) -> bool:
    if not tenant:
        return False
    return is_feature_enabled_for_subscription(getattr(tenant, "subscription", None), feature_key)


def require_fiscal_feature_enabled(
    db: Session,
    tenant_id: int,
    feature_key: str,
    *,
    current_user: models.User | None = None,
) -> None:
    """Bloquea operaciones fiscales beta-controladas si el flag no esta activo."""
    if current_user and getattr(current_user, "is_superadmin", False):
        return

    subscription = (
        db.query(models.Subscription)
        .filter(models.Subscription.tenant_id == tenant_id)
        .first()
    )
    if is_feature_enabled_for_subscription(subscription, feature_key):
        return

    raise HTTPException(
        status_code=403,
        detail={
            "code": "FISCAL_FEATURE_DISABLED",
            "message": (
                "Funcion fiscal disponible en beta controlada. "
                "Solicita activacion a soporte Inkora."
            ),
            "feature": feature_key,
            "contact": "contacto@inkora.pe",
        },
    )


def feature_for_note_type(tipo_nota: str | None) -> str:
    normalized = str(tipo_nota or "").strip().lower()
    if normalized in {"credito", "credit", "nc", "07"}:
        return FISCAL_FEATURE_CREDIT_NOTES
    if normalized in {"debito", "debit", "nd", "08"}:
        return FISCAL_FEATURE_DEBIT_NOTES
    raise ValueError("Tipo de nota fiscal no soportado para feature flags.")
