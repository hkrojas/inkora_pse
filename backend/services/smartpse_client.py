from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import requests

from config import settings


class SmartPSEException(Exception):
    """Business/provider error raised by the Smart PSE integration."""


def _safe_json(response) -> dict:
    try:
        data = response.json()
        return data if isinstance(data, dict) else {"data": data}
    except ValueError:
        return {"raw": getattr(response, "text", "")[:4000]}


def _redacted_provider_message(data: dict) -> str:
    sensitive_keys = {
        "token_acceso",
        "password",
        "usuario_secundaria",
        "client_secret_sunat",
        "sol_password",
        "client_secret",
        "access_token",
        "token",
    }

    def redact(value):
        if isinstance(value, dict):
            return {
                key: ("***" if key in sensitive_keys else redact(inner_value))
                for key, inner_value in value.items()
            }
        if isinstance(value, list):
            return [redact(item) for item in value]
        return value

    redacted = redact(data or {})
    for key in ("message", "mensaje", "error", "detail"):
        value = redacted.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return str(redacted)[:1000]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SmartPSEClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_token: str | None = None,
        timeout_seconds: int | None = None,
        post: Callable[..., Any] | None = None,
        get: Callable[..., Any] | None = None,
        put: Callable[..., Any] | None = None,
        patch: Callable[..., Any] | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ):
        self.base_url = (base_url or settings.SMARTPSE_BASE_URL).strip().rstrip("/")
        self.api_token = (api_token if api_token is not None else settings.SMARTPSE_API_TOKEN).strip()
        self.timeout_seconds = timeout_seconds or settings.SMARTPSE_TIMEOUT_SECONDS
        self._post = post or requests.post
        self._get = get or requests.get
        self._put = put or requests.put
        self._patch = patch or post or requests.patch
        self._now = now_fn or _utc_now
        self._token_cache: dict[int | str, tuple[str, datetime]] = {}

    def _url(self, path: str) -> str:
        if not self.base_url:
            raise SmartPSEException("No hay URL base Smart PSE configurada.")
        return f"{self.base_url}/{path.lstrip('/')}"

    def _management_headers(self) -> dict[str, str]:
        if not self.api_token:
            raise SmartPSEException("Falta SMARTPSE_API_TOKEN para gestionar empresas.")
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def _raise_for_response(self, response, *, action: str) -> None:
        status_code = getattr(response, "status_code", None)
        if status_code is not None and status_code < 400:
            return
        data = _safe_json(response)
        detail = _redacted_provider_message(data)
        raise SmartPSEException(f"Smart PSE rechazo {action}: {detail}")

    def _tenant_cache_key(self, tenant) -> int | str:
        return getattr(tenant, "id", None) or getattr(tenant, "business_ruc", None) or "default"

    def _tenant_cpe_credentials(self, tenant) -> tuple[str, str]:
        usuario = (getattr(tenant, "smartpse_usuario_secundaria", None) or "").strip()
        token = (getattr(tenant, "smartpse_token_acceso", None) or "").strip()
        if not usuario or not token:
            raise SmartPSEException("Faltan credenciales CPE Smart PSE para el tenant.")
        return usuario, token

    def get_cpe_token(self, tenant, *, force_refresh: bool = False) -> str:
        cache_key = self._tenant_cache_key(tenant)
        cached = self._token_cache.get(cache_key)
        if cached and not force_refresh:
            token, expires_at = cached
            if expires_at > self._now():
                return token

        usuario, token_acceso = self._tenant_cpe_credentials(tenant)
        try:
            response = self._post(
                self._url("/api/auth/cpe/token"),
                json={"usuario": usuario, "password": token_acceso},
                headers={"Content-Type": "application/json"},
                timeout=self.timeout_seconds,
            )
        except requests.exceptions.Timeout as exc:
            raise SmartPSEException("Timeout obteniendo token CPE Smart PSE.") from exc
        except requests.exceptions.ConnectionError as exc:
            raise SmartPSEException("No se pudo conectar con Smart PSE para obtener token CPE.") from exc

        self._raise_for_response(response, action="token CPE")
        data = _safe_json(response)
        token = (data.get("token_acceso") or data.get("access_token") or "").strip()
        if not token:
            raise SmartPSEException("Smart PSE no devolvio token CPE.")

        try:
            expires_in = int(data.get("expira_en") or 600)
        except (TypeError, ValueError):
            expires_in = 600
        cache_seconds = min(max(expires_in - 30, 60), 540)
        self._token_cache[cache_key] = (token, self._now() + timedelta(seconds=cache_seconds))
        return token

    def _cpe_headers(self, tenant, *, force_refresh: bool = False) -> dict[str, str]:
        token = self.get_cpe_token(tenant, force_refresh=force_refresh)
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def process_xml(
        self,
        tenant,
        nombre_archivo: str,
        xml_content: bytes | str,
        *,
        demo: bool = False,
        extra_payload: dict | None = None,
    ) -> dict:
        endpoint = "/api/cpe/procesar-demo" if demo else "/api/cpe/procesar"
        content_bytes = xml_content.encode("utf-8") if isinstance(xml_content, str) else xml_content
        payload = {
            "nombre_archivo": nombre_archivo,
            "contenido_archivo": base64.b64encode(content_bytes).decode("ascii"),
        }
        if extra_payload:
            payload.update(extra_payload)

        response = self._post_cpe(endpoint, tenant, payload, force_refresh=False)
        if getattr(response, "status_code", None) == 401:
            response = self._post_cpe(endpoint, tenant, payload, force_refresh=True)

        self._raise_for_response(response, action=f"procesar {nombre_archivo}")
        return _safe_json(response)

    def _post_cpe(self, endpoint: str, tenant, payload: dict, *, force_refresh: bool):
        try:
            return self._post(
                self._url(endpoint),
                json=payload,
                headers=self._cpe_headers(tenant, force_refresh=force_refresh),
                timeout=self.timeout_seconds,
            )
        except requests.exceptions.Timeout as exc:
            raise SmartPSEException(f"Timeout enviando documento Smart PSE a {endpoint}.") from exc
        except requests.exceptions.ConnectionError as exc:
            raise SmartPSEException(f"No se pudo conectar con Smart PSE en {endpoint}.") from exc

    def consult_ticket(self, tenant, nombre_archivo: str) -> dict:
        endpoint = f"/api/cpe/consultar/{nombre_archivo}"
        response = self._get_cpe(endpoint, tenant, force_refresh=False)
        if getattr(response, "status_code", None) == 401:
            response = self._get_cpe(endpoint, tenant, force_refresh=True)
        self._raise_for_response(response, action=f"consultar {nombre_archivo}")
        return _safe_json(response)

    def _get_cpe(self, endpoint: str, tenant, *, force_refresh: bool):
        try:
            return self._get(
                self._url(endpoint),
                headers=self._cpe_headers(tenant, force_refresh=force_refresh),
                timeout=self.timeout_seconds,
            )
        except requests.exceptions.Timeout as exc:
            raise SmartPSEException(f"Timeout consultando ticket Smart PSE en {endpoint}.") from exc
        except requests.exceptions.ConnectionError as exc:
            raise SmartPSEException(f"No se pudo conectar con Smart PSE en {endpoint}.") from exc

    def provision_company(
        self,
        *,
        ruc: str,
        razon_social: str | None = None,
        environment: str = "demo",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict:
        payload = {
            "ruc": "".join(ch for ch in str(ruc or "") if ch.isdigit()),
            "environment": (environment or "demo").strip().lower(),
        }
        if razon_social:
            payload["razon_social"] = razon_social
        if start_date:
            payload["start_date"] = start_date
        if end_date:
            payload["end_date"] = end_date

        try:
            response = self._post(
                self._url("/api/v1/companies"),
                json=payload,
                headers=self._management_headers(),
                timeout=self.timeout_seconds,
            )
        except requests.exceptions.Timeout as exc:
            raise SmartPSEException("Timeout creando empresa Smart PSE.") from exc
        except requests.exceptions.ConnectionError as exc:
            raise SmartPSEException("No se pudo conectar con Smart PSE para crear empresa.") from exc

        self._raise_for_response(response, action="crear empresa")
        data = _safe_json(response)
        company = data.get("data") if isinstance(data.get("data"), dict) else data
        if not isinstance(company, dict):
            raise SmartPSEException("Smart PSE devolvio una respuesta de empresa invalida.")
        return company

    def list_companies(
        self,
        *,
        search: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        params = {
            "page": page,
            "per_page": per_page,
        }
        if search:
            params["search"] = search

        try:
            response = self._get(
                self._url("/api/v1/companies"),
                params=params,
                headers=self._management_headers(),
                timeout=self.timeout_seconds,
            )
        except requests.exceptions.Timeout as exc:
            raise SmartPSEException("Timeout listando empresas Smart PSE.") from exc
        except requests.exceptions.ConnectionError as exc:
            raise SmartPSEException("No se pudo conectar con Smart PSE para listar empresas.") from exc

        self._raise_for_response(response, action="listar empresas")
        data = _safe_json(response)
        page_data = data.get("data") if isinstance(data.get("data"), dict) else data
        if isinstance(page_data, list):
            return {"data": page_data}
        if not isinstance(page_data, dict):
            raise SmartPSEException("Smart PSE devolvio una respuesta de lista invalida.")
        return {
            "data": page_data.get("data") or [],
            "total": page_data.get("total"),
            "current_page": page_data.get("current_page"),
            "last_page": page_data.get("last_page"),
        }

    def get_company(self, company_id: int | str) -> dict:
        try:
            response = self._get(
                self._url(f"/api/v1/companies/{company_id}"),
                headers=self._management_headers(),
                timeout=self.timeout_seconds,
            )
        except requests.exceptions.Timeout as exc:
            raise SmartPSEException("Timeout consultando empresa Smart PSE.") from exc
        except requests.exceptions.ConnectionError as exc:
            raise SmartPSEException("No se pudo conectar con Smart PSE para consultar empresa.") from exc

        self._raise_for_response(response, action="consultar empresa")
        data = _safe_json(response)
        company = data.get("data") if isinstance(data.get("data"), dict) else data
        if not isinstance(company, dict):
            raise SmartPSEException("Smart PSE devolvio una empresa invalida.")
        return company

    def update_company(self, company_id: int | str, data: dict) -> dict:
        payload = dict(data or {})
        try:
            response = self._put(
                self._url(f"/api/v1/companies/{company_id}"),
                json=payload,
                headers=self._management_headers(),
                timeout=self.timeout_seconds,
            )
        except requests.exceptions.Timeout as exc:
            raise SmartPSEException("Timeout actualizando empresa Smart PSE.") from exc
        except requests.exceptions.ConnectionError as exc:
            raise SmartPSEException("No se pudo conectar con Smart PSE para actualizar empresa.") from exc

        self._raise_for_response(response, action="actualizar empresa")
        response_data = _safe_json(response)
        company = response_data.get("data") if isinstance(response_data.get("data"), dict) else response_data
        if not isinstance(company, dict):
            raise SmartPSEException("Smart PSE devolvio una empresa invalida.")
        return company

    def toggle_company_activation(self, company_id: int | str) -> dict:
        try:
            response = self._patch(
                self._url(f"/api/v1/companies/{company_id}/activation"),
                headers=self._management_headers(),
                timeout=self.timeout_seconds,
            )
        except requests.exceptions.Timeout as exc:
            raise SmartPSEException("Timeout cambiando activacion de empresa Smart PSE.") from exc
        except requests.exceptions.ConnectionError as exc:
            raise SmartPSEException(
                "No se pudo conectar con Smart PSE para cambiar activacion de empresa."
            ) from exc

        self._raise_for_response(response, action="cambiar activacion de empresa")
        data = _safe_json(response)
        company = data.get("data") if isinstance(data.get("data"), dict) else data
        if not isinstance(company, dict):
            raise SmartPSEException("Smart PSE devolvio una empresa invalida.")
        return company

    def validate_tenant_credentials(self, tenant) -> dict:
        try:
            token = self.get_cpe_token(tenant, force_refresh=True)
        except SmartPSEException as exc:
            return {
                "valid": False,
                "message": str(exc),
                "provider_status_code": None,
                "provider_detail": "credential_error",
            }
        return {
            "valid": True,
            "message": "Credenciales Smart PSE aceptadas.",
            "provider_status_code": 200,
            "provider_detail": "ok",
            "token_preview": f"{token[:8]}...",
        }


_default_client: SmartPSEClient | None = None


def get_default_client() -> SmartPSEClient:
    global _default_client
    if _default_client is None:
        _default_client = SmartPSEClient()
    return _default_client
