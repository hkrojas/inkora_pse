from typing import Any, Optional

from config import settings


def get_company_tenant(user: Any):
    return getattr(user, "tenant", None)


def get_company_ruc(user: Any) -> Optional[str]:
    tenant = get_company_tenant(user)
    return getattr(tenant, "business_ruc", None)


def get_company_name(user: Any) -> Optional[str]:
    tenant = get_company_tenant(user)
    return getattr(tenant, "business_name", None)


def get_company_address(user: Any) -> Optional[str]:
    tenant = get_company_tenant(user)
    return getattr(tenant, "business_address", None)


def get_company_bank_accounts(user: Any):
    tenant = get_company_tenant(user)
    return getattr(tenant, "bank_accounts", None) or []


def get_apisperu_token(user: Any, *, include_global_fallback: bool = False) -> Optional[str]:
    tenant = get_company_tenant(user)
    token = getattr(tenant, "apisperu_token", None)
    if token:
        return token

    if include_global_fallback:
        return settings.API_TOKEN or None

    return None


def get_document_lookup_token(user: Any) -> Optional[str]:
    if settings.DNIRUC_TOKEN:
        return settings.DNIRUC_TOKEN
    token = get_apisperu_token(user, include_global_fallback=False)
    if token:
        return token
    return settings.API_TOKEN or None
