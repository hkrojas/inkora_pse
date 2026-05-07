from services import fiscal_qr_service


SIGNED_INVOICE_XML = """<?xml version="1.0" encoding="utf-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
    xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
  <cbc:ID>F001-00000042</cbc:ID>
  <cbc:IssueDate>2026-05-06</cbc:IssueDate>
  <cbc:IssueTime>10:30:00</cbc:IssueTime>
  <cbc:InvoiceTypeCode>01</cbc:InvoiceTypeCode>
  <cac:Signature>
    <cac:DigitalSignatureAttachment>
      <cac:ExternalReference>
        <cbc:URI>#SIGN-20123456789</cbc:URI>
      </cac:ExternalReference>
    </cac:DigitalSignatureAttachment>
  </cac:Signature>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyIdentification><cbc:ID schemeID="6">20123456789</cbc:ID></cac:PartyIdentification>
      <cac:PartyLegalEntity><cbc:RegistrationName>INKORA SAC</cbc:RegistrationName></cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyIdentification><cbc:ID schemeID="6">20191308868</cbc:ID></cac:PartyIdentification>
      <cac:PartyLegalEntity><cbc:RegistrationName>CLIENTE SAC</cbc:RegistrationName></cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:TaxTotal><cbc:TaxAmount currencyID="PEN">18.00</cbc:TaxAmount></cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:TaxInclusiveAmount currencyID="PEN">118.00</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="PEN">118.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <ds:Signature>
    <ds:SignedInfo>
      <ds:Reference URI="">
        <ds:DigestValue>abcDigestValue123==</ds:DigestValue>
      </ds:Reference>
    </ds:SignedInfo>
  </ds:Signature>
</Invoice>"""


BOLETA_DNI_XML = SIGNED_INVOICE_XML.replace("<cbc:InvoiceTypeCode>01</cbc:InvoiceTypeCode>", "<cbc:InvoiceTypeCode>03</cbc:InvoiceTypeCode>").replace(
    '<cbc:ID schemeID="6">20191308868</cbc:ID>',
    '<cbc:ID schemeID="1">70123456</cbc:ID>',
)


def _note_xml(root_name: str, type_code_tag: str) -> str:
    namespace = "CreditNote-2" if root_name == "CreditNote" else "DebitNote-2"
    total_tag = "LegalMonetaryTotal" if root_name == "CreditNote" else "RequestedMonetaryTotal"
    return f"""<?xml version="1.0" encoding="utf-8"?>
<{root_name} xmlns="urn:oasis:names:specification:ubl:schema:xsd:{namespace}"
    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
    xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
  <cbc:ID>FF01-00000007</cbc:ID>
  <cbc:IssueDate>2026-05-06</cbc:IssueDate>
  <cbc:{type_code_tag}>01</cbc:{type_code_tag}>
  <cac:AccountingSupplierParty><cac:Party><cac:PartyIdentification><cbc:ID schemeID="6">20123456789</cbc:ID></cac:PartyIdentification></cac:Party></cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty><cac:Party><cac:PartyIdentification><cbc:ID schemeID="6">20191308868</cbc:ID></cac:PartyIdentification></cac:Party></cac:AccountingCustomerParty>
  <cac:TaxTotal><cbc:TaxAmount currencyID="PEN">18.00</cbc:TaxAmount></cac:TaxTotal>
  <cac:{total_tag}><cbc:PayableAmount currencyID="PEN">118.00</cbc:PayableAmount></cac:{total_tag}>
  <ds:Signature><ds:SignedInfo><ds:Reference><ds:DigestValue>noteDigest==</ds:DigestValue></ds:Reference></ds:SignedInfo></ds:Signature>
</{root_name}>"""


def test_builds_sunat_qr_from_signed_invoice_xml_digest_and_preserves_money_text():
    payload = fiscal_qr_service.build_sunat_qr_payload(SIGNED_INVOICE_XML, provider_hash="provider-hash")

    assert payload["ruc"] == "20123456789"
    assert payload["tipo"] == "01"
    assert payload["serie"] == "F001"
    assert payload["numero"] == "00000042"
    assert payload["igv"] == "18.00"
    assert payload["total"] == "118.00"
    assert payload["emision"] == "2026-05-06"
    assert payload["clienteTipo"] == "6"
    assert payload["clienteNumero"] == "20191308868"
    assert payload["valorResumen"] == "abcDigestValue123=="
    assert payload["digest_source"] == "xml_digest"
    assert payload["digest_in_qr"] is True
    assert payload["qr_content"] == "20123456789|01|F001|00000042|18.00|118.00|2026-05-06|6|20191308868|abcDigestValue123=="
    assert "18.0|" not in payload["qr_content"]


def test_builds_sunat_qr_for_boleta_with_dni_customer():
    payload = fiscal_qr_service.build_sunat_qr_payload(BOLETA_DNI_XML)

    assert payload["tipo"] == "03"
    assert payload["clienteTipo"] == "1"
    assert payload["clienteNumero"] == "70123456"
    assert payload["qr_content"].split("|")[7:9] == ["1", "70123456"]


def test_builds_sunat_qr_for_credit_and_debit_notes():
    credit = fiscal_qr_service.build_sunat_qr_payload(_note_xml("CreditNote", "CreditNoteTypeCode"))
    debit = fiscal_qr_service.build_sunat_qr_payload(_note_xml("DebitNote", "DebitNoteTypeCode"))

    assert credit["tipo"] == "07"
    assert debit["tipo"] == "08"
    assert credit["qr_content"].split("|")[1] == "07"
    assert debit["qr_content"].split("|")[1] == "08"


def test_xml_without_digest_uses_provider_hash_as_operational_fallback():
    unsigned_xml = SIGNED_INVOICE_XML.replace("<ds:DigestValue>abcDigestValue123==</ds:DigestValue>", "")

    payload = fiscal_qr_service.build_sunat_qr_payload(unsigned_xml, provider_hash="hash-from-smartpse")

    assert payload["valorResumen"] == "hash-from-smartpse"
    assert payload["digest_source"] == "provider_hash"
    assert payload["digest_in_qr"] is True
    assert payload["qr_content"].endswith("|hash-from-smartpse")


def test_long_digest_is_kept_visible_outside_qr_to_preserve_legibility():
    long_digest = "x" * (fiscal_qr_service.MAX_QR_CONTENT_LENGTH + 1)
    xml = SIGNED_INVOICE_XML.replace("abcDigestValue123==", long_digest)

    payload = fiscal_qr_service.build_sunat_qr_payload(xml)

    assert payload["valorResumen"] == long_digest
    assert payload["digest_source"] == "xml_digest"
    assert payload["digest_in_qr"] is False
    assert payload["qr_visible_summary"] == long_digest
    assert payload["qr_content"] == "20123456789|01|F001|00000042|18.00|118.00|2026-05-06|6|20191308868"
