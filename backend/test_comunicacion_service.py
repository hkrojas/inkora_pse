from types import SimpleNamespace
from urllib.parse import unquote

from services import comunicacion_service


def _tenant():
    return SimpleNamespace(business_name="Inkora Demo", bank_accounts=[])


def _client():
    return SimpleNamespace(razon_social="Cliente Demo", numero_documento="20123456789")


def test_whatsapp_default_usa_etiqueta_factura():
    doc = SimpleNamespace(
        document_kind="fiscal_document",
        tipo_comprobante="01",
        serie="F001",
        correlativo=1,
        moneda="PEN",
        total_venta=118,
        cliente=_client(),
    )

    link = comunicacion_service.generar_link_whatsapp(
        doc,
        "987654321",
        "https://inkora.test/f001.pdf",
        _tenant(),
    )

    assert "wa.me/51987654321" in link
    assert "la factura F001-000001" in unquote(link)


def test_mailto_default_usa_etiqueta_boleta():
    doc = SimpleNamespace(
        document_kind="fiscal_document",
        tipo_comprobante="03",
        serie="B001",
        correlativo=2,
        moneda="PEN",
        total_venta=59,
        cliente=_client(),
    )

    link = comunicacion_service.generar_link_mailto(
        doc,
        "cliente@test.com",
        "https://inkora.test/b001.pdf",
        _tenant(),
    )

    decoded = unquote(link)
    assert decoded.startswith("mailto:cliente@test.com")
    assert "subject=Boleta B001-000002 - Inkora Demo" in decoded
    assert "la boleta B001-000002" in decoded
