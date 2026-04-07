from collections.abc import Iterable
from typing import Any

from fastapi import HTTPException, status

ROLE_SUPERADMIN = "superadmin"
ROLE_ADMIN = "admin"
ROLE_OPERADOR = "operador"
ROLE_VENDEDOR = "vendedor"

ALLOWED_ROLES = {
    ROLE_SUPERADMIN,
    ROLE_ADMIN,
    ROLE_OPERADOR,
    ROLE_VENDEDOR,
}
ELEVATED_TENANT_ROLES = {
    ROLE_SUPERADMIN,
    ROLE_ADMIN,
    ROLE_OPERADOR,
}
TENANT_ADMIN_ROLES = {
    ROLE_SUPERADMIN,
    ROLE_ADMIN,
}
DOCUMENT_EMITTER_ROLES = {
    ROLE_SUPERADMIN,
    ROLE_ADMIN,
    ROLE_OPERADOR,
}
PAYMENT_MANAGER_ROLES = {
    ROLE_SUPERADMIN,
    ROLE_ADMIN,
    ROLE_OPERADOR,
}


def normalize_role(role: str | None) -> str:
    normalized = (role or ROLE_VENDEDOR).strip().lower()
    if normalized not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Rol invalido. Roles permitidos: "
                "superadmin, admin, operador, vendedor."
            ),
        )
    return normalized


def get_effective_role(user: Any) -> str:
    if getattr(user, "is_superadmin", False):
        return ROLE_SUPERADMIN
    return normalize_role(getattr(user, "rol", ROLE_VENDEDOR))


def _normalize_allowed_roles(roles: Iterable[str]) -> set[str]:
    return {normalize_role(role) for role in roles}


def assert_user_has_roles(
    user: Any,
    allowed_roles: Iterable[str],
    *,
    detail: str,
) -> Any:
    effective_role = get_effective_role(user)
    if effective_role not in _normalize_allowed_roles(allowed_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )
    return user


def assert_active_tenant_access(user: Any) -> Any:
    if getattr(user, "is_superadmin", False):
        return user

    tenant = getattr(user, "tenant", None)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario autenticado no tiene tenant asociado.",
        )

    if not getattr(tenant, "is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El tenant se encuentra suspendido o inactivo.",
        )

    return user


def assert_login_allowed(user: Any) -> Any:
    return assert_active_tenant_access(user)


def assert_tenant_resource(
    resource: Any,
    tenant_id: int,
    *,
    resource_name: str,
) -> Any:
    if resource is None or getattr(resource, "tenant_id", None) != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_name} no encontrado.",
        )
    return resource


def can_access_all_tenant_resources(user: Any) -> bool:
    return get_effective_role(user) in ELEVATED_TENANT_ROLES


def assert_same_user_or_elevated(
    resource_user_id: int | None,
    user: Any,
    *,
    resource_name: str,
) -> None:
    if resource_user_id is None:
        return

    if can_access_all_tenant_resources(user):
        return

    if getattr(user, "id", None) != resource_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_name} no encontrado.",
        )
