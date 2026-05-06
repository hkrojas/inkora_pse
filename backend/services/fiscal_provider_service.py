from config import settings
from services import beta_feature_flags


DIRECT_SUNAT_CREDENTIAL_FIELDS = (
    "sunat_usuario_sol",
    "sunat_clave_sol",
    "sunat_cert_password",
    "sunat_cert_url",
)
SMARTPSE_CREDENTIAL_FIELDS = (
    "smartpse_usuario_secundaria",
    "smartpse_token_acceso",
)
SMARTPSE_GRE_CREDENTIAL_FIELDS = (
    "smartpse_gre_sol_username",
    "smartpse_gre_sol_password_enc",
    "smartpse_gre_client_id",
    "smartpse_gre_client_secret_enc",
)


def has_any_direct_sunat_credentials(tenant) -> bool:
    return bool(
        tenant
        and any(getattr(tenant, field, None) for field in DIRECT_SUNAT_CREDENTIAL_FIELDS)
    )


def has_complete_direct_sunat_credentials(tenant) -> bool:
    return bool(
        tenant
        and all(getattr(tenant, field, None) for field in DIRECT_SUNAT_CREDENTIAL_FIELDS)
    )


def has_apisperu_credentials(tenant) -> bool:
    return bool(tenant and getattr(tenant, "apisperu_token", None))


def has_smartpse_credentials(tenant) -> bool:
    return bool(
        tenant
        and all(getattr(tenant, field, None) for field in SMARTPSE_CREDENTIAL_FIELDS)
    )


def has_smartpse_gre_credentials(tenant) -> bool:
    return bool(
        tenant
        and all(getattr(tenant, field, None) for field in SMARTPSE_GRE_CREDENTIAL_FIELDS)
    )


def smartpse_block_reason(tenant) -> str | None:
    if not tenant:
        return "Tenant no encontrado."
    missing = [
        field
        for field in SMARTPSE_CREDENTIAL_FIELDS
        if not getattr(tenant, field, None)
    ]
    if missing:
        return "faltan credenciales Smart PSE del tenant."
    return None


def smartpse_gre_block_reason(tenant) -> str | None:
    if not tenant:
        return "Tenant no encontrado."
    missing = [
        field
        for field in SMARTPSE_GRE_CREDENTIAL_FIELDS
        if not getattr(tenant, field, None)
    ]
    if missing:
        return "faltan credenciales SUNAT GRE para guias Smart PSE."
    return None


def can_use_direct_sunat(tenant) -> bool:
    return (
        settings.is_fiscal_production
        and has_complete_direct_sunat_credentials(tenant)
        and beta_feature_flags.is_feature_enabled_for_tenant(
            tenant,
            beta_feature_flags.FISCAL_FEATURE_DIRECT_SUNAT,
        )
    )


def direct_sunat_block_reason(tenant) -> str | None:
    if not tenant:
        return "Tenant no encontrado."
    if settings.is_fiscal_beta and has_any_direct_sunat_credentials(tenant):
        return "La emision SUNAT directa esta deshabilitada en FISCAL_ENV=beta."
    if has_any_direct_sunat_credentials(tenant) and not has_complete_direct_sunat_credentials(tenant):
        return "Faltan credenciales SUNAT directas del tenant."
    if (
        settings.is_fiscal_production
        and has_complete_direct_sunat_credentials(tenant)
        and not beta_feature_flags.is_feature_enabled_for_tenant(
            tenant,
            beta_feature_flags.FISCAL_FEATURE_DIRECT_SUNAT,
        )
    ):
        return "SUNAT directo esta restringido por feature flag fiscal del tenant."
    return None
