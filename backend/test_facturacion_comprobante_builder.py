from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from schemas.resumenes import ResumenDiarioCreate
from schemas.reversiones import ReversionCreate
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
    tenant = SimpleNamespace(
        business_ruc="20100100100",
        business_name="Empresa Emisora SAC",
        business_address="Jr. Emisor 456",
        apisperu_token="token-demo",
        apisperu_url="https://facturacion.test/api/v1",
        smartpse_company_id="77",
        smartpse_environment="demo",
        smartpse_usuario_secundaria="AB3KPQR9",
        smartpse_token_acceso="MX7TNVQG",
        bank_accounts=[],
    )
    return SimpleNamespace(tenant=tenant)


def test_resumen_schema_acepta_correlativo_completo_rc():
    resumen = ResumenDiarioCreate(
        correlativo="RC-20260501-1",
        fecGeneracion="2026-05-01",
        fecResumen="2026-05-01",
        details=[
            {
                "tipoDoc": "03",
                "serieNro": "B001-1",
                "total": "118.00",
                "mtoOperGravadas": "100.00",
                "mtoIGV": "18.00",
            }
        ],
    )

    assert resumen.correlativo == "20260501-1"


def test_reversion_schema_acepta_correlativo_completo_rr():
    reversion = ReversionCreate(
        correlativo="RR-20260502-1",
        fecGeneracion="2026-05-01",
        fecComunicacion="2026-05-02",
        details=[
            {
                "tipoDoc": "20",
                "serie": "R001",
                "correlativo": "122",
                "desMotivoBaja": "error de sistema",
            }
        ],
    )

    assert reversion.correlativo == "20260502-1"


def _smartpse_accepted(*, tag: str = "Invoice", description: str = "Aceptado"):
    return {
        "estado": 200,
        "mensaje": description,
        "xml_firmado": f"<{tag} />",
        "codigo_hash": "abc123",
        "cdr": "<ApplicationResponse/>",
        "rechazado": False,
    }


def _smartpse_pending(ticket: str, *, tag: str = "ApplicationResponse"):
    return {
        "estado": 202,
        "mensaje": "Pendiente",
        "ticket": ticket,
        "xml_firmado": f"<{tag} />",
        "codigo_hash": "abc123",
    }


class _FakeSmartPSEClient:
    def __init__(self, process_responses, consult_responses=None):
        self.process_responses = list(process_responses)
        self.consult_responses = list(consult_responses or [])
        self.process_calls = []
        self.consult_calls = []

    def process_xml(self, tenant, nombre_archivo, xml_content, *, demo=False):
        self.process_calls.append((tenant, nombre_archivo, xml_content, demo))
        return self.process_responses.pop(0)

    def consult_ticket(self, tenant, nombre_archivo):
        self.consult_calls.append((tenant, nombre_archivo))
        return self.consult_responses.pop(0) if self.consult_responses else _smartpse_accepted()


def _patch_smartpse(fake_client):
    return patch("services.facturacion_service.smartpse_client.get_default_client", return_value=fake_client)


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


def test_base_payload_credito_usa_cronograma_de_cuotas_persistido():
    cotizacion = _mock_cotizacion(
        cuotas_pago=[
            {"fecha_pago": "2026-04-23T00:00:00+00:00", "monto": "59.00"},
            {"fecha_pago": "2026-04-30T00:00:00+00:00", "monto": "59.00"},
        ],
    )

    payload, _ = facturacion_service._base_payload(cotizacion, _mock_user(), "01")

    assert payload["formaPago"]["tipo"] == "Credito"
    assert payload["formaPago"]["monto"] == Decimal("118.00")
    assert len(payload["cuotas"]) == 2
    assert payload["cuotas"][0]["monto"] == Decimal("59.00")
    assert payload["cuotas"][0]["fechaPago"].startswith("2026-04-23")
    assert payload["cuotas"][1]["monto"] == Decimal("59.00")
    assert payload["fecVencimiento"].startswith("2026-04-30")


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


def test_base_payload_prefiere_snapshot_cliente_del_documento():
    cotizacion = _mock_cotizacion(
        cliente_snapshot={
            "tipo_documento": "6",
            "numero_documento": "20999999991",
            "razon_social": "Cliente Snapshot Fiscal",
            "direccion": "Jr. Snapshot Fiscal 321",
            "ubigeo": "150102",
        },
    )

    payload, _ = facturacion_service._base_payload(cotizacion, _mock_user(), "01")

    assert payload["client"]["numDoc"] == "20999999991"
    assert payload["client"]["rznSocial"] == "Cliente Snapshot Fiscal"
    assert payload["client"]["address"]["direccion"] == "Jr. Snapshot Fiscal 321"
    assert payload["client"]["address"]["ubigueo"] == "150102"


def test_emitir_factura_respeta_override_de_serie_y_tipo_operacion():
    cotizacion = _mock_cotizacion(serie="F001", correlativo=4)
    fake_client = _FakeSmartPSEClient([_smartpse_accepted(tag="Invoice")])

    with _patch_smartpse(fake_client):
        result = facturacion_service.emitir_factura(
            cotizacion,
            db=None,
            user=_mock_user(),
            tipo_doc_override="01",
            tipo_operacion_override="0200",
            serie_override="0001",
        )

    _, filename, xml_content, _ = fake_client.process_calls[0]
    xml_text = xml_content.decode("utf-8")
    assert "-01-0001-" in filename
    assert 'listID="0200"' in xml_text
    assert result["success"] is True


def test_resumen_diario_payload_usa_contrato_apisperu():
    payload = {
        "fecGeneracion": "2026-05-01",
        "fecResumen": "2026-05-01",
        "correlativo": "RC-20260501-001",
        "moneda": "pen",
        "details": [
            {
                "tipoDoc": "3",
                "serieNro": "b001-1",
                "estado": "1",
                "clienteTipo": "1",
                "clienteNro": "00000000",
                "total": "118.00",
                "mtoOperGravadas": "100.00",
                "mtoIGV": "18.00",
            },
        ],
    }

    result = facturacion_service.build_resumen_diario_payload(payload, _mock_user())

    assert result["correlativo"] == "20260501-001"
    assert result["fecGeneracion"] == "2026-05-01T00:00:00-05:00"
    assert result["fecResumen"] == "2026-05-01T00:00:00-05:00"
    assert result["moneda"] == "PEN"
    assert result["company"]["ruc"] == "20100100100"
    assert result["details"][0]["tipoDoc"] == "03"
    assert result["details"][0]["serieNro"] == "B001-000001"
    assert result["details"][0]["total"] == Decimal("118.00")


def test_emitir_resumen_diario_con_ticket_queda_pendiente_sin_polling():
    fake_client = _FakeSmartPSEClient([_smartpse_pending("20260501000001", tag="SummaryDocuments")])
    payload = {
        "fecGeneracion": "2026-05-01T00:00:00-05:00",
        "fecResumen": "2026-05-01T00:00:00-05:00",
        "correlativo": "001",
        "moneda": "PEN",
        "details": [
            {
                "tipoDoc": "03",
                "serieNro": "B001-1",
                "estado": "1",
                "clienteTipo": "1",
                "clienteNro": "00000000",
                "total": "118.00",
                "mtoOperGravadas": "100.00",
                "mtoIGV": "18.00",
            },
        ],
    }

    with _patch_smartpse(fake_client):
        result = facturacion_service.emitir_resumen_diario(payload, _mock_user())

    assert result["success"] is True
    assert result["pending"] is True
    assert result["ticket"] == "20260501000001"
    assert fake_client.consult_calls == []
    _, filename, xml_content, _ = fake_client.process_calls[0]
    assert filename == "20100100100-RC-20260501-00001"
    assert b"RC-20260501-00001" in xml_content
    assert b"B001-000001" in xml_content


def test_retencion_payload_usa_contrato_apisperu():
    payload = {
        "serie": "r001",
        "correlativo": "123",
        "fechaEmision": "2026-05-01",
        "proveedor": {
            "tipoDoc": "6",
            "numDoc": "20191308868",
            "rznSocial": "Proveedor Demo SAC",
        },
        "regimen": "01",
        "tasa": "3",
        "details": [
            {
                "tipoDoc": "1",
                "numDoc": "f001-1",
                "fechaEmision": "2026-05-01",
                "fechaRetencion": "2026-05-01",
                "moneda": "pen",
                "impTotal": "118.00",
                "impPagar": "114.46",
                "impRetenido": "3.54",
            },
        ],
    }

    result = facturacion_service.build_retencion_payload(payload, _mock_user())

    assert result["serie"] == "R001"
    assert result["fechaEmision"] == "2026-05-01T00:00:00-05:00"
    assert result["company"]["ruc"] == "20100100100"
    assert result["proveedor"]["numDoc"] == "20191308868"
    assert result["regimen"] == "01"
    assert result["tasa"] == Decimal("3.00")
    assert result["impRetenido"] == Decimal("3.54")
    assert result["impPagado"] == Decimal("114.46")
    assert result["details"][0]["tipoDoc"] == "01"
    assert result["details"][0]["numDoc"] == "F001-1"
    assert result["details"][0]["pagos"][0]["importe"] == Decimal("114.46")
    assert result["details"][0]["tipoCambio"]["factor"] == 1


def test_percepcion_payload_usa_contrato_apisperu():
    payload = {
        "serie": "p001",
        "correlativo": "123",
        "fechaEmision": "2026-05-01",
        "client": {
            "tipoDoc": "6",
            "numDoc": "20191308868",
            "rznSocial": "Cliente Demo SAC",
        },
        "regPercepcion": "01",
        "tasaPercepcion": "2",
        "details": [
            {
                "tipoDoc": "1",
                "serieNro": "f001-1",
                "fechaEmision": "2026-05-01",
                "fechaPercepcion": "2026-05-01",
                "moneda": "pen",
                "impSinPercepcion": "100.00",
                "impPercepcion": "2.00",
                "impConPercepcion": "102.00",
            },
        ],
    }

    result = facturacion_service.build_percepcion_payload(payload, _mock_user())

    assert result["serie"] == "P001"
    assert result["fechaEmision"] == "2026-05-01T00:00:00-05:00"
    assert result["company"]["ruc"] == "20100100100"
    assert result["proveedor"]["numDoc"] == "20191308868"
    assert result["regimen"] == "01"
    assert result["tasa"] == Decimal("2.00")
    assert result["impPercibido"] == Decimal("2.00")
    assert result["impCobrado"] == Decimal("102.00")
    assert result["details"][0]["tipoDoc"] == "01"
    assert result["details"][0]["numDoc"] == "F001-1"
    assert result["details"][0]["cobros"][0]["importe"] == Decimal("102.00")
    assert result["details"][0]["tipoCambio"]["factor"] == 1


def test_reversion_payload_usa_contrato_apisperu():
    payload = {
        "fecGeneracion": "2026-05-01",
        "fecComunicacion": "2026-05-02",
        "correlativo": "RR-20260502-001",
        "details": [
            {
                "tipoDoc": "20",
                "serie": "r001",
                "correlativo": "122",
                "desMotivoBaja": "error de sistema",
            },
        ],
    }

    result = facturacion_service.build_reversion_payload(payload, _mock_user())

    assert result["correlativo"] == "20260502-001"
    assert result["fecGeneracion"] == "2026-05-01T00:00:00-05:00"
    assert result["fecComunicacion"] == "2026-05-02T00:00:00-05:00"
    assert result["company"]["ruc"] == "20100100100"
    assert result["details"][0] == {
        "tipoDoc": "20",
        "serie": "R001",
        "correlativo": "122",
        "desMotivoBaja": "ERROR DE SISTEMA",
    }


def test_emitir_reversion_puede_guardar_ticket_sin_polling():
    fake_client = _FakeSmartPSEClient([_smartpse_pending("20260502000001", tag="VoidedDocuments")])
    payload = {
        "fecGeneracion": "2026-05-01T00:00:00-05:00",
        "fecComunicacion": "2026-05-02T00:00:00-05:00",
        "correlativo": "001",
        "details": [
            {
                "tipoDoc": "20",
                "serie": "R001",
                "correlativo": "122",
                "desMotivoBaja": "ERROR DE SISTEMA",
            },
        ],
    }

    with _patch_smartpse(fake_client):
        result = facturacion_service.emitir_reversion(payload, _mock_user(), poll_async=False)

    assert result["success"] is True
    assert result["pending"] is True
    assert result["ticket"] == "20260502000001"
    assert fake_client.consult_calls == []
    _, filename, xml_content, _ = fake_client.process_calls[0]
    assert filename == "20100100100-RR-20260502-00001"
    assert b"RR-20260502-00001" in xml_content


def test_aplicar_detraccion_usa_tipo_operacion_1001():
    payload = {
        "tipoDoc": "01",
        "tipoOperacion": "0101",
        "mtoOperGravadas": Decimal("1000.00"),
        "mtoOperExoneradas": Decimal("0.00"),
        "mtoOperInafectas": Decimal("0.00"),
        "mtoIGV": Decimal("180.00"),
        "mtoImpVenta": Decimal("1180.00"),
        "mtoImporteTotal": Decimal("1180.00"),
        "legends": [],
    }
    cotizacion = _mock_cotizacion(condicion_pago="contado", total_venta=Decimal("1180.00"))

    result = facturacion_service._aplicar_detraccion(payload, cotizacion, _mock_user(), db=None)

    assert result["tipoOperacion"] == "1001"
    assert result["detraccion"]["percent"] == Decimal("12.00")
    assert result["detraccion"]["mount"] == Decimal("141.60")
