"""Offline panel retry contracts: exact identity/XML, fencing and a single POST."""
import base64
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
import threading
import time
from unittest.mock import Mock

from pydantic import SecretStr
import pytest
import requests

from config import settings
from services import smartpse_panel_client as panel
from services import emission_leases
from test_smartpse_panel_client import NAME, PASSWORD, Response, Session, cdr, invoice_xml, listing, login, row, tenant


RAW = invoice_xml()
XML = RAW.decode()


def retry_row(**changes):
    return row(**{"state": "error", "error_message": "[HTTP] Service Unavailable", "has_cdr": False,
                  "has_signed_xml": True, "hash": "synthetic-provider-digest", "ticket": None, **changes})


class RetrySession(Session):
    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        assert url.startswith(panel.ORIGIN + "/")
        assert kwargs["allow_redirects"] is False
        assert method == "GET" or (method == "POST" and (url == panel.ORIGIN + "/login"
            or re.fullmatch(re.escape(panel.ORIGIN) + r"/panel/documentos/[0-9]+/reintentar", url)))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def retry_client(*responses, now_fn=None):
    sessions = [RetrySession(values) for values in responses]
    remaining = list(sessions)
    client = panel.SmartPSEPanelClient(session_factory=lambda: remaining.pop(0), email=SecretStr("offline@example.test"),
                                     password=SecretStr(PASSWORD), now_fn=now_fn)
    return client, sessions


def ready(*, initial=None, latest=None, xml=RAW, post=None):
    return login() + [listing([initial or retry_row()]), Response(body=xml, content_type="application/xml"),
                      listing([latest or retry_row()]), post or Response(200, page={"props": {"accepted": True}})]


def attempt(client, tenant, before_submit=None, **changes):
    return client.retry_invoice(tenant, NAME, **{"environment": "produccion", "expected_xml": XML,
                                               "before_submit": before_submit or Mock(return_value=True), **changes})


def fiscal_posts(sessions):
    return [call for session in sessions for call in session.calls if call[0] == "POST" and call[1].endswith("/reintentar")]


@pytest.fixture(autouse=True)
def enabled(monkeypatch):
    monkeypatch.setattr(settings, "SMARTPSE_PANEL_RETRY_TENANT_IDS", "5")
    monkeypatch.setattr(settings, "SMARTPSE_PANEL_RECOVERY_TENANT_IDS", "5")


def test_retry_posts_once_after_fence_with_csrf_without_invoice_payload(tenant):
    client, sessions = retry_client(ready())
    events = []
    original = sessions[0].request
    def observe(method, url, **kwargs):
        if url.endswith("/reintentar"):
            events.append("post")
            assert events == ["fence", "post"]
        return original(method, url, **kwargs)
    sessions[0].request = observe
    def fence(metadata):
        assert len(sessions[0].calls) == 5
        assert metadata["panel_retry_attempted"] is False
        assert metadata["provider_document_id"] == "444364"
        assert metadata["provider_company_id"] == "384"
        assert metadata["environment"] == "produccion"
        assert metadata["xml_sha256"] == hashlib.sha256(RAW).hexdigest()
        assert metadata["provider_xml_hash"] == "synthetic-provider-digest"
        assert metadata["provider_error_message"] == "[HTTP] Service Unavailable"
        events.append("fence")
        return True
    result = attempt(client, tenant, fence)
    assert result["panel_retry_attempted"] is True
    assert result["panel_retry_status"] == "response_received"
    assert result["estado"] == 202 and result["pending"] is True and result["cdr"] is None
    assert "provider_verification_status" not in result
    post = fiscal_posts(sessions)[0]
    assert post[1] == panel.ORIGIN + "/panel/documentos/444364/reintentar"
    assert "json" not in post[2] and "data" not in post[2]
    assert post[2]["headers"]["X-XSRF-TOKEN"] == "csrf/token"
    assert post[2]["headers"]["Origin"] == panel.ORIGIN
    assert post[2]["headers"]["Referer"] == panel.ORIGIN + "/panel/documentos"
    assert len(fiscal_posts(sessions)) == 1


@pytest.mark.parametrize("setting,value", [("SMARTPSE_PANEL_RETRY_TENANT_IDS", ""),
    ("SMARTPSE_PANEL_RETRY_TENANT_IDS", "99"), ("SMARTPSE_PANEL_RETRY_TENANT_IDS", "*")])
def test_retry_rollout_off_prevents_even_login(tenant, monkeypatch, setting, value):
    monkeypatch.setattr(settings, setting, value)
    client, sessions = retry_client([])
    with pytest.raises(panel.SmartPSEPanelException):
        attempt(client, tenant)
    assert not sessions[0].calls


def test_retry_and_read_only_rollouts_are_independent(tenant, monkeypatch):
    monkeypatch.setattr(settings, "SMARTPSE_PANEL_RECOVERY_TENANT_IDS", "")
    client, sessions = retry_client(ready())
    assert attempt(client, tenant)["panel_retry_attempted"]
    assert len(fiscal_posts(sessions)) == 1
    with pytest.raises(panel.SmartPSEPanelException):
        client.recover_invoice(tenant, NAME, environment="produccion")


@pytest.mark.parametrize("changes", [{"business_ruc": "20999999999"}, {"smartpse_environment": "demo"},
                                    {"smartpse_company_id": "https://attacker.invalid"}, {"id": 99}])
def test_bad_tenant_retry_identity_prevents_login(tenant, changes):
    for key, value in changes.items():
        setattr(tenant, key, value)
    client, sessions = retry_client([])
    with pytest.raises(panel.SmartPSEPanelException):
        attempt(client, tenant)
    assert not sessions[0].calls


@pytest.mark.parametrize("changes", [{"company_id": 999}, {"environment": "demo"}, {"doc_type": "03"},
                                    {"id": "https://attacker.invalid/"}])
def test_retry_row_scope_must_match_tenant_before_callback(tenant, changes):
    callback = Mock(return_value=True)
    client, sessions = retry_client(login() + [listing([retry_row(**changes)])])
    with pytest.raises(panel.SmartPSEPanelException):
        attempt(client, tenant, callback)
    callback.assert_not_called()
    assert not fiscal_posts(sessions)


@pytest.mark.parametrize("name", [NAME.replace("-01-", "-03-"), NAME.replace("-01-", "-09-"),
                                  NAME.replace("-01-", "-07-"), "foreign-document"])
def test_non_invoice_retry_is_forbidden_before_login(tenant, name):
    client, sessions = retry_client([])
    with pytest.raises(panel.SmartPSEPanelException):
        client.retry_invoice(tenant, name, environment="produccion", expected_xml=XML, before_submit=Mock())
    assert not sessions[0].calls


@pytest.mark.parametrize("state", ["aceptado", "accepted", "observado", "observed", "rechazado", "rejected",
                                  "pendiente", "pending", "firmado", "processing", "ERROR", None])
def test_only_exact_error_state_may_retry(tenant, state):
    callback = Mock()
    client, sessions = retry_client(login() + [listing([retry_row(state=state)])])
    result = attempt(client, tenant, callback)
    assert result["panel_retry_status"] == "blocked"
    assert result["panel_retry_attempted"] is False
    callback.assert_not_called()
    assert not fiscal_posts(sessions)


@pytest.mark.parametrize("error", ["[1033] El comprobante fue registrado previamente con otros datos",
    "[HTTP] Unauthorized", "HTTP 503 duplicado", "HTTP 503 rejected", "HTTP 503 credencial invalida",
    "HTTP 503 error de validacion", "HTTP 503 validation failed", "HTTP 503 forbidden", "HTTP 503 ticket 123",
    "Timeout", "Error desconocido", "Service Unavailable", "HTTP 429", "HTTP 422", None])
def test_unproven_or_definitive_errors_never_retry(tenant, error):
    callback = Mock()
    client, sessions = retry_client(login() + [listing([retry_row(error_message=error)])])
    result = attempt(client, tenant, callback)
    assert result["panel_retry_status"] == "blocked"
    callback.assert_not_called()
    assert not fiscal_posts(sessions)


@pytest.mark.parametrize("error", ["HTTP 500", "HTTP 502", "status_code=503", "HTTP 504",
                                  "[HTTP] Bad Gateway", "[HTTP] Gateway Timeout"])
def test_concrete_temporary_http_categories_are_eligible(tenant, error):
    candidate = retry_row(error_message=error)
    client, sessions = retry_client(ready(initial=candidate, latest=candidate))
    assert attempt(client, tenant)["panel_retry_attempted"] is True
    assert len(fiscal_posts(sessions)) == 1


@pytest.mark.parametrize("changes", [{"has_cdr": None}, {"has_cdr": "false"}, {"has_cdr": 0},
    {"has_signed_xml": False}, {"has_signed_xml": "true"}, {"has_signed_xml": 1}, {"ticket": "known-ticket"}])
def test_retry_requires_literal_evidence_flags_and_no_ticket(tenant, changes):
    callback = Mock()
    client, sessions = retry_client(login() + [listing([retry_row(**changes)])])
    assert attempt(client, tenant, callback)["panel_retry_status"] == "blocked"
    callback.assert_not_called()
    assert not fiscal_posts(sessions)


@pytest.mark.parametrize("error", ["[1033] El comprobante fue registrado previamente con otros datos", "[HTTP] Unauthorized",
                                  "[HTTP] Service Unavailable"])
def test_existing_cdr_blocks_retry_even_when_panel_shows_error(tenant, error):
    callback = Mock()
    client, sessions = retry_client(login() + [listing([retry_row(has_cdr=True, error_message=error)]), Response(body=cdr())])
    result = attempt(client, tenant, callback)
    assert result["panel_retry_status"] == "cdr_available"
    assert base64.b64decode(result["cdr"]) == cdr()
    assert result["panel_retry_attempted"] is False
    callback.assert_not_called()
    assert not fiscal_posts(sessions)


@pytest.mark.parametrize("changes", [{"state": "pendiente"}, {"has_signed_xml": False}, {"error_message": "1033"},
    {"id": 999}, {"hash": "different-provider-digest"}, {"ticket": "new-ticket"}])
def test_row_revalidation_prevents_post_after_a_change(tenant, changes):
    callback = Mock()
    client, sessions = retry_client(ready(latest=retry_row(**changes)))
    assert attempt(client, tenant, callback)["panel_retry_status"] == "blocked"
    callback.assert_not_called()
    assert not fiscal_posts(sessions)


def test_cdr_appearing_during_revalidation_is_recovered_without_post(tenant):
    callback = Mock()
    client, sessions = retry_client(login() + [listing([retry_row()]), Response(body=RAW, content_type="application/xml"),
        listing([retry_row(has_cdr=True, state="aceptado")]), Response(body=cdr())])
    assert attempt(client, tenant, callback)["panel_retry_status"] == "cdr_available"
    callback.assert_not_called()
    assert not fiscal_posts(sessions)


@pytest.mark.parametrize("raw", [RAW + b"\n", invoice_xml(issuer="20999999999"), invoice_xml(reference="FA01-229"),
                                 invoice_xml(kind="03"), b'<!DOCTYPE x><x/>'])
def test_changed_or_unsafe_remote_xml_never_retries(tenant, raw):
    callback = Mock()
    client, sessions = retry_client(login() + [listing([retry_row()]), Response(body=raw, content_type="application/xml")])
    if raw == RAW + b"\n":
        assert attempt(client, tenant, callback)["panel_retry_reason"] == "xml_mismatch"
    else:
        with pytest.raises(panel.SmartPSEPanelException):
            attempt(client, tenant, callback)
    callback.assert_not_called()
    assert not fiscal_posts(sessions)


@pytest.mark.parametrize("original", [ValueError("lease veto"), emission_leases.LeaseLost()])
def test_callback_exception_is_not_wrapped_or_mistaken_for_post_attempt(tenant, original):
    callback = Mock(side_effect=original)
    client, sessions = retry_client(ready())
    with pytest.raises(type(original)) as err:
        attempt(client, tenant, callback)
    assert err.value is original
    assert not fiscal_posts(sessions)


@pytest.mark.parametrize("value", [False, None, 0, 1, "true", Mock()])
def test_callback_without_literal_true_vetoes_post(tenant, value):
    client, sessions = retry_client(ready())
    result = attempt(client, tenant, Mock(return_value=value))
    assert result["panel_retry_attempted"] is False and result["panel_retry_reason"] == "callback_veto"
    assert not fiscal_posts(sessions)


def test_retry_disabled_after_prefetch_vetoes_before_callback(tenant, monkeypatch):
    client, sessions = retry_client(ready())
    original = sessions[0].request
    reads = []
    def disable_on_revalidation(method, url, **kwargs):
        if url.endswith("/panel/documentos"):
            reads.append(url)
            if len(reads) == 2:
                monkeypatch.setattr(settings, "SMARTPSE_PANEL_RETRY_TENANT_IDS", "")
        return original(method, url, **kwargs)
    sessions[0].request = disable_on_revalidation
    callback = Mock(return_value=True)
    assert attempt(client, tenant, callback)["panel_retry_reason"] == "rollout_disabled"
    callback.assert_not_called()
    assert not fiscal_posts(sessions)


def test_known_panel_credentials_are_redacted_in_callback_and_result_metadata(tenant):
    message = "HTTP 503 " + PASSWORD + " offline@example.test"
    candidate = retry_row(error_message=message, hash=PASSWORD)
    client, _ = retry_client(ready(initial=candidate, latest=candidate))
    callback = Mock(return_value=True)
    result = attempt(client, tenant, callback)
    assert PASSWORD not in repr(result)
    assert "offline@example.test" not in repr(result)
    assert PASSWORD not in repr(callback.call_args)
    assert callback.call_args.args[0]["provider_xml_hash"] == "***"


@pytest.mark.parametrize("response", [Response(401), Response(419), Response(403), Response(422), Response(429),
    Response(500), Response(302, redirect="/panel/documentos"), Response(302, redirect="https://attacker.invalid/"),
    requests.Timeout(PASSWORD), requests.ConnectionError(PASSWORD)])
def test_post_errors_are_ambiguous_and_never_retry_or_refresh_auth(tenant, response):
    callback = Mock(return_value=True)
    client, sessions = retry_client(ready(post=response))
    with pytest.raises(panel.SmartPSEPanelRetryException) as err:
        attempt(client, tenant, callback)
    assert err.value.response_data["panel_retry_attempted"] is True
    assert err.value.response_data["panel_retry_status"] == "ambiguous"
    assert err.value.partial_result["pending"] is True
    assert err.value.response_data["cdr"] is None
    assert PASSWORD not in str(err.value)
    assert PASSWORD not in repr(err.value.response_data)
    assert len(fiscal_posts(sessions)) == 1
    assert sum(call[0] == "POST" and call[1].endswith("/login") for call in sessions[0].calls) == 1
    callback.assert_called_once()


@pytest.mark.parametrize("content_type", ["application/json", "application/json; charset=utf-8", "Application/JSON"])
def test_same_post_negative_transient_json_confirms_failure_without_acceptance(tenant, content_type):
    message = "[HTTP] Service Unavailable"
    raw = json.dumps({"ok": False, "message": message}).encode()
    client, sessions = retry_client(ready(post=Response(body=raw, content_type=content_type)))
    callback = Mock(return_value=True)
    result = attempt(client, tenant, callback)
    assert result["panel_retry_status"] == "confirmed_transient_failure"
    assert result["panel_retry_outcome"] == {
        "source": "retry_response", "response_sha256": hashlib.sha256(raw).hexdigest(), "message": message,
    }
    assert result["provider_status_code"] == 200
    assert result["pending"] is True and result["estado"] == 202 and result["cdr"] is None
    assert "provider_verification_status" not in result
    assert result["panel_retry_attempted"] is True
    callback.assert_called_once()
    assert len(fiscal_posts(sessions)) == 1


@pytest.mark.parametrize("payload", [
    {"ok": True, "message": "[HTTP] Service Unavailable"},
    {"ok": 0, "message": "[HTTP] Service Unavailable"},
    {"ok": None, "message": "[HTTP] Service Unavailable"},
    {"ok": "false", "message": "[HTTP] Service Unavailable"},
    {"ok": [], "message": "[HTTP] Service Unavailable"},
    {"ok": {}, "message": "[HTTP] Service Unavailable"},
    {"ok": False}, {"message": "[HTTP] Service Unavailable"},
    {"ok": False, "message": None}, {"ok": False, "message": 503},
    {"ok": False, "message": False}, {"ok": False, "message": ["[HTTP] Service Unavailable"]},
    {"ok": False, "message": {"error": "[HTTP] Service Unavailable"}},
    {"ok": False, "message": ""}, {"ok": False, "message": " "},
    {"ok": False, "message": "Processing"}, {"ok": False, "message": "En proceso"},
    {"ok": False, "message": "Aceptado HTTP 503"},
    {"ok": False, "message": "HTTP 503 duplicado"},
    {"ok": False, "message": "Error desconocido"},
    {"ok": False, "message": "Service Unavailable"},
    {"ok": False, "message": "HTTP 503 " + "x" * 4000},
    {"ok": False, "message": "[HTTP] Service Unavailable", "accepted": True},
    {"ok": False, "message": "[HTTP] Service Unavailable", "pending": True},
    {"ok": False, "message": "[HTTP] Service Unavailable", "cdr": "evidence"},
    {"ok": False, "message": "[HTTP] Service Unavailable", "ticket": "ticket"},
    {"ok": False, "message": "[HTTP] Service Unavailable", "status": "processing"},
    {"ok": False, "message": "[HTTP] Service Unavailable", "unknown": None},
    [{"ok": False, "message": "[HTTP] Service Unavailable"}], None, False, 200, "[HTTP] Service Unavailable",
])
def test_unrecognized_or_contradictory_post_json_never_confirms_transient_failure(tenant, payload):
    client, sessions = retry_client(ready(post=Response(body=json.dumps(payload).encode())))
    result = attempt(client, tenant)
    assert result["panel_retry_status"] == "response_received"
    assert "panel_retry_outcome" not in result
    assert result["pending"] is True and result["cdr"] is None
    assert len(fiscal_posts(sessions)) == 1


@pytest.mark.parametrize("raw", [
    b'{"ok":true,"ok":false,"message":"[HTTP] Service Unavailable"}',
    b'{"ok":false,"ok":true,"message":"[HTTP] Service Unavailable"}',
    b'{"ok":false,"message":"Accepted","message":"[HTTP] Service Unavailable"}',
    b'{"ok":false,"message":"[HTTP] Service Unavailable","message":"Accepted"}',
    b'{"ok":true,"\\u006f\\u006b":false,"message":"[HTTP] Service Unavailable"}',
    b'{"ok":NaN,"message":"[HTTP] Service Unavailable"}',
    b'{"ok":Infinity,"message":"[HTTP] Service Unavailable"}',
    b'{"ok":false,"message":"[HTTP] Service Unavailable"} null',
    b'{"ok":false,"message":"[HTTP] Service Unavailable"',
    b'{"ok":false,"message":"\xff"}', b'not json', b'',
])
def test_duplicate_keys_or_invalid_post_json_never_confirms_failure(tenant, raw):
    client, sessions = retry_client(ready(post=Response(body=raw)))
    result = attempt(client, tenant)
    assert result["panel_retry_status"] == "response_received"
    assert "panel_retry_outcome" not in result
    assert len(fiscal_posts(sessions)) == 1


@pytest.mark.parametrize("content_type", ["text/html", "text/plain", "application/problem+json",
                                        "application/jsonish", "", None])
def test_transient_body_requires_json_media_type(tenant, content_type):
    raw = b'{"ok":false,"message":"[HTTP] Service Unavailable"}'
    client, sessions = retry_client(ready(post=Response(body=raw, content_type=content_type)))
    result = attempt(client, tenant)
    assert result["panel_retry_status"] == "response_received"
    assert "panel_retry_outcome" not in result
    assert len(fiscal_posts(sessions)) == 1


@pytest.mark.parametrize("status", [201, 202, 203, 204])
def test_non_200_success_status_cannot_confirm_retry_failure(tenant, status):
    raw = b'{"ok":false,"message":"[HTTP] Service Unavailable"}'
    client, sessions = retry_client(ready(post=Response(status, body=raw)))
    result = attempt(client, tenant)
    assert result["panel_retry_status"] == "response_received"
    assert "panel_retry_outcome" not in result
    assert len(fiscal_posts(sessions)) == 1


@pytest.mark.parametrize("status", [401, 419, 422, 429, 500, 502, 503, 504])
def test_non_200_error_status_is_ambiguous_even_with_negative_transient_json(tenant, status):
    raw = b'{"ok":false,"message":"[HTTP] Service Unavailable"}'
    client, sessions = retry_client(ready(post=Response(status, body=raw)))
    with pytest.raises(panel.SmartPSEPanelRetryException) as err:
        attempt(client, tenant)
    assert err.value.response_data["panel_retry_status"] == "ambiguous"
    assert "panel_retry_outcome" not in err.value.response_data
    assert len(fiscal_posts(sessions)) == 1


def test_confirmed_failure_message_redacts_known_credentials_but_hashes_original_body(tenant):
    message = "[HTTP] Service Unavailable " + PASSWORD + " offline@example.test"
    raw = json.dumps({"ok": False, "message": message}).encode()
    client, sessions = retry_client(ready(post=Response(body=raw)))
    result = attempt(client, tenant)
    assert result["panel_retry_status"] == "confirmed_transient_failure"
    assert result["panel_retry_outcome"]["message"] == "[HTTP] Service Unavailable *** ***"
    assert result["panel_retry_outcome"]["response_sha256"] == hashlib.sha256(raw).hexdigest()
    assert PASSWORD not in repr(result) and "offline@example.test" not in repr(result)
    assert len(fiscal_posts(sessions)) == 1


def test_panel_failure_shape_with_explicit_error_state_confirms_temporary_failure(tenant):
    # FERR-1 proved the panel response includes state. Its temporary error
    # variant remains synthetic: the real FERR-1 response was a 2074 rejection.
    raw = json.dumps({"ok": False, "message": "[HTTP] Service Unavailable", "state": "error"}).encode()
    client, sessions = retry_client(ready(post=Response(body=raw)))
    result = attempt(client, tenant)
    assert result["panel_retry_status"] == "confirmed_transient_failure"
    assert result["panel_retry_outcome"]["response_sha256"] == hashlib.sha256(raw).hexdigest()
    assert len(fiscal_posts(sessions)) == 1


@pytest.mark.parametrize("state", ["rechazado", "aceptado", "firmado", "pendiente", "procesando",
                                  "processing", "unknown", "", None, False, 0, [], {}])
def test_temporary_message_with_non_error_state_remains_consultation_only(tenant, state):
    raw = json.dumps({"ok": False, "message": "HTTP 503 Service Unavailable", "state": state}).encode()
    client, _ = retry_client(ready(post=Response(body=raw)))
    result = attempt(client, tenant)
    assert result["panel_retry_status"] == "response_received"
    assert "panel_retry_outcome" not in result


def test_real_demo_negative_panel_response_never_confirms_transient_failure(tenant):
    raw = json.dumps({"ok": False, "state": "rechazado", "message":
        "[2074] UBLVersionID - La version del UBL no es correcta"}).encode()
    client, _ = retry_client(ready(post=Response(body=raw)))
    result = attempt(client, tenant)
    assert result["panel_retry_status"] == "response_received"
    assert "panel_retry_outcome" not in result


@pytest.mark.parametrize("contradiction", [
    "processing", "procesando", "en procesamiento", "pending", "pendiente", "queued", "queue",
    "encolado", "en cola", "ticket 123", "success", "exito", "éxito", "completed", "completado",
    "enviado", "submitted", "retry scheduled", "retrying", "reintentando",
    "PROCESAMIENTO", "retry\nscheduled", "en\tcola",
])
def test_transient_post_message_with_contradictory_outcome_does_not_confirm_failure(tenant, contradiction):
    message = "HTTP 503 pero " + contradiction
    raw = json.dumps({"ok": False, "message": message}).encode()
    callback = Mock(return_value=True)
    client, sessions = retry_client(ready(post=Response(body=raw)))
    result = attempt(client, tenant, callback)
    assert panel.confirmed_transient_retry_error(message) is False
    assert result["panel_retry_status"] == "response_received"
    assert "panel_retry_outcome" not in result
    assert result["pending"] is True and result["cdr"] is None
    assert len(fiscal_posts(sessions)) == 1
    callback.assert_called_once()


@pytest.mark.parametrize("message", ["HTTP 500", "HTTP 502", "status_code=503", "HTTP 504",
                                    "[HTTP] Service Unavailable", "[HTTP] Bad Gateway", "[HTTP] Gateway Timeout"])
def test_confirmed_transient_predicate_keeps_supported_temporary_categories(message):
    assert panel.confirmed_transient_retry_error(message) is True


def test_confirmation_veto_does_not_expand_or_change_prefetch_eligibility(tenant):
    message = "HTTP 503 pero en procesamiento"
    candidate = retry_row(error_message=message)
    assert panel.transient_retry_error(message) is True
    assert panel.confirmed_transient_retry_error(message) is False
    client, sessions = retry_client(ready(initial=candidate, latest=candidate))
    assert attempt(client, tenant)["panel_retry_attempted"] is True
    assert len(fiscal_posts(sessions)) == 1


def test_retry_flag_cannot_authorize_a_post_through_read_only_request(tenant):
    client, sessions = retry_client(login() + [listing(), Response(body=cdr())])
    assert client.recover_invoice(tenant, NAME, environment="produccion")["cdr"]
    with pytest.raises(panel.SmartPSEPanelException, match="fuera del alcance"):
        client._request("POST", "/panel/documentos/444364/reintentar", retry_document_id="444364")
    assert not fiscal_posts(sessions)


def test_concurrent_retry_calls_share_one_session_and_are_serialized(tenant):
    second = [listing([retry_row()]), Response(body=RAW, content_type="application/xml"), listing([retry_row()]), Response(200)]
    client, sessions = retry_client(ready() + second)
    original = sessions[0].request
    guard = threading.Lock()
    active = [0, 0]
    def slow(*args, **kwargs):
        with guard:
            active[0] += 1
            active[1] = max(active[1], active[0])
        try:
            time.sleep(0.002)
            return original(*args, **kwargs)
        finally:
            with guard:
                active[0] -= 1
    sessions[0].request = slow
    # Persistent one-attempt policy belongs to the callback/worker. Simulate it
    # across two competing calls for the same invoice under the shared lock.
    called = []
    def once(metadata):
        if called:
            return False
        called.append(metadata)
        return True
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: attempt(client, tenant, once), range(2)))
    assert active[1] == 1
    assert sum(result["panel_retry_attempted"] for result in results) == 1
    assert len(fiscal_posts(sessions)) == 1
