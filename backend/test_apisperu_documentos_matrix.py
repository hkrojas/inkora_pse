"""
test_apisperu_documentos_matrix.py
==================================

Matriz de contrato para todas las familias documentarias del swagger de ApisPeru.

Objetivo:
  - dejar explicito que endpoint usa cada familia
  - verificar si la respuesta es inmediata o asincrona con ticket
  - cubrir las familias soportadas actualmente por el backend
  - cubrir tambien wrappers de servicio para familias aun no expuestas por router

Ejecutar:
    cd backend
    python -m pytest test_apisperu_documentos_matrix.py -v
"""

import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import crud
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from services import facturacion_service


def _make_user_with_apisperu(db_session, suffix: str):
    tenant = make_tenant(db_session, suffix)
    user = make_user(db_session, tenant, email=f"{suffix.lower()}@test.com")
    tenant.apisperu_token = "fake_token"
    tenant.apisperu_url = "https://facturacion.test/api/v1"
    db_session.commit()
    db_session.refresh(tenant)
    return tenant, user


def _mock_immediate_provider_response(*, description: str = "Aceptado"):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "hash": "hash-123",
        "xml": "<xml />",
        "sunatResponse": {
            "success": True,
            "cdrZip": "zip64",
            "cdrResponse": {
                "code": "0",
                "description": description,
                "notes": [],
            },
        },
    }
    return response


def _mock_async_send_response(ticket: str = "ticket-123"):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "hash": "hash-ticket",
        "xml": "<xml-ticket />",
        "sunatResponse": {
            "success": True,
            "ticket": ticket,
        },
    }
    return response


def _mock_async_status_response(*, description: str = "Aceptado"):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "success": True,
        "code": "0",
        "cdrZip": "zip64",
        "cdrResponse": {
            "code": "0",
            "description": description,
            "notes": [],
        },
    }
    return response


def _mock_provider_business_error_response(*, code: str, message: str, xml: str | None = None):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "xml": xml or "<xml />",
        "sunatResponse": {
            "success": False,
            "error": {
                "code": code,
                "message": message,
            },
        },
    }
    return response


def _mock_provider_http_error_response(*, status_code: int, body: dict):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = body
    response.headers = {"Content-Type": "application/json"}
    response.text = json.dumps(body)
    return response


def _mock_xml_render_response():
    response = MagicMock()
    response.status_code = 200
    response.headers = {"Content-Type": "text/xml; charset=UTF-8"}
    response.text = "<?xml version='1.0'?><DespatchAdvice />"
    return response


def _make_fiscal_document(db_session, suffix: str, tipo_comprobante: str):
    tenant, user = _make_user_with_apisperu(db_session, suffix)
    tipo_doc_cliente = "6" if tipo_comprobante == "01" else "1"
    numero_documento = "20191308868" if tipo_doc_cliente == "6" else "72758912"
    cliente = make_cliente(
        db_session,
        tenant,
        suffix,
        tipo_documento=tipo_doc_cliente,
        numero_documento=numero_documento,
    )
    quote = make_quote_via_crud(db_session, tenant, user, cliente)
    fiscal = crud.create_fiscal_document_from_quote(
        db_session,
        quote,
        user.id,
        tipo_comprobante,
    )
    return tenant, user, quote, fiscal


def _make_nota_documento(db_session, suffix: str, *, tipo_nota: str):
    _, user, _, fiscal = _make_fiscal_document(db_session, suffix, "01")
    fiscal.estado = "facturada"
    db_session.commit()
    nota = crud.crear_nota_credito_debito(
        db_session,
        fiscal,
        user.id,
        tipo_nota,
        "01" if tipo_nota == "credito" else "02",
        "Documento de prueba",
    )
    return user, fiscal, nota


def _make_guia(db_session, suffix: str):
    tenant, user, _, fiscal = _make_fiscal_document(db_session, suffix, "01")
    guia = crud.create_guia_remision(
        db_session,
        {
            "cotizacion_id": fiscal.id,
            "fecha_traslado": datetime.now(timezone.utc),
            "motivo_traslado": "01",
            "descripcion_motivo": "VENTA",
            "peso_bruto_total": Decimal("5.00"),
            "unidad_medida_peso": "KGM",
            "numero_bultos": 1,
            "modalidad_traslado": "02",
            "conductor_tipo_doc": "1",
            "conductor_nro_doc": "72758912",
            "conductor_nombres": "KENNEDY",
            "conductor_apellidos": "ROJAS",
            "conductor_licencia": "Q12345678",
            "vehiculo_placa": "ABC123",
            "partida_ubigeo": "150101",
            "partida_direccion": "Av. Origen 100",
            "llegada_ubigeo": "150101",
            "llegada_direccion": "Av. Destino 200",
            "items": [
                {
                    "descripcion": "Paquete de prueba",
                    "cantidad": Decimal("2"),
                    "unidad_medida": "NIU",
                    "codigo_producto": "PK-001",
                }
            ],
        },
        user.id,
        tenant.id,
    )
    return user, guia


class TestApisPeruDocumentosMatrix:
    def test_factura_usa_invoice_send_y_respuesta_inmediata(self, db_session):
        _, user, _, fiscal = _make_fiscal_document(db_session, "MX01", "01")

        with patch("requests.post", return_value=_mock_immediate_provider_response()) as post_mock:
            result = facturacion_service.emitir_factura(
                fiscal,
                db_session,
                user,
                tipo_doc_override="01",
            )

        assert post_mock.call_args.args[0] == "https://facturacion.test/api/v1/invoice/send"
        assert result["success"] is True
        assert "ticket" not in result

    def test_boleta_usa_invoice_send_y_respuesta_inmediata(self, db_session):
        _, user, _, fiscal = _make_fiscal_document(db_session, "MX02", "03")

        with patch("requests.post", return_value=_mock_immediate_provider_response()) as post_mock:
            result = facturacion_service.emitir_factura(
                fiscal,
                db_session,
                user,
                tipo_doc_override="03",
            )

        sent_payload = json.loads(post_mock.call_args.kwargs["data"])
        assert post_mock.call_args.args[0] == "https://facturacion.test/api/v1/invoice/send"
        assert sent_payload["tipoDoc"] == "03"
        assert result["success"] is True
        assert "ticket" not in result

    def test_nota_credito_usa_note_send_y_respuesta_inmediata(self, db_session):
        user, fiscal, nota = _make_nota_documento(db_session, "MX03", tipo_nota="credito")

        with patch("requests.post", return_value=_mock_immediate_provider_response()) as post_mock:
            result = facturacion_service.emitir_nota(
                nota,
                fiscal,
                user,
                "01",
                "ANULACION DE LA OPERACION",
                "credito",
            )

        sent_payload = json.loads(post_mock.call_args.kwargs["data"])
        assert post_mock.call_args.args[0] == "https://facturacion.test/api/v1/note/send"
        assert sent_payload["tipoDoc"] == "07"
        assert sent_payload["serie"] == "FF01"
        assert result["success"] is True

    def test_nota_debito_usa_note_send_y_respuesta_inmediata(self, db_session):
        user, fiscal, nota = _make_nota_documento(db_session, "MX04", tipo_nota="debito")

        with patch("requests.post", return_value=_mock_immediate_provider_response()) as post_mock:
            result = facturacion_service.emitir_nota(
                nota,
                fiscal,
                user,
                "02",
                "AUMENTO DE VALOR",
                "debito",
            )

        sent_payload = json.loads(post_mock.call_args.kwargs["data"])
        assert post_mock.call_args.args[0] == "https://facturacion.test/api/v1/note/send"
        assert sent_payload["tipoDoc"] == "08"
        assert result["success"] is True

    def test_resumen_diario_usa_summary_send_y_status(self, db_session):
        tenant, user = _make_user_with_apisperu(db_session, "MX05")
        payload = {
            "fecGeneracion": "2026-04-11T10:00:00-05:00",
            "fecResumen": "2026-04-11T10:00:00-05:00",
            "correlativo": "00001",
            "moneda": "PEN",
            "company": {"ruc": tenant.business_ruc},
            "details": [],
        }

        with patch("requests.post", return_value=_mock_async_send_response("summary-1")) as post_mock, patch(
            "requests.get",
            return_value=_mock_async_status_response(description="Resumen aceptado"),
        ) as get_mock:
            result = facturacion_service.emitir_resumen_diario(payload, user)

        assert post_mock.call_args.args[0] == "https://facturacion.test/api/v1/summary/send"
        assert get_mock.call_args.args[0] == "https://facturacion.test/api/v1/summary/status"
        assert get_mock.call_args.kwargs["params"]["ticket"] == "summary-1"
        assert get_mock.call_args.kwargs["params"]["ruc"] == tenant.business_ruc
        assert result["success"] is True
        assert result["ticket"] == "summary-1"

    def test_comunicacion_baja_factura_usa_voided_send_y_status(self, db_session):
        _, user, _, fiscal = _make_fiscal_document(db_session, "MX06", "01")
        fiscal.estado = "facturada"
        db_session.commit()

        with patch("requests.post", return_value=_mock_async_send_response("voided-1")) as post_mock, patch(
            "requests.get",
            return_value=_mock_async_status_response(description="Baja aceptada"),
        ) as get_mock:
            result = facturacion_service.anular_comprobante(
                fiscal,
                "ERROR EN CALCULOS",
                user,
            )

        sent_payload = json.loads(post_mock.call_args.kwargs["data"])
        assert post_mock.call_args.args[0] == "https://facturacion.test/api/v1/voided/send"
        assert sent_payload["details"][0]["tipoDoc"] == "01"
        assert get_mock.call_args.args[0] == "https://facturacion.test/api/v1/voided/status"
        assert get_mock.call_args.kwargs["params"]["ruc"] == fiscal.tenant.business_ruc
        assert result["success"] is True
        assert result["ticket"] == "voided-1"

    def test_baja_boleta_usa_summary_send_y_status(self, db_session):
        _, user, _, boleta = _make_fiscal_document(db_session, "MX07", "03")
        boleta.estado = "facturada"
        db_session.commit()

        with patch("requests.post", return_value=_mock_async_send_response("summary-2")) as post_mock, patch(
            "requests.get",
            return_value=_mock_async_status_response(description="Resumen de baja aceptado"),
        ) as get_mock:
            result = facturacion_service.anular_comprobante(
                boleta,
                "ANULACION DE BOLETA",
                user,
            )

        assert post_mock.call_args.args[0] == "https://facturacion.test/api/v1/summary/send"
        assert get_mock.call_args.args[0] == "https://facturacion.test/api/v1/summary/status"
        assert get_mock.call_args.kwargs["params"]["ruc"] == boleta.tenant.business_ruc
        assert result["success"] is True
        assert result["ticket"] == "summary-2"

    def test_guia_remision_usa_despatch_send_y_status(self, db_session):
        user, guia = _make_guia(db_session, "MX08")

        with patch("requests.post", return_value=_mock_async_send_response("despatch-1")) as post_mock, patch(
            "requests.get",
            return_value=_mock_async_status_response(description="Guia aceptada"),
        ) as get_mock:
            result = facturacion_service.emitir_guia_remision(guia, user)

        sent_payload = json.loads(post_mock.call_args.kwargs["data"])
        assert post_mock.call_args.args[0] == "https://facturacion.test/api/v1/despatch/send"
        assert sent_payload["tipoDoc"] == "09"
        assert sent_payload["envio"]["vehiculo"]["placa"] == "ABC123"
        assert sent_payload["envio"]["choferes"][0]["nroDoc"] == "72758912"
        assert "transportista" not in sent_payload["envio"]
        assert get_mock.call_args.args[0] == "https://facturacion.test/api/v1/despatch/status"
        assert get_mock.call_args.kwargs["params"]["ruc"] == guia.tenant.business_ruc
        assert result["success"] is True
        assert result["ticket"] == "despatch-1"

    def test_guia_publica_extiende_payload_con_campos_gre_opcionales(self, db_session):
        user, guia = _make_guia(db_session, "MX08B")
        guia.modalidad_traslado = "01"
        guia.transportista_ruc = "20499709944"
        guia.transportista_razon_social = "GRUPO VEGA DISTRIBUCION S.A.C."
        guia.transportista_nro_mtc = "12345678901"
        guia.sustento_peso = "MANUAL"
        guia.ind_transbordo = True
        guia.num_contenedor = "CONT-123"
        guia.cod_puerto = "123"
        db_session.commit()

        payload = facturacion_service._base_payload_gre(guia, user)

        assert payload["envio"]["transportista"]["nroMtc"] == "12345678901"
        assert payload["envio"]["sustentoPeso"] == "MANUAL"
        assert payload["envio"]["indTransbordo"] is True
        assert payload["envio"]["numContenedor"] == "CONT-123"
        assert payload["envio"]["codPuerto"] == "123"

    def test_guia_privada_extiende_payload_vehiculo_con_campos_opcionales(self, db_session):
        user, guia = _make_guia(db_session, "MX08C")
        guia.modalidad_traslado = "02"
        guia.vehiculo_nro_circulacion = "NC-001"
        guia.vehiculo_cod_emisor = "EM-01"
        guia.vehiculo_nro_autorizacion = "AUTH-001"
        db_session.commit()

        payload = facturacion_service._base_payload_gre(guia, user)

        assert payload["envio"]["vehiculo"]["nroCirculacion"] == "NC-001"
        assert payload["envio"]["vehiculo"]["codEmisor"] == "EM-01"
        assert payload["envio"]["vehiculo"]["nroAutorizacion"] == "AUTH-001"

    def test_retencion_usa_retention_send_y_respuesta_inmediata(self, db_session):
        _, user = _make_user_with_apisperu(db_session, "MX09")
        payload = {
            "serie": "R001",
            "correlativo": "000001",
            "company": {"ruc": "20606751509"},
            "proveedor": {"tipoDoc": "6", "numDoc": "20191308868", "rznSocial": "Proveedor Demo"},
        }

        with patch("requests.post", return_value=_mock_immediate_provider_response()) as post_mock:
            result = facturacion_service.emitir_retencion(payload, user)

        assert post_mock.call_args.args[0] == "https://facturacion.test/api/v1/retention/send"
        assert result["success"] is True
        assert "ticket" not in result

    def test_percepcion_usa_perception_send_y_respuesta_inmediata(self, db_session):
        _, user = _make_user_with_apisperu(db_session, "MX10")
        payload = {
            "serie": "P001",
            "correlativo": "000001",
            "company": {"ruc": "20606751509"},
            "cliente": {"tipoDoc": "6", "numDoc": "20191308868", "rznSocial": "Cliente Demo"},
        }

        with patch("requests.post", return_value=_mock_immediate_provider_response()) as post_mock:
            result = facturacion_service.emitir_percepcion(payload, user)

        assert post_mock.call_args.args[0] == "https://facturacion.test/api/v1/perception/send"
        assert result["success"] is True
        assert "ticket" not in result

    def test_reversion_usa_reversion_send_y_status(self, db_session):
        tenant, user = _make_user_with_apisperu(db_session, "MX11")
        payload = {
            "fecGeneracion": "2026-04-11T10:00:00-05:00",
            "fecComunicacion": "2026-04-11T10:01:00-05:00",
            "correlativo": "00001",
            "company": {"ruc": tenant.business_ruc},
            "details": [],
        }

        with patch("requests.post", return_value=_mock_async_send_response("reversion-1")) as post_mock, patch(
            "requests.get",
            return_value=_mock_async_status_response(description="Reversion aceptada"),
        ) as get_mock:
            result = facturacion_service.emitir_reversion(payload, user)

        assert post_mock.call_args.args[0] == "https://facturacion.test/api/v1/reversion/send"
        assert get_mock.call_args.args[0] == "https://facturacion.test/api/v1/reversion/status"
        assert get_mock.call_args.kwargs["params"]["ticket"] == "reversion-1"
        assert get_mock.call_args.kwargs["params"]["ruc"] == tenant.business_ruc
        assert result["success"] is True
        assert result["ticket"] == "reversion-1"

    def test_poll_async_status_reintenta_cuando_ticket_aun_no_existe(self, db_session):
        tenant, user = _make_user_with_apisperu(db_session, "MX12")
        payload = {
            "fecGeneracion": "2026-04-11T10:00:00-05:00",
            "fecResumen": "2026-04-11T10:00:00-05:00",
            "correlativo": "00001",
            "moneda": "PEN",
            "company": {"ruc": tenant.business_ruc},
            "details": [],
        }
        pending = MagicMock()
        pending.status_code = 200
        pending.json.return_value = {
            "success": False,
            "error": {
                "code": "0127",
                "message": "Ticket no existe",
            },
            "code": "0127",
        }

        with patch("requests.post", return_value=_mock_async_send_response("summary-12")), patch(
            "requests.get",
            side_effect=[
                pending,
                _mock_async_status_response(description="Resumen aceptado luego de espera"),
            ],
        ) as get_mock, patch("services.facturacion_service.time.sleep") as sleep_mock:
            result = facturacion_service.emitir_resumen_diario(payload, user)

        assert get_mock.call_count == 2
        sleep_mock.assert_called_once()
        assert result["success"] is True
        assert result["ticket"] == "summary-12"

    def test_resumen_diario_reporta_diagnostico_si_proveedor_genera_xml_sin_percent(self, db_session):
        tenant, user = _make_user_with_apisperu(db_session, "MX13")
        payload = {
            "fecGeneracion": "2026-04-11T10:00:00-05:00",
            "fecResumen": "2026-04-11T10:00:00-05:00",
            "correlativo": "00001",
            "moneda": "PEN",
            "company": {"ruc": tenant.business_ruc},
            "details": [],
        }
        xml_without_percent = (
            "<cac:TaxSubtotal><cbc:TaxAmount currencyID='PEN'>9.00</cbc:TaxAmount>"
            "<cac:TaxCategory><cac:TaxScheme><cbc:ID>1000</cbc:ID></cac:TaxScheme>"
            "</cac:TaxCategory></cac:TaxSubtotal>"
        )

        with patch(
            "requests.post",
            return_value=_mock_provider_business_error_response(
                code="2992",
                message="Falta tasa del tributo",
                xml=xml_without_percent,
            ),
        ):
            with pytest.raises(facturacion_service.FacturacionException) as exc:
                facturacion_service.emitir_resumen_diario(payload, user)

        assert "<cbc:Percent>" in str(exc.value)

    def test_resumen_baja_payload_usa_estado_anular(self, db_session):
        """_build_summary_payload debe usar estado '3' para anulacion segun Catalogo 19."""
        _, user, _, boleta = _make_fiscal_document(db_session, "MX15", "03")
        boleta.serie = "B001"
        boleta.correlativo = 1
        boleta.total_venta = Decimal("100.00")
        boleta.total_gravada = Decimal("84.75")
        boleta.total_igv = Decimal("15.25")
        db_session.commit()

        payload = facturacion_service._build_summary_payload(boleta, "ANULACION TEST", user)

        assert len(payload["details"]) == 1
        detail = payload["details"][0]
        assert detail["estado"] == "3", (
            f"Baja por resumen debe usar estado '3' (Anular segun Catalogo 19 SUNAT), "
            f"pero se obtuvo '{detail['estado']}'"
        )
        assert detail["desMotivoBaja"] == "ANULACION TEST"
        assert detail["tipoDoc"] == "03"
        assert detail["serieNro"] == "B001-1"

    def test_nota_download_payload_incluye_motivo_y_documento_afectado(self, db_session):
        """_build_download_payload para nota 07/08 debe incluir datos requeridos por /note/pdf."""
        user, fiscal, nota = _make_nota_documento(db_session, "MX16", tipo_nota="credito")

        payload = facturacion_service._build_download_payload(nota, user)

        assert "details" in payload, (
            "El payload de descarga de nota (07/08) debe incluir 'details' para que el "
            "endpoint PDF del proveedor pueda renderizar el documento completo"
        )
        assert len(payload["details"]) > 0
        assert payload.get("serie") == nota.serie
        assert payload.get("correlativo") == str(nota.correlativo).zfill(6)
        assert "company" in payload
        assert "client" in payload
        assert payload["tipDocAfectado"] == fiscal.tipo_comprobante
        assert payload["numDocfectado"] == facturacion_service._document_number(fiscal)
        assert payload["codMotivo"] == "01"
        assert payload["desMotivo"] == "Documento de prueba"

    def test_guia_reporta_cuando_xml_funciona_pero_send_falla(self, db_session):
        user, guia = _make_guia(db_session, "MX14")

        with patch(
            "requests.post",
            side_effect=[
                _mock_provider_http_error_response(
                    status_code=500,
                    body={"error": "Error al comunicarse con el servidor interno"},
                ),
                _mock_xml_render_response(),
            ],
        ):
            with pytest.raises(facturacion_service.FacturacionException) as exc:
                facturacion_service.emitir_guia_remision(guia, user)

        assert "/despatch/xml" in str(exc.value)
        assert "envio SUNAT" in str(exc.value)
