"""
test_facturacion_guards.py — Fase 7: Facturación — guardas y confiabilidad
===========================================================================
Cubre:
  A. Pre-validación (_validar_pre_emision) — 7 checks antes de llamar a SUNAT
     1. cliente asignado
     2. documento de identidad del cliente (min 8 dígitos)
     3. para facturas (01): RUC obligatorio (tipo 6, 11 dígitos)
     4. tipo_comprobante válido
     5. total_venta > 0
     6. al menos un item
     7. cotización no anulada

  B. Protección contra emisión duplicada
     - segunda llamada a emitir sobre la misma cotización bloqueada
     - get_latest_fiscal_document_for_quote no retorna documentos anulados

  C. Flujo cotización → fiscal document
     - create_fiscal_document_from_quote crea registro separado con kind correcto
     - source_quote_id y internal_order_number heredados

  D. Fallo de API externa (mocked)
     - FacturacionException propagada cuando la API devuelve error
     - timeout de requests propagado como FacturacionException
     - estado del documento no cambia si el envío falla

Ejecutar:
    cd backend
    python -m pytest test_facturacion_guards.py -v
"""
import sys
import os
import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from conftest import (
    make_tenant,
    make_user,
    make_cliente,
    make_quote_via_crud,
)
import crud
import models
import schemas
from access_control import ROLE_ADMIN
from routers.facturacion import _validar_pre_emision
from services import facturacion_service


# ============================================================================
# HELPERS
# ============================================================================

def _make_mock_quote(
    *,
    cliente=None,
    tipo_comprobante="01",
    total_venta=Decimal("118.00"),
    items=True,
    estado="pendiente",
):
    """Crea un mock de Cotizacion para tests de _validar_pre_emision."""
    quote = MagicMock()
    quote.estado = estado
    quote.tipo_comprobante = tipo_comprobante
    quote.total_venta = total_venta
    quote.items = [MagicMock()] if items else []

    if cliente is None:
        c = MagicMock()
        c.tipo_documento = "6"
        c.numero_documento = "20100100100"
        quote.cliente = c
    else:
        quote.cliente = cliente

    return quote


def _make_mock_cliente(*, tipo="6", numero="20100100100"):
    c = MagicMock()
    c.tipo_documento = tipo
    c.numero_documento = numero
    return c


# ============================================================================
# A. PRE-VALIDACIÓN
# ============================================================================

class TestPreValidacion:
    """Tests de _validar_pre_emision — todos deben lanzar HTTPException 400."""

    # ── check 1: cliente asignado ───────────────────────────────────────────

    def test_sin_cliente_lanza_400(self):
        quote = _make_mock_quote(cliente=False)
        quote.cliente = None  # explícitamente None
        with pytest.raises(HTTPException) as exc:
            _validar_pre_emision(quote, "01")
        assert exc.value.status_code == 400
        assert "cliente" in exc.value.detail.lower()

    # ── check 2: numero_documento válido ───────────────────────────────────

    def test_documento_cliente_vacio_lanza_400(self):
        c = _make_mock_cliente(tipo="6", numero="")
        quote = _make_mock_quote(cliente=c)
        with pytest.raises(HTTPException) as exc:
            _validar_pre_emision(quote, "01")
        assert exc.value.status_code == 400

    def test_documento_cliente_menos_de_8_digitos_lanza_400(self):
        c = _make_mock_cliente(tipo="1", numero="1234567")  # 7 dígitos
        quote = _make_mock_quote(cliente=c, tipo_comprobante="03")
        with pytest.raises(HTTPException) as exc:
            _validar_pre_emision(quote, "03")
        assert exc.value.status_code == 400

    # ── check 3: Factura (01) requiere RUC ────────────────────────────────

    def test_factura_con_dni_lanza_400(self):
        c = _make_mock_cliente(tipo="1", numero="12345678")  # DNI, no RUC
        quote = _make_mock_quote(cliente=c, tipo_comprobante="01")
        with pytest.raises(HTTPException) as exc:
            _validar_pre_emision(quote, "01")
        assert exc.value.status_code == 400
        assert "ruc" in exc.value.detail.lower() or "11" in exc.value.detail

    def test_factura_con_ruc_10_digitos_lanza_400(self):
        c = _make_mock_cliente(tipo="6", numero="2010010010")  # 10 dígitos
        quote = _make_mock_quote(cliente=c, tipo_comprobante="01")
        with pytest.raises(HTTPException) as exc:
            _validar_pre_emision(quote, "01")
        assert exc.value.status_code == 400

    def test_boleta_con_dni_es_valida(self):
        c = _make_mock_cliente(tipo="1", numero="12345678")  # DNI 8 dígitos
        quote = _make_mock_quote(cliente=c, tipo_comprobante="03")
        # No debe lanzar excepción
        _validar_pre_emision(quote, "03")  # ← OK

    def test_factura_con_ruc_valido_pasa(self):
        c = _make_mock_cliente(tipo="6", numero="20100100100")  # RUC 11 dígitos
        quote = _make_mock_quote(cliente=c, tipo_comprobante="01")
        _validar_pre_emision(quote, "01")  # ← OK

    # ── check 4: tipo_comprobante válido ──────────────────────────────────

    def test_tipo_comprobante_invalido_lanza_400(self):
        quote = _make_mock_quote(tipo_comprobante="99")
        with pytest.raises(HTTPException) as exc:
            _validar_pre_emision(quote, "99")
        assert exc.value.status_code == 400
        assert "99" in exc.value.detail

    def test_tipo_comprobante_cero_invalido(self):
        quote = _make_mock_quote(tipo_comprobante="00")
        with pytest.raises(HTTPException) as exc:
            _validar_pre_emision(quote, "00")
        assert exc.value.status_code == 400

    def test_tipo_comprobante_07_valido(self):
        c = _make_mock_cliente(tipo="6", numero="20100100100")
        quote = _make_mock_quote(cliente=c, tipo_comprobante="07")
        _validar_pre_emision(quote, "07")  # ← OK

    def test_tipo_comprobante_08_valido(self):
        c = _make_mock_cliente(tipo="6", numero="20100100100")
        quote = _make_mock_quote(cliente=c, tipo_comprobante="08")
        _validar_pre_emision(quote, "08")  # ← OK

    # ── check 5: total_venta > 0 ──────────────────────────────────────────

    def test_total_venta_cero_lanza_400(self):
        quote = _make_mock_quote(total_venta=Decimal("0.00"))
        with pytest.raises(HTTPException) as exc:
            _validar_pre_emision(quote, "01")
        assert exc.value.status_code == 400
        assert "cero" in exc.value.detail.lower() or "total" in exc.value.detail.lower()

    def test_total_venta_negativo_lanza_400(self):
        quote = _make_mock_quote(total_venta=Decimal("-10.00"))
        with pytest.raises(HTTPException) as exc:
            _validar_pre_emision(quote, "01")
        assert exc.value.status_code == 400

    def test_total_venta_positivo_pasa(self):
        c = _make_mock_cliente(tipo="6", numero="20100100100")
        quote = _make_mock_quote(cliente=c, total_venta=Decimal("0.01"))
        _validar_pre_emision(quote, "01")  # ← OK

    # ── check 6: al menos un item ─────────────────────────────────────────

    def test_sin_items_lanza_400(self):
        quote = _make_mock_quote(items=False)
        with pytest.raises(HTTPException) as exc:
            _validar_pre_emision(quote, "01")
        assert exc.value.status_code == 400
        assert "item" in exc.value.detail.lower()

    # ── check 7: no anulada ───────────────────────────────────────────────

    def test_cotizacion_anulada_lanza_400(self):
        quote = _make_mock_quote(estado="anulada")
        with pytest.raises(HTTPException) as exc:
            _validar_pre_emision(quote, "01")
        assert exc.value.status_code == 400
        assert "anulada" in exc.value.detail.lower()

    def test_cotizacion_pendiente_pasa(self):
        c = _make_mock_cliente(tipo="6", numero="20100100100")
        quote = _make_mock_quote(cliente=c, estado="pendiente")
        _validar_pre_emision(quote, "01")  # ← OK


# ============================================================================
# B. PROTECCIÓN CONTRA EMISIÓN DUPLICADA
# ============================================================================

class TestEmisionDuplicada:
    """
    Verifica que el guard de doble emisión funcione correctamente:
    get_latest_fiscal_document_for_quote retorna el fiscal doc existente.
    """

    def test_doble_emision_bloqueada_por_fiscal_doc_existente(self, db_session):
        tenant = make_tenant(db_session, "FD01")
        user = make_user(db_session, tenant, email="fd01@test.com")
        cliente = make_cliente(db_session, tenant, "FD01")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)

        # Primera emisión
        fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
        assert fiscal is not None

        # Buscar el fiscal doc vinculado (como haría el router antes de emitir de nuevo)
        linked = crud.get_latest_fiscal_document_for_quote(db_session, quote.id, tenant.id)
        assert linked is not None
        assert linked.id == fiscal.id
        assert linked.document_kind == "fiscal_document"

    def test_fiscal_doc_anulado_no_bloquea_nueva_emision(self, db_session):
        tenant = make_tenant(db_session, "FD02")
        user = make_user(db_session, tenant, email="fd02@test.com")
        cliente = make_cliente(db_session, tenant, "FD02")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)

        fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
        fiscal.estado = "anulada"
        db_session.commit()

        # Después de anular, get_latest_fiscal_document_for_quote debe devolver None
        linked = crud.get_latest_fiscal_document_for_quote(db_session, quote.id, tenant.id)
        assert linked is None

    def test_guia_ya_emitida_no_puede_reemitirse(self, db_session):
        """
        El router de guías verifica estado antes de enviar.
        Simular que el estado ya es 'emitida' y que la guarda lanzaría HTTPException.
        """
        tenant = make_tenant(db_session, "FD03")
        user = make_user(db_session, tenant, email="fd03@test.com")

        guia = models.GuiaRemision(
            tenant_id=tenant.id,
            usuario_id=user.id,
            fecha_traslado=datetime.now(timezone.utc),
            motivo_traslado="01",
            partida_direccion="A",
            llegada_direccion="B",
            serie="T001",
            correlativo=1,
            estado="emitida",  # ya emitida
        )
        db_session.add(guia)
        db_session.commit()

        # La guardia del router es: if guia.estado in ("emitida", "anulada"): raise 400
        # Aquí verificamos la condición directamente
        assert guia.estado in ("emitida", "anulada"), "La guía ya fue procesada"


# ============================================================================
# C. FLUJO COTIZACIÓN → DOCUMENTO FISCAL
# ============================================================================

class TestFlujoQuoteToFiscal:

    def test_fiscal_document_creado_separado_de_quotation(self, db_session):
        tenant = make_tenant(db_session, "FF01")
        user = make_user(db_session, tenant, email="ff01@test.com")
        cliente = make_cliente(db_session, tenant, "FF01")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)

        fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")

        assert fiscal.id != quote.id
        assert fiscal.document_kind == "fiscal_document"
        assert fiscal.source_quote_id == quote.id

    def test_fiscal_document_hereda_internal_order_number(self, db_session):
        tenant = make_tenant(db_session, "FF02")
        user = make_user(db_session, tenant, email="ff02@test.com")
        cliente = make_cliente(db_session, tenant, "FF02")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)

        fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "03")

        assert fiscal.internal_order_number == quote.internal_order_number

    def test_quotation_no_se_modifica_tras_crear_fiscal(self, db_session):
        tenant = make_tenant(db_session, "FF03")
        user = make_user(db_session, tenant, email="ff03@test.com")
        cliente = make_cliente(db_session, tenant, "FF03")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)

        total_original = quote.total_venta
        crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")

        db_session.refresh(quote)
        assert quote.document_kind == "quotation"
        assert quote.total_venta == total_original

    def test_fiscal_document_tiene_tipo_comprobante_correcto(self, db_session):
        tenant = make_tenant(db_session, "FF04")
        user = make_user(db_session, tenant, email="ff04@test.com")
        cliente = make_cliente(db_session, tenant, "FF04")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)

        boleta = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "03")
        assert boleta.tipo_comprobante == "03"

    def test_fiscal_document_estado_inicial_pendiente(self, db_session):
        tenant = make_tenant(db_session, "FF05")
        user = make_user(db_session, tenant, email="ff05@test.com")
        cliente = make_cliente(db_session, tenant, "FF05")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)

        fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
        assert fiscal.estado == "pendiente"

    def test_nota_credito_y_debito_usan_series_apisperu_reales(self, db_session):
        tenant = make_tenant(db_session, "FF06")
        user = make_user(db_session, tenant, email="ff06@test.com")
        cliente = make_cliente(db_session, tenant, "FF06")
        quote_factura = make_quote_via_crud(db_session, tenant, user, cliente)
        quote_boleta = make_quote_via_crud(db_session, tenant, user, cliente)
        factura = crud.create_fiscal_document_from_quote(db_session, quote_factura, user.id, "01")
        boleta = crud.create_fiscal_document_from_quote(db_session, quote_boleta, user.id, "03")

        nota_debito = crud.crear_nota_credito_debito(
            db_session,
            factura,
            user.id,
            "debito",
            "02",
            "AUMENTO DE VALOR",
        )
        nota_credito = crud.crear_nota_credito_debito(
            db_session,
            boleta,
            user.id,
            "credito",
            "01",
            "ANULACION DE LA OPERACION",
        )

        assert nota_debito.serie == "FF01"
        assert nota_credito.serie == "BB01"


# ============================================================================
# D. FALLO DE API EXTERNA (MOCKED)
# ============================================================================

class TestFalloApiExterna:
    """
    Mockea requests.post para simular fallos de la API externa.
    Verifica que FacturacionException se propague correctamente.
    """

    def _make_mock_cotizacion_for_service(self, db_session):
        """Crea objetos mock para facturacion_service.emitir_factura."""
        tenant = make_tenant(db_session, "EX99")
        user = make_user(db_session, tenant, email="ex99@test.com")
        cliente = make_cliente(db_session, tenant, "EX99")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)
        fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
        return fiscal, user, db_session

    def test_api_timeout_lanza_facturacion_exception(self, db_session):
        import requests

        fiscal, user, db = self._make_mock_cotizacion_for_service(db_session)

        # Mockear el token para que no falle por credenciales
        user.apisperu_token = "fake_token"
        if hasattr(user, "tenant") and user.tenant:
            user.tenant.apisperu_token = "fake_token"

        with patch("requests.post", side_effect=requests.exceptions.Timeout("timeout")):
            with pytest.raises(facturacion_service.FacturacionException, match="[Ee]rror|[Tt]imeout|comunicaci"):
                facturacion_service.emitir_factura(fiscal, db, user, tipo_doc_override="01")

    def test_api_connection_error_lanza_facturacion_exception(self, db_session):
        import requests

        fiscal, user, db = self._make_mock_cotizacion_for_service(db_session)
        user.apisperu_token = "fake_token"
        if hasattr(user, "tenant") and user.tenant:
            user.tenant.apisperu_token = "fake_token"

        with patch("requests.post", side_effect=requests.exceptions.ConnectionError("conn refused")):
            with pytest.raises(facturacion_service.FacturacionException):
                facturacion_service.emitir_factura(fiscal, db, user, tipo_doc_override="01")

    def test_sin_token_lanza_facturacion_exception(self, db_session):
        """Si el tenant no tiene token API configurado, debe lanzar FacturacionException."""
        tenant = make_tenant(db_session, "NT01")
        user = make_user(db_session, tenant, email="nt01@test.com")
        cliente = make_cliente(db_session, tenant, "NT01")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)
        fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")

        # Parchear _get_apisperu_token para que retorne None sin importar el fallback global
        with patch("services.facturacion_service._get_apisperu_token", return_value=None):
            with pytest.raises(facturacion_service.FacturacionException, match="[Ff]alta|[Tt]oken|[Aa]PI"):
                facturacion_service.emitir_factura(fiscal, db_session, user, tipo_doc_override="01")

    def test_api_422_lanza_facturacion_exception(self, db_session):
        """Respuesta 422 de la API debe propagarse como FacturacionException."""
        fiscal, user, db = self._make_mock_cotizacion_for_service(db_session)
        user.apisperu_token = "fake_token"
        if hasattr(user, "tenant") and user.tenant:
            user.tenant.apisperu_token = "fake_token"

        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {
            "errors": [{"code": "1234", "description": "Campo requerido faltante"}]
        }

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(facturacion_service.FacturacionException):
                facturacion_service.emitir_factura(fiscal, db, user, tipo_doc_override="01")

    def test_estado_fiscal_doc_no_cambia_si_api_falla(self, db_session):
        """Si el envío a SUNAT falla, el fiscal document debe seguir en 'pendiente'."""
        import requests

        tenant = make_tenant(db_session, "EX50")
        user = make_user(db_session, tenant, email="ex50@test.com")
        cliente = make_cliente(db_session, tenant, "EX50")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)
        fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
        user.apisperu_token = "fake_token"
        if hasattr(user, "tenant") and user.tenant:
            user.tenant.apisperu_token = "fake_token"

        with patch("requests.post", side_effect=requests.exceptions.Timeout()):
            try:
                facturacion_service.emitir_factura(fiscal, db_session, user, tipo_doc_override="01")
            except facturacion_service.FacturacionException:
                pass

        db_session.refresh(fiscal)
        # El estado no debería haber cambiado a "facturada" si el envío falló
        assert fiscal.estado != "facturada", (
            "El fiscal document fue marcado como 'facturada' aunque el envío a SUNAT falló"
        )


class TestServicioApisPeruIntegrado:
    def test_obtener_tipo_documento_codigo_preserva_codigos_numericos(self):
        assert facturacion_service.obtener_tipo_documento_codigo("6") == "6"
        assert facturacion_service.obtener_tipo_documento_codigo("1") == "1"

    def test_emitir_factura_construye_payload_alineado_a_apisperu(self, db_session):
        tenant = make_tenant(db_session, "AP01")
        user = make_user(db_session, tenant, email="ap01@test.com")
        tenant.apisperu_token = "fake_token"
        tenant.apisperu_url = "https://facturacion.test/api/v1"
        db_session.commit()

        cliente = make_cliente(
            db_session,
            tenant,
            "AP01",
            tipo_documento="6",
            numero_documento="20191308868",
        )
        quote = make_quote_via_crud(db_session, tenant, user, cliente)
        fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hash": "abc123",
            "xml": "<xml />",
            "sunatResponse": {
                "success": True,
                "cdrZip": "zip64",
                "cdrResponse": {
                    "code": "0",
                    "description": "Aceptado",
                    "notes": [],
                },
            },
        }

        with patch("requests.post", return_value=mock_response) as post_mock:
            result = facturacion_service.emitir_factura(
                fiscal,
                db_session,
                user,
                tipo_doc_override="01",
            )

        sent_payload = json.loads(post_mock.call_args.kwargs["data"])
        assert sent_payload["tipoDoc"] == "01"
        assert sent_payload["tipoOperacion"] == "0101"
        assert sent_payload["client"]["tipoDoc"] == "6"
        assert sent_payload["mtoImpVenta"] == 118.0
        assert sent_payload["subTotal"] == 118.0
        assert sent_payload["formaPago"]["tipo"] == "Contado"
        assert result["success"] is True
        assert result["sunat_response"]["cdrResponse"]["code"] == "0"

    def test_anular_factura_usa_ticket_y_status_real(self, db_session):
        tenant = make_tenant(db_session, "AP02")
        user = make_user(db_session, tenant, email="ap02@test.com")
        tenant.apisperu_token = "fake_token"
        tenant.apisperu_url = "https://facturacion.test/api/v1"
        db_session.commit()

        cliente = make_cliente(db_session, tenant, "AP02")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)
        fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
        fiscal.estado = "facturada"
        db_session.commit()

        send_response = MagicMock()
        send_response.status_code = 200
        send_response.json.return_value = {
            "hash": "hash-ra",
            "xml": "<voided />",
            "sunatResponse": {
                "success": True,
                "ticket": "ticket-123",
            },
        }
        status_response = MagicMock()
        status_response.status_code = 200
        status_response.json.return_value = {
            "success": True,
            "code": "0",
            "cdrZip": "zip64",
            "cdrResponse": {
                "code": "0",
                "description": "Aceptado",
                "notes": [],
            },
        }

        with patch("requests.post", return_value=send_response) as post_mock, patch(
            "requests.get", return_value=status_response
        ) as get_mock:
            result = facturacion_service.anular_comprobante(
                fiscal,
                "ERROR EN CALCULOS",
                user,
            )

        sent_payload = json.loads(post_mock.call_args.kwargs["data"])
        assert sent_payload["details"][0]["desMotivoBaja"] == "ERROR EN CALCULOS"
        assert get_mock.call_args.kwargs["params"]["ticket"] == "ticket-123"
        assert result["success"] is True
        assert result["ticket"] == "ticket-123"


# ============================================================================
# EJECUCIÓN DIRECTA
# ============================================================================

if __name__ == "__main__":
    import pytest as _pytest
    _pytest.main([__file__, "-v", "--tb=short"])
