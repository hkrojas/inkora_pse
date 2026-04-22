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
    db_session.commit()
    db_session.refresh(tenant)
    return tenant, user


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

    with patch("requests.post", return_value=_mock_async_send_response("voided-pc03")) as post_mock, patch(
        "requests.get",
        return_value=_mock_async_status_response(description="Baja aceptada"),
    ):
        result = facturacion_service.anular_comprobante(
            fiscal,
            "ERROR DE PRUEBA",
            user,
        )

    sent_payload = json.loads(post_mock.call_args.kwargs["data"])
    detail = sent_payload["details"][0]

    assert post_mock.call_args.args[0] == "https://facturacion.test/api/v1/voided/send"
    assert sent_payload["company"]["ruc"] == fiscal.tenant.business_ruc
    assert detail == {
        "tipoDoc": "01",
        "serie": fiscal.serie,
        "correlativo": str(fiscal.correlativo).zfill(6),
        "desMotivoBaja": "ERROR DE PRUEBA",
    }
    assert result["success"] is True
    assert result["ticket"] == "voided-pc03"


def test_baja_boleta_payload_contract_subset_is_stable(db_session):
    _, user, _, boleta = _make_fiscal_document(db_session, "PC04", "03")
    boleta.estado = "facturada"
    db_session.commit()

    with patch("requests.post", return_value=_mock_async_send_response("summary-pc04")) as post_mock, patch(
        "requests.get",
        return_value=_mock_async_status_response(description="Resumen de baja aceptado"),
    ):
        result = facturacion_service.anular_comprobante(
            boleta,
            "ANULACION DE PRUEBA",
            user,
        )

    sent_payload = json.loads(post_mock.call_args.kwargs["data"])
    detail = sent_payload["details"][0]

    assert post_mock.call_args.args[0] == "https://facturacion.test/api/v1/summary/send"
    assert sent_payload["company"]["ruc"] == boleta.tenant.business_ruc
    assert sent_payload["moneda"] == "PEN"
    assert detail["tipoDoc"] == "03"
    assert detail["serieNro"] == f"{boleta.serie}-{boleta.correlativo}"
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
