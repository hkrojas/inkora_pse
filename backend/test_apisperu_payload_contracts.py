"""
test_apisperu_payload_contracts.py
=================================

Pruebas de contrato "golden subset" para payloads antes de salir a ApisPeru.

Objetivo:
  - detectar cambios accidentales en la forma del payload fiscal
  - validar invariantes de factura, nota, baja y guias
  - proteger el contrato sin tocar la logica sensible de emision

Ejecutar:
    cd backend
    python -m pytest test_apisperu_payload_contracts.py -v
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import crud
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from services import facturacion_service


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


def _make_user_with_apisperu(db_session, suffix: str):
    tenant = make_tenant(db_session, suffix)
    user = make_user(db_session, tenant, email=f"{suffix.lower()}@test.com")
    tenant.apisperu_token = "fake_token"
    tenant.apisperu_url = "https://facturacion.test/api/v1"
    tenant.smartpse_company_id = "77"
    tenant.smartpse_environment = "demo"
    tenant.smartpse_usuario_secundaria = "AB3KPQR9"
    tenant.smartpse_token_acceso = "MX7TNVQG"
    db_session.commit()
    db_session.refresh(tenant)
    return tenant, user


def _smartpse_pending(ticket: str, *, tag: str = "VoidedDocuments"):
    return {
        "estado": 202,
        "mensaje": "Pendiente",
        "ticket": ticket,
        "xml_firmado": f"<{tag} />",
        "codigo_hash": "hash-ticket",
    }


def _smartpse_accepted(*, description: str = "Aceptado", tag: str = "VoidedDocuments"):
    return {
        "estado": 200,
        "mensaje": description,
        "xml_firmado": f"<{tag} />",
        "codigo_hash": "hash-ticket",
        "cdr": "<ApplicationResponse/>",
        "rechazado": False,
    }


class _FakeSmartPSEClient:
    def __init__(self, process_responses, consult_responses):
        self.process_responses = list(process_responses)
        self.consult_responses = list(consult_responses)
        self.process_calls = []
        self.consult_calls = []

    def process_xml(self, tenant, nombre_archivo, xml_content, *, demo=False):
        self.process_calls.append((tenant, nombre_archivo, xml_content, demo))
        return self.process_responses.pop(0)

    def consult_ticket(self, tenant, nombre_archivo):
        self.consult_calls.append((tenant, nombre_archivo))
        return self.consult_responses.pop(0)


def _patch_smartpse(fake_client):
    return patch("services.facturacion_service.smartpse_client.get_default_client", return_value=fake_client)


def _filename_ruc(tenant) -> str:
    return "".join(ch for ch in str(tenant.business_ruc) if ch.isdigit())


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


def test_factura_download_payload_contract_subset_is_stable(db_session):
    tenant, user, _, fiscal = _make_fiscal_document(db_session, "PC01", "01")

    payload = facturacion_service._build_download_payload(fiscal, user)

    assert payload["ublVersion"] == "2.1"
    assert payload["tipoDoc"] == "01"
    assert payload["serie"] == fiscal.serie
    assert payload["correlativo"] == str(fiscal.correlativo).zfill(6)
    assert payload["tipoMoneda"] == "PEN"
    assert payload["tipoOperacion"] == "0101"
    assert payload["company"]["ruc"] == tenant.business_ruc
    assert payload["client"]["tipoDoc"] == "6"
    assert payload["client"]["numDoc"] == "20191308868"
    assert payload["formaPago"] == {"moneda": "PEN", "tipo": "Contado"}
    assert "cuotas" not in payload
    assert payload["details"][0]["unidad"] == "NIU"
    assert payload["details"][0]["cantidad"] == Decimal("1.00")
    assert payload["details"][0]["mtoValorUnitario"] == Decimal("100.00")
    assert payload["details"][0]["mtoPrecioUnitario"] == Decimal("118.00")
    assert payload["details"][0]["tipAfeIgv"] == "10"
    assert payload["legends"][0]["code"] == "1000"
    assert "tipDocAfectado" not in payload


def test_factura_download_payload_exonerado_no_envia_igv(db_session):
    _, user, _, fiscal = _make_fiscal_document(db_session, "PC01B", "01")
    item = fiscal.items[0]
    item.precio_unitario = Decimal("100.00")
    item.tipo_afectacion_igv = "20"
    db_session.commit()

    payload = facturacion_service._build_download_payload(fiscal, user)

    assert payload["mtoOperGravadas"] == Decimal("0.00")
    assert payload["mtoOperExoneradas"] == Decimal("100.00")
    assert payload["mtoOperInafectas"] == Decimal("0.00")
    assert payload["mtoIGV"] == Decimal("0.00")
    assert payload["valorVenta"] == Decimal("100.00")
    assert payload["mtoImporteTotal"] == Decimal("100.00")
    assert payload["details"][0]["tipAfeIgv"] == "20"
    assert payload["details"][0]["porcentajeIgv"] == 0
    assert payload["details"][0]["igv"] == Decimal("0.00")


def test_factura_download_payload_usa_sku_real_en_cod_producto(db_session):
    _, user, _, fiscal = _make_fiscal_document(db_session, "PC01C", "01")
    fiscal.items[0].codigo_producto = "IMP-A4-FC"
    db_session.commit()

    payload = facturacion_service._build_download_payload(fiscal, user)

    assert payload["details"][0]["codProducto"] == "IMP-A4-FC"


def test_factura_download_payload_usa_fecha_emision_persistida(db_session):
    _, user, _, fiscal = _make_fiscal_document(db_session, "PC01D", "01")
    fiscal.fecha_emision = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    db_session.commit()

    payload = facturacion_service._build_download_payload(fiscal, user)

    assert payload["fechaEmision"].startswith("2026-05-01")


def test_nota_download_payload_contract_subset_is_stable(db_session):
    user, fiscal, nota = _make_nota_documento(db_session, "PC02", tipo_nota="credito")

    payload = facturacion_service._build_download_payload(nota, user)

    assert payload["ublVersion"] == "2.1"
    assert payload["tipoDoc"] == "07"
    assert payload["serie"] == "FF01"
    assert payload["correlativo"] == str(nota.correlativo).zfill(6)
    assert payload["company"]["ruc"] == fiscal.tenant.business_ruc
    assert payload["client"]["tipoDoc"] == "6"
    assert payload["tipDocAfectado"] == "01"
    assert payload["numDocfectado"] == facturacion_service._document_number(fiscal)
    assert payload["codMotivo"] == "01"
    assert payload["desMotivo"] == "Documento de prueba"
    assert payload["details"][0]["cantidad"] == Decimal("1.00")
    assert payload["details"][0]["mtoPrecioUnitario"] == Decimal("118.00")
    assert "formaPago" not in payload


def test_anular_factura_payload_contract_subset_is_stable(db_session):
    _, user, _, fiscal = _make_fiscal_document(db_session, "PC03", "01")
    fiscal.estado = "facturada"
    db_session.commit()
    fake_client = _FakeSmartPSEClient(
        [_smartpse_pending("voided-pc03")],
        [_smartpse_accepted(description="Baja aceptada")],
    )

    with _patch_smartpse(fake_client):
        result = facturacion_service.anular_comprobante(
            fiscal,
            "ERROR DE PRUEBA",
            user,
        )

    _, filename, xml_content, _ = fake_client.process_calls[0]
    xml_text = xml_content.decode("utf-8")

    assert re.match(rf"^{_filename_ruc(fiscal.tenant)}-RA-\d{{8}}-\d{{5}}$", filename)
    assert "RA-" in xml_text
    assert "DocumentTypeCode" in xml_text
    assert fiscal.serie in xml_text
    assert str(fiscal.correlativo).zfill(6) in xml_text
    assert "ERROR DE PRUEBA" in xml_text
    assert result["success"] is True
    assert result["ticket"] == "voided-pc03"


def test_baja_boleta_payload_contract_subset_is_stable(db_session):
    _, user, _, boleta = _make_fiscal_document(db_session, "PC04", "03")
    boleta.estado = "facturada"
    db_session.commit()
    fake_client = _FakeSmartPSEClient(
        [_smartpse_pending("summary-pc04", tag="SummaryDocuments")],
        [_smartpse_accepted(description="Resumen de baja aceptado", tag="SummaryDocuments")],
    )

    with _patch_smartpse(fake_client):
        result = facturacion_service.anular_comprobante(
            boleta,
            "ANULACION DE PRUEBA",
            user,
        )

    summary_payload = facturacion_service._build_summary_payload(boleta, "ANULACION DE PRUEBA", user)
    detail = summary_payload["details"][0]

    _, filename, xml_content, _ = fake_client.process_calls[0]
    assert re.match(rf"^{_filename_ruc(boleta.tenant)}-RC-\d{{8}}-\d{{5}}$", filename)
    assert b"SummaryDocuments" in xml_content
    assert b"RC-" in xml_content
    assert summary_payload["company"]["ruc"] == boleta.tenant.business_ruc
    assert summary_payload["moneda"] == "PEN"
    assert detail["tipoDoc"] == "03"
    assert detail["serieNro"] == facturacion_service._document_number(boleta)
    assert detail["estado"] == "3"
    assert detail["desMotivoBaja"] == "ANULACION DE PRUEBA"
    assert result["success"] is True
    assert result["ticket"] == "summary-pc04"


def test_guia_payload_contract_subset_is_stable(db_session):
    user, guia = _make_guia(db_session, "PC05")

    payload = facturacion_service._base_payload_gre(guia, user)

    assert payload["version"] == 2022
    assert payload["tipoDoc"] == "09"
    assert payload["serie"] == guia.serie
    assert payload["correlativo"] == str(guia.correlativo).zfill(6)
    assert payload["company"]["ruc"] == guia.tenant.business_ruc
    assert payload["company"]["address"]["codLocal"] == "0000"
    assert payload["destinatario"]["tipoDoc"] == "6"
    assert payload["destinatario"]["numDoc"] == "20191308868"
    assert payload["envio"]["codTraslado"] == "01"
    assert payload["envio"]["modTraslado"] == "02"
    assert payload["envio"]["pesoTotal"] == Decimal("5.00")
    assert payload["envio"]["numBultos"] == 1
    assert payload["envio"]["partida"]["codLocal"] == "0000"
    assert payload["envio"]["partida"]["ruc"] == guia.tenant.business_ruc
    assert payload["envio"]["llegada"]["ruc"] == "20191308868"
    assert "codLocal" not in payload["envio"]["llegada"]
    assert payload["envio"]["vehiculo"]["placa"] == "ABC123"
    assert payload["envio"]["choferes"][0]["nroDoc"] == "72758912"
    assert payload["envio"]["choferes"][0]["licencia"] == "Q12345678"
    assert "transportista" not in payload["envio"]
    assert payload["details"][0]["codigo"] == "PK-001"
    assert payload["details"][0]["cantidad"] == Decimal("2.00")
