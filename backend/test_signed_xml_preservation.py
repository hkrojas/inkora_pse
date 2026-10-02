"""Signed XML transport normalization must preserve its persisted fingerprint."""
import base64
import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from lxml import etree
from signxml import XMLSigner

import crud
from services import emission_queue_service as queue, fiscal_evidence_service as evidence
from services import pdf_storage_service, smartpse_response
from test_emission_queue import _make_fiscal_document
from test_smartpse_response_normalization import _zip_b64


@pytest.fixture(scope="module")
def signing_material():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic XML preservation test")])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=1))
            .sign(key, hashes.SHA256()))
    return key, cert.public_bytes(serialization.Encoding.PEM)


@pytest.mark.parametrize("trailer", ["\n", "\r\n"])
@pytest.mark.parametrize("send_format", ["raw", "base64", "zip"])
def test_signed_zip_then_pending_send_preserves_deliverable_xml(
    db_session, signing_material, trailer, send_format,
):
    tenant, user, document = _make_fiscal_document(db_session, "09231")
    job, _ = queue.enqueue_fiscal_document_job(db_session, document, user, tipo_comprobante="01")
    prepared = job.payload_snapshot["prepared_sale"]
    key, cert = signing_material
    signed_root = XMLSigner().sign(etree.fromstring(prepared["unsigned_xml"].encode()), key=key, cert=cert)
    signed_xml = etree.tostring(signed_root).decode() + trailer
    fingerprint = hashlib.sha256(signed_xml.encode()).hexdigest()
    signed_zip = _zip_b64("synthetic-invoice.xml", signed_xml)

    assert evidence.retain_sale_evidence(
        db_session, document, {"xml_firmado": signed_zip}, payload=prepared["payload"],
    )
    assert document.sunat_xml_content == signed_xml
    assert document.provider_response["inkora_evidence"]["signed_xml_sha256"] == fingerprint
    quota_before = tenant.subscription.documents_used

    encoded_xml = {
        "raw": document.sunat_xml_content,
        "base64": base64.b64encode(document.sunat_xml_content.encode()).decode(),
        "zip": signed_zip,
    }[send_format]
    result = smartpse_response.build_smartpse_result(
        prepared["payload"], {"estado": 202, "xml_firmado": encoded_xml},
        endpoint="/api/cpe/enviar-demo", status_code=200, require_cdr=True,
    )
    crud.guardar_respuesta_sunat(db_session, document.id, result, tenant_id=tenant.id)
    db_session.expire_all()

    assert document.estado == "pendiente"
    assert document.provider_verification_status == "pending_confirmation"
    assert not document.sunat_cdr_content
    assert document.sunat_xml_content == signed_xml
    assert hashlib.sha256(document.sunat_xml_content.encode()).hexdigest() == fingerprint
    assert document.provider_response["inkora_evidence"]["signed_xml_sha256"] == fingerprint
    assert evidence.has_deliverable_xml(document)
    pdf_storage_service.ensure_fiscal_pdf_ready(document)
    assert tenant.subscription.documents_used == quota_before
    assert document.source_quote.estado != "facturada"


def test_raw_xml_detection_preserves_surrounding_whitespace():
    xml = " \n<Invoice/>\r\n "
    assert smartpse_response.extract_xml_from_signed_zip(xml) == xml
