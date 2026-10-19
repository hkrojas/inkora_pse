"""Read-only transport lookups. Never emits documents or stores personal data."""
import re

import httpx

from config import settings
from services.factiliza_lookup_service import FactilizaLookupError, is_configured


def _fetch(kind: str, number: str) -> dict:
    if not is_configured():
        raise FactilizaLookupError(
            "La consulta de transporte no está disponible. Puedes ingresar los datos manualmente.",
            code="TRANSPORT_LOOKUP_NOT_CONFIGURED",
        )
    try:
        with httpx.Client(
            base_url=f"{settings.FACTILIZA_API_URL.rstrip('/')}/",
            headers={"Authorization": f"Bearer {settings.FACTILIZA_API_TOKEN.strip()}"},
            timeout=max(1, settings.FACTILIZA_TIMEOUT_SECONDS),
        ) as client:
            response = client.get(f"{kind}/info/{number}")
        payload = response.json()
    except (httpx.RequestError, ValueError) as exc:
        raise FactilizaLookupError("No se pudo consultar. Inténtalo de nuevo o ingresa los datos manualmente.") from exc
    if not isinstance(payload, dict):
        raise FactilizaLookupError("La consulta devolvió una respuesta incompleta. Ingresa los datos manualmente.")
    # Some providers report errors in the JSON envelope with HTTP 200.
    status = str(payload.get("status", response.status_code))
    if response.status_code == 404 or status == "404":
        raise FactilizaLookupError("No se encontraron datos. Puedes ingresarlos manualmente.", status_code=404)
    if response.status_code >= 400 or not status.startswith("2") or payload.get("success") is False:
        # Do not relay provider text: it can contain credentials or personal data.
        raise FactilizaLookupError("La consulta no está disponible. Puedes ingresar los datos manualmente.")
    data = payload.get("data")
    if not isinstance(data, dict) or not data:
        raise FactilizaLookupError("No se encontraron datos. Puedes ingresarlos manualmente.", status_code=404)
    return data


def _text(data: dict, key: str, limit: int = 120) -> str:
    value = data.get(key)
    return str(value).strip()[:limit] if isinstance(value, (str, int)) else ""


def normalize_plate(value: str) -> str:
    return str(value or "").strip().upper().replace("-", "")


def lookup_plate(plate: str) -> dict:
    number = normalize_plate(plate)
    if not re.fullmatch(r"[A-Z0-9]{5,8}", number):
        raise FactilizaLookupError("Ingresa una placa de 5 a 8 letras o números.", status_code=422)
    data = _fetch("placa", number)
    if normalize_plate(_text(data, "placa")) != number:
        raise FactilizaLookupError("La respuesta no corresponde a la placa consultada.")
    return {"placa": number, **{key: _text(data, key) for key in ("marca", "modelo", "color")}}


def lookup_license(dni: str) -> dict:
    number = str(dni or "").strip()
    if not re.fullmatch(r"[0-9]{8}", number):
        raise FactilizaLookupError("Ingresa los 8 dígitos del DNI del conductor.", status_code=422)
    data = _fetch("licencia", number)
    license_data = data.get("licencia")
    if _text(data, "numero_documento") != number or not isinstance(license_data, dict):
        raise FactilizaLookupError("La respuesta no corresponde al DNI consultado o no incluye la licencia.")
    if not _text(license_data, "numero"):
        raise FactilizaLookupError("No se encontró el número de licencia. Puedes ingresarlo manualmente.", status_code=404)
    return {"documento": number, **{key: _text(license_data, key) for key in ("numero", "categoria", "fecha_vencimiento", "estado")}}
