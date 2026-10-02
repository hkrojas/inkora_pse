"""Persist authenticated provider evidence without claiming fiscal acceptance."""
from __future__ import annotations

import hashlib
from decimal import Decimal

from lxml import etree
from signxml import XMLVerifier, SignatureConfiguration, SignatureMethod, DigestAlgorithm

from services import fiscal_qr_service, smartpse_response
from services.smartpse_client import SmartPSEException


DS = "http://www.w3.org/2000/09/xmldsig#"
SENSITIVE_KEYS = {"password", "token", "token_acceso", "access_token", "sol_password",
                  "client_secret", "client_secret_sunat", "authorization"}


def safe_response(value):
    if isinstance(value, dict):
        return {key: "***" if key.lower() in SENSITIVE_KEYS else safe_response(inner)
                for key, inner in value.items()}
    if isinstance(value, list):
        return [safe_response(inner) for inner in value]
    return value


def expected_sale_payload(document, tenant) -> dict:
    return {"tipoDoc": document.tipo_comprobante, "serie": document.serie,
            "correlativo": str(document.correlativo), "company": {"ruc": tenant.business_ruc},
            "mtoImpVenta": document.total_venta, "mtoIGV": document.total_igv}


def validate_signed_sale_xml(xml: str, payload: dict) -> str:
    """Check the entire signed UBL, identity and amounts received over provider TLS.

    The certificate comes from the authenticated PSE response. This verifies the
    signature, not SUNAT acceptance or independent certificate-chain accreditation.
    """
    try:
        root = etree.fromstring(xml.encode("utf-8"), etree.XMLParser(resolve_entities=False, no_network=True))
        certs = root.findall(f".//{{{DS}}}X509Certificate")
        signatures = root.findall(f".//{{{DS}}}Signature")
        if len(signatures) != 1 or not certs or not certs[0].text:
            raise ValueError("Falta firma digital verificable del XML")
        cert = "-----BEGIN CERTIFICATE-----\n" + certs[0].text.strip() + "\n-----END CERTIFICATE-----"
        config = SignatureConfiguration(
            require_x509=True, expect_references=1,
            signature_methods=frozenset({SignatureMethod.RSA_SHA256, SignatureMethod.RSA_SHA1}),
            digest_algorithms=frozenset({DigestAlgorithm.SHA256, DigestAlgorithm.SHA1}),
        )
        verified = XMLVerifier().verify(root, x509_cert=cert, expect_config=config).signed_xml
        if (verified.tag != root.tag or verified.tag.rsplit("}", 1)[-1] not in {"Invoice", "CreditNote", "DebitNote"}
                or root.xpath(".//*[local-name()='Invoice' or local-name()='CreditNote' or local-name()='DebitNote']")):
            raise ValueError("La firma no cubre el comprobante completo")
        reference = signatures[0].find(f".//{{{DS}}}Reference")
        uri = reference.get("URI", "") if reference is not None else None
        if uri is None or (uri and uri != "#" + (root.get("Id") or root.get("ID") or root.get("id") or "")):
            raise ValueError("La referencia de firma no cubre la raiz del comprobante")
        # Inspect only the verified root, never an unverified sibling/wrapper.
        identity = smartpse_response.extract_sale_document_identity(etree.tostring(verified).decode())
        expected_id = f"{payload.get('serie')}-{payload.get('correlativo')}"
        if smartpse_response._normalize_document_id(identity.get("document_id")) != smartpse_response._normalize_document_id(expected_id):
            raise ValueError("El XML firmado corresponde a otro comprobante")
        if identity.get("ruc") != str((payload.get("company") or {}).get("ruc") or ""):
            raise ValueError("El XML firmado corresponde a otra empresa")
        if identity.get("tipo_doc") != str(payload.get("tipoDoc") or "").zfill(2):
            raise ValueError("El XML firmado tiene otro tipo de comprobante")
        if payload.get("fechaEmision") and identity.get("issue_date") != str(payload["fechaEmision"])[:10]:
            raise ValueError("El XML firmado tiene otra fecha de emision")
        ns = smartpse_response.NS
        if payload.get("tipoMoneda") and verified.findtext("./cbc:DocumentCurrencyCode", namespaces=ns) != payload["tipoMoneda"]:
            raise ValueError("El XML firmado tiene otra moneda")
        client = payload.get("client")
        if isinstance(client, dict):
            receivers = verified.findall("./cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID",
                                         namespaces=ns)
            if (len(receivers) != 1 or not client.get("numDoc") or not client.get("tipoDoc")
                    or str(receivers[0].text or "").strip() != str(client["numDoc"]).strip()
                    or str(receivers[0].get("schemeID") or "").strip() != str(client["tipoDoc"]).strip()):
                raise ValueError("El XML firmado corresponde a otro receptor del comprobante")
        for expected, path in (("mtoImpVenta", "./cac:LegalMonetaryTotal/cbc:PayableAmount"),
                               ("mtoIGV", "./cac:TaxTotal/cbc:TaxAmount")):
            if payload.get(expected) is not None:
                actual = verified.findtext(path, namespaces=ns)
                if actual is None or Decimal(actual) != Decimal(str(payload[expected])):
                    raise ValueError("Los importes del XML firmado no coinciden")
        return hashlib.sha256(xml.encode("utf-8")).hexdigest()
    except Exception as exc:
        raise SmartPSEException(f"Evidencia XML invalida: {exc}") from exc


def retain_sale_evidence(db, document, response: dict, *, payload: dict, status_code=None, partial_result=None):
    """Keep raw redacted evidence even if its XML cannot be trusted for delivery."""
    document = db.query(type(document)).filter_by(id=document.id, tenant_id=document.tenant_id).populate_existing().with_for_update().one()
    if document.estado == "facturada" and document.sunat_accepted:
        ready = has_deliverable_xml(document)
        db.commit()
        return ready
    response = response or {}
    partial_result = partial_result or {}
    previous = document.provider_response if isinstance(document.provider_response, dict) else {}
    metadata = dict(previous.get("inkora_evidence") or {})
    document.provider_response = {"process": safe_response(response), "inkora_evidence": metadata}
    if status_code is not None:
        document.provider_status_code = status_code
    candidate = partial_result.get("xml") or smartpse_response.extract_xml_from_signed_zip(
        response.get("xml_firmado") or response.get("xml"))
    if candidate:
        try:
            fingerprint = validate_signed_sale_xml(candidate, payload)
            if document.sunat_xml_content and document.sunat_xml_content != candidate:
                raise SmartPSEException("El proveedor devolvio otro XML para una identidad ya firmada.")
            document.sunat_xml_content = candidate
            document.sunat_qr_payload = fiscal_qr_service.build_sunat_qr_payload(candidate)
            document.sunat_hash = (document.sunat_qr_payload or {}).get("valorResumen")
            metadata["signed_xml_sha256"] = fingerprint
            metadata.pop("xml_validation_error", None)
        except SmartPSEException as exc:
            metadata["xml_validation_error"] = str(exc)
    document.provider_response = {"process": safe_response(response), "inkora_evidence": metadata}
    db.commit()
    return bool(candidate and not metadata.get("xml_validation_error"))


def has_deliverable_xml(document) -> bool:
    if getattr(document, "provider_verification_status", None) == "rejected" or getattr(document, "estado", None) == "anulada":
        return False
    xml = getattr(document, "sunat_xml_content", None)
    if not xml:
        return False
    response = getattr(document, "provider_response", None) or {}
    evidence = response.get("inkora_evidence", {}) if isinstance(response, dict) else {}
    if evidence.get("signed_xml_sha256") == hashlib.sha256(xml.encode("utf-8")).hexdigest():
        return True
    # Existing accepted documents retain their prior artifact contract.
    return getattr(document, "estado", None) == "facturada" and bool(
        getattr(document, "sunat_cdr_content", None) or getattr(document, "sunat_cdr_url", None))
