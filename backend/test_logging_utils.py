import io
import logging
import logging.config
import sys
import warnings
from copy import deepcopy

import pytest
import httpx

from logging_utils import KeyValueFormatter, _redact_text, configure_logging


def render(message, args=(), **extra):
    record = logging.LogRecord("httpx", logging.INFO, __file__, 1, message, args, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return KeyValueFormatter().format(record)


@pytest.mark.parametrize("url", [
    "https://api.example.test/v1/ruc?token=FAKE_SECRET&number=123",
    "https://api.example.test/v1/ruc?%74oken=FAKE_SECRET",
    "https://api.example.test/v1/ruc?TOKEN=FAKE_SECRET#fragment",
    "/v1/ruc?token=FAKE_SECRET&next=public",
    "https://api.example.test/v1/ruc?custom_provider_key=FAKE_SECRET",
    "https://api.example.test/v1/ruc?token%3DFAKE_SECRET",
])
def test_http_client_and_relative_url_queries_hide_values(url):
    output = render('HTTP Request: GET %s "HTTP/1.1 200 OK"', (url,))
    assert "FAKE_SECRET" not in output
    assert "[REDACTED]" in output
    assert "/v1/ruc" in output
    assert "200 OK" in output


@pytest.mark.parametrize("message", [
    "Authorization: Bearer FAKE_SECRET",
    "Authorization: Basic FAKE_SECRET",
    "{'password': 'FAKE_SECRET with spaces'}",
    '{"api_key": "FAKE_SECRET"}',
    "SMARTPSE_PANEL_PASSWORD=FAKE_SECRET",
    "access_token=FAKE_SECRET",
    "postgresql://user:FAKE_SECRET@localhost/db",
])
def test_secrets_in_messages_are_hidden(message):
    assert "FAKE_SECRET" not in render(message)


def test_structured_context_is_redacted_without_changing_original_record():
    context = {"job_id": 265, "token": "FAKE_TOKEN", "nested": [
        {"password": "FAKE_PASSWORD", "url": "https://api.test/a?key=FAKE_URL"}
    ], "status": "pending"}
    output = render("provider_lookup", context=context, event="lookup", status_code=200)
    assert all(secret not in output for secret in ("FAKE_TOKEN", "FAKE_PASSWORD", "FAKE_URL"))
    assert "265" in output and "pending" in output and "status_code=200" in output
    assert context["token"] == "FAKE_TOKEN"


def test_exception_tracebacks_are_redacted_and_remain_diagnostic():
    try:
        raise RuntimeError("provider failed https://api.test/a?token=FAKE_SECRET")
    except RuntimeError:
        output = render("lookup_failed", exc_info=sys.exc_info())
    assert "FAKE_SECRET" not in output
    assert "RuntimeError" in output and "Traceback" in output


def test_real_handler_formats_httpx_record_and_remains_repeatable():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(KeyValueFormatter())
    record = logging.LogRecord("httpx", logging.INFO, __file__, 1,
        "HTTP Request: GET %s", ("https://api.test/a?token=FAKE_SECRET",), None)
    handler.handle(record)
    handler.handle(record)
    assert "FAKE_SECRET" not in stream.getvalue()
    assert stream.getvalue().count("[REDACTED]") == 2
    assert record.args == ("https://api.test/a?token=FAKE_SECRET",)


@pytest.mark.parametrize("key", ["token_acceso", "smartpse_token_acceso",
    "clave_sol", "sunat_cert_password_enc", "SUPABASE_SERVICE_ROLE_KEY",
    "client_secret_sunat", "usuario_secundaria", "sol_password", "client_secret"])
def test_inkora_credential_aliases_in_context_and_text(key):
    assert "FAKE_SECRET" not in render("credentials", context={key: "FAKE_SECRET"})
    assert "FAKE_SECRET" not in render(f"{key}=FAKE_SECRET")
    provider_message = f"{key}=FAKE_SECRET"
    try:
        raise RuntimeError(provider_message)
    except RuntimeError:
        assert "FAKE_SECRET" not in render("lookup_failed", exc_info=sys.exc_info())


@pytest.mark.parametrize("header", ["Cookie", "Set-Cookie"])
def test_all_cookie_values_are_hidden(header):
    output = render(f"{header}: session=COOKIE_A; sid=COOKIE_B\nHTTP status 200")
    assert "COOKIE_A" not in output and "COOKIE_B" not in output
    assert "HTTP status 200" in output


def test_redaction_is_idempotent():
    clean = _redact_text("https://api.test/a?token=FAKE_SECRET&next=other")
    assert _redact_text(clean) == clean
    assert "[REDACTED]]" not in clean


def test_digest_authorization_hides_all_header_parameters():
    output = render('Authorization: Digest username="FAKE_USER", response="FAKE_SECRET"\nstatus=401')
    assert "FAKE_USER" not in output and "FAKE_SECRET" not in output
    assert "status=401" in output


def test_httpx_emission_is_redacted_without_altering_outbound_request():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(KeyValueFormatter())
    logger = logging.getLogger("httpx")
    original = logger.handlers[:], logger.level, logger.propagate
    logger.handlers, logger.propagate = [handler], False
    logger.setLevel(logging.INFO)
    requests_seen = []
    def respond(request):
        requests_seen.append(request)
        return httpx.Response(200, json={"ok": True})
    try:
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            assert client.get("https://api.example.test/ruc?token=FAKE_SECRET").status_code == 200
    finally:
        logger.handlers, logger.level, logger.propagate = original
    assert requests_seen[0].url.params["token"] == "FAKE_SECRET"
    assert "FAKE_SECRET" not in stream.getvalue()
    assert "HTTP/1.1 200 OK" in stream.getvalue()


@pytest.fixture
def restore_logging_configuration(monkeypatch):
    manager = logging.Logger.manager
    original_names = set(manager.loggerDict)
    loggers = [logging.getLogger()] + [value for value in manager.loggerDict.values()
        if isinstance(value, logging.Logger)]
    states = [(logger, logger.handlers[:], logger.filters[:], logger.level, logger.propagate, logger.disabled)
        for logger in loggers]
    handler_refs = logging._handlerList[:]
    registered_handlers = dict(logging._handlers)
    handler_states = [(ref(), ref().formatter, ref().filters[:]) for ref in handler_refs if ref() is not None]
    showwarning, captured_warning = warnings.showwarning, logging._warnings_showwarning
    # dictConfig normally closes every existing handler, including pytest's
    # capture handlers. Keep those alive while installing actual Uvicorn defaults.
    monkeypatch.setattr(logging.config, "_clearExistingHandlers", lambda: None)
    try:
        yield
    finally:
        for ref in logging._handlerList[:]:
            handler = ref()
            if handler is not None and all(handler is not saved[0] for saved in handler_states):
                handler.close()
        for logger, handlers, filters, level, propagate, disabled in states:
            logger.handlers, logger.filters = handlers, filters
            logger.setLevel(level)
            logger.propagate, logger.disabled = propagate, disabled
        for handler, formatter, filters in handler_states:
            handler.setFormatter(formatter)
            handler.filters = filters
        for name in set(manager.loggerDict) - original_names:
            del manager.loggerDict[name]
        logging._handlerList[:] = handler_refs
        logging._handlers.clear()
        logging._handlers.update(registered_handlers)
        warnings.showwarning, logging._warnings_showwarning = showwarning, captured_warning


def test_configure_logging_covers_uvicorn_defaults_and_httpx_root_without_duplicates(
    monkeypatch, restore_logging_configuration,
):
    from uvicorn.config import LOGGING_CONFIG

    stdout, stderr = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)
    logging.config.dictConfig(deepcopy(LOGGING_CONFIG))
    named = [logging.getLogger(name) for name in ("uvicorn", "uvicorn.error", "uvicorn.access")]
    original = [(logger, logger.handlers[:], logger.level, logger.propagate,
        [(handler, handler.stream, handler.level) for handler in logger.handlers]) for logger in named]
    http_logger = logging.getLogger("httpx")
    http_logger.handlers.clear()
    http_logger.setLevel(logging.INFO)
    http_logger.propagate = True
    requests_seen = []
    sensitive_url = "https://api.example.test/ruc?token=" + "FAKE_SECRET"

    def respond(request):
        requests_seen.append(request)
        return httpx.Response(200, json={"ok": True})

    for _ in range(2):
        configure_logging(environment="test")
        logging.getLogger("uvicorn.access").info('%s - "%s %s HTTP/%s" %d',
            "127.0.0.1:8000", "GET", "/ruc?token=" + "FAKE_SECRET", "1.1", 200)
        try:
            raise RuntimeError(sensitive_url)
        except RuntimeError:
            logging.getLogger("uvicorn.error").exception("synthetic_request_failure")
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            assert client.get(sensitive_url).status_code == 200
        assert len(logging.getLogger().handlers) == 1
        for logger, handlers, level, propagate, streams in original:
            assert logger.handlers == handlers and logger.level == level and logger.propagate == propagate
            for handler, stream, handler_level in streams:
                assert handler.stream is stream and handler.level == handler_level

    output = stdout.getvalue() + stderr.getvalue()
    assert "FAKE_SECRET" not in output
    assert output.count("HTTP Request:") == 2
    assert output.count("synthetic_request_failure") == 2
    assert output.count("127.0.0.1:8000") == 2
    assert "RuntimeError" in output and "Traceback" in output
    assert all(request.url.params["token"] == "FAKE_SECRET" for request in requests_seen)
