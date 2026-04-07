from typing import Any, Optional

from config import settings


def get_company_tenant(user: Any):
    return getattr(user, "tenant", None)


def get_company_ruc(user: Any) -> Optional[str]:
    tenant = get_company_tenant(user)
    # TODO LEGACY: eliminar fallback a User.business_ruc cuando Tenant sea la única fuente.
    return getattr(tenant, "business_ruc", None) or getattr(user, "business_ruc", None)


def get_company_name(user: Any) -> Optional[str]:
    tenant = get_company_tenant(user)
    # TODO LEGACY: eliminar fallback a User.business_name cuando Tenant sea la única fuente.
    return getattr(tenant, "business_name", None) or getattr(user, "business_name", None)


def get_company_address(user: Any) -> Optional[str]:
    tenant = get_company_tenant(user)
    # TODO LEGACY: eliminar fallback a User.business_address cuando Tenant sea la única fuente.
    return getattr(tenant, "business_address", None) or getattr(user, "business_address", None)


def get_company_bank_accounts(user: Any):
    tenant = get_company_tenant(user)
    # TODO LEGACY: eliminar fallback a User.bank_accounts cuando Tenant sea la única fuente.
    return getattr(tenant, "bank_accounts", None) or getattr(user, "bank_accounts", None) or []


def get_apisperu_token(user: Any, *, include_global_fallback: bool = True) -> Optional[str]:
    tenant = get_company_tenant(user)
    token = getattr(tenant, "apisperu_token", None)
    if token:
        return token

    # TODO LEGACY: eliminar fallback a User.apisperu_token cuando Tenant sea la única fuente.
    token = getattr(user, "apisperu_token", None)
    if token:
        return token

    if include_global_fallback:
        return settings.API_TOKEN or None

    return None


def get_document_lookup_token(user: Any) -> Optional[str]:
    token = get_apisperu_token(user, include_global_fallback=False)
    if token:
        return token
    return settings.DNIRUC_TOKEN or None
