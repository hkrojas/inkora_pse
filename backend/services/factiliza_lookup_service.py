"""Read-only Factiliza API Consulta client for SUNAT establishment snapshots.

This module deliberately does not expose Factiliza invoicing, CPE or artifact
endpoints.  Network calls return a normalized snapshot that is persisted by a
separate short database transaction.
"""
from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from config import settings


logger = logging.getLogger(__name__)


class FactilizaLookupError(RuntimeError):
    def __init__(self, message: str, *, code: str = "FACTILIZA_LOOKUP_FAILED", status_code: int = 503):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def is_configured() -> bool:
    return bool(settings.FACTILIZA_API_URL.strip() and settings.FACTILIZA_API_TOKEN.strip())


def _validate_ruc(ruc: str) -> str:
    normalized = str(ruc or "").strip()
    if not re.fullmatch(r"\d{11}", normalized):
        raise FactilizaLookupError(
            "El RUC de la empresa debe tener 11 dígitos.",
            code="INVALID_RUC",
            status_code=422,
        )
    return normalized


def _request(client: httpx.Client, path: str, *, empty_annexes_on_not_found: bool = False) -> Any:
    try:
        response = client.get(path.lstrip("/"))
    except httpx.TimeoutException as exc:
        raise FactilizaLookupError("Factiliza no respondió dentro del tiempo esperado.") from exc
    except httpx.RequestError as exc:
        raise FactilizaLookupError("No se pudo conectar con Factiliza.") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise FactilizaLookupError("Factiliza devolvió una respuesta no válida.") from exc

    if response.status_code >= 400 or payload.get("success") is False:
        message = str(payload.get("message") or "Factiliza rechazó la consulta.").strip()
        missing_annexes = (
            response.status_code == 404
            and message.lower().startswith("no hay anexos registrados")
        )
        if missing_annexes:
            if empty_annexes_on_not_found:
                return []
            raise FactilizaLookupError(
                "Factiliza no pudo confirmar los establecimientos anexos. Vuelve a intentar la actualización.",
                code="FACTILIZA_ANNEXES_UNCONFIRMED",
                status_code=503,
            )
        raise FactilizaLookupError(
            message,
            code="FACTILIZA_LOOKUP_REJECTED",
            status_code=422 if response.status_code == 400 else 503,
        )
    return payload.get("data")


def _normalized_location(raw: dict, *, code: str, name: str, is_main: bool) -> dict:
    sunat_code = str(code or "").strip().zfill(4)
    ubigeo = str(raw.get("ubigeo_sunat") or "").strip()
    address = str(raw.get("direccion_completa") or raw.get("direccion") or "").strip()
    if not re.fullmatch(r"\d{4}", sunat_code):
        raise FactilizaLookupError(
            "Factiliza devolvió un código de establecimiento inválido.",
            code="INVALID_ESTABLISHMENT_DATA",
        )
    if not re.fullmatch(r"\d{6}", ubigeo) or not address:
        raise FactilizaLookupError(
            f"El establecimiento SUNAT {sunat_code} no tiene dirección y ubigeo completos.",
            code="INCOMPLETE_ESTABLISHMENT_DATA",
            status_code=422,
        )
    return {
        "sunat_code": sunat_code,
        "name": str(name or f"Establecimiento SUNAT {sunat_code}").strip()[:120],
        "ubigeo": ubigeo,
        "address": address[:500],
        "is_main": bool(is_main),
    }


def fetch_company_locations(ruc: str, *, require_annex_confirmation: bool = False) -> list[dict]:
    """Fetch the main fiscal domicile plus every registered SUNAT annex."""
    normalized_ruc = _validate_ruc(ruc)
    if not is_configured():
        raise FactilizaLookupError(
            "Configura el token de Factiliza Consulta para sincronizar establecimientos.",
            code="FACTILIZA_NOT_CONFIGURED",
            status_code=409,
        )

    headers = {"Authorization": f"Bearer {settings.FACTILIZA_API_TOKEN.strip()}"}
    base_url = f"{settings.FACTILIZA_API_URL.rstrip('/')}/"
    timeout = max(1, settings.FACTILIZA_TIMEOUT_SECONDS)
    with httpx.Client(base_url=base_url, headers=headers, timeout=timeout) as client:
        company = _request(client, f"/ruc/info/{normalized_ruc}")
        annexes = _request(
            client,
            f"/ruc/anexo/{normalized_ruc}",
            empty_annexes_on_not_found=not require_annex_confirmation,
        )

    if not isinstance(company, dict):
        raise FactilizaLookupError("Factiliza no devolvió la ficha RUC esperada.")
    if annexes is None:
        annexes = []
    if not isinstance(annexes, list):
        raise FactilizaLookupError("Factiliza no devolvió la lista de establecimientos esperada.")
    if str(company.get("numero") or normalized_ruc).strip() != normalized_ruc:
        raise FactilizaLookupError(
            "La ficha recibida no corresponde al RUC consultado.",
            code="RUC_IDENTITY_MISMATCH",
        )

    locations = [
        _normalized_location(
            company,
            code="0000",
            name="Establecimiento principal",
            is_main=True,
        )
    ]
    seen = {"0000"}
    for raw in annexes:
        if not isinstance(raw, dict):
            continue
        code = str(raw.get("codigo") or "").strip().zfill(4)
        if code in seen:
            continue
        locations.append(
            _normalized_location(
                raw,
                code=code,
                name=raw.get("tipo_establecimiento") or f"Establecimiento SUNAT {code}",
                is_main=False,
            )
        )
        seen.add(code)
    return locations


def fetch_company_locations_for_onboarding(ruc: str) -> list[dict] | None:
    """Best-effort onboarding lookup; explicit refresh remains recoverable.

    Creating a tenant must not be rolled back because an optional lookup
    provider is unavailable. The failure is logged without credentials and an
    administrator can run the explicit synchronization endpoint later.
    """
    if not is_configured():
        return None
    try:
        return fetch_company_locations(ruc)
    except FactilizaLookupError as exc:
        logger.warning("Factiliza onboarding lookup failed: code=%s ruc=%s", exc.code, ruc)
        return None
