"""
==========================================================
TEST SUITE: Validación Fiscal UBL 2.1 para SUNAT
==========================================================
Archivo: test_facturacion_fiscal.py
Cubre: Precisión numérica, Detracciones SPOT, y Anticipos.

Ejecutar con:
    cd backend
    python -m pytest test_facturacion_fiscal.py -v
==========================================================
"""
import sys
import os
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

# Asegurar que el directorio backend esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import crud
import models
import schemas
from conftest import make_cliente, make_tenant, make_user, make_quote_via_crud
from fastapi import BackgroundTasks, HTTPException, Request
from routers import facturacion
from services import calculations
from services import emission_queue_service
from services import facturacion_service
from services.document_flow_service import (
    DOCUMENT_KIND_CREDIT_NOTE,
    DOCUMENT_KIND_DEBIT_NOTE,
    DOCUMENT_STATUS_ISSUED,
)
from services.fiscal_balance_service import (
    get_credit_note_available_amount,
    get_fiscal_document_balance,
)


def _test_request(path: str = "/facturacion/notas/emitir") -> Request:
    return Request({
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": [],
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
        "scheme": "http",
    })


# ==========================================
# HELPERS: Fábricas de objetos Mock
# ==========================================

def _mock_item(descripcion: str, cantidad, precio_unitario):
    """Crea un mock de CotizacionItem con los campos necesarios."""
    item = MagicMock()
    item.descripcion = descripcion
    item.cantidad = Decimal(str(cantidad))
    item.precio_unitario = Decimal(str(precio_unitario))
    item.producto_id = 1
    item.valor_unitario = calculations.redondear_extendido(
        Decimal(str(precio_unitario)) / calculations.FACTOR_IGV
    )
    item.total_base_igv = calculations.redondear(
        item.valor_unitario * item.cantidad
    )
    item.total_item = calculations.redondear(item.cantidad * item.precio_unitario)
    item.total_igv = calculations.redondear(item.total_item - item.total_base_igv)
    item.unidad_medida = "NIU"
    item.tipo_afectacion_igv = "10"
    return item


def _mock_cliente(tipo_documento="6", numero_documento="20123456789",
                  razon_social="Imprenta Test SAC"):
    """Crea un mock de Cliente."""
    cliente = MagicMock()
    cliente.tipo_documento = tipo_documento
    cliente.numero_documento = numero_documento
    cliente.razon_social = razon_social
    cliente.direccion = "Av. Test 123"
    return cliente


def _mock_user(ruc="20100100100", nombre="Empresa Emisora SAC"):
    """Crea un mock de User (Emisor)."""
    tenant = MagicMock()
    tenant.business_ruc = ruc
    tenant.business_name = nombre
    tenant.business_address = "Jr. Emisor 456"
    tenant.apisperu_token = "test_token_123"
    tenant.apisperu_url = "https://facturacion.test/api/v1"
    tenant.bank_accounts = [
        {"banco": "Banco de la Nacion", "moneda": "Soles", "cuenta": "00-123-456789"}
    ]

    user = MagicMock()
    user.tenant = tenant
    return user


def _mock_cotizacion(items, moneda="PEN", tipo_comprobante="01",
                     anticipos_deducidos=None, porcentaje_detraccion=None,
                     cuenta_banco_nacion=None):
    """Crea un mock de Cotizacion con todos los campos requeridos."""
    cotizacion = MagicMock()
    cotizacion.id = 1
    cotizacion.serie = "F001"
    cotizacion.correlativo = 1
    cotizacion.moneda = moneda
    cotizacion.tipo_comprobante = tipo_comprobante
    cotizacion.estado = "pendiente"
    cotizacion.items = items
    cotizacion.cliente = _mock_cliente()
    cotizacion.anticipos_deducidos = anticipos_deducidos
    cotizacion.total_anticipos = Decimal("0.00")
    cotizacion.porcentaje_detraccion = porcentaje_detraccion
    cotizacion.sujeta_detraccion = False
    cotizacion.monto_detraccion = None
    cotizacion.cuenta_banco_nacion = cuenta_banco_nacion
    
    # Calcular totales desde items
    total_gravada = sum(i.total_base_igv for i in items)
    total_igv = sum(i.total_igv for i in items)
    total_venta = sum(i.total_item for i in items)
    cotizacion.total_gravada = calculations.redondear(total_gravada)
    cotizacion.total_igv = calculations.redondear(total_igv)
    cotizacion.total_venta = calculations.redondear(total_venta)
    
    return cotizacion


def _make_accepted_fiscal_document(db_session, tenant, user, cliente, *, precio="500.00"):
    quote = make_quote_via_crud(
        db_session,
        tenant,
        user,
        cliente,
        precio=precio,
    )
    fiscal = crud.create_fiscal_document_from_quote(
        db_session,
        quote,
        user.id,
        "01",
    )
    fiscal.estado = DOCUMENT_STATUS_ISSUED
    db_session.commit()
    db_session.refresh(fiscal)
    return quote, fiscal


def _partial_note_items(*, total="118.00", afectacion="10"):
    return [
        schemas.CotizacionItemCreate(
            descripcion="Ajuste parcial",
            cantidad=Decimal("1"),
            precio_unitario=Decimal(total),
            tipo_afectacion_igv=afectacion,
        )
    ]


def _create_note(
    db_session,
    fiscal,
    user,
    *,
    tipo_nota="credito",
    items=None,
    estado=None,
):
    note = crud.crear_nota_credito_debito(
        db_session,
        fiscal,
        user.id,
        tipo_nota,
        "01",
        "Ajuste de prueba",
        items=items,
    )
    if estado is not None:
        note.estado = estado
        db_session.commit()
        db_session.refresh(note)
    return note


async def _noop_async(*args, **kwargs):
    return None


def _provider_success_response():
    return {
        "success": True,
        "serie": "NC01",
        "correlativo": "000001",
        "provider_endpoint": "/invoice/send",
        "provider_status_code": 200,
        "sunat_response": {"success": True, "cdrResponse": {"description": "Aceptado"}},
    }


def _set_active_subscription(db_session, tenant):
    subscription = crud.get_subscription_by_tenant(db_session, tenant.id)
    if subscription is None:
        subscription = models.Subscription(tenant_id=tenant.id)
        db_session.add(subscription)
    subscription.status = models.SUBSCRIPTION_STATUS_ACTIVE
    db_session.commit()
    db_session.refresh(subscription)
    return subscription


def _enable_apisperu_for_worker(db_session, tenant):
    tenant.smartpse_company_id = "77"
    tenant.smartpse_environment = "demo"
    tenant.smartpse_usuario_secundaria = "AB3KPQR9"
    tenant.smartpse_token_acceso = "MX7TNVQG"
    subscription = _set_active_subscription(db_session, tenant)
    subscription.beta_feature_flags = {
        "credit_notes": True,
        "debit_notes": True,
    }
    db_session.commit()


class TestNotasParcialesFiscalBalance:

    def test_nota_total_legacy_sigue_funcionando_sin_items(self, db_session):
        tenant = make_tenant(db_session, "NP01")
        user = make_user(db_session, tenant, email="np01@test.com")
        cliente = make_cliente(db_session, tenant, "NP01")
        _quote, fiscal = _make_accepted_fiscal_document(
            db_session,
            tenant,
            user,
            cliente,
            precio="118.00",
        )

        note = _create_note(db_session, fiscal, user)

        assert note.document_kind == DOCUMENT_KIND_CREDIT_NOTE
        assert note.total_gravada == fiscal.total_gravada
        assert note.total_exonerada == fiscal.total_exonerada
        assert note.total_inafecta == fiscal.total_inafecta
        assert note.total_igv == fiscal.total_igv
        assert note.total_venta == fiscal.total_venta
        assert len(note.items) == len(fiscal.items)

    def test_nota_parcial_calcula_gravada_exonerada_inafecta_igv_y_total(self, db_session):
        tenant = make_tenant(db_session, "NP02")
        user = make_user(db_session, tenant, email="np02@test.com")
        cliente = make_cliente(db_session, tenant, "NP02")
        _quote, fiscal = _make_accepted_fiscal_document(
            db_session,
            tenant,
            user,
            cliente,
            precio="500.00",
        )
        items = [
            schemas.CotizacionItemCreate(
                descripcion="Gravado",
                cantidad=Decimal("1"),
                precio_unitario=Decimal("118.00"),
                tipo_afectacion_igv="10",
            ),
            schemas.CotizacionItemCreate(
                descripcion="Exonerado",
                cantidad=Decimal("1"),
                precio_unitario=Decimal("50.00"),
                tipo_afectacion_igv="20",
            ),
            schemas.CotizacionItemCreate(
                descripcion="Inafecto",
                cantidad=Decimal("1"),
                precio_unitario=Decimal("30.00"),
                tipo_afectacion_igv="30",
            ),
        ]

        note = _create_note(db_session, fiscal, user, items=items)

        assert note.total_gravada == Decimal("100.00")
        assert note.total_exonerada == Decimal("50.00")
        assert note.total_inafecta == Decimal("30.00")
        assert note.total_igv == Decimal("18.00")
        assert note.total_venta == Decimal("198.00")
        assert len(note.items) == 3

    def test_nota_parcial_con_item_gravado_calcula_igv_correctamente(self, db_session):
        tenant = make_tenant(db_session, "NP03")
        user = make_user(db_session, tenant, email="np03@test.com")
        cliente = make_cliente(db_session, tenant, "NP03")
        _quote, fiscal = _make_accepted_fiscal_document(
            db_session,
            tenant,
            user,
            cliente,
            precio="500.00",
        )

        note = _create_note(
            db_session,
            fiscal,
            user,
            items=_partial_note_items(total="118.00", afectacion="10"),
        )

        assert note.total_gravada == Decimal("100.00")
        assert note.total_igv == Decimal("18.00")
        assert note.total_venta == Decimal("118.00")

    def test_dos_notas_credito_aceptadas_no_pueden_exceder_disponible(self, db_session):
        tenant = make_tenant(db_session, "NP04")
        user = make_user(db_session, tenant, email="np04@test.com")
        cliente = make_cliente(db_session, tenant, "NP04")
        _quote, fiscal = _make_accepted_fiscal_document(
            db_session,
            tenant,
            user,
            cliente,
            precio="300.00",
        )
        _create_note(
            db_session,
            fiscal,
            user,
            items=_partial_note_items(total="200.00", afectacion="20"),
            estado=DOCUMENT_STATUS_ISSUED,
        )

        with pytest.raises(ValueError, match="excede el monto fiscal disponible"):
            _create_note(
                db_session,
                fiscal,
                user,
                items=_partial_note_items(total="101.00", afectacion="20"),
            )

    def test_nota_credito_pendiente_o_rechazada_no_consume_disponibilidad(self, db_session):
        tenant = make_tenant(db_session, "NP05")
        user = make_user(db_session, tenant, email="np05@test.com")
        cliente = make_cliente(db_session, tenant, "NP05")
        _quote, fiscal = _make_accepted_fiscal_document(
            db_session,
            tenant,
            user,
            cliente,
            precio="300.00",
        )
        pending_note = _create_note(
            db_session,
            fiscal,
            user,
            items=_partial_note_items(total="250.00", afectacion="20"),
        )
        assert get_credit_note_available_amount(
            db_session,
            tenant.id,
            fiscal.id,
        ) == Decimal("300.00")

        pending_note.estado = "rechazada"
        db_session.commit()
        assert get_credit_note_available_amount(
            db_session,
            tenant.id,
            fiscal.id,
        ) == Decimal("300.00")

        full_note = _create_note(
            db_session,
            fiscal,
            user,
            items=_partial_note_items(total="300.00", afectacion="20"),
        )
        assert full_note.total_venta == Decimal("300.00")

    def test_nota_credito_aceptada_reduce_balance_y_debito_aceptada_aumenta_balance(self, db_session):
        tenant = make_tenant(db_session, "NP06")
        user = make_user(db_session, tenant, email="np06@test.com")
        cliente = make_cliente(db_session, tenant, "NP06")
        _quote, fiscal = _make_accepted_fiscal_document(
            db_session,
            tenant,
            user,
            cliente,
            precio="300.00",
        )
        _create_note(
            db_session,
            fiscal,
            user,
            tipo_nota="credito",
            items=_partial_note_items(total="100.00", afectacion="20"),
            estado=DOCUMENT_STATUS_ISSUED,
        )
        credit_balance = get_fiscal_document_balance(db_session, tenant.id, fiscal.id)
        assert credit_balance.credit_notes_total == Decimal("100.00")
        assert credit_balance.saldo_pendiente == Decimal("200.00")

        _create_note(
            db_session,
            fiscal,
            user,
            tipo_nota="debito",
            items=_partial_note_items(total="50.00", afectacion="20"),
            estado=DOCUMENT_STATUS_ISSUED,
        )
        debit_balance = get_fiscal_document_balance(db_session, tenant.id, fiscal.id)
        assert debit_balance.debit_notes_total == Decimal("50.00")
        assert debit_balance.saldo_pendiente == Decimal("250.00")

    def test_nota_contra_documento_otro_tenant_devuelve_404(self, db_session):
        tenant = make_tenant(db_session, "NP07")
        other_tenant = make_tenant(db_session, "NP08")
        user = make_user(db_session, tenant, email="np07@test.com")
        other_user = make_user(db_session, other_tenant, email="np08@test.com")
        cliente = make_cliente(db_session, tenant, "NP07")
        other_cliente = make_cliente(db_session, other_tenant, "NP08")
        _quote, _fiscal = _make_accepted_fiscal_document(
            db_session,
            tenant,
            user,
            cliente,
            precio="118.00",
        )
        _other_quote, other_fiscal = _make_accepted_fiscal_document(
            db_session,
            other_tenant,
            other_user,
            other_cliente,
            precio="118.00",
        )

        with pytest.raises(HTTPException) as exc:
            facturacion.emitir_nota(
                _test_request(),
                schemas.NotaCreate(
                    comprobante_afectado_id=other_fiscal.id,
                    tipo_nota="credito",
                    cod_motivo="01",
                    descripcion_motivo="Nota de otro tenant",
                ),
                BackgroundTasks(),
                db=db_session,
                current_user=user,
                _emission_check=user,
                mode="sync",
            )

        assert exc.value.status_code == 404

    def test_nota_contra_documento_no_aceptado_o_cotizacion_comercial_falla(self, db_session):
        tenant = make_tenant(db_session, "NP09")
        user = make_user(db_session, tenant, email="np09@test.com")
        cliente = make_cliente(db_session, tenant, "NP09")
        quote = make_quote_via_crud(
            db_session,
            tenant,
            user,
            cliente,
            precio="118.00",
        )
        fiscal = crud.create_fiscal_document_from_quote(
            db_session,
            quote,
            user.id,
            "01",
        )

        with pytest.raises(ValueError, match="estado 'facturada'"):
            _create_note(db_session, fiscal, user)

        with pytest.raises(ValueError, match="comprobantes fiscales"):
            _create_note(db_session, quote, user)

    def test_nota_credito_mayor_al_disponible_falla_con_error_claro(self, db_session):
        tenant = make_tenant(db_session, "NP10")
        user = make_user(db_session, tenant, email="np10@test.com")
        cliente = make_cliente(db_session, tenant, "NP10")
        _quote, fiscal = _make_accepted_fiscal_document(
            db_session,
            tenant,
            user,
            cliente,
            precio="118.00",
        )

        with pytest.raises(ValueError, match="excede el monto fiscal disponible"):
            _create_note(
                db_session,
                fiscal,
                user,
                items=_partial_note_items(total="119.00", afectacion="20"),
            )

    def test_dos_nc_pendientes_solo_una_puede_terminar_aceptada(self, db_session):
        tenant = make_tenant(db_session, "NP11")
        user = make_user(db_session, tenant, email="np11@test.com")
        cliente = make_cliente(db_session, tenant, "NP11")
        _quote, fiscal = _make_accepted_fiscal_document(
            db_session,
            tenant,
            user,
            cliente,
            precio="100.00",
        )
        first_note = _create_note(
            db_session,
            fiscal,
            user,
            items=_partial_note_items(total="100.00", afectacion="20"),
        )
        second_note = _create_note(
            db_session,
            fiscal,
            user,
            items=_partial_note_items(total="100.00", afectacion="20"),
        )

        crud.guardar_respuesta_sunat(
            db_session,
            first_note.id,
            {"success": True, "xml": "<xml/>"},
            tenant_id=tenant.id,
        )
        blocked = crud.guardar_respuesta_sunat(
            db_session,
            second_note.id,
            {"success": True, "xml": "<xml/>"},
            tenant_id=tenant.id,
        )

        db_session.refresh(first_note)
        db_session.refresh(second_note)
        assert first_note.estado == DOCUMENT_STATUS_ISSUED
        assert blocked.estado != DOCUMENT_STATUS_ISSUED
        assert second_note.estado != DOCUMENT_STATUS_ISSUED
        assert "excede el monto fiscal disponible" in second_note.sunat_error

    def test_nc_pendiente_no_llama_proveedor_si_otra_nc_aceptada_consumio_disponible(self, db_session):
        tenant = make_tenant(db_session, "NP12")
        _enable_apisperu_for_worker(db_session, tenant)
        user = make_user(db_session, tenant, email="np12@test.com")
        cliente = make_cliente(db_session, tenant, "NP12")
        _quote, fiscal = _make_accepted_fiscal_document(
            db_session,
            tenant,
            user,
            cliente,
            precio="100.00",
        )
        first_note = _create_note(
            db_session,
            fiscal,
            user,
            items=_partial_note_items(total="100.00", afectacion="20"),
        )
        second_note = _create_note(
            db_session,
            fiscal,
            user,
            items=_partial_note_items(total="100.00", afectacion="20"),
        )
        crud.guardar_respuesta_sunat(
            db_session,
            first_note.id,
            {"success": True, "xml": "<xml/>"},
            tenant_id=tenant.id,
        )
        job, _ = emission_queue_service.enqueue_note_job(
            db_session,
            second_note,
            user,
            tipo_nota="credito",
            cod_motivo="01",
            descripcion_motivo="Ajuste de prueba",
        )
        crud.claim_next_emission_job(db_session)

        with patch("services.emission_queue_service.facturacion_service.emitir_nota") as provider_call:
            processed = emission_queue_service.process_emission_job(
                job.id,
                db_session=db_session,
            )

        db_session.expire_all()
        updated_job = crud.get_emission_job(db_session, job.id)
        updated_note = crud.get_cotizacion(db_session, second_note.id, user)
        assert processed is False
        assert updated_job.status == models.EMISSION_JOB_STATUS_FAILED
        assert "excede el monto fiscal disponible" in updated_job.last_error
        assert updated_note.estado != DOCUMENT_STATUS_ISSUED
        provider_call.assert_not_called()

    def test_nc_rechazada_no_consume_disponibilidad_y_otra_puede_emitirse(self, db_session):
        tenant = make_tenant(db_session, "NP13")
        _enable_apisperu_for_worker(db_session, tenant)
        user = make_user(db_session, tenant, email="np13@test.com")
        cliente = make_cliente(db_session, tenant, "NP13")
        _quote, fiscal = _make_accepted_fiscal_document(
            db_session,
            tenant,
            user,
            cliente,
            precio="100.00",
        )
        rejected_note = _create_note(
            db_session,
            fiscal,
            user,
            items=_partial_note_items(total="100.00", afectacion="20"),
        )
        crud.guardar_respuesta_sunat(
            db_session,
            rejected_note.id,
            {"success": False, "message": "Rechazado"},
            tenant_id=tenant.id,
        )
        second_note = _create_note(
            db_session,
            fiscal,
            user,
            items=_partial_note_items(total="100.00", afectacion="20"),
        )
        job, _ = emission_queue_service.enqueue_note_job(
            db_session,
            second_note,
            user,
            tipo_nota="credito",
            cod_motivo="01",
            descripcion_motivo="Ajuste de prueba",
        )
        crud.claim_next_emission_job(db_session)

        with patch(
            "services.emission_queue_service.facturacion_service.emitir_nota",
            return_value=_provider_success_response(),
        ) as provider_call, patch(
            "services.emission_queue_service.pdf_storage_service.process_pdf_background",
            side_effect=_noop_async,
        ):
            processed = emission_queue_service.process_emission_job(
                job.id,
                db_session=db_session,
            )

        db_session.expire_all()
        updated_note = crud.get_cotizacion(db_session, second_note.id, user)
        assert processed is True
        assert updated_note.estado == DOCUMENT_STATUS_ISSUED
        provider_call.assert_called_once()

    def test_nota_debito_aceptada_aumenta_disponibilidad_para_nc(self, db_session):
        tenant = make_tenant(db_session, "NP14")
        user = make_user(db_session, tenant, email="np14@test.com")
        cliente = make_cliente(db_session, tenant, "NP14")
        _quote, fiscal = _make_accepted_fiscal_document(
            db_session,
            tenant,
            user,
            cliente,
            precio="100.00",
        )
        _create_note(
            db_session,
            fiscal,
            user,
            tipo_nota="debito",
            items=_partial_note_items(total="50.00", afectacion="20"),
            estado=DOCUMENT_STATUS_ISSUED,
        )
        credit_note = _create_note(
            db_session,
            fiscal,
            user,
            items=_partial_note_items(total="150.00", afectacion="20"),
        )

        accepted = crud.guardar_respuesta_sunat(
            db_session,
            credit_note.id,
            {"success": True, "xml": "<xml/>"},
            tenant_id=tenant.id,
        )

        assert accepted.estado == DOCUMENT_STATUS_ISSUED
        balance = get_fiscal_document_balance(db_session, tenant.id, fiscal.id)
        assert balance.debit_notes_total == Decimal("50.00")
        assert balance.credit_notes_total == Decimal("150.00")
        assert balance.saldo_pendiente == Decimal("0.00")

    def test_revalidacion_de_nc_mantiene_tenant_isolation(self, db_session):
        tenant = make_tenant(db_session, "NP15")
        other_tenant = make_tenant(db_session, "NP16")
        user = make_user(db_session, tenant, email="np15@test.com")
        other_user = make_user(db_session, other_tenant, email="np16@test.com")
        cliente = make_cliente(db_session, tenant, "NP15")
        other_cliente = make_cliente(db_session, other_tenant, "NP16")
        _quote, fiscal = _make_accepted_fiscal_document(
            db_session,
            tenant,
            user,
            cliente,
            precio="100.00",
        )
        other_note = models.Cotizacion(
            tenant_id=other_tenant.id,
            cliente_id=other_cliente.id,
            usuario_id=other_user.id,
            serie="NCX",
            correlativo=1,
            document_kind=DOCUMENT_KIND_CREDIT_NOTE,
            tipo_comprobante="07",
            estado=DOCUMENT_STATUS_ISSUED,
            nota_referencia_id=fiscal.id,
            total_gravada=Decimal("0.00"),
            total_exonerada=Decimal("100.00"),
            total_inafecta=Decimal("0.00"),
            total_igv=Decimal("0.00"),
            total_venta=Decimal("100.00"),
        )
        db_session.add(other_note)
        db_session.commit()
        own_note = _create_note(
            db_session,
            fiscal,
            user,
            items=_partial_note_items(total="100.00", afectacion="20"),
        )

        accepted = crud.guardar_respuesta_sunat(
            db_session,
            own_note.id,
            {"success": True, "xml": "<xml/>"},
            tenant_id=tenant.id,
        )

        assert accepted.estado == DOCUMENT_STATUS_ISSUED
        balance = get_fiscal_document_balance(db_session, tenant.id, fiscal.id)
        assert balance.credit_notes_total == Decimal("100.00")


# ==========================================
# TEST 1: REDONDEO EXTREMO USD + TC FRACCIONARIO
# ==========================================

class TestRedondeoExtremoBimonetario:
    """
    Escenario: Factura en USD con tipo de cambio fraccionario.
    Item: $13.33 x 3 = $39.99
    TC: S/ 3.731
    
    La regla de oro SUNAT UBL 2.1:
        Base Imponible + IGV == Total (exactamente, sin ±0.01)
    """
    
    def test_cuadre_exacto_item_usd(self):
        """Verifica que un ítem individual cuadra: base + igv == total."""
        precio_usd = Decimal("13.33")
        cantidad = Decimal("3")
        
        calc = calculations.calcular_item(cantidad, precio_usd)
        
        # Aserción fundamental: la suma de partes DEBE igualar el todo
        assert calc["total_base_igv"] + calc["total_igv"] == calc["total_item"], (
            f"¡DESCUADRE DETECTADO!\n"
            f"  Base: {calc['total_base_igv']}\n"
            f"  IGV:  {calc['total_igv']}\n"
            f"  Total: {calc['total_item']}\n"
            f"  Suma:  {calc['total_base_igv'] + calc['total_igv']}\n"
            f"  Diff:  {calc['total_item'] - (calc['total_base_igv'] + calc['total_igv'])}"
        )
    
    def test_valor_unitario_precision_extendida(self):
        """Verifica que el valor unitario usa más de 2 decimales (UBL n(12,10))."""
        precio = Decimal("13.33")
        cantidad = Decimal("1")
        
        calc = calculations.calcular_item(cantidad, precio)
        
        # El valor unitario debe tener más de 2 decimales para cumplir n(12,10)
        vu_str = str(calc["valor_unitario"])
        decimales = len(vu_str.split(".")[-1]) if "." in vu_str else 0
        assert decimales > 2, (
            f"Valor unitario {calc['valor_unitario']} tiene solo {decimales} decimales. "
            f"UBL 2.1 requiere precisión extendida (hasta 10 decimales)."
        )
    
    def test_conversion_tipo_cambio_fraccionario(self):
        """Verifica la conversión USD -> PEN con TC=3.731 sin pérdida."""
        precio_usd = Decimal("13.33")
        cantidad = Decimal("3")
        tc = Decimal("3.731")
        
        # Convertir a soles con precisión
        precio_pen = calculations.redondear(precio_usd * tc)
        
        calc = calculations.calcular_item(cantidad, precio_pen)
        
        # Aserción: cuadre exacto sin importar las fracciones del TC
        diferencia = calc["total_item"] - (calc["total_base_igv"] + calc["total_igv"])
        assert diferencia == Decimal("0"), (
            f"Descuadre de {diferencia} al convertir USD con TC={tc}.\n"
            f"  Precio PEN: {precio_pen}\n"
            f"  Base: {calc['total_base_igv']}, IGV: {calc['total_igv']}, Total: {calc['total_item']}"
        )
    
    def test_sumatoria_multiples_items_cuadra(self):
        """Verifica que la sumarización de múltiples items no acumula errores."""
        items_calc = []
        precios = [Decimal("13.33"), Decimal("27.50"), Decimal("99.99")]
        cantidades = [Decimal("3"), Decimal("7"), Decimal("1")]
        
        for precio, qty in zip(precios, cantidades):
            items_calc.append(calculations.calcular_item(qty, precio))
        
        totales = calculations.sumarizar_cotizacion(items_calc)
        
        # Regla SUNAT: Gravada + IGV == Total Venta
        assert totales["total_gravada"] + totales["total_igv"] == totales["total_venta"], (
            f"Sumarización descuadrada:\n"
            f"  Gravada: {totales['total_gravada']}\n"
            f"  IGV: {totales['total_igv']}\n"
            f"  Total: {totales['total_venta']}"
        )


# ==========================================
# TEST 2: DETRACCIÓN AUTOMÁTICA SPOT
# ==========================================

class TestDetraccionAutomaticaSPOT:
    """
    Escenario: Factura de servicio de impresión por S/ 850.00.
    Regla SUNAT: Si PEN > S/700 en Factura (01) → Detracción al 12%.
    Monto esperado: 850.00 * 0.12 = S/ 102.00
    """
    
    def test_detraccion_se_activa_sobre_umbral(self):
        """Verifica que se inyecta el nodo 'detraccion' cuando supera S/ 700."""
        items = [_mock_item("Impresión de folletos a todo color", 1, Decimal("850.00"))]
        cotizacion = _mock_cotizacion(items, moneda="PEN", tipo_comprobante="01")
        user = _mock_user()
        
        payload, _ = facturacion_service._base_payload(cotizacion, user, "01")
        payload["tipoDoc"] = "01"
        payload["legends"] = [{"code": "1000", "value": "OCHOCIENTOS CINCUENTA..."}]
        
        resultado = facturacion_service._aplicar_detraccion(payload, cotizacion, user, db=None)
        
        assert "detraccion" in resultado, "El nodo 'detraccion' no fue inyectado en el payload."
    
    def test_detraccion_porcentaje_correcto(self):
        """Verifica que el porcentaje aplicado sea 12%."""
        items = [_mock_item("Impresión offset", 1, Decimal("850.00"))]
        cotizacion = _mock_cotizacion(items, moneda="PEN", tipo_comprobante="01")
        user = _mock_user()
        
        payload, _ = facturacion_service._base_payload(cotizacion, user, "01")
        payload["legends"] = [{"code": "1000", "value": "test"}]
        resultado = facturacion_service._aplicar_detraccion(payload, cotizacion, user, db=None)
        
        detraccion = resultado["detraccion"]
        assert detraccion["percent"] == Decimal("12.00"), (
            f"Porcentaje incorrecto: {detraccion['percent']}. Esperado: 12.00%"
        )
    
    def test_detraccion_monto_exacto(self):
        """Verifica que el monto de detracción sea exactamente S/ 102.00."""
        items = [_mock_item("Servicio de impresión digital", 1, Decimal("850.00"))]
        cotizacion = _mock_cotizacion(items, moneda="PEN", tipo_comprobante="01")
        user = _mock_user()
        
        payload, _ = facturacion_service._base_payload(cotizacion, user, "01")
        payload["legends"] = [{"code": "1000", "value": "test"}]
        resultado = facturacion_service._aplicar_detraccion(payload, cotizacion, user, db=None)
        
        monto = resultado["detraccion"]["mount"]
        assert monto == Decimal("102.00"), (
            f"Monto detracción incorrecto: S/ {monto}. Esperado: S/ 102.00"
        )
    
    def test_detraccion_cuenta_banco_nacion(self):
        """Verifica que se extraiga la cuenta del Banco de la Nación del perfil."""
        items = [_mock_item("Impresión", 1, Decimal("850.00"))]
        cotizacion = _mock_cotizacion(items, moneda="PEN", tipo_comprobante="01")
        user = _mock_user()
        
        payload, _ = facturacion_service._base_payload(cotizacion, user, "01")
        payload["legends"] = [{"code": "1000", "value": "test"}]
        resultado = facturacion_service._aplicar_detraccion(payload, cotizacion, user, db=None)
        
        assert resultado["detraccion"]["ctaBanco"] == "00-123-456789", (
            f"Cuenta BN incorrecta: {resultado['detraccion']['ctaBanco']}"
        )
    
    def test_detraccion_NO_se_activa_bajo_umbral(self):
        """Verifica que NO se inyecte detracción para montos <= S/ 700."""
        items = [_mock_item("Impresión básica", 1, Decimal("650.00"))]
        cotizacion = _mock_cotizacion(items, moneda="PEN", tipo_comprobante="01")
        user = _mock_user()
        
        payload, _ = facturacion_service._base_payload(cotizacion, user, "01")
        payload["legends"] = [{"code": "1000", "value": "test"}]
        resultado = facturacion_service._aplicar_detraccion(payload, cotizacion, user, db=None)
        
        assert "detraccion" not in resultado, (
            "Se inyectó detracción para monto <= S/700. Esto es un error."
        )
    
    def test_detraccion_NO_se_activa_en_boletas(self):
        """Verifica que NO se active en Boletas (03), solo en Facturas (01)."""
        items = [_mock_item("Impresión volantes", 1, Decimal("900.00"))]
        cotizacion = _mock_cotizacion(items, moneda="PEN", tipo_comprobante="03")
        user = _mock_user()
        
        payload, _ = facturacion_service._base_payload(cotizacion, user, "03")
        payload["legends"] = [{"code": "1000", "value": "test"}]
        resultado = facturacion_service._aplicar_detraccion(payload, cotizacion, user, db=None)
        
        assert "detraccion" not in resultado, (
            "Se inyectó detracción en Boleta. Las detracciones solo aplican a Facturas."
        )
    
    def test_detraccion_persiste_en_modelo(self):
        """Verifica que los datos de detracción se marquen en el objeto cotizacion."""
        items = [_mock_item("Impresión", 1, Decimal("850.00"))]
        cotizacion = _mock_cotizacion(items, moneda="PEN", tipo_comprobante="01")
        user = _mock_user()
        
        payload, _ = facturacion_service._base_payload(cotizacion, user, "01")
        payload["legends"] = [{"code": "1000", "value": "test"}]
        facturacion_service._aplicar_detraccion(payload, cotizacion, user, db=None)
        
        assert cotizacion.sujeta_detraccion is True
        assert cotizacion.porcentaje_detraccion == Decimal("12.00")
        assert cotizacion.monto_detraccion == Decimal("102.00")


# ==========================================
# TEST 3: AMORTIZACIÓN DE ANTICIPOS (SEÑAS)
# ==========================================

class TestAmortizacionAnticipos:
    """
    Escenario: Factura final por S/ 2000.00.
    Anticipo previo: S/ 1000.00 (factura de anticipo F001-000001).
    
    Resultado esperado:
    - mtoImporteTotal ajustado: S/ 1000.00
    - Gravada e IGV proporcional descontados
    - Bloque 'anticipos' presente en el payload
    """
    
    def test_anticipos_deduce_del_total(self):
        """Verifica que el mtoImporteTotal refleje el saldo a pagar."""
        items = [_mock_item("Servicio de impresión completo", 1, Decimal("2000.00"))]
        anticipos = [
            {"serie": "F001", "correlativo": "000001", "monto": 1000.00, "tipo_doc": "02"}
        ]
        cotizacion = _mock_cotizacion(items, anticipos_deducidos=anticipos)
        user = _mock_user()
        
        payload, _ = facturacion_service._base_payload(cotizacion, user, "01")
        payload["legends"] = [{"code": "1000", "value": "test"}]
        resultado = facturacion_service._aplicar_anticipos(payload, cotizacion, user)
        
        mto_total = calculations.to_decimal(resultado["mtoImporteTotal"])
        assert mto_total == Decimal("1000.00"), (
            f"mtoImporteTotal incorrecto: S/ {mto_total}. "
            f"Esperado S/ 1000.00 (2000 - 1000 de anticipo)."
        )
    
    def test_anticipos_bloque_presente(self):
        """Verifica que el bloque 'anticipos' y 'totalAnticipos' estén en el payload."""
        items = [_mock_item("Impresión catálogos", 1, Decimal("2000.00"))]
        anticipos = [
            {"serie": "F001", "correlativo": "000001", "monto": 1000.00, "tipo_doc": "02"}
        ]
        cotizacion = _mock_cotizacion(items, anticipos_deducidos=anticipos)
        user = _mock_user()
        
        payload, _ = facturacion_service._base_payload(cotizacion, user, "01")
        payload["legends"] = [{"code": "1000", "value": "test"}]
        resultado = facturacion_service._aplicar_anticipos(payload, cotizacion, user)
        
        assert "anticipos" in resultado, "Falta el bloque 'anticipos' en el payload."
        assert "totalAnticipos" in resultado, "Falta 'totalAnticipos' en el payload."
        assert resultado["totalAnticipos"] == Decimal("1000.00")
        assert len(resultado["anticipos"]) == 1
    
    def test_anticipos_igv_no_duplicado(self):
        """Verifica que el IGV no se duplique tras descontar anticipos."""
        items = [_mock_item("Impresión total", 1, Decimal("2000.00"))]
        anticipos = [
            {"serie": "F001", "correlativo": "000001", "monto": 1000.00, "tipo_doc": "02"}
        ]
        cotizacion = _mock_cotizacion(items, anticipos_deducidos=anticipos)
        user = _mock_user()
        
        payload, _ = facturacion_service._base_payload(cotizacion, user, "01")
        payload["legends"] = [{"code": "1000", "value": "test"}]
        resultado = facturacion_service._aplicar_anticipos(payload, cotizacion, user)
        
        # Cuadre fundamental: Gravada ajustada + IGV ajustado == Total ajustado
        gravada = calculations.to_decimal(resultado["mtoOperGravadas"])
        igv = calculations.to_decimal(resultado["mtoIGV"])
        total = calculations.to_decimal(resultado["mtoImporteTotal"])
        
        assert gravada + igv == total, (
            f"¡DESCUADRE tras anticipos!\n"
            f"  Gravada ajustada: {gravada}\n"
            f"  IGV ajustado: {igv}\n"
            f"  Total ajustado: {total}\n"
            f"  Suma: {gravada + igv}"
        )
    
    def test_sin_anticipos_no_modifica_payload(self):
        """Verifica que sin anticipos el payload permanece intacto."""
        items = [_mock_item("Impresión simple", 1, Decimal("500.00"))]
        cotizacion = _mock_cotizacion(items, anticipos_deducidos=None)
        user = _mock_user()
        
        payload, _ = facturacion_service._base_payload(cotizacion, user, "01")
        total_original = payload["mtoImporteTotal"]
        
        resultado = facturacion_service._aplicar_anticipos(payload, cotizacion, user)
        
        assert resultado["mtoImporteTotal"] == total_original, (
            "El payload fue modificado a pesar de no tener anticipos."
        )
        assert "anticipos" not in resultado
    
    def test_anticipos_persiste_total_en_modelo(self):
        """Verifica que total_anticipos se persista en el modelo cotizacion."""
        items = [_mock_item("Impresión", 1, Decimal("2000.00"))]
        anticipos = [
            {"serie": "F001", "correlativo": "1", "monto": 1000.00, "tipo_doc": "02"}
        ]
        cotizacion = _mock_cotizacion(items, anticipos_deducidos=anticipos)
        user = _mock_user()
        
        payload, _ = facturacion_service._base_payload(cotizacion, user, "01")
        payload["legends"] = [{"code": "1000", "value": "test"}]
        facturacion_service._aplicar_anticipos(payload, cotizacion, user)
        
        assert cotizacion.total_anticipos == Decimal("1000.00")


# ==========================================
# EJECUCIÓN DIRECTA
# ==========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
