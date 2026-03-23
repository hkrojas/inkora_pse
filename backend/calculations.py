from decimal import Decimal, ROUND_HALF_UP

# ==========================================
# CONFIGURACIÓN MATEMÁTICA
# ==========================================

# Tasa de IGV (18%)
IGV_RATE = Decimal("0.18")
FACTOR_IGV = Decimal("1.00") + IGV_RATE # 1.18
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

def calcular_item(cantidad: Decimal, precio_con_igv: Decimal):
    """Calcula el desglose de un item a partir de su precio final."""
    qty = to_decimal(cantidad)
    precio_final = to_decimal(precio_con_igv)

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
        "tipo_afectacion_igv": "10" 
    }

def sumarizar_cotizacion(items_procesados: list):
    """Suma totales para la cabecera de la cotización."""
    total_gravada = Decimal("0.00")
    total_igv = Decimal("0.00")
    total_venta = Decimal("0.00")

    for item in items_procesados:
        total_gravada += to_decimal(item["total_base_igv"])
        total_igv += to_decimal(item["total_igv"])
        total_venta += to_decimal(item["total_item"])

    return {
        "total_gravada": redondear(total_gravada),
        "total_igv": redondear(total_igv),
        "total_venta": redondear(total_venta),
        "total_exonerada": Decimal("0.00"),
        "total_inafecta": Decimal("0.00")
    }

# --- FUNCIONES DE SOPORTE PARA PDF GENERATOR (V3) ---

def get_line_totals_v3(cantidad, precio_unitario_con_igv):
    """Función de compatibilidad para el generador de PDF."""
    calc = calcular_item(cantidad, precio_unitario_con_igv)
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
        else:
            qty = getattr(item, 'cantidad', 0)
            price = getattr(item, 'precio_unitario', 0)
        
        calc = get_line_totals_v3(qty, price)
        line_totals.append(calc)
        
        total_gravada += calc['valor_venta_linea']
        total_igv += calc['igv_linea']
        monto_total += calc['precio_total_linea']

    return {
        'total_gravado_v3': total_gravada,
        'total_igv_v3': total_igv,
        'monto_total_v3': monto_total,
        'line_totals': line_totals
    }