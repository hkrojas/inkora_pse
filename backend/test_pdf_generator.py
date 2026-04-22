from datetime import datetime
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import crud
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from services import fiscal_xml_service, pdf_generator, pdf_storage_service


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

SIMPLE_QR_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="120" height="120" viewBox="0 0 120 120">
  <rect x="0" y="0" width="120" height="120" fill="#ffffff"/>
  <rect x="20" y="20" width="80" height="80" fill="#000000"/>
</svg>
"""


def _fake_tenant():
    return SimpleNamespace(
        primary_color="#004aad",
        business_ruc="20606751509",
        logo_filename=None,
        business_name="Inkora Test SAC",
        business_address="Av. Prueba 123, Lima",
        business_phone="999999999",
        bank_accounts=[],
        pdf_note_1="Nota 1",
        pdf_note_1_color="#FF0000",
        pdf_note_2="Nota 2",
    )


def _fake_cliente():
    return SimpleNamespace(
        razon_social="Cliente Demo SAC",
        tipo_documento="6",
        numero_documento="20111111111",
        direccion="Jr. Cliente 456, Lima",
    )


def _fake_item():
    return SimpleNamespace(
        descripcion="Impresion full color",
        cantidad=1,
        precio_unitario=118,
    )


def _fake_user():
    return SimpleNamespace(
        email="ventas@inkora.test",
        business_name=None,
        business_ruc=None,
        business_address=None,
        business_phone=None,
        business_email=None,
        logo_filename=None,
        bank_accounts=[
            {
                "banco": "Banco de Prueba",
                "tipo_cuenta": "Cta Corriente",
                "moneda": "Soles",
                "cuenta": "1234567890",
                "cci": "12345678901234567890",
            }
        ],
        tenant=None,
    )


def test_generar_pdf_cotizacion_crea_binario():
    cotizacion = SimpleNamespace(
        cliente=_fake_cliente(),
        items=[_fake_item()],
        moneda="PEN",
        serie="COT",
        correlativo=1,
        created_at=datetime.now(),
    )

    buffer = pdf_generator.generar_pdf_cotizacion(cotizacion, _fake_tenant())

    assert isinstance(buffer, BytesIO)
    assert len(buffer.getvalue()) > 0


def test_generar_pdf_cotizacion_no_genera_qr():
    cotizacion = SimpleNamespace(
        cliente=_fake_cliente(),
        items=[_fake_item()],
        moneda="PEN",
        serie="COT",
        correlativo=37,
        created_at=datetime.now(),
        usuario=_fake_user(),
    )

    with patch("services.pdf_generator.qrcode.make") as qr_make:
        buffer = pdf_generator.generar_pdf_cotizacion(cotizacion, _fake_tenant())

    assert isinstance(buffer, BytesIO)
    assert len(buffer.getvalue()) > 0
    qr_make.assert_not_called()


def test_resolve_quote_company_data_usa_email_usuario_y_fallback_bancario():
    tenant = _fake_tenant()
    user = _fake_user()
    user.tenant = tenant
    tenant.bank_accounts = []

    company_data = pdf_generator._resolve_quote_company_data(
        SimpleNamespace(usuario=user),
        tenant,
    )

    assert company_data["email"] == "ventas@inkora.test"
    assert company_data["bank_accounts"] == user.bank_accounts


def test_build_payment_methods_text_soporta_bancos_y_billeteras():
    payment_text = pdf_generator._build_payment_methods_text(
        [
            {
                "tipo": "bank",
                "banco": "Banco de la Nacion",
                "tipo_cuenta": "Cta Corriente",
                "moneda": "Soles",
                "cuenta": "00045115666",
                "cci": "01804500004511566655",
            },
            {
                "tipo": "wallet",
                "proveedor": "Yape",
                "titular": "Inkora Test SAC",
                "numero": "999888777",
                "nota": "Pago inmediato",
            },
        ],
        beneficiary_name="Inkora Test SAC",
    )

    assert "Datos para la Transferencia" in payment_text
    assert "Beneficiario: INKORA TEST SAC" in payment_text
    assert "Banco de la Nacion" in payment_text
    assert "Cuenta Detraccion en Soles" in payment_text
    assert "Yape" in payment_text
    assert "Titular: Inkora Test SAC" in payment_text
    assert "Numero: 999888777" in payment_text
    assert "Pago inmediato" in payment_text


def test_create_comprobante_pdf_crea_binario():
    comprobante = SimpleNamespace(
        cliente=_fake_cliente(),
        items=[_fake_item()],
        moneda="PEN",
        serie="F001",
        correlativo=1,
        fecha_emision=datetime.now(),
        tipo_comprobante="01",
    )

    buffer = pdf_generator.create_comprobante_pdf(comprobante, _fake_tenant())

    assert isinstance(buffer, BytesIO)
    assert len(buffer.getvalue()) > 0


def test_create_comprobante_pdf_prioriza_xml_y_qr_oficial():
    comprobante = SimpleNamespace(
        cliente=SimpleNamespace(
            razon_social="CLIENTE LOCAL INCORRECTO",
            tipo_documento="1",
            numero_documento="00000000",
            direccion="Direccion local",
        ),
        items=[SimpleNamespace(descripcion="ITEM LOCAL", cantidad=99, precio_unitario=999)],
        moneda="USD",
        serie="X999",
        correlativo=999999,
        fecha_emision=datetime.now(),
        tipo_comprobante="03",
        sunat_xml_content=SAMPLE_INVOICE_XML,
        sunat_qr_svg=SIMPLE_QR_SVG,
        sunat_qr_payload=fiscal_xml_service.build_sale_qr_payload_from_xml(SAMPLE_INVOICE_XML),
    )

    with patch("services.pdf_generator.qrcode.make") as qr_make:
        buffer = pdf_generator.create_comprobante_pdf(comprobante, _fake_tenant())

    assert isinstance(buffer, BytesIO)
    assert len(buffer.getvalue()) > 0
    qr_make.assert_not_called()


def test_generate_and_upload_pdf_usa_renderer_de_cotizacion(db_session):
    tenant = make_tenant(db_session, "PDF01")
    user = make_user(db_session, tenant, email="pdf01@test.com")
    cliente = make_cliente(db_session, tenant, "PDF01", numero_documento="20191308868")
    cotizacion = make_quote_via_crud(db_session, tenant, user, cliente)

    with patch(
        "services.pdf_storage_service.pdf_generator.generar_pdf_cotizacion",
        return_value=BytesIO(b"quote-pdf"),
    ) as quote_renderer, patch(
        "services.pdf_storage_service.pdf_generator.create_comprobante_pdf",
        return_value=BytesIO(b"doc-pdf"),
    ) as comprobante_renderer, patch(
        "services.pdf_storage_service.storage_service.upload_to_storage",
        new=AsyncMock(return_value="https://storage.test/cotizacion.pdf"),
    ):
        result = _run(pdf_storage_service.generate_and_upload_pdf(db_session, cotizacion))

    assert result == "https://storage.test/cotizacion.pdf"
    assert quote_renderer.called is True
    assert comprobante_renderer.called is False


def test_generate_and_upload_pdf_usa_renderer_de_comprobante(db_session):
    tenant = make_tenant(db_session, "PDF02")
    user = make_user(db_session, tenant, email="pdf02@test.com")
    cliente = make_cliente(db_session, tenant, "PDF02", numero_documento="20191308868")
    quote = make_quote_via_crud(db_session, tenant, user, cliente)
    fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")

    with patch(
        "services.pdf_storage_service.pdf_generator.generar_pdf_cotizacion",
        return_value=BytesIO(b"quote-pdf"),
    ) as quote_renderer, patch(
        "services.pdf_storage_service.pdf_generator.create_comprobante_pdf",
        return_value=BytesIO(b"doc-pdf"),
    ) as comprobante_renderer, patch(
        "services.pdf_storage_service.storage_service.upload_to_storage",
        new=AsyncMock(return_value="https://storage.test/comprobante.pdf"),
    ):
        result = _run(pdf_storage_service.generate_and_upload_pdf(db_session, fiscal))

    assert result == "https://storage.test/comprobante.pdf"
    assert quote_renderer.called is False
    assert comprobante_renderer.called is True


def _run(awaitable):
    import asyncio

    return asyncio.run(awaitable)
