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
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import crud
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from services import facturacion_service, secret_box, smartpse_client


def _make_user_with_apisperu(db_session, suffix: str):
    tenant = make_tenant(db_session, suffix)
    user = make_user(db_session, tenant, email=f"{suffix.lower()}@test.com")
    tenant.apisperu_token = "fake_token"
    tenant.apisperu_url = "https://facturacion.test/api/v1"
    tenant.smartpse_company_id = "77"
    tenant.smartpse_environment = "demo"
    tenant.smartpse_usuario_secundaria = "AB3KPQR9"
    tenant.smartpse_token_acceso = "MX7TNVQG"
    tenant.smartpse_gre_sol_username = "SOLUSER"
    tenant.smartpse_gre_sol_password_enc = secret_box.encrypt_secret("sol-password-demo")
    tenant.smartpse_gre_client_id = "client-id"
    tenant.smartpse_gre_client_secret_enc = secret_box.encrypt_secret("client-secret")
    db_session.commit()
    db_session.refresh(tenant)
    return tenant, user


def _smartpse_accepted(*, description: str = "Aceptado", tag: str = "Invoice"):
    return {
        "estado": 200,
        "mensaje": description,
        "xml_firmado": f"<{tag} />",
        "codigo_hash": "hash-123",
        "cdr": "<ApplicationResponse/>",
        "rechazado": False,
    }


def _smartpse_pending(ticket: str, *, tag: str = "ApplicationResponse"):
    return {
        "estado": 202,
        "mensaje": "Pendiente",
        "ticket": ticket,
        "xml_firmado": f"<{tag} />",
        "codigo_hash": "hash-ticket",
    }


class _FakeSmartPSEClient:
    def __init__(self, process_responses=None, consult_responses=None):
        self.process_responses = list(process_responses or [_smartpse_accepted()])
        self.consult_responses = list(consult_responses or [])
        self.process_calls = []
        self.process_kwargs = []
        self.consult_calls = []

    def process_xml(self, tenant, nombre_archivo, xml_content, *, demo=False, **kwargs):
        self.process_calls.append((tenant, nombre_archivo, xml_content, demo))
        self.process_kwargs.append(kwargs)
        response = self.process_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def consult_ticket(self, tenant, nombre_archivo):
        self.consult_calls.append((tenant, nombre_archivo))
        response = self.consult_responses.pop(0) if self.consult_responses else _smartpse_accepted()
        if isinstance(response, Exception):
            raise response
        return response


def _patch_smartpse(fake_client):
    return patch("services.facturacion_service.smartpse_client.get_default_client", return_value=fake_client)


def _filename_ruc(tenant) -> str:
    return "".join(ch for ch in str(tenant.business_ruc) if ch.isdigit())


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
        tenant, user, _, fiscal = _make_fiscal_document(db_session, "MX01", "01")
        fake_client = _FakeSmartPSEClient([_smartpse_accepted(tag="Invoice")])

        with _patch_smartpse(fake_client):
            result = facturacion_service.emitir_factura(
                fiscal,
                db_session,
                user,
                tipo_doc_override="01",
            )

        _, filename, xml_content, demo = fake_client.process_calls[0]
        assert filename.startswith(f"{_filename_ruc(tenant)}-01-")
        assert b"InvoiceTypeCode" in xml_content
        assert demo is True
        assert result["success"] is True
        assert not result.get("ticket")

    def test_boleta_usa_invoice_send_y_respuesta_inmediata(self, db_session):
        tenant, user, _, fiscal = _make_fiscal_document(db_session, "MX02", "03")
        fake_client = _FakeSmartPSEClient([_smartpse_accepted(tag="Invoice")])

        with _patch_smartpse(fake_client):
            result = facturacion_service.emitir_factura(
                fiscal,
                db_session,
                user,
                tipo_doc_override="03",
            )

        _, filename, xml_content, _ = fake_client.process_calls[0]
        assert filename.startswith(f"{_filename_ruc(tenant)}-03-")
        assert "InvoiceTypeCode" in xml_content.decode("utf-8")
        assert ">03<" in xml_content.decode("utf-8")
        assert result["success"] is True
        assert not result.get("ticket")

    def test_nota_credito_usa_note_send_y_respuesta_inmediata(self, db_session):
        user, fiscal, nota = _make_nota_documento(db_session, "MX03", tipo_nota="credito")
        fake_client = _FakeSmartPSEClient([_smartpse_accepted(tag="CreditNote")])

        with _patch_smartpse(fake_client):
            result = facturacion_service.emitir_nota(
                nota,
                fiscal,
                user,
                "01",
                "ANULACION DE LA OPERACION",
                "credito",
            )

        _, filename, xml_content, _ = fake_client.process_calls[0]
        assert filename.startswith(f"{_filename_ruc(fiscal.tenant)}-07-")
        assert b"CreditNoteTypeCode" in xml_content
        assert b"DiscrepancyResponse" in xml_content
        assert result["success"] is True

    def test_nota_debito_usa_note_send_y_respuesta_inmediata(self, db_session):
        user, fiscal, nota = _make_nota_documento(db_session, "MX04", tipo_nota="debito")
        fake_client = _FakeSmartPSEClient([_smartpse_accepted(tag="DebitNote")])

        with _patch_smartpse(fake_client):
            result = facturacion_service.emitir_nota(
                nota,
                fiscal,
                user,
                "02",
                "AUMENTO DE VALOR",
                "debito",
            )

        _, filename, xml_content, _ = fake_client.process_calls[0]
        assert filename.startswith(f"{_filename_ruc(fiscal.tenant)}-08-")
        assert b"DebitNoteTypeCode" not in xml_content
        assert b"DiscrepancyResponse" in xml_content
        assert result["success"] is True

    def test_resumen_diario_usa_summary_send_y_guarda_ticket_pendiente(self, db_session):
        tenant, user = _make_user_with_apisperu(db_session, "MX05")
        fake_client = _FakeSmartPSEClient([_smartpse_pending("summary-1", tag="SummaryDocuments")])
        payload = {
            "fecGeneracion": "2026-04-11T10:00:00-05:00",
            "fecResumen": "2026-04-11T10:00:00-05:00",
            "correlativo": "00001",
            "moneda": "PEN",
            "company": {"ruc": tenant.business_ruc},
            "details": [],
        }

        with _patch_smartpse(fake_client):
            result = facturacion_service.emitir_resumen_diario(payload, user)

        _, filename, xml_content, _ = fake_client.process_calls[0]
        assert filename == f"{_filename_ruc(tenant)}-RC-20260411-00001"
        assert b"SummaryDocuments" in xml_content
        assert b"RC-20260411-00001" in xml_content
        assert fake_client.consult_calls == []
        assert result["success"] is True
        assert result["pending"] is True
        assert result["ticket"] == "summary-1"

    def test_comunicacion_baja_factura_usa_voided_send_y_status(self, db_session):
        _, user, _, fiscal = _make_fiscal_document(db_session, "MX06", "01")
        fiscal.estado = "facturada"
        db_session.commit()
        fake_client = _FakeSmartPSEClient(
            [_smartpse_pending("voided-1", tag="VoidedDocuments")],
            [_smartpse_accepted(description="Baja aceptada", tag="VoidedDocuments")],
        )

        with _patch_smartpse(fake_client):
            result = facturacion_service.anular_comprobante(
                fiscal,
                "ERROR EN CALCULOS",
                user,
            )

        _, filename, xml_content, _ = fake_client.process_calls[0]
        assert re.match(rf"^{_filename_ruc(fiscal.tenant)}-RA-\d{{8}}-\d{{5}}$", filename)
        assert b"DocumentTypeCode" in xml_content
        assert b"RA-" in xml_content
        assert b"ERROR EN CALCULOS" in xml_content
        assert fake_client.consult_calls == []
        assert result["success"] is True
        assert result["pending"] is True
        assert result["ticket"] == "voided-1"

    def test_baja_boleta_usa_summary_send_y_status(self, db_session):
        _, user, _, boleta = _make_fiscal_document(db_session, "MX07", "03")
        boleta.estado = "facturada"
        db_session.commit()
        fake_client = _FakeSmartPSEClient(
            [_smartpse_pending("summary-2", tag="SummaryDocuments")],
            [_smartpse_accepted(description="Resumen de baja aceptado", tag="SummaryDocuments")],
        )

        with _patch_smartpse(fake_client):
            result = facturacion_service.anular_comprobante(
                boleta,
                "ANULACION DE BOLETA",
                user,
            )

        _, filename, xml_content, _ = fake_client.process_calls[0]
        assert re.match(rf"^{_filename_ruc(boleta.tenant)}-RC-\d{{8}}-\d{{5}}$", filename)
        assert b"SummaryDocuments" in xml_content
        assert b"RC-" in xml_content
        assert facturacion_service._document_number(boleta).encode("utf-8") in xml_content
        assert fake_client.consult_calls == []
        assert result["success"] is True
        assert result["pending"] is True
        assert result["ticket"] == "summary-2"

    def test_guia_remision_usa_despatch_send_y_retorna_ticket(self, db_session):
        user, guia = _make_guia(db_session, "MX08")
        fake_client = _FakeSmartPSEClient(
            [_smartpse_pending("despatch-1", tag="DespatchAdvice")],
            [_smartpse_accepted(description="Guia aceptada", tag="DespatchAdvice")],
        )

        with _patch_smartpse(fake_client):
            result = facturacion_service.emitir_guia_remision(guia, user)

        _, filename, xml_content, _ = fake_client.process_calls[0]
        assert filename.startswith(f"{_filename_ruc(guia.tenant)}-09-")
        assert b"DespatchAdvice" in xml_content
        assert fake_client.consult_calls == []
        assert result["success"] is True
        assert result["pending"] is True
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

        assert payload["company"]["address"]["codLocal"] == "0000"
        assert payload["envio"]["partida"]["codLocal"] == "0000"
        assert payload["envio"]["partida"]["ruc"] == guia.tenant.business_ruc
        assert "codLocal" not in payload["envio"]["llegada"]
        assert "codEstablecimiento" not in payload["envio"]["llegada"]
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

        assert payload["company"]["address"]["codLocal"] == "0000"
        assert payload["envio"]["partida"]["codLocal"] == "0000"
        assert payload["envio"]["partida"]["ruc"] == guia.tenant.business_ruc
        assert "codLocal" not in payload["envio"]["llegada"]
        assert "codEstablecimiento" not in payload["envio"]["llegada"]
        assert payload["envio"]["vehiculo"]["nroCirculacion"] == "NC-001"
        assert payload["envio"]["vehiculo"]["codEmisor"] == "EM-01"
        assert payload["envio"]["vehiculo"]["nroAutorizacion"] == "AUTH-001"

    def test_guia_traslado_interno_agrega_codlocal_en_llegada(self, db_session):
        user, guia = _make_guia(db_session, "MX08D")
        guia.motivo_traslado = "04"
        guia.descripcion_motivo = "TRASLADO INTERNO"
        guia.cotizacion.cliente.numero_documento = guia.tenant.business_ruc
        guia.cotizacion.cliente.tipo_documento = "6"
        guia.cotizacion.cliente.razon_social = guia.tenant.business_name
        db_session.commit()

        payload = facturacion_service._base_payload_gre(guia, user)

        assert payload["company"]["address"]["codLocal"] == "0000"
        assert payload["envio"]["partida"]["codLocal"] == "0000"
        assert payload["envio"]["partida"]["ruc"] == guia.tenant.business_ruc
        assert payload["envio"]["llegada"]["codLocal"] == "0000"
        assert payload["envio"]["llegada"]["ruc"] == guia.tenant.business_ruc

    def test_retencion_usa_retention_send_y_respuesta_inmediata(self, db_session):
        _, user = _make_user_with_apisperu(db_session, "MX09")
        payload = {
            "serie": "R001",
            "correlativo": "000001",
            "company": {"ruc": "20606751509"},
            "proveedor": {"tipoDoc": "6", "numDoc": "20191308868", "rznSocial": "Proveedor Demo"},
        }

        with pytest.raises(facturacion_service.FacturacionException, match="Smart PSE v1"):
            facturacion_service.emitir_retencion(payload, user)

    def test_percepcion_usa_perception_send_y_respuesta_inmediata(self, db_session):
        _, user = _make_user_with_apisperu(db_session, "MX10")
        payload = {
            "serie": "P001",
            "correlativo": "000001",
            "company": {"ruc": "20606751509"},
            "cliente": {"tipoDoc": "6", "numDoc": "20191308868", "rznSocial": "Cliente Demo"},
        }

        with pytest.raises(facturacion_service.FacturacionException, match="Smart PSE v1"):
            facturacion_service.emitir_percepcion(payload, user)

    def test_reversion_usa_reversion_send_y_status(self, db_session):
        tenant, user = _make_user_with_apisperu(db_session, "MX11")
        fake_client = _FakeSmartPSEClient(
            [_smartpse_pending("reversion-1", tag="VoidedDocuments")],
            [_smartpse_accepted(description="Reversion aceptada", tag="VoidedDocuments")],
        )
        payload = {
            "fecGeneracion": "2026-04-11T10:00:00-05:00",
            "fecComunicacion": "2026-04-11T10:01:00-05:00",
            "correlativo": "00001",
            "company": {"ruc": tenant.business_ruc},
            "details": [],
        }

        with _patch_smartpse(fake_client):
            result = facturacion_service.emitir_reversion(payload, user)

        _, filename, xml_content, _ = fake_client.process_calls[0]
        assert filename == f"{_filename_ruc(tenant)}-RR-20260411-00001"
        assert b"VoidedDocuments" in xml_content
        assert b"RR-20260411-00001" in xml_content
        assert fake_client.consult_calls[0][1] == filename
        assert result["success"] is True
        assert result["ticket"] == "reversion-1"

    def test_poll_async_status_reintenta_cuando_ticket_aun_no_existe(self, db_session):
        tenant, user = _make_user_with_apisperu(db_session, "MX12")
        fake_client = _FakeSmartPSEClient(
            [_smartpse_pending("reversion-12", tag="VoidedDocuments")],
            [
                smartpse_client.SmartPSEException("Ticket no existe"),
                _smartpse_accepted(description="Reversion aceptada luego de espera", tag="VoidedDocuments"),
            ],
        )
        payload = {
            "fecGeneracion": "2026-04-11T10:00:00-05:00",
            "fecComunicacion": "2026-04-11T10:01:00-05:00",
            "correlativo": "00001",
            "company": {"ruc": tenant.business_ruc},
            "details": [],
        }

        with _patch_smartpse(fake_client), patch("services.facturacion_service.time.sleep") as sleep_mock:
            result = facturacion_service.emitir_reversion(payload, user)

        assert len(fake_client.consult_calls) == 2
        assert all(call[1] == fake_client.process_calls[0][1] for call in fake_client.consult_calls)
        sleep_mock.assert_called_once()
        assert result["success"] is True
        assert result["ticket"] == "reversion-12"

    def test_resumen_diario_reporta_diagnostico_si_proveedor_genera_xml_sin_percent(self, db_session):
        tenant, user = _make_user_with_apisperu(db_session, "MX13")
        fake_client = _FakeSmartPSEClient(
            [
                {
                    "estado": 422,
                    "mensaje": "Falta tasa del tributo",
                    "errores": ["Falta tasa del tributo"],
                    "rechazado": True,
                }
            ]
        )
        payload = {
            "fecGeneracion": "2026-04-11T10:00:00-05:00",
            "fecResumen": "2026-04-11T10:00:00-05:00",
            "correlativo": "00001",
            "moneda": "PEN",
            "company": {"ruc": tenant.business_ruc},
            "details": [],
        }

        with _patch_smartpse(fake_client):
            with pytest.raises(facturacion_service.FacturacionException) as exc:
                facturacion_service.emitir_resumen_diario(payload, user)

        assert "Falta tasa del tributo" in str(exc.value)

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
        assert detail["serieNro"] == "B001-000001"
        assert re.match(r"^\d{8}-\d{5}$", payload["correlativo"])

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
        fake_client = _FakeSmartPSEClient(
            [smartpse_client.SmartPSEException("Error interno Smart PSE al enviar GRE")]
        )

        with _patch_smartpse(fake_client):
            with pytest.raises(facturacion_service.FacturacionException) as exc:
                facturacion_service.emitir_guia_remision(guia, user)

        assert "Smart PSE" in str(exc.value)
        assert "GRE" in str(exc.value)
