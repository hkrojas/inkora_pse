"""
test_payments.py — Fase 7: Pagos y cobranza
=============================================
Cubre:
  - pago parcial: saldo correcto tras primer pago
  - pago completo: saldo_pendiente == 0, payment_status == "pagado"
  - rechazo de sobrepago (excede saldo)
  - múltiples pagos hasta completar
  - no se puede pagar sobre comprobante anulado
  - no se puede pagar sobre nota de crédito
  - tenant isolation: get_pagos_cotizacion filtra correctamente
  - saldo_pendiente nunca puede ser negativo
  - payment_status: pendiente → parcial → pagado
  - payment_status vencido cuando fecha_vencimiento < hoy y no está pagado

Ejecutar:
    cd backend
    python -m pytest test_payments.py -v
"""
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from conftest import (
    make_tenant,
    make_user,
    make_cliente,
    make_cotizacion,
    make_quote_via_crud,
)
import crud
import models
import schemas
from access_control import ROLE_ADMIN


# ============================================================================
# PAGO PARCIAL
# ============================================================================

class TestPagoParcial:
    """Verifica que un pago parcial actualice saldo_pendiente correctamente."""

    def test_pago_parcial_reduce_saldo(self, db_session):
        tenant = make_tenant(db_session, "P01")
        user = make_user(db_session, tenant, email="p01@test.com")
        cliente = make_cliente(db_session, tenant, "P01")
        quote = make_quote_via_crud(db_session, tenant, user, cliente, precio="236.00")

        pago = crud.registrar_pago(
            db_session,
            quote.id,
            schemas.PagoCreate(monto_pagado=Decimal("100.00"), metodo_pago="Yape", tipo="adelanto"),
            tenant.id,
        )

        db_session.refresh(quote)
        assert pago.monto_pagado == Decimal("100.00")
        assert quote.monto_pagado == Decimal("100.00")
        assert quote.saldo_pendiente == quote.total_venta - Decimal("100.00")

    def test_payment_status_parcial_tras_primer_pago(self, db_session):
        tenant = make_tenant(db_session, "P02")
        user = make_user(db_session, tenant, email="p02@test.com")
        cliente = make_cliente(db_session, tenant, "P02")
        quote = make_quote_via_crud(db_session, tenant, user, cliente, precio="118.00")

        crud.registrar_pago(
            db_session,
            quote.id,
            schemas.PagoCreate(monto_pagado=Decimal("50.00"), metodo_pago="Efectivo", tipo="adelanto"),
            tenant.id,
        )

        db_session.refresh(quote)
        assert quote.payment_status == "parcial"

    def test_pago_parcial_crea_registro_en_tabla_pagos(self, db_session):
        tenant = make_tenant(db_session, "P03")
        user = make_user(db_session, tenant, email="p03@test.com")
        cliente = make_cliente(db_session, tenant, "P03")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)

        crud.registrar_pago(
            db_session,
            quote.id,
            schemas.PagoCreate(monto_pagado=Decimal("30.00"), metodo_pago="Transferencia", tipo="adelanto"),
            tenant.id,
        )

        pagos = crud.get_pagos_cotizacion(db_session, quote.id, tenant.id)
        assert len(pagos) == 1
        assert pagos[0].monto_pagado == Decimal("30.00")
        assert pagos[0].tenant_id == tenant.id


# ============================================================================
# PAGO COMPLETO
# ============================================================================

class TestPagoCompleto:
    """Verifica el estado pagado y balance cero tras pago total."""

    def test_pago_completo_deja_saldo_en_cero(self, db_session):
        tenant = make_tenant(db_session, "P10")
        user = make_user(db_session, tenant, email="p10@test.com")
        cliente = make_cliente(db_session, tenant, "P10")
        quote = make_quote_via_crud(db_session, tenant, user, cliente, precio="118.00")
        total = quote.total_venta

        crud.registrar_pago(
            db_session,
            quote.id,
            schemas.PagoCreate(monto_pagado=total, metodo_pago="Yape", tipo="pago"),
            tenant.id,
        )

        db_session.refresh(quote)
        assert quote.saldo_pendiente == Decimal("0.00")
        assert quote.monto_pagado == total

    def test_payment_status_pagado_tras_liquidacion_total(self, db_session):
        tenant = make_tenant(db_session, "P11")
        user = make_user(db_session, tenant, email="p11@test.com")
        cliente = make_cliente(db_session, tenant, "P11")
        quote = make_quote_via_crud(db_session, tenant, user, cliente, precio="118.00")
        total = quote.total_venta

        crud.registrar_pago(
            db_session,
            quote.id,
            schemas.PagoCreate(monto_pagado=total, metodo_pago="BCP", tipo="pago"),
            tenant.id,
        )

        db_session.refresh(quote)
        assert quote.payment_status == "pagado"

    def test_pagos_multiples_hasta_completar(self, db_session):
        tenant = make_tenant(db_session, "P12")
        user = make_user(db_session, tenant, email="p12@test.com")
        cliente = make_cliente(db_session, tenant, "P12")
        quote = make_quote_via_crud(db_session, tenant, user, cliente, precio="300.00")

        crud.registrar_pago(
            db_session, quote.id,
            schemas.PagoCreate(monto_pagado=Decimal("100.00"), metodo_pago="Yape", tipo="adelanto"),
            tenant.id,
        )
        crud.registrar_pago(
            db_session, quote.id,
            schemas.PagoCreate(monto_pagado=Decimal("100.00"), metodo_pago="Yape", tipo="adelanto"),
            tenant.id,
        )
        crud.registrar_pago(
            db_session, quote.id,
            schemas.PagoCreate(monto_pagado=Decimal("100.00"), metodo_pago="Yape", tipo="pago"),
            tenant.id,
        )

        db_session.refresh(quote)
        assert quote.saldo_pendiente == Decimal("0.00")
        assert quote.payment_status == "pagado"

        pagos = crud.get_pagos_cotizacion(db_session, quote.id, tenant.id)
        assert len(pagos) == 3


# ============================================================================
# SOBREPAGO: rechazo
# ============================================================================

class TestSobrepago:
    """Verifica que un pago que excede el saldo sea rechazado con ValueError."""

    def test_sobrepago_lanza_value_error(self, db_session):
        tenant = make_tenant(db_session, "P20")
        user = make_user(db_session, tenant, email="p20@test.com")
        cliente = make_cliente(db_session, tenant, "P20")
        quote = make_quote_via_crud(db_session, tenant, user, cliente, precio="100.00")

        with pytest.raises(ValueError, match="excede el saldo"):
            crud.registrar_pago(
                db_session,
                quote.id,
                schemas.PagoCreate(monto_pagado=Decimal("200.00"), metodo_pago="Yape", tipo="pago"),
                tenant.id,
            )

    def test_sobrepago_no_modifica_estado(self, db_session):
        tenant = make_tenant(db_session, "P21")
        user = make_user(db_session, tenant, email="p21@test.com")
        cliente = make_cliente(db_session, tenant, "P21")
        quote = make_quote_via_crud(db_session, tenant, user, cliente, precio="100.00")
        original_saldo = quote.saldo_pendiente

        try:
            crud.registrar_pago(
                db_session, quote.id,
                schemas.PagoCreate(monto_pagado=Decimal("999.00"), metodo_pago="X", tipo="pago"),
                tenant.id,
            )
        except ValueError:
            pass

        db_session.refresh(quote)
        assert quote.saldo_pendiente == original_saldo
        assert quote.monto_pagado == Decimal("0.00")

    def test_sobrepago_en_segundo_pago_rechazado(self, db_session):
        """Si se pagó S/80 de S/100, solo queda S/20. Intentar pagar S/50 debe fallar."""
        tenant = make_tenant(db_session, "P22")
        user = make_user(db_session, tenant, email="p22@test.com")
        cliente = make_cliente(db_session, tenant, "P22")
        quote = make_quote_via_crud(db_session, tenant, user, cliente, precio="100.00")

        crud.registrar_pago(
            db_session, quote.id,
            schemas.PagoCreate(monto_pagado=Decimal("80.00"), metodo_pago="Yape", tipo="adelanto"),
            tenant.id,
        )

        with pytest.raises(ValueError, match="excede el saldo"):
            crud.registrar_pago(
                db_session, quote.id,
                schemas.PagoCreate(monto_pagado=Decimal("50.00"), metodo_pago="Yape", tipo="pago"),
                tenant.id,
            )


# ============================================================================
# RESTRICCIONES DE PAGO: documentos anulados y notas
# ============================================================================

class TestPagoRestricciones:

    def test_no_pago_sobre_cotizacion_anulada(self, db_session):
        tenant = make_tenant(db_session, "P30")
        user = make_user(db_session, tenant, email="p30@test.com")
        cliente = make_cliente(db_session, tenant, "P30")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)
        # Marcar como anulada directamente
        quote.estado = "anulada"
        db_session.commit()

        # El fiscal document anulado también debe bloquear pagos
        fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")
        fiscal.estado = "anulada"
        db_session.commit()

        with pytest.raises(ValueError):
            crud.registrar_pago(
                db_session, fiscal.id,
                schemas.PagoCreate(monto_pagado=Decimal("10.00"), metodo_pago="Yape", tipo="pago"),
                tenant.id,
            )

    def test_no_pago_sobre_nota_credito(self, db_session):
        tenant = make_tenant(db_session, "P31")
        user = make_user(db_session, tenant, email="p31@test.com")
        cliente = make_cliente(db_session, tenant, "P31")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)
        fiscal = crud.create_fiscal_document_from_quote(db_session, quote, user.id, "01")

        nota = crud.crear_nota_credito_debito(
            db=db_session,
            doc_afectado=fiscal,
            usuario_id=user.id,
            tipo_nota="credito",
            cod_motivo="01",
            descripcion_motivo="Test",
        )

        with pytest.raises(ValueError, match="notas"):
            crud.registrar_pago(
                db_session, nota.id,
                schemas.PagoCreate(monto_pagado=Decimal("10.00"), metodo_pago="Yape", tipo="pago"),
                tenant.id,
            )


# ============================================================================
# TENANT ISOLATION
# ============================================================================

class TestPagosTenantIsolation:
    """Pagos deben ser visibles solo dentro del tenant correcto."""

    def test_get_pagos_filtra_por_tenant(self, db_session):
        tenant_a = make_tenant(db_session, "P40")
        tenant_b = make_tenant(db_session, "P41")
        user_a = make_user(db_session, tenant_a, email="pa@test.com")
        user_b = make_user(db_session, tenant_b, email="pb@test.com")
        cliente_a = make_cliente(db_session, tenant_a, "P40")
        cliente_b = make_cliente(db_session, tenant_b, "P41")

        quote_a = make_quote_via_crud(db_session, tenant_a, user_a, cliente_a)
        quote_b = make_quote_via_crud(db_session, tenant_b, user_b, cliente_b)

        crud.registrar_pago(
            db_session, quote_a.id,
            schemas.PagoCreate(monto_pagado=Decimal("20.00"), metodo_pago="Yape", tipo="pago"),
            tenant_a.id,
        )
        crud.registrar_pago(
            db_session, quote_b.id,
            schemas.PagoCreate(monto_pagado=Decimal("30.00"), metodo_pago="BCP", tipo="pago"),
            tenant_b.id,
        )

        pagos_a = crud.get_pagos_cotizacion(db_session, quote_a.id, tenant_a.id)
        pagos_b_wrong = crud.get_pagos_cotizacion(db_session, quote_a.id, tenant_b.id)

        assert len(pagos_a) == 1
        assert pagos_a[0].monto_pagado == Decimal("20.00")
        assert pagos_b_wrong == []

    def test_pago_no_accede_cotizacion_de_otro_tenant(self, db_session):
        tenant_a = make_tenant(db_session, "P42")
        tenant_b = make_tenant(db_session, "P43")
        user_a = make_user(db_session, tenant_a, email="pa2@test.com")
        cliente_a = make_cliente(db_session, tenant_a, "P42")
        quote_a = make_quote_via_crud(db_session, tenant_a, user_a, cliente_a)

        with pytest.raises(ValueError, match="Cotizacion no encontrada"):
            crud.registrar_pago(
                db_session, quote_a.id,
                schemas.PagoCreate(monto_pagado=Decimal("10.00"), metodo_pago="Yape", tipo="pago"),
                tenant_b.id,  # ← tenant incorrecto
            )


# ============================================================================
# PAYMENT STATUS: transiciones de estado
# ============================================================================

class TestPaymentStatus:
    """Verifica la propiedad payment_status en distintos estados."""

    def test_estado_pendiente_sin_pago(self, db_session):
        tenant = make_tenant(db_session, "PS01")
        user = make_user(db_session, tenant, email="ps01@test.com")
        cliente = make_cliente(db_session, tenant, "PS01")
        quote = make_quote_via_crud(db_session, tenant, user, cliente)

        assert quote.payment_status == "pendiente"

    def test_estado_vencido_cuando_fecha_vencimiento_paso(self, db_session):
        tenant = make_tenant(db_session, "PS02")
        user = make_user(db_session, tenant, email="ps02@test.com")
        cliente = make_cliente(db_session, tenant, "PS02")
        # fecha_vencimiento en el pasado, sin pagos
        vencimiento_pasado = datetime.utcnow() - timedelta(days=10)
        cot = make_cotizacion(
            db_session, tenant, user, cliente,
            total="118.00",
            fecha_vencimiento=vencimiento_pasado,
        )

        assert cot.payment_status == "vencido"

    def test_estado_no_vencido_si_pagado_completo(self, db_session):
        """Aunque la fecha haya vencido, si está pagado el estado es 'pagado'."""
        tenant = make_tenant(db_session, "PS03")
        user = make_user(db_session, tenant, email="ps03@test.com")
        cliente = make_cliente(db_session, tenant, "PS03")
        vencimiento_pasado = datetime.utcnow() - timedelta(days=10)
        cot = make_cotizacion(
            db_session, tenant, user, cliente,
            total="118.00",
            monto_pagado="118.00",
            fecha_vencimiento=vencimiento_pasado,
        )

        assert cot.payment_status == "pagado"

    def test_estado_pendiente_si_fecha_futura(self, db_session):
        tenant = make_tenant(db_session, "PS04")
        user = make_user(db_session, tenant, email="ps04@test.com")
        cliente = make_cliente(db_session, tenant, "PS04")
        vencimiento_futuro = datetime.utcnow() + timedelta(days=30)
        cot = make_cotizacion(
            db_session, tenant, user, cliente,
            total="118.00",
            fecha_vencimiento=vencimiento_futuro,
        )

        assert cot.payment_status == "pendiente"


# ============================================================================
# EJECUCIÓN DIRECTA
# ============================================================================

if __name__ == "__main__":
    import pytest as _pytest
    _pytest.main([__file__, "-v", "--tb=short"])
