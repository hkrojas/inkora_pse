from datetime import datetime, timedelta
from io import BytesIO
import re
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import BackgroundTasks
from starlette.requests import Request

import crud
import schemas
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from routers import cotizaciones as cotizaciones_router
from services import fiscal_xml_service, pdf_generator, pdf_storage_service, storage_service


def _make_png_bytes() -> bytes:
    from PIL import Image as PillowImage

    buffer = BytesIO()
    image = PillowImage.new("RGB", (16, 16), color="white")
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _make_request(path: str = "/test") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [],
            "client": ("testclient", 50000),
        }
    )


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

TINY_PNG_BYTES = _make_png_bytes()


def _count_pdf_pages(buffer: BytesIO) -> int:
    return len(re.findall(br"/Type /Page\b", buffer.getvalue()))


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


def test_resolve_document_client_data_prefiere_snapshot_sobre_ficha_actual():
    document = SimpleNamespace(
        cliente=_fake_cliente(),
        cliente_snapshot={
            "razon_social": "Cliente historico PDF",
            "tipo_documento": "6",
            "numero_documento": "20999999991",
            "direccion": "Jr. Historico 789",
        },
    )

    client_data = pdf_generator._resolve_document_client_data(document)

    assert client_data["name"] == "Cliente historico PDF"
    assert client_data["doc_type_label"] == "RUC"
    assert client_data["doc_number"] == "20999999991"
    assert client_data["address"] == "Jr. Historico 789"


def test_quote_detail_col_widths_expande_codigo_sin_cambiar_ancho_total():
    styles = pdf_generator.getSampleStyleSheet()
    base = styles["Normal"]
    header_style = pdf_generator.ParagraphStyle(
        name="TestHeader",
        parent=base,
        fontName="Helvetica-Bold",
        fontSize=7.45,
    )
    text_style = pdf_generator.ParagraphStyle(
        name="TestText",
        parent=base,
        fontName="Helvetica",
        fontSize=7.86,
    )
    money_style = pdf_generator.ParagraphStyle(
        name="TestMoney",
        parent=text_style,
        fontSize=8.1,
    )
    total_width = 540
    lines = [
        {
            "indice": 1,
            "codigo": "PROD-8847D4",
            "descripcion": "Bolsa pastillera",
            "cantidad": 850,
            "unidad": "UND",
            "valor_unitario": 0.81,
            "p_unit_con_igv": 0.95,
            "subtotal_item": 684.32,
            "precio_total_item": 807.50,
        }
    ]

    widths = pdf_generator._build_quote_detail_col_widths(
        lines,
        total_width,
        header_style=header_style,
        text_style=text_style,
        money_style=money_style,
        symbol="S/",
    )

    assert round(sum(widths), 6) == total_width
    assert widths[2] > total_width * 0.09
    assert widths[3] >= total_width * 0.22


def test_generar_pdf_cotizacion_genera_qr_para_billetera_o_fallback():
    tenant = _fake_tenant()
    tenant.bank_accounts = [
        {
            "tipo": "wallet",
            "proveedor": "Yape",
            "titular": "Inkora Test SAC",
            "numero": "999888777",
            "nota": "Pago inmediato",
        }
    ]
    cotizacion = SimpleNamespace(
        cliente=_fake_cliente(),
        items=[_fake_item()],
        moneda="PEN",
        serie="COT",
        correlativo=37,
        created_at=datetime.now(),
        usuario=_fake_user(),
    )

    with patch("services.pdf_generator.qrcode.make", wraps=pdf_generator.qrcode.make) as qr_make:
        buffer = pdf_generator.generar_pdf_cotizacion(cotizacion, tenant)

    assert isinstance(buffer, BytesIO)
    assert len(buffer.getvalue()) > 0
    qr_make.assert_called()


def test_generar_pdf_cotizacion_compacta_permanece_en_una_sola_pagina_con_tres_items():
    tenant = _fake_tenant()
    tenant.pdf_note_1 = "TODO TRABAJO SE REALIZA CON EL 50% DE ADELANTO"
    tenant.pdf_note_2 = "LOS PRECIOS NO INCLUYEN ENVIOS"
    tenant.bank_accounts = [
        {
            "tipo": "payment_qr_image",
            "url": "https://cdn.test/qr-cobro.png",
        },
        {
            "id": "wallet-yape",
            "tipo": "wallet",
            "proveedor": "Yape",
            "titular": "Papeleria Grafica y Publicitaria SAC.",
            "numero": "949985395",
        },
        {
            "tipo": "bank",
            "banco": "BCP",
            "tipo_cuenta": "Cta Corriente",
            "moneda": "Soles",
            "cuenta": "1919870450013",
            "cci": "00219100987045001355",
            "mostrar_en_cotizaciones": True,
        },
        {
            "tipo": "bank",
            "banco": "Banco de la Nacion",
            "tipo_cuenta": "Cuenta Detraccion",
            "moneda": "Soles",
            "cuenta": "00045115666",
            "cci": "01804500004511566655",
            "mostrar_en_cotizaciones": True,
        },
    ]
    cotizacion = SimpleNamespace(
        cliente=SimpleNamespace(
            razon_social="LOPEZ TITO ROQUE ROGER",
            tipo_documento="6",
            numero_documento="10446458243",
            direccion="JR. MARIANO MELGAR 568 URB. REYNOSO COLEGIO POLITECNICO PROV. CONST. DEL CALLAO PROV. CONST. DEL CALLAO-CARMEN DE LA LEGUA REYNOSO",
        ),
        items=[
            SimpleNamespace(codigo="001", descripcion="bolsa de papel kraft n20 con imp a un color en una cara", cantidad=1000, precio_unitario=0.27),
            SimpleNamespace(codigo="002", descripcion="bolsa de papel kraft N4 con imp un color en una cara", cantidad=1000, precio_unitario=0.11),
            SimpleNamespace(codigo="003", descripcion="bolsa de papel kraft N2 con impresion a un color en una cara", cantidad=1000, precio_unitario=0.08),
        ],
        moneda="PEN",
        serie="COT",
        correlativo=1,
        created_at=datetime(2026, 6, 17, 9, 30),
        fecha_emision=datetime(2026, 6, 17, 9, 30),
        fecha_vencimiento=datetime(2026, 6, 17, 9, 30),
        usuario=_fake_user(),
        quote_selected_wallet_id="wallet-yape",
    )

    with patch("services.pdf_generator._load_remote_logo_bytes", return_value=TINY_PNG_BYTES):
        buffer = pdf_generator.generar_pdf_cotizacion(cotizacion, tenant)

    assert isinstance(buffer, BytesIO)
    assert len(buffer.getvalue()) > 0
    assert _count_pdf_pages(buffer) == 1

def test_generar_pdf_cotizacion_usa_qr_subido_en_lugar_de_generar_qr():
    tenant = _fake_tenant()
    tenant.bank_accounts = [
        {"tipo": "payment_qr_image", "url": "https://cdn.test/qr-cobro.png"},
        {
            "tipo": "wallet",
            "proveedor": "Yape",
            "titular": "Inkora Test SAC",
            "numero": "999888777",
            "nota": "Pago inmediato",
        },
    ]
    cotizacion = SimpleNamespace(
        cliente=_fake_cliente(),
        items=[_fake_item()],
        moneda="PEN",
        serie="COT",
        correlativo=38,
        created_at=datetime.now(),
        usuario=_fake_user(),
    )

    with (
        patch("services.pdf_generator._load_remote_logo_bytes", return_value=TINY_PNG_BYTES) as load_image,
        patch("services.pdf_generator.qrcode.make", wraps=pdf_generator.qrcode.make) as qr_make,
    ):
        buffer = pdf_generator.generar_pdf_cotizacion(cotizacion, tenant)

    assert isinstance(buffer, BytesIO)
    assert len(buffer.getvalue()) > 0
    load_image.assert_called_with("https://cdn.test/qr-cobro.png")
    qr_make.assert_not_called()


def test_resolve_quote_due_date_display_respeta_vencimiento_explicito():
    issue_date = datetime(2026, 6, 16, 9, 30)
    due_date = issue_date + timedelta(days=7)

    fecha_emision, fecha_vencimiento = pdf_generator._resolve_quote_due_date_display(
        SimpleNamespace(
            fecha_emision=issue_date,
            fecha_vencimiento=due_date,
            condicion_pago="credito_7",
        )
    )

    assert fecha_emision == "16/06/2026"
    assert fecha_vencimiento == "23/06/2026"


def test_resolve_quote_due_date_display_usa_credito_15_por_defecto():
    issue_date = datetime(2026, 6, 16, 9, 30)

    fecha_emision, fecha_vencimiento = pdf_generator._resolve_quote_due_date_display(
        SimpleNamespace(
            fecha_emision=issue_date,
            fecha_vencimiento=None,
            condicion_pago=None,
        )
    )

    assert fecha_emision == "16/06/2026"
    assert fecha_vencimiento == "01/07/2026"


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
    assert company_data["bank_accounts"] == []
    assert company_data["quote_bank_accounts"] == []
    assert company_data["name"] == tenant.business_name


def test_resolve_quote_company_data_respeta_visibilidad_global_y_override_de_cotizacion():
    tenant = _fake_tenant()
    user = _fake_user()
    user.tenant = tenant
    tenant.bank_accounts = [
        {
            "tipo": "bank",
            "banco": "BCP",
            "tipo_cuenta": "Cta Corriente",
            "moneda": "Soles",
            "cuenta": "1919870450013",
            "cci": "00219100987045001355",
            "mostrar_en_cotizaciones": True,
        },
        {
            "tipo": "bank",
            "banco": "Banco de la Nacion",
            "tipo_cuenta": "Cuenta Detraccion",
            "moneda": "Soles",
            "cuenta": "00045115666",
            "cci": "01804500004511566655",
            "mostrar_en_cotizaciones": False,
        },
        {
            "tipo": "wallet",
            "proveedor": "Yape",
            "titular": "Inkora Test SAC",
            "numero": "999888777",
        },
    ]

    fallback = pdf_generator._resolve_quote_company_data(
        SimpleNamespace(usuario=user),
        tenant,
    )
    override = pdf_generator._resolve_quote_company_data(
        SimpleNamespace(
            usuario=user,
            quote_payment_methods=[
                {
                    "tipo": "bank",
                    "banco": "Banco de la Nacion",
                    "tipo_cuenta": "Cuenta Detraccion",
                    "moneda": "Soles",
                    "cuenta": "00045115666",
                    "cci": "01804500004511566655",
                }
            ],
        ),
        tenant,
    )

    assert [method["banco"] for method in fallback["quote_bank_accounts"]] == ["BCP"]
    assert [method["banco"] for method in override["quote_bank_accounts"]] == ["Banco de la Nacion"]
    assert any(method["tipo"] == "wallet" for method in override["bank_accounts"])


def test_build_quote_client_layout_ancla_bloque_derecho():
    total_width = 540

    layout = pdf_generator._build_quote_client_layout(total_width)

    assert round(sum(layout["col_widths"]), 6) == total_width
    assert layout["col_widths"][3] <= total_width * 0.12
    assert layout["right_block_align"] == "RIGHT"
    assert layout["right_block_left_padding"] == 0


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


def test_build_payment_methods_text_puede_excluir_billeteras():
    payment_text = pdf_generator._build_payment_methods_text(
        [
            {
                "tipo": "bank",
                "banco": "BCP",
                "tipo_cuenta": "Cta Corriente",
                "moneda": "Soles",
                "cuenta": "1919870450013",
                "cci": "00219100987045001355",
            },
            {
                "tipo": "wallet",
                "proveedor": "Yape",
                "titular": "Inkora Test SAC",
                "numero": "999888777",
            },
        ],
        beneficiary_name="Inkora Test SAC",
        exclude_wallets=True,
    )

    assert "Datos para la Transferencia" in payment_text
    assert "BCP" in payment_text
    assert "1919870450013" in payment_text
    assert "Yape" not in payment_text
    assert "999888777" not in payment_text


def test_build_quote_wallet_qr_content_prefiere_wallet():
    qr_content, wallet = pdf_generator._build_quote_wallet_qr_content(
        [
            {
                "id": "wallet-yape",
                "tipo": "wallet",
                "proveedor": "Yape",
                "titular": "Inkora Test SAC",
                "numero": "999888777",
                "nota": "Pago inmediato",
            }
        ],
        beneficiary_name="Inkora Test SAC",
    )

    assert "Yape" in qr_content
    assert "999888777" in qr_content
    assert wallet is not None


def test_build_quote_wallet_qr_content_respeta_wallet_seleccionada():
    qr_content, wallet = pdf_generator._build_quote_wallet_qr_content(
        [
            {
                "id": "wallet-yape",
                "tipo": "wallet",
                "proveedor": "Yape",
                "titular": "Inkora Test SAC",
                "numero": "999888777",
            },
            {
                "id": "wallet-plin",
                "tipo": "wallet",
                "proveedor": "Plin",
                "titular": "Inkora Test SAC",
                "numero": "999111222",
            },
        ],
        beneficiary_name="Inkora Test SAC",
        selected_wallet_id="wallet-plin",
    )

    assert "Plin" in qr_content
    assert "999111222" in qr_content
    assert wallet is not None
    assert wallet["id"] == "wallet-plin"


def test_build_document_footer_layout_compacta_cotizacion():
    layout = pdf_generator._build_document_footer_layout(is_comprobante=False)

    assert layout["generated_qr_size"] == 1.3 * pdf_generator.inch
    assert layout["block_top_padding"] == 8
    assert layout["block_bottom_padding"] == 8
    assert layout["footer_top_padding"] == 4
    assert layout["bottom_gap"] == 0


def test_modern_pdf_header_height_is_5cm():
    assert pdf_generator.MODERN_PDF_HEADER_HEIGHT == 5.0 * pdf_generator.cm


def test_should_pin_footer_to_page_bottom_en_cotizacion_que_cabe():
    should_pin = pdf_generator._should_pin_footer_to_page_bottom(
        usable_height=700,
        consumed_height=320,
        footer_height=180,
        is_comprobante=False,
    )

    assert should_pin is True


def test_resolve_footer_spacer_height_limita_cotizacion_en_fallback():
    spacer_height = pdf_generator._resolve_footer_spacer_height(
        usable_height=700,
        consumed_height=320,
        footer_height=180,
        is_comprobante=False,
    )

    assert spacer_height == 24


def test_resolve_footer_spacer_height_conserva_colchon_en_comprobantes():
    spacer_height = pdf_generator._resolve_footer_spacer_height(
        usable_height=700,
        consumed_height=320,
        footer_height=180,
        is_comprobante=True,
    )

    assert spacer_height == 172


def test_resolve_quote_company_data_usa_snapshot_de_medios_de_cobro():
    tenant = _fake_tenant()
    tenant.bank_accounts = [
        {
            "id": "wallet-yape",
            "tipo": "wallet",
            "proveedor": "Yape",
            "titular": "Tenant actual",
            "numero": "999888777",
        }
    ]
    user = _fake_user()
    user.tenant = tenant

    company_data = pdf_generator._resolve_quote_company_data(
        SimpleNamespace(
            usuario=user,
            quote_selected_wallet_id="wallet-plin",
            quote_payment_methods=[
                {
                    "id": "wallet-plin",
                    "tipo": "wallet",
                    "proveedor": "Plin",
                    "titular": "Snapshot historico",
                    "numero": "999111222",
                }
            ],
        ),
        tenant,
    )

    assert company_data["selected_wallet_id"] == "wallet-plin"
    assert company_data["bank_accounts"][0]["id"] == "wallet-plin"


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
    private_ref = storage_service.build_private_storage_reference(
        "cotizaciones/tenant_1/cotizacion.pdf"
    )

    with patch(
        "services.pdf_storage_service.pdf_generator.generar_pdf_cotizacion",
        return_value=BytesIO(b"quote-pdf"),
    ) as quote_renderer, patch(
        "services.pdf_storage_service.pdf_generator.create_comprobante_pdf",
        return_value=BytesIO(b"doc-pdf"),
    ) as comprobante_renderer, patch(
        "services.pdf_storage_service.storage_service.upload_to_storage",
        new=Mock(return_value=private_ref),
    ):
        result = _run(pdf_storage_service.generate_and_upload_pdf(db_session, cotizacion))

    assert result == private_ref
    assert cotizacion.sunat_pdf_url == private_ref
    assert quote_renderer.called is True
    assert comprobante_renderer.called is False


def test_generate_and_upload_pdf_usa_renderer_de_comprobante(db_session):
    tenant = make_tenant(db_session, "PDF02")
    user = make_user(db_session, tenant, email="pdf02@test.com")
    cliente = make_cliente(db_session, tenant, "PDF02", numero_documento="20191308868")
    quote = make_quote_via_crud(db_session, tenant, user, cliente)
    fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
    private_ref = storage_service.build_private_storage_reference(
        "cotizaciones/tenant_2/comprobante.pdf"
    )

    with patch(
        "services.pdf_storage_service.pdf_generator.generar_pdf_cotizacion",
        return_value=BytesIO(b"quote-pdf"),
    ) as quote_renderer, patch(
        "services.pdf_storage_service.pdf_generator.create_comprobante_pdf",
        return_value=BytesIO(b"doc-pdf"),
    ) as comprobante_renderer, patch(
        "services.pdf_storage_service.storage_service.upload_to_storage",
        new=Mock(return_value=private_ref),
    ):
        result = _run(pdf_storage_service.generate_and_upload_pdf(db_session, fiscal))

    assert result == private_ref
    assert fiscal.sunat_pdf_url == private_ref
    assert quote_renderer.called is False
    assert comprobante_renderer.called is True


def test_generate_and_upload_pdf_usa_renderer_de_comprobante_para_nota(db_session):
    tenant = make_tenant(db_session, "PDF03")
    user = make_user(db_session, tenant, email="pdf03@test.com")
    cliente = make_cliente(db_session, tenant, "PDF03", numero_documento="20191308868")
    quote = make_quote_via_crud(db_session, tenant, user, cliente)
    fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
    fiscal.estado = "facturada"
    db_session.commit()
    nota = crud.crear_nota_credito_debito(
        db_session,
        fiscal,
        user.id,
        "credito",
        "01",
        "ANULACION DE LA OPERACION",
    )

    with patch(
        "services.pdf_storage_service.pdf_generator.generar_pdf_cotizacion",
        return_value=BytesIO(b"quote-pdf"),
    ) as quote_renderer, patch(
        "services.pdf_storage_service.pdf_generator.create_comprobante_pdf",
        return_value=BytesIO(b"note-pdf"),
    ) as comprobante_renderer, patch(
        "services.pdf_storage_service.storage_service.upload_to_storage",
        new=Mock(return_value=storage_service.build_private_storage_reference("cotizaciones/tenant_3/nota.pdf")),
    ):
        _run(pdf_storage_service.generate_and_upload_pdf(db_session, nota))

    assert quote_renderer.called is False
    assert comprobante_renderer.called is True


def test_cotizacion_response_serializa_pdf_privado_como_url_firmada(db_session):
    tenant = make_tenant(db_session, "PDF04")
    user = make_user(db_session, tenant, email="pdf04@test.com")
    cliente = make_cliente(db_session, tenant, "PDF04", numero_documento="20191308868")
    cotizacion = make_quote_via_crud(db_session, tenant, user, cliente)
    cotizacion.sunat_pdf_url = storage_service.build_private_storage_reference(
        f"cotizaciones/tenant_{tenant.id}/cotizacion.pdf"
    )
    db_session.commit()

    with patch(
        "services.storage_service.resolve_storage_download_url",
        return_value="https://signed.test/cotizacion.pdf",
    ):
        payload = schemas.CotizacionResponse.model_validate(
            cotizacion,
            from_attributes=True,
        ).model_dump(mode="json")

    assert payload["sunat_pdf_url"] == "https://signed.test/cotizacion.pdf"


def test_descargar_pdf_publico_redirige_a_url_firmada():
    documento = SimpleNamespace(
        sunat_pdf_url=storage_service.build_private_storage_reference(
            "cotizaciones/tenant_1/publico.pdf"
        )
    )

    with patch(
        "routers.cotizaciones.crud.get_cotizacion_by_uuid",
        return_value=documento,
    ), patch(
        "routers.cotizaciones.storage_service.resolve_storage_download_url",
        return_value="https://signed.test/publico.pdf",
    ):
        response = _run(
            cotizaciones_router.descargar_pdf_publico(
                _make_request("/public/cotizaciones/uuid-demo/pdf"),
                "uuid-demo",
                None,
                SimpleNamespace(),
            )
        )

    assert response.status_code == 307
    assert response.headers["location"] == "https://signed.test/publico.pdf"


def test_descargar_pdf_interno_devuelve_url_firmada_para_api():
    documento = SimpleNamespace(
        document_kind="quotation",
        linked_fiscal_document=None,
        sunat_pdf_url=storage_service.build_private_storage_reference(
            "cotizaciones/tenant_1/interno.pdf"
        ),
    )
    current_user = SimpleNamespace(tenant_id=1)

    with patch(
        "routers.cotizaciones.crud.get_cotizacion",
        return_value=documento,
    ), patch(
        "routers.cotizaciones.storage_service.resolve_storage_download_url",
        return_value="https://signed.test/interno.pdf",
    ):
        payload = _run(
            cotizaciones_router.descargar_pdf_interno(
                _make_request("/cotizaciones/1/pdf"),
                1,
                BackgroundTasks(),
                False,
                SimpleNamespace(),
                current_user,
            )
        )

    assert payload == {"url": "https://signed.test/interno.pdf"}


def test_compartir_cotizacion_usa_contacto_del_snapshot():
    cotizacion = SimpleNamespace(
        id=1,
        uuid_publico="uuid-demo",
        cliente=_fake_cliente(),
        cliente_snapshot={
            "razon_social": "Cliente Snapshot",
            "tipo_documento": "6",
            "numero_documento": "20999999991",
            "email": "snapshot@test.com",
            "telefono": "987654321",
            "whatsapp": "987654321",
        },
    )
    tenant = _fake_tenant()

    with patch(
        "routers.cotizaciones.crud.get_cotizacion",
        return_value=cotizacion,
    ), patch(
        "routers.cotizaciones.comunicacion_service.generar_link_whatsapp",
        return_value="https://wa.test",
    ) as whatsapp_link, patch(
        "routers.cotizaciones.comunicacion_service.generar_link_mailto",
        return_value="mailto:snapshot@test.com",
    ) as mailto_link:
        payload = _run(
            cotizaciones_router.compartir_cotizacion(
                1,
                SimpleNamespace(),
                SimpleNamespace(tenant=tenant),
            )
        )

    whatsapp_link.assert_called_once()
    assert whatsapp_link.call_args.args[1] == "987654321"
    mailto_link.assert_called_once()
    assert mailto_link.call_args.args[1] == "snapshot@test.com"
    assert payload["whatsapp_link"] == "https://wa.test"


def _run(awaitable):
    import asyncio

    return asyncio.run(awaitable)
