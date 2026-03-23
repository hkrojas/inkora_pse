import requests
import json
from datetime import datetime
import decimal
from fastapi import HTTPException
from sqlalchemy.orm import Session
import models
import schemas
from config import settings
import calculations

# ==========================================
# UTILITARIOS Y CONFIGURACIÓN
# ==========================================

class FacturacionException(Exception):
    """Excepción para errores de negocio en facturación."""
    pass

class SUNATDecimalEncoder(json.JSONEncoder):
    """Codificador JSON custom para serializar tipos Decimal asegurados sin recaer en hardware fp"""
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super(SUNATDecimalEncoder, self).default(obj)

UNIDADES = {0: "", 1: "UN", 2: "DOS", 3: "TRES", 4: "CUATRO", 5: "CINCO", 6: "SEIS", 7: "SIETE", 8: "OCHO", 9: "NUEVE"}
DECENAS = {10: "DIEZ", 11: "ONCE", 12: "DOCE", 13: "TRECE", 14: "CATORCE", 15: "QUINCE", 20: "VEINTE", 30: "TREINTA", 40: "CUARENTA", 50: "CINCUENTA", 60: "SESENTA", 70: "SETENTA", 80: "OCHENTA", 90: "NOVENTA"}
CENTENAS = {100: "CIEN", 200: "DOSCIENTOS", 300: "TRESCIENTOS", 400: "CUATROCIENTOS", 500: "QUINIENTOS", 600: "SEISCIENTOS", 700: "SETECIENTOS", 800: "OCHOCIENTOS", 900: "NOVECIENTOS"}

def numero_a_letras(numero):
    parte_entera = int(numero)
    parte_decimal = int(round((numero - parte_entera) * 100))
    letras = convert_number(parte_entera)
    return f"SON: {letras} CON {parte_decimal:02d}/100 SOLES"

def convert_number(n):
    if n == 0: return "CERO"
    if n < 10: return UNIDADES[n]
    if n < 20: return DECENAS.get(n, "DIECI" + UNIDADES[n-10])
    if n < 30: return "VEINTI" + UNIDADES[n-20] if n > 20 else "VEINTE"
    if n < 100: 
        decena, unidad = divmod(n, 10)
        return DECENAS[decena*10] + (" Y " + UNIDADES[unidad] if unidad > 0 else "")
    if n < 1000:
        if n == 100: return "CIEN"
        centena, resto = divmod(n, 100)
        return (CENTENAS[centena*100] if centena > 1 else "CIENTO") + (" " + convert_number(resto) if resto > 0 else "")
    if n < 1000000:
        miles, resto = divmod(n, 1000)
        return (convert_number(miles) + " MIL" if miles > 1 else "MIL") + (" " + convert_number(resto) if resto > 0 else "")
    return "NUMERO DEMASIADO GRANDE"

def obtener_tipo_documento_codigo(tipo: str) -> str:
    if not tipo: return "1"
    tipo = tipo.upper().strip()
    mapping = {"RUC": "6", "DNI": "1", "CE": "4", "PASAPORTE": "7"}
    return mapping.get(tipo, "1")

# ==========================================
# CONSTRUCTORES DE PAYLOAD
# ==========================================

def _construir_items_payload(items):
    items_payload = []
    totales = {"gravada": calculations.Decimal("0.00"), "igv": calculations.Decimal("0.00"), "venta": calculations.Decimal("0.00")}

    for item in items:
        calc = calculations.calcular_item(item.cantidad, item.precio_unitario)

        totales["gravada"] += calc["total_base_igv"]
        totales["igv"] += calc["total_igv"]
        totales["venta"] += calc["total_item"]

        items_payload.append({
            "codProducto": "P001",
            "unidad": calc["unidad_medida"],
            "descripcion": item.descripcion,
            "cantidad": calc["cantidad"],
            "mtoValorUnitario": calc["valor_unitario"],
            "mtoValorVenta": calc["total_base_igv"],
            "mtoBaseIgv": calc["total_base_igv"],
            "porcentajeIgv": 18,
            "igv": calc["total_igv"],
            "tipAfeIgv": calc["tipo_afectacion_igv"],
            "totalImpuestos": calc["total_igv"],
            "mtoPrecioUnitario": calc["precio_unitario"]
        })
    
    return items_payload, totales

def _base_payload(cotizacion, user, tipo_doc_comprobante):
    """Construye el payload base común para Facturas, Boletas y Notas."""
    cliente = cotizacion.cliente
    if not cliente: raise FacturacionException("Cotización sin cliente.")
    if not user.business_ruc: raise FacturacionException("Emisor sin RUC configurado.")

    items_payload, totales = _construir_items_payload(cotizacion.items)
    leyenda_monto = numero_a_letras(totales["venta"])
    fecha_emision = datetime.now().astimezone().replace(microsecond=0).isoformat()

    return {
        "ublVersion": "2.1",
        "tipoDoc": tipo_doc_comprobante,
        "fechaEmision": fecha_emision,
        "tipoMoneda": "PEN",
        "mtoOperGravadas": totales["gravada"],
        "mtoIGV": totales["igv"],
        "totalImpuestos": totales["igv"],
        "valorVenta": totales["gravada"],
        "mtoImporteTotal": totales["venta"],
        "company": {
            "ruc": user.business_ruc,
            "razonSocial": user.business_name,
            "address": {"direccion": user.business_address or "-"}
        },
        "client": {
            "tipoDoc": obtener_tipo_documento_codigo(cliente.tipo_documento),
            "numDoc": str(cliente.numero_documento).strip(),
            "rznSocial": cliente.razon_social,
            "address": {"direccion": cliente.direccion or "-"}
        },
        "details": items_payload,
        "legends": [{"code": "1000", "value": leyenda_monto}]
    }, totales

# ==========================================
# REGLAS FISCALES AUTOMATIZADAS
# ==========================================

# Umbral mínimo SUNAT para detracción (S/ 700.00)
UMBRAL_DETRACCION = calculations.Decimal("700.00")
# Porcentaje estándar para servicios de imprenta (Catálogo 54 - Código 012)
PORCENTAJE_DETRACCION_IMPRENTA = calculations.Decimal("12.00")
CODIGO_DETRACCION_IMPRENTA = "012"  # Servicios de fabricación de bienes por encargo

def _aplicar_detraccion(payload, cotizacion, user, db: Session):
    """
    Inyecta el nodo 'detraccion' en el payload si corresponde:
    - Moneda PEN y monto total > S/ 700.00
    - Solo para Facturas (01), no Boletas.
    Persiste los datos en el modelo Cotizacion.
    """
    from decimal import Decimal
    
    monto_total = calculations.to_decimal(payload.get("mtoImporteTotal", 0))
    moneda = cotizacion.moneda or "PEN"
    tipo_doc = payload.get("tipoDoc", "00")
    
    # Solo aplica a Facturas en Soles que superen el umbral
    if moneda != "PEN" or tipo_doc != "01" or monto_total <= UMBRAL_DETRACCION:
        return payload
    
    porcentaje = calculations.to_decimal(
        cotizacion.porcentaje_detraccion or PORCENTAJE_DETRACCION_IMPRENTA
    )
    monto_detraccion = calculations.redondear(monto_total * porcentaje / Decimal("100"))
    
    # Obtener cuenta Banco de la Nación del modelo o de las cuentas bancarias del usuario
    cuenta_bn = cotizacion.cuenta_banco_nacion
    if not cuenta_bn and user.bank_accounts:
        # Buscar cuenta de Banco de la Nación en las cuentas bancarias del usuario
        for cuenta in (user.bank_accounts or []):
            if isinstance(cuenta, dict) and "nacion" in (cuenta.get("banco", "")).lower():
                cuenta_bn = cuenta.get("cuenta", "")
                break
    if not cuenta_bn:
        cuenta_bn = ""  # Se debe configurar en el perfil del emisor
    
    # Inyectar nodo detraccion en el payload SUNAT/ApisPeru
    payload["detraccion"] = {
        "codBienDetraccion": CODIGO_DETRACCION_IMPRENTA,
        "codMedioPago": "001",  # Depósito en cuenta
        "ctaBanco": cuenta_bn,
        "percent": porcentaje,
        "mount": monto_detraccion
    }
    
    # Agregar leyenda obligatoria de detracción
    payload["legends"].append({
        "code": "2006",
        "value": "Operación sujeta al Sistema de Pago de Obligaciones Tributarias"
    })
    
    # Persistir en el modelo para la BD
    cotizacion.sujeta_detraccion = True
    cotizacion.porcentaje_detraccion = porcentaje
    cotizacion.monto_detraccion = monto_detraccion
    cotizacion.cuenta_banco_nacion = cuenta_bn
    
    if db:
        try:
            db.commit()
        except Exception:
            db.rollback()
    
    return payload

def _aplicar_anticipos(payload, cotizacion, user):
    """
    Si la cotización tiene anticipos_deducidos (JSON), inyecta los nodos 
    'anticipos' y 'totalAnticipos' en el payload y ajusta los totales.
    Estructura esperada de anticipos_deducidos:
    [
        {"serie": "F001", "correlativo": "000001", "monto": 500.00, "tipo_doc": "02"},
        ...
    ]
    """
    from decimal import Decimal
    
    anticipos_json = cotizacion.anticipos_deducidos
    if not anticipos_json or not isinstance(anticipos_json, list) or len(anticipos_json) == 0:
        return payload
    
    anticipos_payload = []
    total_anticipos = Decimal("0.00")
    
    for anticipo in anticipos_json:
        monto = calculations.to_decimal(anticipo.get("monto", 0))
        total_anticipos += monto
        
        serie = anticipo.get("serie", "F001")
        correlativo = str(anticipo.get("correlativo", "1")).zfill(6)
        tipo_doc_anticipo = anticipo.get("tipo_doc", "02")  # Catálogo 12: 02=Factura antic.
        
        anticipos_payload.append({
            "nroDocRel": f"{serie}-{correlativo}",
            "tipoDocRel": tipo_doc_anticipo,
            "total": monto
        })
    
    total_anticipos = calculations.redondear(total_anticipos)
    
    # Inyectar en payload
    payload["anticipos"] = anticipos_payload
    payload["totalAnticipos"] = total_anticipos
    
    # Ajustar totales: descontar anticipos para no duplicar ingresos ni IGV
    # El anticipo ya tributó IGV cuando se emitió su factura de anticipo
    anticipo_gravada = calculations.redondear(total_anticipos / calculations.FACTOR_IGV)
    anticipo_igv = calculations.redondear(total_anticipos - anticipo_gravada)
    
    mto_gravadas = calculations.to_decimal(payload.get("mtoOperGravadas", 0))
    mto_igv = calculations.to_decimal(payload.get("mtoIGV", 0))
    mto_total = calculations.to_decimal(payload.get("mtoImporteTotal", 0))
    
    payload["mtoOperGravadas"] = calculations.redondear(mto_gravadas - anticipo_gravada)
    payload["mtoIGV"] = calculations.redondear(mto_igv - anticipo_igv)
    payload["totalImpuestos"] = payload["mtoIGV"]
    payload["valorVenta"] = payload["mtoOperGravadas"]
    payload["mtoImporteTotal"] = calculations.redondear(mto_total - total_anticipos)
    
    # Persistir total de anticipos en el modelo
    cotizacion.total_anticipos = total_anticipos
    
    return payload

# ==========================================
# FUNCIONES PRINCIPALES DE EMISIÓN
# ==========================================

def emitir_factura(cotizacion: models.Cotizacion, db: Session, user: models.User, tipo_doc_override=None):
    """Emite Factura (01) o Boleta (03)."""
    # Determinar tipo
    if tipo_doc_override:
        tipo_comprobante = tipo_doc_override
    else:
        tipo_cliente = obtener_tipo_documento_codigo(cotizacion.cliente.tipo_documento)
        tipo_comprobante = "01" if tipo_cliente == "6" else "03"
    
    serie = "F001" if tipo_comprobante == "01" else "B001"
    
    payload, totales = _base_payload(cotizacion, user, tipo_comprobante)
    payload["serie"] = serie
    payload["correlativo"] = str(cotizacion.id).zfill(6)
    
    # --- REGLAS FISCALES AUTOMÁTICAS ---
    # 1. Detracciones SPOT (PEN > S/700 en Facturas)
    payload = _aplicar_detraccion(payload, cotizacion, user, db)
    
    # 2. Anticipos / Señas de producción
    payload = _aplicar_anticipos(payload, cotizacion, user)
    
    return _enviar_a_api(payload, user, "/invoice/send")

def emitir_nota(nota: models.Cotizacion, doc_afectado: models.Cotizacion, user: models.User, cod_motivo: str, descripcion: str, tipo_nota: str):
    """
    Emite Nota de Crédito (07) o Débito (08).
    'nota' es la cotización con los nuevos montos/items.
    'doc_afectado' es el comprobante original.
    """
    tipo_comprobante = "07" if tipo_nota == "credito" else "08"
    serie_origen = doc_afectado.serie # Ej: F001
    serie_nota = "FC01" if serie_origen.startswith("F") else "BC01" # Serie fija para notas
    
    payload, totales = _base_payload(nota, user, tipo_comprobante)
    payload["serie"] = serie_nota
    payload["correlativo"] = str(nota.id).zfill(6)
    
    # Agregar sección específica de Notas
    payload["perception"] = {
        "codReg": "01",
        "tasa": 0,
        "mto": 0,
        "mtoTotal": 0,
        "mtoBase": 0
    }
    
    # Bloque 'note' específico de ApisPeru
    payload["note"] = {
        "code": cod_motivo,
        "value": descripcion
    }
    
    # Documento Afectado (Referencia)
    # IMPORTANTE: ApisPeru usa 'affectedDocument' en la raíz para asociar
    # Pero el estándar UBL lo pone en otro lado. ApisPeru simplifica esto.
    # Verificamos estructura del JSON. Para /note/send suele requerir datos del documento afectado.
    # En la doc de ApisPeru, los campos van directos al payload si se usa el builder, 
    # pero aquí lo armamos manual.
    
    # Estructura típica ApisPeru para notas:
    payload["codMotivo"] = cod_motivo
    payload["desMotivo"] = descripcion
    payload["tipDocAfectado"] = doc_afectado.tipo_comprobante # 01 o 03
    payload["numDocfectado"] = f"{doc_afectado.serie}-{str(doc_afectado.correlativo).zfill(6)}"

    return _enviar_a_api(payload, user, "/note/send")

def anular_comprobante(comprobante: models.Cotizacion, motivo: str, user: models.User):
    """
    Anula una Factura (Baja) o Boleta (Resumen).
    """
    base_url = settings.API_URL.rstrip('/')
    token = user.apisperu_token or settings.API_TOKEN
    
    if not token: raise FacturacionException("Falta Token API.")
    if not user.business_ruc: raise FacturacionException("Falta RUC Emisor.")

    tipo_doc = comprobante.tipo_comprobante # 01 o 03
    correlativo = str(comprobante.correlativo).zfill(6)
    
    # Payload común
    payload = {
        "correlativo": "00001", # Correlativo del envío de la baja/resumen (no del documento)
        "fecGeneracion": datetime.now().strftime("%Y-%m-%d"),
        "fecComunicacion": datetime.now().strftime("%Y-%m-%d"),
        "company": {
            "ruc": user.business_ruc,
            "razonSocial": user.business_name,
            "address": {"direccion": user.business_address or "-"}
        },
        "details": [
            {
                "tipoDoc": tipo_doc,
                "serie": comprobante.serie,
                "correlativo": correlativo,
                "motivo": motivo
            }
        ]
    }

    endpoint = "/voided/send" # Default para Facturas
    
    # Si es Boleta (03) o Nota asociada a Boleta, se usa Resumen Diario
    if tipo_doc in ["03"] or (tipo_doc in ["07", "08"] and comprobante.serie.startswith("B")):
        endpoint = "/summary/send"
        # Ajuste específico para resumen: 'details' cambia estructura ligeramente
        payload["fecResumen"] = datetime.now().strftime("%Y-%m-%d")
        payload["details"][0]["estado"] = "3" # 3 = Anulación

    return _enviar_a_api(payload, user, endpoint)

# ==========================================
# ENVÍO Y DESCARGA
# ==========================================

def _enviar_a_api(payload, user, endpoint):
    base_url = settings.API_URL.rstrip('/')
    token = user.apisperu_token or settings.API_TOKEN
    url = f"{base_url}{endpoint}"
    
    try:
        print(f"--- ENVIANDO A: {url} ---")
        payload_str = json.dumps(payload, cls=SUNATDecimalEncoder)
        response = requests.post(url, data=payload_str, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }, timeout=30)
        
        if response.status_code == 422:
            err = response.json()
            msg = err.get('message', 'Error validación')
            if 'errors' in err: msg += f": {err['errors']}"
            raise FacturacionException(f"Rechazo: {msg}")

        response.raise_for_status()
        data = response.json()
        
        return {
            "success": True,
            "sunat_response": {
                "success": True,
                "cdrResponse": {"description": "Enviado a SUNAT"},
                "links": {
                    "xml": data.get("xml"),
                    "pdf": data.get("pdf"),
                    "cdr": data.get("cdr")
                }
            }
        }
    except Exception as e:
        print(f"Error API: {e}")
        raise FacturacionException(f"Error comunicación: {str(e)}")

def descargar_archivo(tipo_archivo: str, comprobante: models.Cotizacion, user: models.User):
    """
    Recupera el link o binario de XML/PDF/CDR.
    Endpoint: /invoice/pdf, /invoice/xml, /invoice/cdr
    """
    base_url = settings.API_URL.rstrip('/')
    token = user.apisperu_token or settings.API_TOKEN
    endpoint = f"/invoice/{tipo_archivo}"
    
    # Reconstruimos un payload mínimo para identificar el documento
    payload = {
        "tipoDoc": comprobante.tipo_comprobante,
        "serie": comprobante.serie,
        "correlativo": str(comprobante.correlativo).zfill(6), # Asegurar formato
        "company": {"ruc": user.business_ruc}
    }
    
    url = f"{base_url}{endpoint}"
    print(f"--- DESCARGANDO {tipo_archivo.upper()}: {url} ---")
    
    response = requests.post(url, json=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }, stream=True)
    
    if response.status_code != 200:
        raise FacturacionException(f"No se pudo descargar el archivo: {response.text}")
    
    return response.content