from datetime import datetime
import re
from types import SimpleNamespace
from unittest.mock import patch

from reportlab.lib.units import cm

from services import guide_pdf_service


CDR_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ApplicationResponse xmlns="urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2"
 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ResponseCode>0</cbc:ResponseCode>
  <cbc:Description>Aceptado</cbc:Description>
</ApplicationResponse>
"""

SIGNED_GRE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<DespatchAdvice xmlns="urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2"
 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  <cbc:ID>T009-77</cbc:ID>
  <cbc:IssueDate>2026-09-16</cbc:IssueDate>
  <cbc:IssueTime>15:45:12</cbc:IssueTime>
  <cbc:DespatchAdviceTypeCode>09</cbc:DespatchAdviceTypeCode>
  <cac:DespatchSupplierParty><cac:Party>
    <cac:PartyIdentification><cbc:ID>20606751509</cbc:ID></cac:PartyIdentification>
    <cac:PartyLegalEntity><cbc:RegistrationName>PAPELERIA XML SAC</cbc:RegistrationName></cac:PartyLegalEntity>
  </cac:Party></cac:DespatchSupplierParty>
</DespatchAdvice>
"""


def _tenant():
    return SimpleNamespace(
        business_name="PAPELERIA GRAFICA Y PUBLICITARIA SAC.",
        business_ruc="20606751509",
        business_address="AV. ALFONSO UGARTE 252 INT. 1023, LIMA",
        business_phone="999999999",
        business_email="ventas@papeleriagyp.test",
        primary_color="#004AAD",
        logo_filename=None,
    )


def _item(index=1):
    return SimpleNamespace(
        cantidad="1.0000",
        unidad_medida="NIU",
        codigo_producto=f"PROD-{index:03d}",
        descripcion=f"CB MAS UNA COPIA TAMAÑO A4 - LÍNEA {index}",
    )


def _guide(**overrides):
    values = {
        "tipo_documento": "09",
        "serie": "T001",
        "correlativo": 1,
        "fecha_emision": datetime(2026, 9, 17, 9, 0),
        "fecha_traslado": datetime(2026, 9, 18, 8, 0),
        "estado": "pendiente_smartpse",
        "provider_response": {},
        "sunat_hash": None,
        "cotizacion": SimpleNamespace(document_number="FA01-000178", cliente=None),
        "goods_invoice_reference": None,
        "related_guide": None,
        "external_gre_reference": None,
        "cliente": SimpleNamespace(
            razon_social="CONTIPAPERSA S.A.C.",
            nombre=None,
            numero_documento="20602861091",
            direccion="CAL. LAS ACACIAS MZA. I LOTE. 5",
        ),
        "cliente_nombre": "CONTIPAPERSA S.A.C.",
        "cliente_documento": "20602861091",
        "destinatario_razon_social": "CONTIPAPERSA S.A.C.",
        "destinatario_nro_doc": "20602861091",
        "motivo_traslado": "01",
        "descripcion_motivo": "VENTA",
        "modalidad_traslado": "02",
        "fecha_entrega_transportista": None,
        "indicador_m1_l": False,
        "registrar_vehiculo_transportista": False,
        "transportista_acuerdo_confirmado_at": None,
        "observaciones": None,
        "internal_order_number": None,
        "peso_bruto_total": "1.000",
        "unidad_medida_peso": "KGM",
        "numero_bultos": 1,
        "partida_ubigeo": "150101",
        "partida_direccion": "AV. ALFONSO UGARTE 252 INT. 1023, LIMA",
        "partida_codigo_local": None,
        "llegada_ubigeo": "150118",
        "llegada_direccion": "CAL. LAS ACACIAS MZA. I LOTE. 5, LURIGANCHO",
        "llegada_codigo_local": None,
        "num_contenedor": None,
        "cod_puerto": None,
        "transportista_razon_social": None,
        "transportista_ruc": None,
        "transportista_nro_mtc": None,
        "vehiculo_placa": "ABC123",
        "vehiculo_nro_circulacion": None,
        "conductor_tipo_doc": "1",
        "conductor_nro_doc": "72758912",
        "conductor_nombres": "ANA",
        "conductor_apellidos": "ROJAS",
        "conductor_licencia": "Q12345678",
        "items": [_item()],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_pdf_guia_pendiente_usa_diseno_inkora_y_estado_humano():
    pdf_bytes = guide_pdf_service.build_guide_pdf(_guide(), _tenant())

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 3_500
    assert guide_pdf_service._STATUS_META["pendiente_smartpse"] == (
        "PENDIENTE DE ACEPTACIÓN",
        "PENDIENTE DE ACEPTACIÓN",
    )
    assert guide_pdf_service._invoice_reference(_guide()) == "FA01-000178"


def test_pdf_resumen_omite_estado_interno_y_mantiene_fechas_en_una_fila():
    captured = {}

    class FakeDocument:
        def __init__(self, *args, **kwargs):
            pass

        def build(self, elements, **kwargs):
            captured["elements"] = elements

    guide = _guide(estado="emitida")

    with patch("services.guide_pdf_service.SimpleDocTemplate", FakeDocument):
        guide_pdf_service.build_guide_pdf(guide, _tenant())

    summary = captured["elements"][2]
    summary_cells = summary._cellvalues[0]
    summary_text = " ".join(cell.getPlainText() for cell in summary_cells)

    assert len(summary._cellvalues) == 1
    assert len(summary_cells) == 2
    assert "Fecha de emisión:" in summary_text
    assert "Hora:" in summary_text
    assert "Fecha de traslado:" in summary_text
    assert "Estado:" not in summary_text
    assert "ACEPTADA POR SUNAT" not in summary_text


def test_pdf_titulos_gre_09_y_31_caben_en_dos_lineas_del_recuadro():
    captured_titles = []
    document_box = guide_pdf_service.pdf_generator._RoundedDocumentBox

    def capture_document_box(*args, **kwargs):
        captured_titles.append(kwargs["title_paragraph"])
        return document_box(*args, **kwargs)

    with patch(
        "services.guide_pdf_service.pdf_generator._RoundedDocumentBox",
        side_effect=capture_document_box,
    ):
        guide_pdf_service.build_guide_pdf(_guide(tipo_documento="09"), _tenant())
        guide_pdf_service.build_guide_pdf(_guide(tipo_documento="31"), _tenant())

    assert len(captured_titles) == 2
    for title in captured_titles:
        title.wrap((4.9 * cm) - 12, 100)
        assert len(title.blPara.lines) == 2


def test_pdf_traslado_interno_muestra_transferencia_y_codigos_locales_sin_factura():
    guide = _guide(
        motivo_traslado="04",
        descripcion_motivo="TRASLADO ENTRE ESTABLECIMIENTOS DE LA MISMA EMPRESA",
        cotizacion=None,
        cliente=None,
        destinatario_razon_social="PAPELERIA GRAFICA Y PUBLICITARIA SAC.",
        destinatario_nro_doc="20606751509",
        internal_order_number="TI-18",
        partida_codigo_local="0000",
        llegada_codigo_local="0001",
    )

    with patch("services.guide_pdf_service._label_value", wraps=guide_pdf_service._label_value) as label_value:
        pdf_bytes = guide_pdf_service.build_guide_pdf(guide, _tenant())

    rendered_rows = [(call.args[0], str(call.args[1])) for call in label_value.call_args_list]
    assert pdf_bytes.startswith(b"%PDF")
    assert ("Transferencia interna", "TI-18") in rendered_rows
    assert any(label == "Punto de partida" and value.startswith("0000") for label, value in rendered_rows)
    assert any(label == "Punto de llegada" and value.startswith("0001") for label, value in rendered_rows)
    assert all(label not in {"Factura de bienes", "Boleta de venta"} for label, _ in rendered_rows)


def test_pdf_guia_aceptada_incluye_qr_y_leyenda_fiscal():
    guide = _guide(
        estado="emitida",
        provider_response={"cdr": CDR_XML, "qr_content": "QR-OFICIAL-SMARTPSE"},
        sunat_hash="HASH-DEMO-ACEPTADO",
    )

    with patch("services.guide_pdf_service._qr_image", wraps=guide_pdf_service._qr_image) as qr_image:
        pdf_bytes = guide_pdf_service.build_guide_pdf(guide, _tenant())

    assert pdf_bytes.startswith(b"%PDF")
    assert len(re.findall(rb"/Type\s*/Page\b", pdf_bytes)) == 1
    qr_image.assert_called_once()
    assert guide_pdf_service._cdr_qr_content(guide, _tenant()) == "QR-OFICIAL-SMARTPSE"


def test_pdf_guia_aceptada_mantiene_qr_en_primera_hoja_hasta_cinco_productos():
    provider_response = {"cdr": CDR_XML, "qr_content": "QR-OFICIAL-SMARTPSE"}
    five_items = _guide(
        estado="emitida",
        provider_response=provider_response,
        items=[_item(index) for index in range(1, 6)],
    )
    six_items = _guide(
        estado="emitida",
        provider_response=provider_response,
        items=[_item(index) for index in range(1, 7)],
    )

    five_item_pdf = guide_pdf_service.build_guide_pdf(five_items, _tenant())
    with patch("services.guide_pdf_service._build_items", wraps=guide_pdf_service._build_items) as build_items:
        six_item_pdf = guide_pdf_service.build_guide_pdf(six_items, _tenant())

    assert len(re.findall(rb"/Type\s*/Page\b", five_item_pdf)) == 1
    assert len(re.findall(rb"/Type\s*/Page\b", six_item_pdf)) == 2
    assert [len(call.args[0]) for call in build_items.call_args_list] == [5, 1]


def test_pdf_guia_multipagina_coloca_qr_antes_del_primer_salto_y_balancea_solo_continuaciones():
    captured = {}
    footer_marker = object()

    class FakeDocument:
        def __init__(self, *args, **kwargs):
            pass

        def build(self, elements, **kwargs):
            captured["elements"] = elements

    guide = _guide(
        estado="emitida",
        provider_response={"cdr": CDR_XML, "qr_content": "QR-OFICIAL-SMARTPSE"},
        items=[_item(index) for index in range(1, 26)],
    )

    with (
        patch("services.guide_pdf_service.SimpleDocTemplate", FakeDocument),
        patch("services.guide_pdf_service._build_footer", return_value=footer_marker),
        patch("services.guide_pdf_service._build_items", wraps=guide_pdf_service._build_items) as build_items,
    ):
        guide_pdf_service.build_guide_pdf(guide, _tenant())

    chunks = [list(call.args[0]) for call in build_items.call_args_list]
    elements = captured["elements"]
    first_page_break = next(
        index
        for index, element in enumerate(elements)
        if isinstance(element, guide_pdf_service.PageBreak)
    )

    assert [len(chunk) for chunk in chunks] == [5, 10, 10]
    assert sum(len(chunk) for chunk in chunks) == 25
    assert elements.index(footer_marker) < first_page_break


def test_pdf_guia_no_inventa_qr_cuando_proveedor_no_entrega_payload():
    guide = _guide(
        estado="emitida",
        provider_response={"cdr": CDR_XML},
        sunat_hash="HASH-DEMO-ACEPTADO",
    )

    with patch("services.guide_pdf_service._qr_image", wraps=guide_pdf_service._qr_image) as qr_image:
        pdf_bytes = guide_pdf_service.build_guide_pdf(guide, _tenant())

    assert pdf_bytes.startswith(b"%PDF")
    qr_image.assert_not_called()
    assert guide_pdf_service._cdr_qr_content(guide, _tenant()) is None


def test_pdf_guia_prioriza_punto_de_llegada_sobre_direccion_actual_del_cliente():
    guide = _guide(llegada_direccion="DESTINO FISCAL CONGELADO")

    assert guide_pdf_service._recipient(guide)[2] == "DESTINO FISCAL CONGELADO"


def test_pdf_guia_prioriza_identidad_y_hora_del_xml_firmado():
    guide = _guide(sunat_xml_content=SIGNED_GRE_XML)

    identity = guide_pdf_service._fiscal_identity(guide)

    assert guide_pdf_service._guide_number(guide) == "T009-77"
    assert identity["issue_date"] == "2026-09-16"
    assert identity["issue_time"] == "15:45:12"
    assert identity["issuer_name"] == "PAPELERIA XML SAC"
    assert guide_pdf_service._format_time(identity["issue_time"]) == "15:45"




def test_pdf_gre_31_muestra_emisor_transportista_y_gre_remitente():
    guide = _guide(
        tipo_documento="31",
        serie="V001",
        related_guide=SimpleNamespace(serie="T001", correlativo=88),
        transportista_razon_social="TRANSPORTES INKORA SAC",
        transportista_ruc="20555555555",
        transportista_nro_mtc="MTC-12345",
    )

    pdf_bytes = guide_pdf_service.build_guide_pdf(guide, _tenant())

    assert pdf_bytes.startswith(b"%PDF")
    assert guide_pdf_service._gre_reference(guide) == "T001-000088"
    assert guide_pdf_service._guide_number(guide) == "V001-000001"


def test_pdf_guia_extensa_distribuye_todos_los_productos_con_maximo_diez_por_hoja():
    guide = _guide(items=[_item(index) for index in range(1, 76)])

    with patch("services.guide_pdf_service._build_items", wraps=guide_pdf_service._build_items) as build_items:
        pdf_bytes = guide_pdf_service.build_guide_pdf(guide, _tenant())

    chunks = [list(call.args[0]) for call in build_items.call_args_list]
    starts = [call.args[1] for call in build_items.call_args_list]
    assert [len(chunk) for chunk in chunks] == [8, 10, 10, 10, 10, 9, 9, 9]
    assert starts == [1, 9, 19, 29, 39, 49, 58, 67]
    assert sum(len(chunk) for chunk in chunks) == 75
    assert max(len(chunk) for chunk in chunks) == 10
    assert len(re.findall(rb"/Type\s*/Page\b", pdf_bytes)) == 8


def test_pdf_boleta_m1l_muestra_origen_y_no_inventa_conductor():
    guide = _guide(
        cotizacion=SimpleNamespace(document_number="B001-000178", tipo_comprobante="03", cliente=None),
        modalidad_traslado="01",
        fecha_entrega_transportista=datetime(2026, 9, 18, 10, 0),
        indicador_m1_l=True,
        conductor_nro_doc=None,
        conductor_nombres=None,
        conductor_apellidos=None,
        conductor_licencia=None,
        observaciones="Entrega coordinada con el destinatario.",
    )

    with patch("services.guide_pdf_service._label_value", wraps=guide_pdf_service._label_value) as label_value:
        pdf_bytes = guide_pdf_service.build_guide_pdf(guide, _tenant())

    rendered_rows = [(call.args[0], str(call.args[1])) for call in label_value.call_args_list]
    assert pdf_bytes.startswith(b"%PDF")
    assert ("Boleta de venta", "B001-000178") in rendered_rows
    assert any(label == "Escenario" and "M1/L" in value for label, value in rendered_rows)
    assert ("Observaciones", "Entrega coordinada con el destinatario.") in rendered_rows
    assert all(label != "Documento conductor" for label, _ in rendered_rows)
