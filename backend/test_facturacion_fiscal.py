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

import calculations
import facturacion_service


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
    user = MagicMock()
    user.business_ruc = ruc
    user.business_name = nombre
    user.business_address = "Jr. Emisor 456"
    user.apisperu_token = "test_token_123"
    user.bank_accounts = [
        {"banco": "Banco de la Nacion", "moneda": "Soles", "cuenta": "00-123-456789"}
    ]
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
