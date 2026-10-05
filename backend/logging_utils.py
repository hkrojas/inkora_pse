import json
import logging
import re
import sys


_SECRET_KEY = (
    r"(?:[\w-]*[_-])?(?:token(?:_acceso)?|password(?:_enc)?|passwd|secret(?:_sunat)?|"
    r"api[_-]?key|authorization|cookie|set-cookie|credential|credentials|"
    r"clave_sol|service_role_key|usuario_secundaria)"
)
_SECRET_FIELD = re.compile(
    rf"(?i)(?<![\w-])(?P<key>[\"']?{_SECRET_KEY}[\"']?\s*[:=]\s*)"
    r"(?:\[REDACTED\]|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|[^\s,;&}\]]+)"
)
_COOKIE_HEADER = re.compile(r"(?im)(\b(?:cookie|set-cookie)\s*:\s*)[^\r\n]+")
_AUTH_HEADER = re.compile(
    r"(?im)(\b(?:authorization|proxy-authorization)\s*[:=]\s*)[^\r\n]+"
)
_USERINFO = re.compile(r"(?i)(\b[a-z][a-z0-9+.-]*://)[^\s/]+@")
_QUERY_VALUE = re.compile(r"([?&][^=\s\"'<>?#&]+(?:=|%3[dD]))[^&\s\"'<>#]*")


def _redact_text(value: str) -> str:
    # Query values can contain provider-specific secrets or signed storage tokens.
    # Retain the path and parameter names, but never their values in logs.
    value = _USERINFO.sub(r"\1[REDACTED]@", value)
    value = _QUERY_VALUE.sub(r"\1[REDACTED]", value)
    value = _COOKIE_HEADER.sub(r"\1[REDACTED]", value)
    value = _AUTH_HEADER.sub(r"\1[REDACTED]", value)
    return _SECRET_FIELD.sub(lambda match: match.group("key") + "[REDACTED]", value)


def _redact_value(value: object) -> object:
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, dict):
        return {
            _redact_text(str(key)): "[REDACTED]" if re.fullmatch(_SECRET_KEY, str(key), re.I)
            else _redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact_value(item) for item in value]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _redact_text(str(value))


class KeyValueFormatter(logging.Formatter):
    default_time_format = "%Y-%m-%dT%H:%M:%S"

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "time": self.formatTime(record, self.default_time_format),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field in (
            "environment",
            "event",
            "context",
            "path",
            "method",
            "status_code",
            "request_id",
            "duration_ms",
        ):
            value = getattr(record, field, None)
            if value not in (None, ""):
                payload[field] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        parts = []
        for key, value in payload.items():
            value = _redact_value(value)
            if isinstance(value, str):
                rendered = json.dumps(value, ensure_ascii=False)
            else:
                rendered = str(value)
            parts.append(f"{key}={rendered}")
        return " ".join(parts)


class EnvironmentFilter(logging.Filter):
    def __init__(self, environment: str):
        super().__init__()
        self.environment = environment

    def filter(self, record: logging.LogRecord) -> bool:
        record.environment = self.environment
        return True


def configure_logging(*, level: str = "INFO", environment: str = "development") -> None:
    root_logger = logging.getLogger()
    formatter = KeyValueFormatter()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(EnvironmentFilter(environment))

    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level.upper())
    # Uvicorn configures its own non-propagating handlers before importing the
    # API. Redact their output without replacing streams or changing routing.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        for uvicorn_handler in logging.getLogger(name).handlers:
            uvicorn_handler.setFormatter(formatter)
    logging.captureWarnings(True)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
