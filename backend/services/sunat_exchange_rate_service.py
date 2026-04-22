from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from threading import Lock

import requests

from logging_utils import get_logger

SUNAT_EXCHANGE_RATE_URL = "https://www.sunat.gob.pe/a/txt/tipoCambio.txt"
_CACHE_TTL = timedelta(minutes=30)
_CACHE_LOCK = Lock()
_CACHE_VALUE: dict[str, object] | None = None
_CACHE_EXPIRES_AT: datetime | None = None

logger = get_logger(__name__)


class SunatExchangeRateError(RuntimeError):
    """Error controlado al consultar o parsear el tipo de cambio SUNAT."""


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _decimal_to_string(value: str) -> str:
    try:
        return format(Decimal(value), "f")
    except (InvalidOperation, TypeError) as exc:
        raise SunatExchangeRateError(
            "SUNAT devolvio un tipo de cambio invalido."
        ) from exc


def _parse_exchange_rate_payload(raw_text: str) -> dict[str, object]:
    first_line = (raw_text or "").strip().splitlines()
    if not first_line:
        raise SunatExchangeRateError("SUNAT devolvio una respuesta vacia.")

    parts = [segment.strip() for segment in first_line[0].split("|")]
    if len(parts) < 3 or not parts[0] or not parts[1] or not parts[2]:
        raise SunatExchangeRateError(
            "SUNAT devolvio una estructura de tipo de cambio invalida."
        )

    try:
        exchange_date = datetime.strptime(parts[0], "%d/%m/%Y").date().isoformat()
    except ValueError as exc:
        raise SunatExchangeRateError(
            "SUNAT devolvio una fecha de tipo de cambio invalida."
        ) from exc

    fetched_at = _now_utc().isoformat()
    return {
        "source": "sunat",
        "source_url": SUNAT_EXCHANGE_RATE_URL,
        "date": exchange_date,
        "buy": _decimal_to_string(parts[1]),
        "sell": _decimal_to_string(parts[2]),
        "fetched_at": fetched_at,
        "status": "ok",
        "stale": False,
    }


def _fetch_exchange_rate() -> dict[str, object]:
    try:
        response = requests.get(SUNAT_EXCHANGE_RATE_URL, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SunatExchangeRateError(
            "No se pudo consultar el tipo de cambio de SUNAT."
        ) from exc

    return _parse_exchange_rate_payload(response.text)


def _get_cached_value() -> dict[str, object] | None:
    with _CACHE_LOCK:
        if _CACHE_VALUE is None or _CACHE_EXPIRES_AT is None:
            return None
        if _CACHE_EXPIRES_AT <= _now_utc():
            return None
        return dict(_CACHE_VALUE)


def _set_cached_value(payload: dict[str, object]) -> None:
    with _CACHE_LOCK:
        global _CACHE_VALUE, _CACHE_EXPIRES_AT
        _CACHE_VALUE = dict(payload)
        _CACHE_EXPIRES_AT = _now_utc() + _CACHE_TTL


def _get_any_cached_value() -> dict[str, object] | None:
    with _CACHE_LOCK:
        if _CACHE_VALUE is None:
            return None
        return dict(_CACHE_VALUE)


def get_exchange_rate(*, force_refresh: bool = False) -> dict[str, object]:
    if not force_refresh:
        cached = _get_cached_value()
        if cached is not None:
            return cached

    try:
        payload = _fetch_exchange_rate()
        _set_cached_value(payload)
        return payload
    except SunatExchangeRateError as exc:
        cached = _get_any_cached_value()
        if cached is None:
            raise

        logger.warning(
            "sunat_exchange_rate_stale_cache",
            extra={
                "event": "sunat_exchange_rate_stale_cache",
                "context": str(exc),
            },
        )
        cached["status"] = "stale"
        cached["stale"] = True
        cached["warning"] = str(exc)
        return cached
