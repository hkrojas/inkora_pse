import json
import logging
import sys


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
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(KeyValueFormatter())
    handler.addFilter(EnvironmentFilter(environment))

    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level.upper())
    logging.captureWarnings(True)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
