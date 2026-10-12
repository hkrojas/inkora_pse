"""PDF delivery guards and sharing, using local evidence and mocked Storage."""
import asyncio
from copy import deepcopy
import hashlib
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock
import zipfile
from datetime import datetime, timedelta

import pytest
from fastapi import BackgroundTasks, HTTPException

import crud
import models
from conftest import make_tenant, make_user
from test_fiscal_contingency_recovery import sale, sign_xml  # noqa: F401
from test_pdf_generator import _make_request
from services import fiscal_evidence_service as evidence, pdf_storage_service as pdf
from services import facturacion_service
from services import emission_queue_service as queue, fiscal_recovery_service as recovery, smartpse_client
from test_smartpse_response_normalization import _sale_cdr
from routers import cotizaciones as router


def signed_document(db, sale, sign_xml):
    tenant, user, doc, job = sale
    prepared = job.payload_snapshot["prepared_sale"]
    xml = sign_xml(prepared["unsigned_xml"])
    assert evidence.retain_sale_evidence(db, doc, {"xml_firmado": xml}, payload=prepared["payload"])
    return tenant, user, doc


def block_document(db, doc, status):
    if status == "rejected":
        doc.provider_verification_status = "rejected"
    else:
        doc.estado = "anulada"
    db.commit()


@pytest.mark.parametrize("stage", ["upload", "download"])
@pytest.mark.parametrize("status", ["rejected", "anulada"])
def test_pdf_request_rechecks_state_after_external_io(db_session, sale, sign_xml, monkeypatch, stage, status):
    _, user, doc = signed_document(db_session, sale, sign_xml)
    reference = "supabase-private://audit/fiscal-" + pdf._pdf_source_fingerprint(doc)[:12] + ".pdf"
    def upload(*args):
        if stage == "upload":
            block_document(db_session, doc, status)
        return reference
    def download(*args):
        block_document(db_session, doc, status)
        return b"%PDF should never be delivered"
    monkeypatch.setattr(pdf.pdf_generator, "create_comprobante_pdf", lambda *args: BytesIO(b"%PDF local"))
    monkeypatch.setattr(pdf.storage_service, "upload_to_storage", upload)
    downloader = Mock(side_effect=download)
    monkeypatch.setattr(pdf.storage_service, "download_private_storage_reference", downloader)
    if stage == "download":
        doc.sunat_pdf_url = reference
        db_session.commit()
    with pytest.raises(HTTPException) as caught:
        asyncio.run(router.descargar_pdf_interno_como_archivo(_make_request(), doc.id, db_session, user))
    assert caught.value.status_code == 409
    assert not evidence.has_deliverable_xml(doc)
    if stage == "upload":
        assert doc.sunat_pdf_url is None
        downloader.assert_not_called()


def test_pdf_download_allows_acceptance_with_same_signed_xml(db_session, sale, sign_xml, monkeypatch):
    _, user, doc = signed_document(db_session, sale, sign_xml)
    reference = "supabase-private://audit/fiscal-" + pdf._pdf_source_fingerprint(doc)[:12] + ".pdf"
    doc.sunat_pdf_url = reference
    db_session.commit()
    def download(*args):
        doc.estado = "facturada"
        doc.provider_verification_status = "verified"
        doc.sunat_cdr_content = "<ApplicationResponse/>"
        db_session.commit()
        return b"%PDF unchanged"
    monkeypatch.setattr(pdf.storage_service, "download_private_storage_reference", download)
    response = asyncio.run(router.descargar_pdf_interno_como_archivo(_make_request(), doc.id, db_session, user))
    assert response.status_code == 200 and response.body == b"%PDF unchanged"


def test_real_pdf_generated_before_cdr_is_reused_after_reconciliation(db_session, sale, sign_xml, monkeypatch):
    tenant, user, document, job = sale
    prepared = job.payload_snapshot["prepared_sale"]
    signed = sign_xml(prepared["unsigned_xml"])
    client = Mock()
    client.sign_xml.return_value = {"xml_firmado": signed}
    client.send_signed_xml.side_effect = smartpse_client.SmartPSEException("Timeout enviando documento")
    client.consult_ticket.return_value = {"xml_firmado": signed, "estado": 200,
        "cdr": _sale_cdr(document_id=f"{document.serie}-{document.correlativo}", ruc=tenant.business_ruc)}
    monkeypatch.setattr(smartpse_client, "get_default_client", lambda: client)
    crud.claim_next_emission_job(db_session)
    assert not queue.process_emission_job(job.id, db_session=db_session)
    db_session.expire_all()
    assert document.estado == "pendiente" and not document.sunat_cdr_content
    upload = Mock(side_effect=lambda content, folder, filename, *args: "supabase-private://audit/" + folder + "/" + filename)
    monkeypatch.setattr(pdf.storage_service, "upload_to_storage", upload)
    reference = asyncio.run(pdf.generate_and_upload_pdf(db_session, document))
    assert upload.call_args.args[0].startswith(b"%PDF")
    qr = document.sunat_qr_payload.copy()
    circuit = db_session.get(models.FiscalProviderCircuit, recovery.scope_for(tenant))
    circuit.next_probe_at = job.available_at = datetime.now() - timedelta(seconds=1)
    db_session.commit()
    crud.claim_next_emission_job(db_session)
    assert queue.process_emission_job(job.id, db_session=db_session)
    assert document.estado == "facturada" and document.sunat_cdr_content
    assert asyncio.run(pdf.generate_and_upload_pdf(db_session, document)) == reference
    assert upload.call_count == client.sign_xml.call_count == client.send_signed_xml.call_count == 1
    assert client.consult_ticket.call_count == 1
    assert document.sunat_xml_content == signed and document.sunat_qr_payload == qr


@pytest.mark.parametrize("public", [True, False])
@pytest.mark.parametrize("status", ["rejected", "anulada"])
def test_pdf_url_rechecks_state_after_url_signing(db_session, sale, sign_xml, monkeypatch, public, status):
    _, user, doc = signed_document(db_session, sale, sign_xml)
    doc.sunat_pdf_url = "supabase-private://audit/fiscal-" + pdf._pdf_source_fingerprint(doc)[:12] + ".pdf"
    db_session.commit()
    def resolve_url(document):
        block_document(db_session, doc, status)
        return "https://signed.test/should-not-be-returned.pdf"
    monkeypatch.setattr(router, "_resolve_pdf_download_url", resolve_url)
    with pytest.raises(HTTPException) as caught:
        if public:
            asyncio.run(router.descargar_pdf_publico(_make_request(), doc.uuid_publico, None, db_session))
        else:
            asyncio.run(router.descargar_pdf_interno(_make_request(), doc.id, BackgroundTasks(), False, db_session, user))
    assert caught.value.status_code == 409


def test_pdf_download_rejects_changed_reference(db_session, sale, sign_xml, monkeypatch):
    _, user, doc = signed_document(db_session, sale, sign_xml)
    doc.sunat_pdf_url = "supabase-private://audit/fiscal-" + pdf._pdf_source_fingerprint(doc)[:12] + ".pdf"
    db_session.commit()
    def download(*args):
        doc.sunat_pdf_url = "supabase-private://audit/replacement.pdf"
        db_session.commit()
        return b"%PDF old"
    monkeypatch.setattr(pdf.storage_service, "download_private_storage_reference", download)
    with pytest.raises(HTTPException) as caught:
        asyncio.run(router.descargar_pdf_interno_como_archivo(_make_request(), doc.id, db_session, user))
    assert caught.value.status_code == 202


def test_share_source_uses_fiscal_uuid_and_messages(db_session, sale, sign_xml, monkeypatch):
    _, user, doc = signed_document(db_session, sale, sign_xml)
    source = doc.source_quote
    whatsapp = Mock(return_value="https://wa.test")
    email = Mock(return_value="mailto:test")
    monkeypatch.setattr(router.comunicacion_service, "generar_link_whatsapp", whatsapp)
    monkeypatch.setattr(router.comunicacion_service, "generar_link_mailto", email)
    share = asyncio.run(router.compartir_cotizacion(source.id, db_session, user))
    assert f"/{doc.uuid_publico}/pdf" in share["url_compartir"]
    assert source.uuid_publico not in share["url_compartir"]
    assert whatsapp.call_args.args[0].id == email.call_args.args[0].id == doc.id
    assert router._resolve_pdf_document(db_session, source).id == doc.id


def test_pdf_download_rejects_changed_source_with_same_reference(db_session, sale, sign_xml, monkeypatch):
    _, user, doc = signed_document(db_session, sale, sign_xml)
    doc.sunat_pdf_url = "supabase-private://audit/fiscal-" + pdf._pdf_source_fingerprint(doc)[:12] + ".pdf"
    db_session.commit()
    def download(*args):
        doc.sunat_hash = "updated-hash"
        db_session.commit()
        return b"%PDF old"
    monkeypatch.setattr(pdf.storage_service, "download_private_storage_reference", download)
    with pytest.raises(HTTPException) as caught:
        asyncio.run(router.descargar_pdf_interno_como_archivo(_make_request(), doc.id, db_session, user))
    assert caught.value.status_code == 202


def test_pdf_download_does_not_compare_new_version_with_old_bytes(db_session, sale, sign_xml, monkeypatch):
    _, user, doc = signed_document(db_session, sale, sign_xml)
    async def prepare(db, document):
        document.sunat_pdf_url = "supabase-private://audit/new.pdf"
        db.commit()
        return "supabase-private://audit/old.pdf"
    monkeypatch.setattr(router, "_prepare_pdf", prepare)
    downloader = Mock(return_value=b"%PDF old")
    monkeypatch.setattr(pdf.storage_service, "download_private_storage_reference", downloader)
    with pytest.raises(HTTPException) as caught:
        asyncio.run(router.descargar_pdf_interno_como_archivo(_make_request(), doc.id, db_session, user))
    assert caught.value.status_code == 202
    downloader.assert_not_called()


def test_existing_public_quote_uuid_still_resolves_quote(db_session, sale, sign_xml, monkeypatch):
    _, _, doc = signed_document(db_session, sale, sign_xml)
    source = doc.source_quote
    source.sunat_pdf_url = "supabase-private://audit/quote.pdf"
    db_session.commit()
    monkeypatch.setattr(router, "_resolve_pdf_download_url", lambda current: "https://signed.test/" + str(current.id))
    response = asyncio.run(router.descargar_pdf_publico(_make_request(), source.uuid_publico, None, db_session))
    assert response.headers["location"] == "https://signed.test/" + str(source.id)


def test_share_does_not_expose_unsigned_pending_fiscal(db_session, sale):
    _, user, doc, _ = sale
    with pytest.raises(HTTPException) as caught:
        asyncio.run(router.compartir_cotizacion(doc.source_quote.id, db_session, user))
    assert caught.value.status_code == 409


def test_foreign_user_cannot_share_source(db_session, sale):
    _, _, doc, _ = sale
    foreign = make_tenant(db_session, "FOREIGNPDF")
    user = make_user(db_session, foreign, email="foreignpdf@test.com")
    with pytest.raises(HTTPException) as caught:
        asyncio.run(router.compartir_cotizacion(doc.source_quote.id, db_session, user))
    assert caught.value.status_code == 404


def test_resolver_rejects_foreign_fiscal_link(db_session, sale):
    _, _, doc, _ = sale
    foreign = make_tenant(db_session, "FOREIGNLINK")
    source = doc.source_quote
    doc.tenant_id = foreign.id
    db_session.commit()
    assert source.linked_fiscal_document_id == doc.id
    with pytest.raises(HTTPException) as caught:
        router._resolve_pdf_document(db_session, source)
    assert caught.value.status_code == 404


def test_cdr_download_uses_retained_xml_when_storage_is_unavailable(monkeypatch):
    doc = SimpleNamespace(serie="F001", correlativo=1, sunat_cdr_url="supabase-private://audit/cdr.zip",
                          sunat_cdr_content="<ApplicationResponse>retained</ApplicationResponse>")
    monkeypatch.setattr(facturacion_service.storage_service, "download_private_storage_reference", Mock(side_effect=RuntimeError("offline")))
    content = facturacion_service.descargar_archivo("cdr", doc, None)
    with zipfile.ZipFile(BytesIO(content)) as archive:
        assert archive.read(archive.namelist()[0]).decode() == doc.sunat_cdr_content


def test_cdr_storage_failure_does_not_invent_missing_cdr(monkeypatch):
    doc = SimpleNamespace(sunat_cdr_url="supabase-private://audit/cdr.zip", sunat_cdr_content=None)
    monkeypatch.setattr(facturacion_service.storage_service, "download_private_storage_reference", Mock(side_effect=RuntimeError("offline")))
    with pytest.raises(RuntimeError):
        facturacion_service.descargar_archivo("cdr", doc, None)


@pytest.mark.parametrize("kind", ["quotation", "fiscal_document", "credit_note", "debit_note"])
def test_note_renderer_version_preserves_non_note_fingerprint_contract(monkeypatch, kind):
    document = SimpleNamespace(
        id=11, document_kind=kind, sunat_xml_content="<retained/>", cliente_id=22,
        fecha_emision=None, fecha_vencimiento=None, moneda="PEN", observaciones=None,
        condicion_pago=None, total_gravada=100, total_exonerada=0, total_inafecta=0,
        total_igv=18, total_venta=118, items=[],
    )
    # Frozen identity from the pre-version contract: invoices and quotations
    # must not invalidate their existing representations when notes are fixed.
    legacy = "b48ca24b7bc5515a38b08d552d0bfd2efe31a9ccb20f3744bcca5b8d6477099d"
    current = pdf._pdf_source_fingerprint(document)
    if kind in {"quotation", "fiscal_document"}:
        assert current == legacy
    else:
        assert current != legacy
    monkeypatch.setattr(pdf, "NOTE_PDF_RENDERER_VERSION", "synthetic-next-note-renderer")
    if kind in {"quotation", "fiscal_document"}:
        assert pdf._pdf_source_fingerprint(document) == legacy
    else:
        assert pdf._pdf_source_fingerprint(document) != current


def _retained_note(db, sale, note_type, *, verified_evidence=False, with_xml=True):
    _, user, source, _ = sale
    source.estado = "facturada"
    db.commit()
    note = crud.crear_nota_credito_debito(
        db, source, user.id, note_type, "01", "Ajuste fiscal local",
    )
    note.estado = "facturada"
    note.provider_verification_status = "verified"
    root = "CreditNote" if note_type == "credito" else "DebitNote"
    note.sunat_xml_content = f"<{root}>synthetic retained accepted XML</{root}>" if with_xml else None
    note.sunat_xml_url = "supabase-private://audit/retained-note.xml" if with_xml else None
    note.sunat_cdr_content = "<ApplicationResponse>synthetic accepted CDR</ApplicationResponse>"
    note.sunat_cdr_url = "supabase-private://audit/retained-note-cdr.zip"
    note.sunat_hash = "retained-note-digest"
    note.sunat_qr_payload = {"document_type": note.tipo_comprobante, "retained": True}
    if verified_evidence:
        note.provider_response = {"inkora_evidence": {
            "signed_xml_sha256": hashlib.sha256(note.sunat_xml_content.encode()).hexdigest(),
        }}
    db.commit()
    return note, source


def _fiscal_snapshot(document):
    # Every persisted field except the representation pointer is immutable in
    # this repair, including XML/CDR, amounts, number, status and QR evidence.
    return {
        "document": deepcopy({column.key: getattr(document, column.key)
                              for column in models.Cotizacion.__table__.columns
                              if column.key != "sunat_pdf_url"}),
        "items": deepcopy([{column.key: getattr(item, column.key)
                            for column in models.CotizacionItem.__table__.columns}
                           for item in document.items]),
    }


@pytest.mark.parametrize("note_type", ["credito", "debito"])
@pytest.mark.parametrize("verified_evidence", [False, True], ids=["accepted-legacy", "verified-xml"])
def test_old_note_pdf_regenerates_once_without_changing_fiscal_data(
    db_session, sale, monkeypatch, note_type, verified_evidence,
):
    note, source = _retained_note(db_session, sale, note_type, verified_evidence=verified_evidence)
    # The old fingerprint had no kind-specific version; an invoice with these
    # same inputs therefore produces precisely the pre-fix cache identity.
    kind = note.document_kind
    note.document_kind = "fiscal_document"
    old_fingerprint = pdf._pdf_source_fingerprint(note)
    note.document_kind = kind
    assert old_fingerprint != pdf._pdf_source_fingerprint(note)
    old_reference = f"supabase-private://audit/note-{old_fingerprint[:12]}.pdf"
    note.sunat_pdf_url = old_reference
    db_session.commit()
    assert evidence.has_deliverable_xml(note)
    assert pdf.has_legacy_accepted_pdf(note) is not verified_evidence
    before = _fiscal_snapshot(note)
    source_before = _fiscal_snapshot(source)
    quote_before = _fiscal_snapshot(source.source_quote)
    renderer = Mock(return_value=BytesIO(b"%PDF synthetic corrected note"))
    uploader = Mock(side_effect=lambda content, folder, filename, mime: f"supabase-private://audit/{folder}/{filename}")
    monkeypatch.setattr(pdf.pdf_generator, "create_comprobante_pdf", renderer)
    monkeypatch.setattr(pdf.storage_service, "upload_to_storage", uploader)

    reference = asyncio.run(pdf.generate_and_upload_pdf(db_session, note))
    db_session.expire_all()
    assert reference != old_reference
    assert reference == note.sunat_pdf_url
    assert f"-{pdf._pdf_source_fingerprint(note)[:12]}.pdf" in reference
    assert _fiscal_snapshot(note) == before
    assert _fiscal_snapshot(source) == source_before
    assert _fiscal_snapshot(source.source_quote) == quote_before
    assert asyncio.run(pdf.generate_and_upload_pdf(db_session, note)) == reference
    renderer.assert_called_once()
    uploader.assert_called_once()
    assert uploader.call_args.args[0] == b"%PDF synthetic corrected note"
    assert _fiscal_snapshot(note) == before


@pytest.mark.parametrize("note_type", ["credito", "debito"])
def test_legacy_note_without_deliverable_xml_keeps_stored_pdf(db_session, sale, monkeypatch, note_type):
    note, _ = _retained_note(db_session, sale, note_type, with_xml=False)
    note.sunat_pdf_url = "supabase-private://audit/historical-note-without-xml.pdf"
    db_session.commit()
    before = _fiscal_snapshot(note)
    assert pdf.has_legacy_accepted_pdf(note)
    assert not evidence.has_deliverable_xml(note)
    renderer = Mock(side_effect=AssertionError("No XML: historical PDF must not be rendered"))
    uploader = Mock(side_effect=AssertionError("No XML: historical PDF must not be replaced"))
    monkeypatch.setattr(pdf.pdf_generator, "create_comprobante_pdf", renderer)
    monkeypatch.setattr(pdf.storage_service, "upload_to_storage", uploader)
    assert asyncio.run(pdf.generate_and_upload_pdf(db_session, note)) == note.sunat_pdf_url
    assert _fiscal_snapshot(note) == before
    renderer.assert_not_called()
    uploader.assert_not_called()
