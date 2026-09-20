"""Politica HTTP comun para la API de Inkora.

La politica se mantiene en un unico modulo para evitar que CORS, las respuestas
normales y los errores terminen con configuraciones divergentes.
"""

from collections.abc import MutableMapping


CORS_ALLOWED_HEADERS = [
    "Accept",
    "Authorization",
    "Content-Type",
    "Idempotency-Key",
    "Origin",
    "X-Request-Id",
    "X-Requested-With",
]

CORS_EXPOSE_HEADERS = [
    "Content-Disposition",
    "X-Request-Id",
]

SECURITY_HEADERS = {
    "Content-Security-Policy": "frame-ancestors 'none'; base-uri 'none'; object-src 'none'",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}

HSTS_HEADER_VALUE = "max-age=31536000; includeSubDomains"


def apply_security_headers(
    headers: MutableMapping[str, str],
    *,
    include_hsts: bool,
) -> None:
    """Agrega cabeceras seguras sin sobrescribir decisiones explicitas."""

    for name, value in SECURITY_HEADERS.items():
        headers.setdefault(name, value)
    if include_hsts:
        headers.setdefault("Strict-Transport-Security", HSTS_HEADER_VALUE)
