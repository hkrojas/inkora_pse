from decimal import Decimal, ROUND_HALF_UP

from fiscal_catalogs import tax_affectation_bucket

# ==========================================
# CONFIGURACIÓN MATEMÁTICA
# ==========================================

# Tasa de IGV (18%)
IGV_RATE = Decimal("0.18")
FACTOR_IGV = Decimal("1.00") + IGV_RATE # 1.18
UNIT_PRICE_PRECISION = Decimal("0.0001")
QUANTITY_PRECISION = Decimal("0.0001")
TOTAL_PRECISION = Decimal("0.01") # Precisión a 2 decimales
EXTENDED_PRECISION = Decimal("0.0000000001") # Precisión UBL 2.1 (10 decimales)

def to_decimal(val):
    """Convierte un valor a Decimal de forma segura."""
    if val is None:
        return Decimal("0.00")
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except (ValueError, TypeError):
        return Decimal("0.00")

def redondear(valor: Decimal) -> Decimal:
    """Redondeo estricto a 2 decimales (estándar SUNAT)."""
    if not isinstance(valor, Decimal):
        valor = to_decimal(valor)
    return valor.quantize(TOTAL_PRECISION, rounding=ROUND_HALF_UP)

def redondear_extendido(valor: Decimal) -> Decimal:
    """Redondeo extendido a 10 decimales para el Valor Unitario UBL 2.1 (PriceAmount)."""
    if not isinstance(valor, Decimal):
        valor = to_decimal(valor)
    return valor.quantize(EXTENDED_PRECISION, rounding=ROUND_HALF_UP)

def redondear_precio_unitario(valor: Decimal) -> Decimal:
    """Redondeo a 4 decimales para precios unitarios comerciales menores a un centimo."""
    if not isinstance(valor, Decimal):
        valor = to_decimal(valor)
    return valor.quantize(UNIT_PRICE_PRECISION, rounding=ROUND_HALF_UP)

def redondear_cantidad(valor: Decimal) -> Decimal:
    """Normaliza cantidades comerciales a cuatro decimales antes del cálculo fiscal."""
    if not isinstance(valor, Decimal):
        valor = to_decimal(valor)
    return valor.quantize(QUANTITY_PRECISION, rounding=ROUND_HALF_UP)

def calcular_item(
    cantidad: Decimal,
    precio_con_igv: Decimal,
    tipo_afectacion_igv: str = "10",
):
    """Calcula el desglose de un item segun su afectacion SUNAT."""
    qty = redondear_cantidad(cantidad)
    precio_final = redondear_precio_unitario(to_decimal(precio_con_igv))
    bucket = tax_affectation_bucket(tipo_afectacion_igv)

    if bucket != "gravada":
        valor_unitario = redondear_extendido(precio_final)
        total_base = redondear(precio_final * qty)
        return {
            "cantidad": qty,
            "precio_unitario": precio_final,
            "valor_unitario": valor_unitario,
            "total_base_igv": total_base,
            "total_igv": Decimal("0.00"),
            "total_item": total_base,
            "unidad_medida": "NIU",
            "tipo_afectacion_igv": tipo_afectacion_igv,
        }

    # 1. Valor Unitario (Base Imponible Unitaria)
    valor_unitario_preciso = precio_final / FACTOR_IGV
    # Aplicar la regla n(12,10) de UBL 2.1
    valor_unitario = redondear_extendido(valor_unitario_preciso)

    # 2. Total Base (Valor Venta)
    # Se usa la fracción nativa precisa para el total exacto de la línea antes de redondear a 2
    total_base = redondear(valor_unitario_preciso * qty)

    # 3. Total Venta (Precio Venta)
    total_item = precio_final * qty
    total_item = redondear(total_item)

    # 4. Total IGV
    total_igv = total_item - total_base
    
    return {
        "cantidad": qty,
        "precio_unitario": precio_final, # Con IGV
        "valor_unitario": valor_unitario, # Sin IGV
        "total_base_igv": total_base,
        "total_igv": total_igv,
        "total_item": total_item,
        "unidad_medida": "NIU",
        "tipo_afectacion_igv": tipo_afectacion_igv,
    }

def sumarizar_cotizacion(items_procesados: list):
    """Suma totales para la cabecera de la cotización."""
    total_gravada = Decimal("0.00")
    total_exonerada = Decimal("0.00")
    total_inafecta = Decimal("0.00")
    total_igv = Decimal("0.00")
    total_venta = Decimal("0.00")

    for item in items_procesados:
        bucket = tax_affectation_bucket(item.get("tipo_afectacion_igv", "10"))
        base = to_decimal(item["total_base_igv"])
        if bucket == "exonerada":
            total_exonerada += base
        elif bucket == "inafecta":
            total_inafecta += base
        else:
            total_gravada += base
        total_igv += to_decimal(item["total_igv"])
        total_venta += to_decimal(item["total_item"])

    return {
        "total_gravada": redondear(total_gravada),
        "total_igv": redondear(total_igv),
        "total_venta": redondear(total_venta),
        "total_exonerada": redondear(total_exonerada),
        "total_inafecta": redondear(total_inafecta),
    }

# --- FUNCIONES DE SOPORTE PARA PDF GENERATOR (V3) ---

def get_line_totals_v3(cantidad, precio_unitario_con_igv, tipo_afectacion_igv: str = "10"):
    """Función de compatibilidad para el generador de PDF."""
    calc = calcular_item(cantidad, precio_unitario_con_igv, tipo_afectacion_igv)
    return {
        'mto_valor_unitario': calc['valor_unitario'],
        'mto_precio_unitario_con_igv': calc['precio_unitario'],
        'valor_venta_linea': calc['total_base_igv'],
        'igv_linea': calc['total_igv'],
        'precio_total_linea': calc['total_item']
    }

def calculate_cotizacion_totals_v3(items):
    """Calcula totales globales de una lista de items para el PDF."""
    total_gravada = Decimal("0.00")
    total_igv = Decimal("0.00")
    monto_total = Decimal("0.00")
    line_totals = []

    for item in items:
        # Soporte para dict o objeto
        if isinstance(item, dict):
            qty = item.get('unidades', 0)
            price = item.get('precio_unitario', 0)
            tipo_afectacion = item.get('tipo_afectacion_igv', '10')
        else:
            qty = getattr(item, 'cantidad', 0)
            price = getattr(item, 'precio_unitario', 0)
            tipo_afectacion = getattr(item, 'tipo_afectacion_igv', '10')
        
        calc = get_line_totals_v3(qty, price, tipo_afectacion)
        line_totals.append(calc)
        
        if tax_affectation_bucket(tipo_afectacion) == "gravada":
            total_gravada += calc['valor_venta_linea']
        total_igv += calc['igv_linea']
        monto_total += calc['precio_total_linea']

    return {
        'total_gravado_v3': total_gravada,
        'total_igv_v3': total_igv,
        'monto_total_v3': monto_total,
        'line_totals': line_totals
    }
