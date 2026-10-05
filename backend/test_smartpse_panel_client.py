"""Offline panel contracts: no sends, credentials, origin and immutable CDR identity."""
import base64
from concurrent.futures import ThreadPoolExecutor
from html import escape
import json
import threading
import time
from types import SimpleNamespace

from pydantic import SecretStr
import pytest
import requests

from config import settings
from services import smartpse_panel_client as panel


NAME = "20606751509-01-FA01-00000228"
PASSWORD = "offline-password-must-never-appear"


def cdr(*, issuer="20606751509", reference="FA01-228", code="0"):
    return (f'<ar:ApplicationResponse xmlns:ar="urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2" '
            f'xmlns:cac="{panel.NS["cac"]}" xmlns:cbc="{panel.NS["cbc"]}">'
            f'<cac:ReceiverParty><cac:PartyIdentification><cbc:ID>{issuer}</cbc:ID></cac:PartyIdentification></cac:ReceiverParty>'
            f'<cac:DocumentResponse><cac:Response><cbc:ReferenceID>{reference}</cbc:ReferenceID>'
            f'<cbc:ResponseCode>{code}</cbc:ResponseCode></cac:Response><cac:DocumentReference>'
            f'<cbc:ID>{reference}</cbc:ID></cac:DocumentReference></cac:DocumentResponse></ar:ApplicationResponse>').encode()


def row(**kwargs):
    return dict({"id": 444364, "company_id": 384, "xml_filename": NAME,
                 "doc_type": "01", "environment": "produccion", "has_cdr": True}, **kwargs)


class Response:
    def __init__(self, status=200, *, body=b"", page=None, redirect=None, content_type="application/json"):
        self.status_code = status
        self.headers = {"Content-Type": content_type}
        if redirect:
            self.headers["Location"] = redirect
        self.raw = json.dumps(page).encode() if page is not None else body
        if page is None and body.startswith(b'<ar:ApplicationResponse'):
            self.headers["Content-Type"] = "application/xml"
        self.closed = False

    def iter_content(self, chunk_size):
        for start in range(0, len(self.raw), chunk_size):
            yield self.raw[start:start + chunk_size]

    def close(self):
        self.closed = True


def login():
    data = escape(json.dumps({"component": "Auth/Login", "props": {}}), quote=True)
    return [Response(body=f'<div id="app" data-page="{data}"></div>'.encode(), content_type="text/html"),
            Response(302, redirect="/dashboard")]


def listing(rows=None, last_page=1):
    return Response(page={"component": "Documents/Index", "props": {
        "documents": {"data": [row()] if rows is None else rows, "last_page": last_page}}})


class Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.headers = {}
        self.cookies = requests.cookies.RequestsCookieJar()
        self.cookies.set("XSRF-TOKEN", "csrf%2Ftoken")
        self.calls = []
        self.closed = False

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        assert url.startswith(panel.ORIGIN + "/")
        assert kwargs["allow_redirects"] is False
        assert method == "GET" or (method == "POST" and url == panel.ORIGIN + "/login")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def enabled(monkeypatch):
    monkeypatch.setattr(settings, "SMARTPSE_PANEL_RECOVERY_TENANT_IDS", "5")


@pytest.fixture
def tenant():
    return SimpleNamespace(id=5, business_ruc="20606751509", smartpse_company_id="384", smartpse_environment="produccion")


def client_for(*responses, now_fn=None):
    sessions = [Session(values) for values in responses]
    remaining = list(sessions)
    client = panel.SmartPSEPanelClient(session_factory=lambda: remaining.pop(0),
        email=SecretStr("offline@example.test"), password=SecretStr(PASSWORD), now_fn=now_fn)
    return client, sessions


def test_recovery_uses_csrf_exact_company_filters_and_preserves_cdr(tenant):
    raw = cdr()
    client, sessions = client_for(login() + [listing(), Response(body=raw, content_type="application/xml")])
    result = client.recover_invoice(tenant, NAME, environment="produccion")
    assert result["estado"] == 200
    assert result["recovery_source"] == "smartpse_panel"
    assert base64.b64decode(result["cdr"]) == raw
    calls = sessions[0].calls
    assert calls[1][2]["headers"]["X-XSRF-TOKEN"] == "csrf/token"
    assert calls[1][2]["json"] == {"email": "offline@example.test", "password": PASSWORD, "remember": False}
    assert calls[2][2]["params"] == {"company_id": "384", "search": "00000228", "doc_type": "01",
                                         "environment": "produccion", "page": 1}
    assert calls[3][1] == panel.ORIGIN + "/panel/documentos/444364/cdr"


@pytest.mark.parametrize("expired", [Response(401), Response(419), Response(302, redirect="/login"),
    Response(page={"component": "Auth/Login", "props": {}})])
def test_session_renews_once(tenant, expired):
    client, sessions = client_for(login() + [expired], login() + [listing(), Response(body=cdr())])
    assert client.recover_invoice(tenant, NAME, environment="produccion")["cdr"]
    assert sessions[0].closed
    assert len(sessions[0].cookies) == 0
    assert len([call for session in sessions for call in session.calls if call[0] == "POST"]) == 2


def test_repeated_expiry_stops_auth_loop_and_cools_down(tenant):
    clock = [1.0]
    client, sessions = client_for(login() + [Response(419)], login() + [Response(401)], now_fn=lambda: clock[0])
    for _ in range(2):
        with pytest.raises(panel.SmartPSEPanelException) as failure:
            client.recover_invoice(tenant, NAME, environment="produccion")
        assert failure.value.response_data == {"recovery_source": "smartpse_panel"}
    assert sum(len(session.calls) for session in sessions) == 6


def test_bad_credentials_cool_down_and_never_leak_body_or_password(tenant):
    client, sessions = client_for([login()[0], Response(422, body=PASSWORD.encode())])
    for _ in range(2):
        with pytest.raises(panel.SmartPSEPanelException) as failure:
            client.recover_invoice(tenant, NAME, environment="produccion")
        assert PASSWORD not in str(failure.value)
        assert PASSWORD not in repr(failure.value.response_data)
    assert len(sessions[0].calls) == 2
    assert sessions[0].closed and not sessions[0].cookies


@pytest.mark.parametrize("changes", [{"company_id": 999}, {"environment": "demo"}, {"doc_type": "03"},
    {"id": "https://attacker.invalid/secret"}])
def test_wrong_row_identity_never_downloads(tenant, changes):
    client, sessions = client_for(login() + [listing([row(**changes)])])
    with pytest.raises(panel.SmartPSEPanelException):
        client.recover_invoice(tenant, NAME, environment="produccion")
    assert len(sessions[0].calls) == 3


@pytest.mark.parametrize("attribute,value", [("id", 999), ("business_ruc", "20999999999"),
    ("smartpse_company_id", "https://attacker.invalid"), ("smartpse_environment", "demo")])
def test_invalid_tenant_context_never_logs_in(tenant, attribute, value):
    setattr(tenant, attribute, value)
    client, sessions = client_for([])
    with pytest.raises(panel.SmartPSEPanelException):
        client.recover_invoice(tenant, NAME, environment="produccion")
    assert not sessions[0].calls


@pytest.mark.parametrize("raw", [cdr(issuer="20999999999"), cdr(reference="FA01-229"),
    cdr().replace(b'ApplicationResponse-2', b'Invoice-2'), b'<!DOCTYPE x [<!ENTITY a "bad">]><x/>',
    cdr().decode().encode("utf-16"), b'<html>login</html>', cdr(code="")])
def test_invalid_cdr_is_never_returned(tenant, raw):
    client, _ = client_for(login() + [listing(), Response(body=raw)])
    with pytest.raises(panel.SmartPSEPanelException):
        client.recover_invoice(tenant, NAME, environment="produccion")


@pytest.mark.parametrize("responses", [[listing([])], [listing([row(has_cdr=False)])],
    [listing(), Response(404)], [Response(404)], [listing(last_page=panel.MAX_PAGES + 1)]])
def test_missing_evidence_stays_pending(tenant, responses):
    client, _ = client_for(login() + responses)
    result = client.recover_invoice(tenant, NAME, environment="produccion")
    assert result["estado"] == 202 and not result["cdr"]
    assert result["recovery_source"] == "smartpse_panel"


def test_duplicates_across_pages_are_rejected_without_download(tenant):
    client, sessions = client_for(login() + [listing(last_page=2), listing(last_page=2)])
    with pytest.raises(panel.SmartPSEPanelException):
        client.recover_invoice(tenant, NAME, environment="produccion")
    assert len(sessions[0].calls) == 4
    assert sessions[0].calls[-1][2]["params"]["page"] == 2


@pytest.mark.parametrize("where", ["login", "documents", "cdr"])
def test_external_redirects_are_never_followed(tenant, where):
    redirect = Response(302, redirect="https://attacker.invalid/" + PASSWORD)
    values = [login()[0], redirect] if where == "login" else login() + [redirect]
    if where == "cdr":
        values = login() + [listing(), redirect]
    client, sessions = client_for(values)
    with pytest.raises(panel.SmartPSEPanelException) as failure:
        client.recover_invoice(tenant, NAME, environment="produccion")
    assert PASSWORD not in str(failure.value)
    assert all(call[1].startswith(panel.ORIGIN) for call in sessions[0].calls)


def test_rate_limit_defers_calls_without_auth_loop(tenant):
    response = Response(429, body=PASSWORD.encode())
    response.headers["Retry-After"] = "120"
    client, sessions = client_for(login() + [response], now_fn=lambda: 1.0)
    with pytest.raises(panel.SmartPSEPanelException) as failure:
        client.recover_invoice(tenant, NAME, environment="produccion")
    assert failure.value.status_code == 429
    with pytest.raises(panel.SmartPSEPanelException):
        client.recover_invoice(tenant, NAME, environment="produccion")
    assert len(sessions[0].calls) == 3
    assert PASSWORD not in str(failure.value)


def test_transport_exception_does_not_expose_credentials(tenant):
    client, _ = client_for(login() + [requests.ConnectionError(PASSWORD)])
    with pytest.raises(panel.SmartPSEPanelException) as failure:
        client.recover_invoice(tenant, NAME, environment="produccion")
    assert PASSWORD not in str(failure.value)
    assert failure.value.__suppress_context__


def test_session_ttl_renews_without_persisting_credentials(tenant):
    clock = [1.0]
    client, sessions = client_for(login() + [listing(), Response(body=cdr())],
        login() + [listing(), Response(body=cdr())], now_fn=lambda: clock[0])
    assert client.recover_invoice(tenant, NAME, environment="produccion")["cdr"]
    clock[0] += settings.SMARTPSE_PANEL_SESSION_TTL_SECONDS + 1
    assert client.recover_invoice(tenant, NAME, environment="produccion")["cdr"]
    assert sessions[0].closed


def test_large_cdr_is_rejected_during_download(tenant, monkeypatch):
    monkeypatch.setattr(panel, "MAX_CDR_BYTES", 20)
    response = Response(body=cdr())
    client, _ = client_for(login() + [listing(), response])
    with pytest.raises(panel.SmartPSEPanelException):
        client.recover_invoice(tenant, NAME, environment="produccion")
    assert response.closed


def test_concurrent_recovery_serializes_session_and_logs_in_once(tenant):
    client, sessions = client_for(login() + [listing(), Response(body=cdr()), listing(), Response(body=cdr())])
    session = sessions[0]
    original = session.request
    active = [0, 0]
    guard = threading.Lock()
    def slow_request(*args, **kwargs):
        with guard:
            active[0] += 1
            active[1] = max(active[1], active[0])
        try:
            time.sleep(0.005)
            return original(*args, **kwargs)
        finally:
            with guard:
                active[0] -= 1
    session.request = slow_request
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: client.recover_invoice(tenant, NAME, environment="produccion"), range(2)))
    assert all(result["cdr"] for result in results)
    assert active[1] == 1
    assert sum(call[0] == "POST" for call in session.calls) == 1


def test_settings_credentials_are_secret_strings():
    assert isinstance(settings.SMARTPSE_PANEL_EMAIL, SecretStr)
    assert isinstance(settings.SMARTPSE_PANEL_PASSWORD, SecretStr)


def test_close_clears_session_and_next_read_logs_in_again(tenant):
    client, sessions = client_for(login() + [listing(), Response(body=cdr())],
        login() + [listing(), Response(body=cdr())])
    client.recover_invoice(tenant, NAME, environment="produccion")
    client.close()
    assert sessions[0].closed and not sessions[0].cookies
    client.recover_invoice(tenant, NAME, environment="produccion")
    client.close()
    assert sessions[1].closed and not sessions[1].cookies


def test_login_page_instead_of_cdr_renews_once(tenant):
    expired = Response(page={"component": "Auth/Login", "props": {}})
    client, sessions = client_for(login() + [listing(), expired], login() + [listing(), Response(body=cdr())])
    assert client.recover_invoice(tenant, NAME, environment="produccion")["cdr"]
    assert sessions[0].closed


def test_slow_stream_obeys_total_recovery_budget(tenant):
    clock = [1.0]
    response = Response(body=cdr())
    def drip(chunk_size):
        assert chunk_size == 1
        clock[0] += settings.SMARTPSE_PANEL_RECOVERY_BUDGET_SECONDS + 1
        yield b"<"
    response.iter_content = drip
    client, _ = client_for(login() + [listing(), response], now_fn=lambda: clock[0])
    with pytest.raises(panel.SmartPSEPanelException, match="agotó el tiempo"):
        client.recover_invoice(tenant, NAME, environment="produccion")
    assert response.closed


def test_compressed_stream_is_rejected_before_decoder_can_buffer(tenant):
    response = Response(body=cdr())
    response.headers["Content-Encoding"] = "gzip"
    client, sessions = client_for(login() + [listing(), response])
    with pytest.raises(panel.SmartPSEPanelException, match="codificación"):
        client.recover_invoice(tenant, NAME, environment="produccion")
    assert sessions[0].headers["Accept-Encoding"] == "identity"
    assert response.closed


def invoice_xml(*, issuer="20606751509", reference="FA01-00000228", kind="01"):
    return (f'<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" '
            f'xmlns:cac="{panel.NS["cac"]}" xmlns:cbc="{panel.NS["cbc"]}">'
            f'<cbc:ID>{reference}</cbc:ID><cbc:InvoiceTypeCode>{kind}</cbc:InvoiceTypeCode>'
            f'<cac:AccountingSupplierParty><cac:Party><cac:PartyIdentification><cbc:ID>{issuer}</cbc:ID>'
            f'</cac:PartyIdentification></cac:Party></cac:AccountingSupplierParty></Invoice>\n').encode()


def test_cdr_and_missing_local_xml_can_be_recovered_together(tenant):
    raw = invoice_xml()
    client, sessions = client_for(login() + [listing(), Response(body=cdr()),
        Response(body=raw, content_type="application/xml")])
    result = client.recover_invoice(tenant, NAME, environment="produccion", include_xml=True)
    assert result["estado"] == 200 and result["cdr"]
    assert base64.b64decode(result["xml_firmado"]) == raw
    assert sessions[0].calls[-1][1] == panel.ORIGIN + "/panel/documentos/444364/xml"


@pytest.mark.parametrize("raw", [invoice_xml(issuer="20999999999"), invoice_xml(reference="FA01-229"),
    invoice_xml(kind="03"), b'<!DOCTYPE x><x/>'])
def test_foreign_or_unsafe_recovered_xml_cannot_complete_recovery(tenant, raw):
    client, _ = client_for(login() + [listing(), Response(body=cdr()),
        Response(body=raw, content_type="application/xml")])
    with pytest.raises(panel.SmartPSEPanelException):
        client.recover_invoice(tenant, NAME, environment="produccion", include_xml=True)


def test_xml_absent_after_cdr_preserves_evidence_without_claiming_completion(tenant):
    client, _ = client_for(login() + [listing(), Response(body=cdr()), Response(404)])
    result = client.recover_invoice(tenant, NAME, environment="produccion", include_xml=True)
    assert result["estado"] == 202
    assert base64.b64decode(result["cdr"]) == cdr()
    assert result["provider_document_id"] == "444364"
    assert result["environment"] == "produccion"
    assert not result.get("xml_firmado")


@pytest.mark.parametrize("signed_metadata", [{}, {"has_signed_xml": False}, {"has_signed_xml": "true"}])
def test_include_xml_does_not_download_unsigned_evidence_without_cdr(tenant, signed_metadata):
    client, sessions = client_for(login() + [listing([row(has_cdr=False, **signed_metadata)])])
    result = client.recover_invoice(tenant, NAME, environment="produccion", include_xml=True)
    assert result["estado"] == 202
    assert len(sessions[0].calls) == 3


def test_signed_xml_without_cdr_is_recovered_as_pending(tenant):
    raw = invoice_xml()
    client, sessions = client_for(login() + [listing([row(has_cdr=False, has_signed_xml=True)]),
        Response(body=raw, content_type="application/xml")])
    result = client.recover_invoice(tenant, NAME, environment="produccion", include_xml=True)
    assert result["estado"] == 202 and result["cdr"] is None
    assert result["provider_document_id"] == "444364"
    assert result["environment"] == "produccion"
    assert base64.b64decode(result["xml_firmado"]) == raw
    assert sessions[0].calls[-1][1] == panel.ORIGIN + "/panel/documentos/444364/xml"
    assert not any(url.endswith("/cdr") for _, url, _ in sessions[0].calls)


def test_signed_xml_without_cdr_is_not_requested_if_include_xml_is_false(tenant):
    client, sessions = client_for(login() + [listing([row(has_cdr=False, has_signed_xml=True)])])
    result = client.recover_invoice(tenant, NAME, environment="produccion")
    assert result["estado"] == 202 and result["cdr"] is None
    assert len(sessions[0].calls) == 3


def test_pending_signed_xml_download_absent_preserves_remote_identity(tenant):
    client, _ = client_for(login() + [listing([row(has_cdr=False, has_signed_xml=True)]), Response(404)])
    result = client.recover_invoice(tenant, NAME, environment="produccion", include_xml=True)
    assert result["estado"] == 202 and result["cdr"] is None
    assert result["provider_document_id"] == "444364"
    assert result["environment"] == "produccion"
    assert not result.get("xml_firmado")


@pytest.mark.parametrize("raw", [invoice_xml(issuer="20999999999"), invoice_xml(reference="FA01-229"),
    invoice_xml(kind="03"), b'<!DOCTYPE x><x/>'])
def test_invalid_pending_xml_cannot_complete_recovery(tenant, raw):
    client, _ = client_for(login() + [listing([row(has_cdr=False, has_signed_xml=True)]),
        Response(body=raw, content_type="application/xml")])
    with pytest.raises(panel.SmartPSEPanelException):
        client.recover_invoice(tenant, NAME, environment="produccion", include_xml=True)


def test_rollout_is_explicit_and_invalid_ids_never_match_wildcard(monkeypatch):
    monkeypatch.setattr(settings, "SMARTPSE_PANEL_RECOVERY_TENANT_IDS", "")
    assert not panel.enabled_for_tenant(5)
    monkeypatch.setattr(settings, "SMARTPSE_PANEL_RECOVERY_TENANT_IDS", "*")
    assert panel.enabled_for_tenant(5)
    assert not panel.enabled_for_tenant(None)
    assert not panel.enabled_for_tenant(0)
