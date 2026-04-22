from services import fiscal_xml_service


SAMPLE_INVOICE_XML = """<?xml version="1.0" encoding="utf-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>F001-123456</cbc:ID>
  <cbc:IssueDate>2026-04-13</cbc:IssueDate>
  <cbc:IssueTime>10:15:30</cbc:IssueTime>
  <cbc:InvoiceTypeCode>01</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>PEN</cbc:DocumentCurrencyCode>
  <cbc:Note languageLocaleID="1000">SON: CINCUENTA Y NUEVE CON 00/100 SOLES</cbc:Note>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyIdentification>
        <cbc:ID schemeID="6">20606751509</cbc:ID>
      </cac:PartyIdentification>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>PAPELERIA GRAFICA Y PUBLICITARIA SAC.</cbc:RegistrationName>
        <cac:RegistrationAddress>
          <cbc:ID>150101</cbc:ID>
          <cac:AddressLine>
            <cbc:Line>AV. ALFONSO UGARTE 252</cbc:Line>
          </cac:AddressLine>
        </cac:RegistrationAddress>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyIdentification>
        <cbc:ID schemeID="6">20111111111</cbc:ID>
      </cac:PartyIdentification>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>CLIENTE XML SAC</cbc:RegistrationName>
        <cac:RegistrationAddress>
          <cbc:ID>150102</cbc:ID>
          <cac:AddressLine>
            <cbc:Line>JR. CLIENTE 456</cbc:Line>
          </cac:AddressLine>
        </cac:RegistrationAddress>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:TaxTotal>
    <cbc:TaxAmount>9.00</cbc:TaxAmount>
  </cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount>50.00</cbc:LineExtensionAmount>
    <cbc:TaxInclusiveAmount>59.00</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount>59.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:InvoiceLine>
    <cbc:ID>1</cbc:ID>
    <cbc:InvoicedQuantity unitCode="NIU">1.00</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount>50.00</cbc:LineExtensionAmount>
    <cac:TaxTotal>
      <cbc:TaxAmount>9.00</cbc:TaxAmount>
    </cac:TaxTotal>
    <cac:PricingReference>
      <cac:AlternativeConditionPrice>
        <cbc:PriceAmount>59.00</cbc:PriceAmount>
      </cac:AlternativeConditionPrice>
    </cac:PricingReference>
    <cac:Item>
      <cbc:Description>ITEM XML</cbc:Description>
      <cac:SellersItemIdentification>
        <cbc:ID>ITEM-001</cbc:ID>
      </cac:SellersItemIdentification>
    </cac:Item>
  </cac:InvoiceLine>
</Invoice>
"""


def test_parse_sale_document_xml_extrae_campos_principales():
    parsed = fiscal_xml_service.parse_sale_document_xml(SAMPLE_INVOICE_XML)

    assert parsed is not None
    assert parsed["document_id"] == "F001-123456"
    assert parsed["tipo_comprobante"] == "01"
    assert parsed["supplier"]["doc_number"] == "20606751509"
    assert parsed["customer"]["name"] == "CLIENTE XML SAC"
    assert parsed["totals"]["payable_amount"] == 59
    assert parsed["lines"][0]["description"] == "ITEM XML"
    assert parsed["lines"][0]["price_amount"] == 59


def test_build_sale_qr_payload_from_xml_construye_payload():
    qr_payload = fiscal_xml_service.build_sale_qr_payload_from_xml(SAMPLE_INVOICE_XML)

    assert qr_payload == {
        "ruc": "20606751509",
        "tipo": "01",
        "serie": "F001",
        "numero": "123456",
        "emision": "2026-04-13T10:15:30-05:00",
        "igv": 9.0,
        "total": 59.0,
        "clienteTipo": "6",
        "clienteNumero": "20111111111",
    }
