from __future__ import annotations

from typing import Any, Callable

import requests

from config import settings
from services import secret_box


GRE_CREDENTIAL_FIELDS = (
    "smartpse_gre_sol_username",
    "smartpse_gre_sol_password_enc",
    "smartpse_gre_client_id",
    "smartpse_gre_client_secret_enc",
)


class SmartPSEGreCredentialsError(ValueError):
    """Raised when GRE credentials are missing or invalid locally."""


def _digits(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _text(value: Any) -> str:
    return str(value or "").strip()


def normalize_sol_username(value: str | None) -> str:
    return _text(value).upper()


def missing_gre_credential_fields(tenant) -> list[str]:
    if not tenant:
        return list(GRE_CREDENTIAL_FIELDS)
    return [field for field in GRE_CREDENTIAL_FIELDS if not _text(getattr(tenant, field, None))]


def has_complete_gre_credentials(tenant) -> bool:
    return bool(tenant and not missing_gre_credential_fields(tenant))


def build_smartpse_gre_extra_payload(tenant) -> dict[str, str]:
    missing = missing_gre_credential_fields(tenant)
    if missing:
        raise SmartPSEGreCredentialsError(
            "Faltan credenciales SUNAT GRE para emitir guias con Smart PSE."
        )

    ruc = _digits(getattr(tenant, "business_ruc", None))
    sol_username = normalize_sol_username(getattr(tenant, "smartpse_gre_sol_username", None))
    sol_password = secret_box.decrypt_secret(getattr(tenant, "smartpse_gre_sol_password_enc", None))
    client_id = _text(getattr(tenant, "smartpse_gre_client_id", None))
    client_secret = secret_box.decrypt_secret(getattr(tenant, "smartpse_gre_client_secret_enc", None))

    if not ruc:
        raise SmartPSEGreCredentialsError("El tenant no tiene RUC emisor configurado.")
    if not sol_password or not client_secret:
        raise SmartPSEGreCredentialsError(
            "No se pudieron descifrar las credenciales SUNAT GRE del tenant."
        )

    return {
        "client_id_sunat": client_id,
        "client_secret_sunat": client_secret,
        "sol_user": f"{ruc}{sol_username}",
        "sol_password": sol_password,
    }


def _safe_json(response) -> dict:
    try:
        data = response.json()
        return data if isinstance(data, dict) else {"data": data}
    except ValueError:
        return {"raw": getattr(response, "text", "")[:1000]}


def validate_tenant_gre_credentials(
    tenant,
    *,
    post: Callable[..., Any] | None = None,
) -> dict:
    try:
        extra = build_smartpse_gre_extra_payload(tenant)
    except (SmartPSEGreCredentialsError, secret_box.SecretBoxError) as exc:
        return {
            "valid": False,
            "message": str(exc),
            "provider_status_code": None,
            "provider_detail": "credential_error",
        }

    request_post = post or requests.post
    client_id = extra["client_id_sunat"]
    url = f"https://api-seguridad.sunat.gob.pe/v1/clientessol/{client_id}/oauth2/token/"
    form_data = {
        "grant_type": "password",
        "scope": "https://api-cpe.sunat.gob.pe",
        "client_id": client_id,
        "client_secret": extra["client_secret_sunat"],
        "username": extra["sol_user"],
        "password": extra["sol_password"],
    }

    try:
        response = request_post(
            url,
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=settings.SMARTPSE_TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        return {
            "valid": False,
            "message": "Timeout validando credenciales SUNAT GRE.",
            "provider_status_code": None,
            "provider_detail": "timeout",
        }
    except requests.exceptions.ConnectionError:
        return {
            "valid": False,
            "message": "No se pudo conectar con SUNAT para validar credenciales GRE.",
            "provider_status_code": None,
            "provider_detail": "connection_error",
        }

    status_code = getattr(response, "status_code", None)
    data = _safe_json(response)
    token = str(data.get("access_token") or data.get("token") or "").strip()
    if status_code is not None and status_code < 400 and token:
        return {
            "valid": True,
            "message": "Credenciales GRE aceptadas.",
            "provider_status_code": status_code,
            "provider_detail": "ok",
        }

    detail = data.get("error_description") or data.get("error") or data.get("message") or data.get("raw")
    return {
        "valid": False,
        "message": "SUNAT rechazo las credenciales GRE.",
        "provider_status_code": status_code,
        "provider_detail": str(detail or "invalid_credentials")[:500],
    }
