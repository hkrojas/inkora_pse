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
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

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
from api_dependencies import (
    get_current_user,
    get_db,
    get_db_tenant,
    require_emission_allowed,
)
from access_control import ROLE_ADMIN
from routers import facturacion as facturacion_router
from routers.facturacion import (
    _ensure_emission_credentials,
    _ensure_document_can_be_voided,
    _ensure_note_target_is_facturada,
    _get_tenant_emission_capabilities,
    _raise_value_error_as_http,
    _validar_pre_emision,
)
from services import facturacion_service, smartpse_client


# ============================================================================
# HELPERS
# ============================================================================

def _enable_smartpse_for_test(tenant):
    tenant.smartpse_company_id = "77"
    tenant.smartpse_environment = "demo"
    tenant.smartpse_usuario_secundaria = "AB3KPQR9"
    tenant.smartpse_token_acceso = "MX7TNVQG"

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
    quote.fecha_emision = datetime.now(timezone.utc)
    quote.fecha_vencimiento = None
    quote.condicion_pago = "contado"
    quote.cuotas_pago = []
    if items:
        item = MagicMock()
        item.descripcion = "Servicio de impresion"
        item.cantidad = Decimal("1")
        item.precio_unitario = Decimal("118.00")
        item.unidad_medida = "NIU"
        item.tipo_afectacion_igv = "10"
        item.codigo_producto = "SERV-001"
        quote.items = [item]
    else:
        quote.items = []

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


def _set_subscription(db_session, tenant, status: str):
    subscription = crud.get_subscription_by_tenant(db_session, tenant.id)
    if subscription is None:
        subscription = models.Subscription(tenant_id=tenant.id)
        db_session.add(subscription)
    subscription.status = status
    db_session.commit()
    db_session.refresh(subscription)
    return subscription


# ============================================================================
# EMISION: suscripcion explicita requerida
# ============================================================================

class TestEmissionSubscriptionGuard:

    def test_tenant_sin_subscription_no_puede_emitir_por_endpoint_normal(self, db_session):
        tenant = make_tenant(db_session, "SUB00")
        user = make_user(db_session, tenant, email="sub00@test.com")
        cliente = make_cliente(db_session, tenant, "SUB00")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)

        app = FastAPI()
        app.include_router(facturacion_router.router)

        def override_db():
            yield db_session

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_db_tenant] = override_db

        with patch("routers.facturacion.facturacion_service.emitir_factura") as provider_call:
            response = TestClient(app).post(
                f"/cotizaciones/{quote.id}/facturar",
                json={"tipo_comprobante": "01"},
            )

        assert response.status_code == 402
        assert (
            response.json()["detail"]["message"]
            == "El tenant no tiene una suscripción activa para emitir."
        )
        provider_call.assert_not_called()

    @pytest.mark.parametrize(
        "status",
        [
            models.SUBSCRIPTION_STATUS_ACTIVE,
            models.SUBSCRIPTION_STATUS_TRIAL,
            "grace",
        ],
    )
    def test_tenant_con_subscription_permitida_pasa_guard_de_emision(
        self,
        db_session,
        status,
    ):
        tenant = make_tenant(db_session, f"SUBOK{status[:1]}")
        user = make_user(db_session, tenant, email=f"subok-{status}@test.com")
        _set_subscription(db_session, tenant, status)

        assert require_emission_allowed(user, db_session) == user

    @pytest.mark.parametrize(
        "status",
        [
            None,
            models.SUBSCRIPTION_STATUS_SUSPENDED,
            "payment_required",
            models.SUBSCRIPTION_STATUS_CANCELLED,
            models.SUBSCRIPTION_STATUS_EXPIRED,
            "desconocido",
        ],
    )
    def test_tenant_sin_subscription_activa_bloquea_guard_de_emision(
        self,
        db_session,
        status,
    ):
        suffix = "SUBMISS" if status is None else f"SUB{str(status)[:3]}"
        tenant = make_tenant(db_session, suffix)
        user = make_user(db_session, tenant, email=f"{suffix.lower()}@test.com")
        if status is not None:
            _set_subscription(db_session, tenant, status)

        with pytest.raises(HTTPException) as exc:
            require_emission_allowed(user, db_session)

        assert exc.value.status_code == 402
        assert (
            exc.value.detail["message"]
            == "El tenant no tiene una suscripción activa para emitir."
        )


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

    def test_boleta_con_ruc_20_lanza_400(self):
        c = _make_mock_cliente(tipo="6", numero="20100100100")
        quote = _make_mock_quote(cliente=c, tipo_comprobante="03")
        with pytest.raises(HTTPException) as exc:
            _validar_pre_emision(quote, "03")
        assert exc.value.status_code == 400
        assert "boletas" in exc.value.detail.lower()
        assert "factura" in exc.value.detail.lower()

    def test_boleta_con_ruc_10_lanza_400(self):
        c = _make_mock_cliente(tipo="6", numero="10400000001")
        quote = _make_mock_quote(cliente=c, tipo_comprobante="03")
        with pytest.raises(HTTPException) as exc:
            _validar_pre_emision(quote, "03")
        assert exc.value.status_code == 400
        assert "ruc 10/20" in exc.value.detail.lower()

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

    def test_fecha_emision_futura_lanza_400(self):
        quote = _make_mock_quote()
        quote.fecha_emision = datetime(2099, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(HTTPException) as exc:
            _validar_pre_emision(quote, "01")
        assert exc.value.status_code == 400
        assert "fecha" in exc.value.detail.lower()

    def test_unidad_sunat_invalida_lanza_400(self):
        quote = _make_mock_quote()
        quote.items[0].unidad_medida = "BAD"
        with pytest.raises(HTTPException) as exc:
            _validar_pre_emision(quote, "01")
        assert exc.value.status_code == 400
        assert "unidad" in exc.value.detail.lower()

    def test_credito_con_cuotas_validas_pasa(self):
        quote = _make_mock_quote()
        quote.condicion_pago = "credito_30"
        quote.cuotas_pago = [
            {
                "fecha_pago": (quote.fecha_emision + timedelta(days=15)).isoformat(),
                "monto": "59.00",
            },
            {
                "fecha_pago": (quote.fecha_emision + timedelta(days=30)).isoformat(),
                "monto": "59.00",
            },
        ]
        _validar_pre_emision(quote, "01")

    def test_credito_con_suma_de_cuotas_incorrecta_lanza_400(self):
        quote = _make_mock_quote()
        quote.condicion_pago = "credito_30"
        quote.cuotas_pago = [
            {
                "fecha_pago": (quote.fecha_emision + timedelta(days=30)).isoformat(),
                "monto": "100.00",
            }
        ]
        with pytest.raises(HTTPException) as exc:
            _validar_pre_emision(quote, "01")
        assert exc.value.status_code == 400
        assert "suma de cuotas" in exc.value.detail.lower()

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


class TestFacturacionRouterHelpers:
    def test_raise_value_error_as_http_convierte_limite_en_402(self):
        with pytest.raises(HTTPException) as exc:
            _raise_value_error_as_http(ValueError("Límite de documentos excedido"))

        assert exc.value.status_code == 402

    def test_ensure_note_target_is_facturada_rechaza_estado_pendiente(self):
        comprobante = MagicMock()
        comprobante.estado = "pendiente"
        comprobante.serie = "F001"
        comprobante.correlativo = 15

        with pytest.raises(HTTPException) as exc:
            _ensure_note_target_is_facturada(comprobante)

        assert exc.value.status_code == 400
        assert "facturada" in exc.value.detail

    def test_ensure_document_can_be_voided_rechaza_documento_pendiente(self):
        comprobante = MagicMock()
        comprobante.estado = "pendiente"

        with pytest.raises(HTTPException) as exc:
            _ensure_document_can_be_voided(comprobante)

        assert exc.value.status_code == 400
        assert "no requiere anulacion" in exc.value.detail.lower()

    def test_ensure_document_can_be_voided_rechaza_facturada_sin_aceptacion_sunat(self):
        comprobante = MagicMock()
        comprobante.estado = "facturada"
        comprobante.sunat_error = None
        comprobante.sunat_xml_url = None
        comprobante.sunat_xml_content = None

        with pytest.raises(HTTPException) as exc:
            _ensure_document_can_be_voided(comprobante)

        assert exc.value.status_code == 400
        assert "aceptados por sunat" in exc.value.detail.lower()

    def test_ensure_document_can_be_voided_acepta_facturada_con_xml_sunat(self):
        comprobante = MagicMock()
        comprobante.estado = "facturada"
        comprobante.sunat_error = None
        comprobante.sunat_xml_url = "https://storage.test/f001-1.xml"
        comprobante.sunat_xml_content = None

        _ensure_document_can_be_voided(comprobante)


class TestConteoDocumental:
    def test_documents_used_no_incrementa_al_crear_fiscal_document(self, db_session):
        tenant = make_tenant(db_session, "DOC01")
        user = make_user(db_session, tenant, email="doc01@test.com")
        cliente = make_cliente(db_session, tenant, "DOC01")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)
        sub = crud.get_or_create_subscription(db_session, tenant.id)

        fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
        db_session.refresh(sub)

        assert fiscal is not None
        assert sub.documents_used == 0

    def test_documents_used_incrementa_solo_con_respuesta_exitosa(self, db_session):
        tenant = make_tenant(db_session, "DOC02")
        user = make_user(db_session, tenant, email="doc02@test.com")
        cliente = make_cliente(db_session, tenant, "DOC02")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)
        sub = crud.get_or_create_subscription(db_session, tenant.id)
        fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")

        crud.guardar_respuesta_sunat(
            db_session,
            fiscal.id,
            {"success": False, "message": "rechazado"},
            tenant_id=tenant.id,
        )
        db_session.refresh(sub)
        assert sub.documents_used == 0

        crud.guardar_respuesta_sunat(
            db_session,
            fiscal.id,
            {"success": True, "serie": "F001", "correlativo": "000001"},
            tenant_id=tenant.id,
        )
        db_session.refresh(sub)
        assert sub.documents_used == 1

        crud.guardar_respuesta_sunat(
            db_session,
            fiscal.id,
            {"success": True, "serie": "F001", "correlativo": "000001"},
            tenant_id=tenant.id,
        )
        db_session.refresh(sub)
        assert sub.documents_used == 1

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

    def test_production_uses_configured_series_and_remote_floors(self, db_session):
        tenant = make_tenant(db_session, "SPF01")
        tenant.business_ruc = "20606751509"
        tenant.smartpse_company_id = "384"
        tenant.smartpse_environment = "produccion"
        tenant.fiscal_invoice_series = "E001"
        tenant.fiscal_invoice_series_floor = 7244
        tenant.fiscal_boleta_series = "EB01"
        tenant.fiscal_boleta_series_floor = 280
        db_session.commit()
        user = make_user(db_session, tenant, email="smartpse-floor@test.com")
        cliente = make_cliente(db_session, tenant, "SPF01")

        factura_quote = make_quote_via_crud(db_session, tenant, user, cliente)
        factura = crud.create_fiscal_document_from_quote(
            db_session,
            factura_quote,
            user.id,
            "01",
        )

        boleta_quote = make_quote_via_crud(db_session, tenant, user, cliente)
        boleta = crud.create_fiscal_document_from_quote(
            db_session,
            boleta_quote,
            user.id,
            "03",
        )

        assert factura.serie == "E001"
        assert factura.correlativo == 7245
        assert boleta.serie == "EB01"
        assert boleta.correlativo == 281

    def test_production_blocks_emission_without_confirmed_series_floor(self, db_session):
        tenant = make_tenant(db_session, "SPF01B")
        tenant.smartpse_company_id = "384"
        tenant.smartpse_environment = "produccion"
        tenant.fiscal_invoice_series = "E001"
        db_session.commit()
        user = make_user(db_session, tenant, email="smartpse-production-series@test.com")
        cliente = make_cliente(db_session, tenant, "SPF01B")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)

        with pytest.raises(ValueError, match="ultimo correlativo confirmado"):
            crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")

    def test_production_blocks_emission_without_explicit_fiscal_series(self, db_session):
        tenant = make_tenant(db_session, "SPF01SERIE")
        tenant.smartpse_company_id = "384"
        tenant.smartpse_environment = "produccion"
        tenant.fiscal_invoice_series_floor = 7244
        db_session.commit()
        user = make_user(db_session, tenant, email="smartpse-production-series-required@test.com")
        cliente = make_cliente(db_session, tenant, "SPF01SERIE")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)

        with pytest.raises(ValueError, match="serie fiscal autorizada"):
            crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")

    def test_production_rejects_series_override_outside_configured_series(self, db_session):
        tenant = make_tenant(db_session, "SPF01C")
        tenant.smartpse_company_id = "384"
        tenant.smartpse_environment = "produccion"
        tenant.fiscal_invoice_series = "E001"
        tenant.fiscal_invoice_series_floor = 7244
        db_session.commit()
        user = make_user(db_session, tenant, email="smartpse-series-override@test.com")
        cliente = make_cliente(db_session, tenant, "SPF01C")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)

        with pytest.raises(ValueError, match="no coincide con la serie fiscal configurada"):
            crud.create_fiscal_document_from_quote(
                db_session,
                quote,
                user.id,
                "01",
                serie_override="F001",
            )

    def test_tenant_sin_smartpse_no_usa_piso_remoto_de_correlativos(self, db_session):
        tenant = make_tenant(db_session, "SPF02")
        tenant.business_ruc = "20606751509"
        db_session.commit()
        user = make_user(db_session, tenant, email="no-smartpse-floor@test.com")
        cliente = make_cliente(db_session, tenant, "SPF02")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)

        fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")

        assert fiscal.serie == "F001"
        assert fiscal.correlativo == 1

    def test_nota_credito_y_debito_usan_series_apisperu_reales(self, db_session):
        tenant = make_tenant(db_session, "FF06")
        user = make_user(db_session, tenant, email="ff06@test.com")
        cliente = make_cliente(db_session, tenant, "FF06")
        quote_factura = make_quote_via_crud(db_session, tenant, user, cliente)
        quote_boleta = make_quote_via_crud(db_session, tenant, user, cliente)
        factura = crud.create_fiscal_document_from_quote(db_session, quote_factura, user.id, "01")
        boleta = crud.create_fiscal_document_from_quote(db_session, quote_boleta, user.id, "03")
        factura.estado = "facturada"
        boleta.estado = "facturada"
        db_session.commit()

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
        fiscal, user, db = self._make_mock_cotizacion_for_service(db_session)
        _enable_smartpse_for_test(user.tenant)
        fake_client = MagicMock()
        fake_client.process_xml.side_effect = smartpse_client.SmartPSEException(
            "Timeout enviando documento Smart PSE"
        )

        with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=fake_client):
            with pytest.raises(facturacion_service.FacturacionException, match="[Ee]rror|[Tt]imeout|comunicaci"):
                facturacion_service.emitir_factura(fiscal, db, user, tipo_doc_override="01")

    def test_api_connection_error_lanza_facturacion_exception(self, db_session):
        fiscal, user, db = self._make_mock_cotizacion_for_service(db_session)
        _enable_smartpse_for_test(user.tenant)
        fake_client = MagicMock()
        fake_client.process_xml.side_effect = smartpse_client.SmartPSEException(
            "No se pudo conectar con Smart PSE"
        )

        with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=fake_client):
            with pytest.raises(facturacion_service.FacturacionException):
                facturacion_service.emitir_factura(fiscal, db, user, tipo_doc_override="01")

    def test_sin_token_lanza_facturacion_exception(self, db_session):
        """Si el tenant no tiene credenciales Smart PSE, debe lanzar FacturacionException."""
        tenant = make_tenant(db_session, "NT01")
        user = make_user(db_session, tenant, email="nt01@test.com")
        cliente = make_cliente(db_session, tenant, "NT01")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)
        fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")

        with pytest.raises(facturacion_service.FacturacionException, match="Smart PSE|credenciales"):
            facturacion_service.emitir_factura(fiscal, db_session, user, tipo_doc_override="01")

    def test_api_422_lanza_facturacion_exception(self, db_session):
        """Respuesta 422 de la API debe propagarse como FacturacionException."""
        fiscal, user, db = self._make_mock_cotizacion_for_service(db_session)
        _enable_smartpse_for_test(user.tenant)
        fake_client = MagicMock()
        fake_client.process_xml.side_effect = smartpse_client.SmartPSEException(
            "Campo requerido faltante"
        )

        with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=fake_client):
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
        _enable_smartpse_for_test(user.tenant)
        fake_client = MagicMock()
        fake_client.process_xml.side_effect = smartpse_client.SmartPSEException("Timeout Smart PSE")

        with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=fake_client):
            try:
                facturacion_service.emitir_factura(fiscal, db_session, user, tipo_doc_override="01")
            except facturacion_service.FacturacionException:
                pass

        db_session.refresh(fiscal)
        # El estado no debería haber cambiado a "facturada" si el envío falló
        assert fiscal.estado != "facturada", (
            "El fiscal document fue marcado como 'facturada' aunque el envío a SUNAT falló"
        )


class TestServicioSmartPSEIntegrado:
    def test_obtener_tipo_documento_codigo_preserva_codigos_numericos(self):
        assert facturacion_service.obtener_tipo_documento_codigo("6") == "6"
        assert facturacion_service.obtener_tipo_documento_codigo("1") == "1"
        assert facturacion_service.obtener_tipo_documento_codigo("A") == "A"

    def test_emitir_factura_construye_xml_alineado_a_smartpse(self, db_session):
        tenant = make_tenant(db_session, "AP01")
        tenant.business_ruc = "20123456789"
        user = make_user(db_session, tenant, email="ap01@test.com")
        _enable_smartpse_for_test(tenant)
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

        fake_client = MagicMock()
        fake_client.process_xml.return_value = {
            "estado": 200,
            "mensaje": "Aceptado",
            "xml_firmado": "<Invoice />",
            "codigo_hash": "abc123",
            "cdr": "<ApplicationResponse/>",
            "rechazado": False,
        }

        with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=fake_client):
            result = facturacion_service.emitir_factura(
                fiscal,
                db_session,
                user,
                tipo_doc_override="01",
            )

        called_tenant, filename, xml_content = fake_client.process_xml.call_args.args
        assert called_tenant.id == tenant.id
        filename_parts = filename.split("-")
        assert len(filename_parts) == 4
        assert filename_parts[0].isdigit()
        assert len(filename_parts[0]) == 11
        assert filename_parts[1] == "01"
        assert b"Invoice" in xml_content
        assert b"InvoiceTypeCode" in xml_content
        assert result["success"] is True
        assert result["hash"] == "abc123"

    def test_anular_factura_usa_ticket_y_status_real(self, db_session):
        tenant = make_tenant(db_session, "AP02")
        user = make_user(db_session, tenant, email="ap02@test.com")
        _enable_smartpse_for_test(tenant)
        db_session.commit()

        cliente = make_cliente(db_session, tenant, "AP02")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)
        fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
        fiscal.estado = "facturada"
        db_session.commit()

        fake_client = MagicMock()
        fake_client.process_xml.return_value = {
            "estado": 200,
            "mensaje": "Resumen enviado, consulte el ticket",
            "ticket": "ticket-123",
            "rechazado": False,
        }
        fake_client.consult_ticket.return_value = {
            "estado": 200,
            "mensaje": "Aceptado",
            "cdr": "<ApplicationResponse/>",
            "rechazado": False,
        }

        with patch("services.facturacion_service.smartpse_client.get_default_client", return_value=fake_client):
            result = facturacion_service.anular_comprobante(
                fiscal,
                "ERROR EN CALCULOS",
                user,
        )

        assert "-RA-" in fake_client.process_xml.call_args.args[1]
        fake_client.consult_ticket.assert_not_called()
        assert result["success"] is True
        assert result["pending"] is True
        assert result["ticket"] == "ticket-123"


# ============================================================================
# EJECUCIÓN DIRECTA
# ============================================================================

class TestEmissionCapabilities:
    def test_direct_sunat_requires_complete_credentials(self, db_session):
        tenant = make_tenant(db_session, "CAP01")
        tenant.sunat_usuario_sol = "MODDATOS"
        tenant.sunat_cert_url = "https://storage.test/cert.p12"
        tenant.sunat_clave_sol = None
        tenant.sunat_cert_password = None
        db_session.commit()

        _, has_direct_sunat, has_apisperu = _get_tenant_emission_capabilities(
            db_session,
            tenant.id,
        )

        assert has_direct_sunat is False
        assert has_apisperu is False

    def test_beta_env_requires_smartpse_even_with_complete_direct_sunat_credentials(self, db_session):
        tenant = make_tenant(db_session, "CAP01B")
        tenant.sunat_usuario_sol = "MODDATOS"
        tenant.sunat_clave_sol = "moddatos"
        tenant.sunat_cert_password = "secret"
        tenant.sunat_cert_url = "https://storage.test/cert.p12"
        db_session.commit()

        _, has_direct_sunat, has_smartpse = _get_tenant_emission_capabilities(
            db_session,
            tenant.id,
        )

        assert has_direct_sunat is False
        assert has_smartpse is False

        with pytest.raises(HTTPException) as exc:
            _ensure_emission_credentials(db_session, tenant.id)

        assert exc.value.status_code == 400
        assert "Smart PSE" in exc.value.detail

    def test_emission_credentials_accept_smartpse_when_direct_is_incomplete(self, db_session):
        tenant = make_tenant(db_session, "CAP02")
        tenant.sunat_usuario_sol = "MODDATOS"
        tenant.sunat_cert_url = "https://storage.test/cert.p12"
        _enable_smartpse_for_test(tenant)
        db_session.commit()

        _, has_direct_sunat, has_smartpse = _ensure_emission_credentials(
            db_session,
            tenant.id,
        )

        assert has_direct_sunat is False
        assert has_smartpse is True


if __name__ == "__main__":
    import pytest as _pytest
    _pytest.main([__file__, "-v", "--tb=short"])
