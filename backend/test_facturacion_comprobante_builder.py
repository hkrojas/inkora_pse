from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services import facturacion_service


def _mock_item():
    return SimpleNamespace(
        descripcion="Servicio de impresión",
        cantidad=Decimal("2"),
        precio_unitario=Decimal("59.00"),
        producto_id=1,
        unidad_medida="NIU",
        tipo_afectacion_igv="10",
    )


def _mock_cliente():
    return SimpleNamespace(
        tipo_documento="6",
        numero_documento="20123456789",
        razon_social="Cliente Demo SAC",
        direccion="Av. Cliente 123",
        ubigeo="150101",
    )


def _mock_user():
    return SimpleNamespace(
        business_ruc="20100100100",
        business_name="Empresa Emisora SAC",
        business_address="Jr. Emisor 456",
        apisperu_token="token-demo",
        bank_accounts=[],
        tenant=None,
    )


def _mock_cotizacion(**overrides):
    data = {
        "id": 1,
        "serie": "F001",
        "correlativo": 1,
        "fecha_emision": datetime(2026, 4, 16, 10, 0, tzinfo=timezone.utc),
        "fecha_vencimiento": datetime(2026, 4, 30, 10, 0, tzinfo=timezone.utc),
        "moneda": "PEN",
        "tipo_comprobante": "01",
        "condicion_pago": "credito_15",
        "observaciones": "Entrega parcial coordinada con el cliente.",
        "cliente": _mock_cliente(),
        "items": [_mock_item()],
        "total_gravada": Decimal("100.00"),
        "total_igv": Decimal("18.00"),
        "total_venta": Decimal("118.00"),
        "porcentaje_detraccion": None,
        "sujeta_detraccion": False,
        "monto_detraccion": None,
        "cuenta_banco_nacion": None,
        "anticipos_deducidos": None,
        "total_anticipos": Decimal("0.00"),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_base_payload_credito_incluye_forma_pago_vencimiento_y_cuota():
    cotizacion = _mock_cotizacion()
    payload, _ = facturacion_service._base_payload(cotizacion, _mock_user(), "01")

    assert payload["formaPago"]["tipo"] == "Credito"
    assert payload["formaPago"]["monto"] == Decimal("118.00")
    assert payload["fecVencimiento"].startswith("2026-04-30")
    assert payload["cuotas"][0]["monto"] == Decimal("118.00")


def test_base_payload_incluye_observacion_y_tipo_operacion_override():
    cotizacion = _mock_cotizacion(condicion_pago="contado")
    payload, _ = facturacion_service._base_payload(
        cotizacion,
        _mock_user(),
        "01",
        tipo_operacion_override="0200",
    )

    assert payload["observacion"] == "Entrega parcial coordinada con el cliente."
    assert payload["tipoOperacion"] == "0200"
    assert payload["formaPago"]["tipo"] == "Contado"


def test_emitir_factura_respeta_override_de_serie_y_tipo_operacion():
    cotizacion = _mock_cotizacion(serie="F001", correlativo=4)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "hash": "abc123",
        "xml": "<xml />",
        "sunatResponse": {
            "success": True,
            "cdrResponse": {"code": "0", "description": "Aceptado", "notes": []},
        },
    }
    mock_response.headers = {"Content-Type": "application/json"}

    with patch("requests.post", return_value=mock_response) as post_mock:
        result = facturacion_service.emitir_factura(
            cotizacion,
            db=None,
            user=_mock_user(),
            tipo_doc_override="01",
            tipo_operacion_override="0200",
            serie_override="0001",
        )

    sent_payload = post_mock.call_args.kwargs["data"]
    assert '"tipoOperacion": "0200"' in sent_payload
    assert '"serie": "0001"' in sent_payload
    assert result["success"] is True
