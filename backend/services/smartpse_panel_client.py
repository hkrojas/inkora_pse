"""Bounded evidence recovery and separately gated retry through Smart PSE's panel.

Evidence recovery reads cached artifacts. An explicit retry uses its own rollout
and a fenced callback; fiscal acceptance still requires a matching CDR.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import threading
import time
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlsplit
from xml.etree import ElementTree as ET

import requests

from config import settings
from services.smartpse_client import SmartPSEException


ORIGIN = "https://panel.smartpse.pe"
MAX_PAGE_BYTES = 4_000_000
MAX_CDR_BYTES = 2_000_000
MAX_PAGES = 5
NS = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}
_NAME = re.compile(r"([0-9]{11})-01-([A-Z0-9]{4})-([0-9]{1,8})")


class SmartPSEPanelException(SmartPSEException):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message, {"recovery_source": "smartpse_panel"}, status_code=status_code)


class SmartPSEPanelRetryException(SmartPSEPanelException):
    """An attempted panel POST has an uncertain fiscal outcome; never repeat it."""

    def __init__(self, message: str, result: dict, *, status_code: int | None = None):
        super().__init__(message, status_code=status_code)
        self.response_data = dict(result)
        self.partial_result = dict(result)


class _SessionExpired(Exception):
    pass


def enabled_for_tenant(tenant_id: int) -> bool:
    if not re.fullmatch(r"[0-9]{1,20}", str(tenant_id)) or int(tenant_id) < 1:
        return False
    values = settings.SMARTPSE_PANEL_RECOVERY_TENANT_IDS.strip()
    return values == "*" or str(tenant_id) in {part.strip() for part in values.split(",") if part.strip()}


def retry_enabled_for_tenant(tenant_id: int) -> bool:
    if not re.fullmatch(r"[0-9]{1,20}", str(tenant_id)) or int(tenant_id) < 1:
        return False
    values = getattr(settings, "SMARTPSE_PANEL_RETRY_TENANT_IDS", "").strip()
    return str(tenant_id) in {part.strip() for part in values.split(",") if part.strip().isdigit()}


def transient_retry_error(message) -> bool:
    """Admit known temporary provider failures, never a generic error or timeout."""
    if not isinstance(message, str) or not message.strip() or len(message) > 4000:
        return False
    lowered = message.lower()
    forbidden = ("1033", "0111", "duplic", "rechaz", "reject", "credencial", "credential",
                 "validaci", "validation", "unauthorized", "unauthorised", "forbidden", "permission",
                 "permiso", "aceptad", "accepted", "informado", "registrado", "ticket")
    if any(value in lowered for value in forbidden):
        return False
    # Observed on an existing signed invoice without CDR. The marker alone
    # does not prove a retryable SUNAT failure; require its specific message.
    normalized = re.sub(r"\s+", " ", lowered).strip()
    if re.fullmatch(r"\[circuit_open\] sunat no responde, reintente en unos segundos[.!]?", normalized):
        return True
    return bool(re.search(r"\b(?:http|status(?:_code)?)\s*[:=]?\s*(?:500|502|503|504)\b", lowered)
                or re.search(r"\[http\]\s*(?:service unavailable|bad gateway|gateway timeout)\b", lowered))


def confirmed_transient_retry_error(message) -> bool:
    """Require a temporary failure without signs of ongoing work or success."""
    if not transient_retry_error(message):
        return False
    normalized = re.sub(r"\s+", " ", message.lower())
    contradictory = ("processing", "procesando", "procesamiento", "pending", "pendiente", "queue",
                     "encol", "en cola", "ticket", "success", "exito", "éxito", "complet", "enviad",
                     "submitted", "retry scheduled", "retrying", "reintentando")
    return not any(value in normalized for value in contradictory)


def _confirmed_transient_retry_message(status, headers, raw):
    """Recognize only the strict supported shape of this retry POST response."""
    content_type = headers.get("Content-Type", "")
    if (status != 200 or not isinstance(content_type, str)
            or content_type.split(";", 1)[0].strip().lower() != "application/json"):
        return None

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError()
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError()

    try:
        response = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                              parse_constant=reject_constant)
    except (ValueError, UnicodeError, TypeError, RecursionError):
        return None
    if (not isinstance(response, dict) or set(response) not in (
            {"ok", "message"}, {"ok", "message", "state"})
            or ("state" in response and response["state"] != "error")
            or response["ok"] is not False or not isinstance(response["message"], str)
            or not confirmed_transient_retry_error(response["message"])):
        return None
    return response["message"]


def _secret(value) -> str:
    return value.get_secret_value() if hasattr(value, "get_secret_value") else str(value or "")


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.pages = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id") == "app" and attrs.get("data-page"):
            self.pages.append(json.loads(attrs["data-page"]))


def _page(raw: bytes, content_type: str) -> dict:
    try:
        text = raw.decode("utf-8")
        if "application/json" in content_type.lower():
            page = json.loads(text)
        else:
            parser = _PageParser()
            parser.feed(text)
            if len(parser.pages) != 1:
                raise ValueError()
            page = parser.pages[0]
        if not isinstance(page, dict) or not isinstance(page.get("props"), dict):
            raise ValueError()
        return page
    except (ValueError, UnicodeError, TypeError, RecursionError):
        raise SmartPSEPanelException("El panel devolvió una página no reconocible.") from None


def _document_number(value: str) -> tuple[str, int]:
    match = re.fullmatch(r"([A-Z0-9]{4})-([0-9]{1,8})", str(value or ""))
    if not match or int(match[2]) < 1:
        raise SmartPSEPanelException("El CDR no identifica el comprobante solicitado.")
    return match[1], int(match[2])


def _validate_cdr(raw: bytes, name: str) -> None:
    try:
        text = raw.decode("utf-8")
        if not raw or len(raw) > MAX_CDR_BYTES or "\x00" in text or any(
            declaration in text.upper() for declaration in ("<!DOCTYPE", "<!ENTITY")
        ):
            raise ValueError()
        root = ET.fromstring(text)
    except (ValueError, UnicodeError, ET.ParseError):
        raise SmartPSEPanelException("La descarga no contiene un CDR XML admitido.") from None
    if root.tag != "{urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2}ApplicationResponse":
        raise SmartPSEPanelException("La descarga no contiene un CDR XML admitido.")
    issuer, _, series, number = name.split("-")
    receiver = root.findtext("cac:ReceiverParty/cac:PartyIdentification/cbc:ID", namespaces=NS)
    responses = root.findall("cac:DocumentResponse", NS)
    if receiver != issuer or len(responses) != 1:
        raise SmartPSEPanelException("El CDR no corresponde a la empresa solicitada.")
    response = responses[0]
    expected = (series, int(number))
    reference = response.findtext("cac:DocumentReference/cbc:ID", namespaces=NS)
    alternate = response.findtext("cac:Response/cbc:ReferenceID", namespaces=NS)
    if _document_number(reference) != expected or (alternate and _document_number(alternate) != expected):
        raise SmartPSEPanelException("El CDR no corresponde al comprobante solicitado.")
    code = response.findtext("cac:Response/cbc:ResponseCode", namespaces=NS)
    if not code or not re.fullmatch(r"[0-9]{1,6}", code.strip()):
        raise SmartPSEPanelException("El CDR no contiene un resultado fiscal reconocible.")


def _validate_invoice_xml(raw: bytes, name: str) -> None:
    try:
        text = raw.decode("utf-8")
        if not raw or len(raw) > MAX_CDR_BYTES or "\x00" in text or any(
            declaration in text.upper() for declaration in ("<!DOCTYPE", "<!ENTITY")
        ):
            raise ValueError()
        root = ET.fromstring(text)
    except (ValueError, UnicodeError, ET.ParseError):
        raise SmartPSEPanelException("La descarga no contiene un XML fiscal admitido.") from None
    issuer, _, series, number = name.split("-")
    supplier = root.findtext("cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID", namespaces=NS)
    if (root.tag != "{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice"
            or root.findtext("cbc:InvoiceTypeCode", namespaces=NS) != "01" or supplier != issuer
            or _document_number(root.findtext("cbc:ID", namespaces=NS)) != (series, int(number))):
        raise SmartPSEPanelException("El XML fiscal no corresponde al comprobante solicitado.")


class SmartPSEPanelClient:
    def __init__(self, *, session_factory=None, email=None, password=None, now_fn=None):
        self._session_factory = session_factory or requests.Session
        self._email = email if email is not None else settings.SMARTPSE_PANEL_EMAIL
        self._password = password if password is not None else settings.SMARTPSE_PANEL_PASSWORD
        self._now = now_fn or time.monotonic
        self._session = None
        self._expires_at = 0.0
        self._blocked_until = 0.0
        self._deadline = 0.0
        self._retry_post_document_id = None
        self._lock = threading.Lock()

    def close(self):
        """Clear the in-memory cookie session after all active reads finish."""
        if not self._lock.acquire(timeout=settings.SMARTPSE_PANEL_TIMEOUT_SECONDS):
            raise SmartPSEPanelException("La sesión de recuperación está ocupada.")
        try:
            self._invalidate()
        finally:
            self._lock.release()

    def _invalidate(self):
        if self._session is not None:
            self._session.cookies.clear()
            self._session.close()
        self._session = None
        self._expires_at = 0.0

    @staticmethod
    def _redirect_path(response) -> str:
        location = response.headers.get("Location", "")
        target = urlsplit(urljoin(ORIGIN, location))
        if (not location or target.scheme != "https" or target.netloc != "panel.smartpse.pe"
                or target.username or target.password):
            raise SmartPSEPanelException("El panel devolvió una redirección fuera del destino permitido.")
        return target.path

    def _request(self, method, path, *, limit=MAX_PAGE_BYTES, retry_document_id=None, **kwargs):
        allowed = (method == "GET" and (path in {"/login", "/panel/documentos"}
                   or re.fullmatch(r"/panel/documentos/[0-9]+/(cdr|xml)", path))) or (method == "POST" and path == "/login")
        if (method == "POST" and retry_document_id is not None
                and re.fullmatch(r"[0-9]{1,20}", str(retry_document_id))
                and path == f"/panel/documentos/{retry_document_id}/reintentar"
                and self._retry_post_document_id == str(retry_document_id)):
            allowed = True
            self._retry_post_document_id = None
        if not allowed:
            raise SmartPSEPanelException("Ruta fuera del alcance de recuperación.")
        remaining = self._deadline - self._now()
        if remaining <= 0:
            raise SmartPSEPanelException("Se agotó el tiempo de recuperación del panel.")
        try:
            response = self._session.request(
                method, ORIGIN + path, timeout=(min(10, remaining), min(settings.SMARTPSE_PANEL_TIMEOUT_SECONDS, remaining)),
                allow_redirects=False, stream=True, **kwargs)
            try:
                status = response.status_code
                headers = response.headers
                if self._now() >= self._deadline:
                    raise SmartPSEPanelException("Se agotó el tiempo de recuperación del panel.")
                if status in {301, 302, 303, 307, 308}:
                    redirect = self._redirect_path(response)
                    return status, headers, b"", redirect
                if status == 429:
                    try:
                        wait = int(headers.get("Retry-After", "60"))
                    except (ValueError, TypeError):
                        wait = 60
                    self._blocked_until = self._now() + min(max(wait, 60), 3600)
                    raise SmartPSEPanelException("El panel limita temporalmente las consultas.", status_code=429)
                raw = bytearray()
                if headers.get("Content-Encoding", "identity").lower() not in {"", "identity"}:
                    raise SmartPSEPanelException("El panel devolvió una codificación de transporte no admitida.")
                # Single-byte reads expose progress even for a slow drip feed.
                # Identity encoding prevents a decoder buffering that progress.
                for chunk in response.iter_content(chunk_size=1):
                    if self._now() >= self._deadline:
                        raise SmartPSEPanelException("Se agotó el tiempo de recuperación del panel.")
                    if len(raw) + len(chunk) > limit:
                        raise SmartPSEPanelException("La respuesta del panel supera el límite permitido.")
                    raw.extend(chunk)
                return status, headers, bytes(raw), None
            finally:
                response.close()
        except requests.RequestException:
            raise SmartPSEPanelException("No se pudo completar la lectura del panel.") from None

    def _login(self):
        if self._now() < self._blocked_until:
            raise SmartPSEPanelException("La recuperación del panel está temporalmente pausada.")
        email, password = _secret(self._email).strip(), _secret(self._password)
        if not email or not password:
            raise SmartPSEPanelException("Faltan credenciales para recuperar evidencia del panel.")
        self._invalidate()
        self._session = self._session_factory()
        self._session.headers.update({"User-Agent": "Inkora-CDR-Recovery/1.0", "Accept": "application/json",
                                      "Accept-Encoding": "identity"})
        try:
            status, headers, raw, redirect = self._request("GET", "/login")
            if status != 200 or _page(raw, headers.get("Content-Type", "")).get("component") != "Auth/Login":
                raise SmartPSEPanelException("No se reconoció el formulario de autenticación del panel.")
            csrf = self._session.cookies.get("XSRF-TOKEN")
            if not csrf:
                raise SmartPSEPanelException("No se recibió protección CSRF del panel.")
            status, headers, raw, redirect = self._request("POST", "/login",
                json={"email": email, "password": password, "remember": False},
                headers={"X-XSRF-TOKEN": unquote(csrf), "Referer": ORIGIN + "/login", "Origin": ORIGIN})
            if status not in {200, 302, 303} or redirect == "/login":
                raise SmartPSEPanelException("El panel no aceptó la autenticación.", status_code=status)
            if status == 200:
                page = _page(raw, headers.get("Content-Type", ""))
                if page.get("component") == "Auth/Login" or page["props"].get("errors"):
                    raise SmartPSEPanelException("El panel no aceptó la autenticación.")
            self._expires_at = self._now() + settings.SMARTPSE_PANEL_SESSION_TTL_SECONDS
        except (SmartPSEPanelException, requests.cookies.CookieConflictError) as exc:
            self._blocked_until = max(self._blocked_until, self._now() + settings.SMARTPSE_PANEL_AUTH_COOLDOWN_SECONDS)
            self._invalidate()
            raise SmartPSEPanelException("No se pudo autenticar la recuperación del panel; está temporalmente pausada.",
                                        status_code=getattr(exc, "status_code", None)) from None

    def _get(self, path, **kwargs):
        status, headers, raw, redirect = self._request("GET", path, **kwargs)
        if status in {401, 419} or redirect == "/login":
            raise _SessionExpired()
        if redirect:
            raise SmartPSEPanelException("El panel pidió una redirección no admitida para la lectura.")
        if status == 404:
            return None
        if status != 200:
            raise SmartPSEPanelException("El panel rechazó la lectura de evidencia.", status_code=status)
        if path.endswith(("/cdr", "/xml")) and any(kind in headers.get("Content-Type", "").lower()
                                         for kind in ("text/html", "application/json")):
            page = _page(raw, headers.get("Content-Type", ""))
            if page.get("component") == "Auth/Login":
                raise _SessionExpired()
        return raw, headers

    @staticmethod
    def _pending():
        return {"estado": 202, "mensaje": "Evidencia fiscal pendiente de conciliación.",
                "recovery_source": "smartpse_panel", "cdr": None}

    def _find_invoice(self, company_id, name, environment):
        matches = []
        page_number, last_page = 1, 1
        while page_number <= last_page:
            result = self._get("/panel/documentos", params={"company_id": company_id,
                "search": name.rsplit("-", 1)[-1], "doc_type": "01", "environment": environment,
                "page": page_number})
            if result is None:
                return None
            page = _page(result[0], result[1].get("Content-Type", ""))
            if page.get("component") == "Auth/Login":
                raise _SessionExpired()
            documents = page["props"].get("documents")
            if not isinstance(documents, dict) or not isinstance(documents.get("data"), list):
                raise SmartPSEPanelException("La lista de documentos del panel no es reconocible.")
            last = documents.get("last_page", 1)
            if type(last) is not int or last < page_number or last > MAX_PAGES:
                return None
            last_page = last
            for row in documents["data"]:
                if not isinstance(row, dict):
                    raise SmartPSEPanelException("La lista contiene identidades no reconocibles.")
                if row.get("xml_filename") != name:
                    continue
                if (str(row.get("company_id")) != company_id or row.get("environment") != environment
                        or row.get("doc_type") != "01"):
                    raise SmartPSEPanelException("La evidencia del panel no coincide con empresa, ambiente o tipo.")
                matches.append(row)
            page_number += 1
        if not matches:
            return None
        if len(matches) != 1:
            raise SmartPSEPanelException("La identidad del documento es ambigua en el panel.")
        row = matches[0]
        document_id = str(row.get("id", ""))
        if not re.fullmatch(r"[0-9]{1,20}", document_id) or int(document_id) < 1:
            raise SmartPSEPanelException("El identificador del documento no es válido.")
        return row

    def _recover(self, company_id, name, environment, include_xml):
        row = self._find_invoice(company_id, name, environment)
        if row is None:
            return self._pending()
        document_id = str(row["id"])
        metadata = {"provider_document_id": document_id, "environment": environment}
        result = dict(self._pending(), **metadata)
        if row.get("has_cdr") is True:
            downloaded = self._get(f"/panel/documentos/{document_id}/cdr", limit=MAX_CDR_BYTES)
            if downloaded is not None:
                raw = downloaded[0]
                _validate_cdr(raw, name)
                result.update(estado=200, mensaje="CDR recuperado del panel.",
                              cdr=base64.b64encode(raw).decode("ascii"))
        if include_xml and (result["cdr"] or row.get("has_signed_xml") is True):
            downloaded_xml = self._get(f"/panel/documentos/{document_id}/xml", limit=MAX_CDR_BYTES)
            if downloaded_xml is None:
                # Preserve a verified CDR even when the separate XML download is
                # unavailable. The caller still requires a validated signed XML
                # before accepting the document (it may already have one).
                return dict(result, estado=202, mensaje="XML firmado pendiente de recuperacion.")
            _validate_invoice_xml(downloaded_xml[0], name)
            # The caller verifies the full signature, amounts and frozen payload.
            result["xml_firmado"] = base64.b64encode(downloaded_xml[0]).decode("ascii")
        return result

    def _retry_metadata(self, row, environment, expected_xml):
        def redacted(value):
            if not isinstance(value, str) or len(value) > 4000:
                return None
            for credential in (_secret(self._email), _secret(self._password)):
                if credential:
                    value = value.replace(credential, "***")
            return value

        return {"provider_document_id": str(row["id"]), "provider_company_id": str(row["company_id"]),
                "environment": environment,
                "xml_sha256": hashlib.sha256(expected_xml).hexdigest(), "provider_xml_hash": redacted(row.get("hash")),
                "provider_error_message": redacted(row.get("error_message")), "state": redacted(row.get("state")),
                "recovery_source": "smartpse_panel", "panel_retry_attempted": False}

    @staticmethod
    def _retry_blocked(metadata, reason):
        return {**SmartPSEPanelClient._pending(), **metadata, "pending": True,
                "panel_retry_status": "blocked", "panel_retry_reason": reason}

    @staticmethod
    def _retry_eligible(row):
        return (row.get("state") == "error" and row.get("has_cdr") is False
                and row.get("has_signed_xml") is True and not row.get("ticket")
                and transient_retry_error(row.get("error_message")))

    def _retry_existing_cdr(self, row, name, metadata):
        downloaded = self._get(f"/panel/documentos/{row['id']}/cdr", limit=MAX_CDR_BYTES)
        if downloaded is None:
            return self._retry_blocked(metadata, "cdr_unavailable")
        _validate_cdr(downloaded[0], name)
        return dict(metadata, estado=200, mensaje="CDR disponible; requiere conciliacion fiscal.",
                    cdr=base64.b64encode(downloaded[0]).decode("ascii"), panel_retry_status="cdr_available")

    def _prepare_retry(self, company_id, name, environment, expected_xml):
        row = self._find_invoice(company_id, name, environment)
        if row is None:
            return self._retry_blocked({"environment": environment, "panel_retry_attempted": False}, "not_found"), False
        metadata = self._retry_metadata(row, environment, expected_xml)
        if row.get("has_cdr") is True:
            return self._retry_existing_cdr(row, name, metadata), False
        if not self._retry_eligible(row):
            return self._retry_blocked(metadata, "ineligible_state"), False
        downloaded = self._get(f"/panel/documentos/{row['id']}/xml", limit=MAX_CDR_BYTES)
        if downloaded is None:
            return self._retry_blocked(metadata, "xml_unavailable"), False
        _validate_invoice_xml(downloaded[0], name)
        if downloaded[0] != expected_xml:
            return self._retry_blocked(metadata, "xml_mismatch"), False
        latest = self._find_invoice(company_id, name, environment)
        if latest is None or str(latest["id"]) != str(row["id"]):
            return self._retry_blocked(metadata, "document_changed"), False
        latest_metadata = self._retry_metadata(latest, environment, expected_xml)
        if latest.get("has_cdr") is True:
            return self._retry_existing_cdr(latest, name, latest_metadata), False
        if not self._retry_eligible(latest):
            return self._retry_blocked(latest_metadata, "ineligible_state"), False
        if any(latest.get(key) != row.get(key) for key in ("hash", "error_message", "state", "ticket")):
            return self._retry_blocked(latest_metadata, "document_changed"), False
        return latest_metadata, True

    def retry_invoice(self, tenant, nombre_archivo: str, *, environment: str, expected_xml: str, before_submit) -> dict:
        """Retry one positively identified temporary panel failure after a fenced callback.

        The caller verifies the frozen XML signature/payload and persists its one
        permitted panel attempt in before_submit. Every POST outcome needs later
        reconciliation; no HTTP response establishes fiscal acceptance.
        """
        match = _NAME.fullmatch(str(nombre_archivo or ""))
        company_id = str(getattr(tenant, "smartpse_company_id", "") or "")
        if (not retry_enabled_for_tenant(getattr(tenant, "id", None)) or not match
                or match[1] != str(getattr(tenant, "business_ruc", "")) or int(match[3]) < 1
                or not re.fullmatch(r"[0-9]{1,20}", company_id) or int(company_id) < 1
                or environment not in {"demo", "produccion"}
                or environment != getattr(tenant, "smartpse_environment", None)
                or not isinstance(expected_xml, str) or not expected_xml or not callable(before_submit)):
            raise SmartPSEPanelException("El reintento del panel no esta habilitado para esta identidad y ambiente.")
        expected_bytes = expected_xml.encode("utf-8")
        _validate_invoice_xml(expected_bytes, nombre_archivo)
        if not self._lock.acquire(timeout=settings.SMARTPSE_PANEL_TIMEOUT_SECONDS):
            raise SmartPSEPanelException("La sesion del panel esta ocupada.")
        try:
            self._deadline = self._now() + settings.SMARTPSE_PANEL_RECOVERY_BUDGET_SECONDS
            if self._now() < self._blocked_until:
                raise SmartPSEPanelException("El reintento del panel esta temporalmente pausado.")
            for attempt in range(2):
                if self._session is None or self._now() >= self._expires_at:
                    self._login()
                try:
                    result, eligible = self._prepare_retry(company_id, nombre_archivo, environment, expected_bytes)
                    break
                except _SessionExpired:
                    self._invalidate()
                    if attempt == 1:
                        self._blocked_until = self._now() + settings.SMARTPSE_PANEL_AUTH_COOLDOWN_SECONDS
                        raise SmartPSEPanelException("La sesion del panel vencio antes del reintento.") from None
            if not eligible:
                return result
            if not retry_enabled_for_tenant(tenant.id):
                return self._retry_blocked(result, "rollout_disabled")
            if self._now() >= self._deadline:
                raise SmartPSEPanelException("Se agoto el tiempo antes del reintento del panel.")
            try:
                csrf = self._session.cookies.get("XSRF-TOKEN")
            except requests.cookies.CookieConflictError:
                csrf = None
            if not csrf:
                raise SmartPSEPanelException("Falta proteccion CSRF para reintentar el documento.")
            if before_submit(dict(result)) is not True:
                return self._retry_blocked(result, "callback_veto")
            result = {**self._pending(), **result, "pending": True, "panel_retry_attempted": True,
                      "panel_retry_status": "ambiguous", "provider_status_code": None}
            self._retry_post_document_id = result["provider_document_id"]
            try:
                status, headers, raw, _ = self._request("POST", f"/panel/documentos/{result['provider_document_id']}/reintentar",
                    retry_document_id=result["provider_document_id"], headers={
                        "X-XSRF-TOKEN": unquote(csrf), "Referer": ORIGIN + "/panel/documentos", "Origin": ORIGIN,
                        "X-Requested-With": "XMLHttpRequest"})
            except SmartPSEPanelException as exc:
                raise SmartPSEPanelRetryException("El reintento del panel requiere conciliacion fiscal.", result,
                                                  status_code=exc.status_code) from None
            result["provider_status_code"] = status
            if status in {401, 419}:
                self._invalidate()
            if not 200 <= status < 300:
                raise SmartPSEPanelRetryException("El panel no confirmo el resultado del reintento; requiere conciliacion.",
                                                  result, status_code=status)
            result["panel_retry_status"] = "response_received"
            message = _confirmed_transient_retry_message(status, headers, raw)
            if message is not None:
                # Preserve the exact response fingerprint without exposing any
                # known credential echoed inside the provider's message.
                for credential in (_secret(self._email), _secret(self._password)):
                    if credential:
                        message = message.replace(credential, "***")
                result["panel_retry_status"] = "confirmed_transient_failure"
                result["panel_retry_outcome"] = {
                    "source": "retry_response", "response_sha256": hashlib.sha256(raw).hexdigest(), "message": message,
                }
            return result
        finally:
            self._retry_post_document_id = None
            self._lock.release()

    def recover_invoice(self, tenant, nombre_archivo: str, *, environment: str, include_xml: bool = False) -> dict:
        match = _NAME.fullmatch(str(nombre_archivo or ""))
        company_id = str(getattr(tenant, "smartpse_company_id", "") or "")
        if (not enabled_for_tenant(getattr(tenant, "id", None)) or not match
                or match[1] != str(getattr(tenant, "business_ruc", "")) or int(match[3]) < 1
                or not re.fullmatch(r"[0-9]{1,20}", company_id) or int(company_id) < 1
                or environment not in {"demo", "produccion"}
                or environment != getattr(tenant, "smartpse_environment", None)):
            raise SmartPSEPanelException("La recuperación no está habilitada para esta identidad y ambiente.")
        if not self._lock.acquire(timeout=settings.SMARTPSE_PANEL_TIMEOUT_SECONDS):
            raise SmartPSEPanelException("La sesión de recuperación está ocupada.")
        try:
            self._deadline = self._now() + settings.SMARTPSE_PANEL_RECOVERY_BUDGET_SECONDS
            if self._now() < self._blocked_until:
                raise SmartPSEPanelException("La recuperación del panel está temporalmente pausada.")
            for attempt in range(2):
                if self._session is None or self._now() >= self._expires_at:
                    self._login()
                try:
                    return self._recover(company_id, nombre_archivo, environment, include_xml)
                except _SessionExpired:
                    self._invalidate()
                    if attempt == 1:
                        self._blocked_until = self._now() + settings.SMARTPSE_PANEL_AUTH_COOLDOWN_SECONDS
                        raise SmartPSEPanelException("La sesión del panel no permite recuperar evidencia; está pausada.") from None
            raise SmartPSEPanelException("No se pudo recuperar evidencia del panel.")
        finally:
            self._lock.release()


_default_client = None
_default_lock = threading.Lock()


def get_default_client() -> SmartPSEPanelClient:
    global _default_client
    with _default_lock:
        if _default_client is None:
            _default_client = SmartPSEPanelClient()
        return _default_client
