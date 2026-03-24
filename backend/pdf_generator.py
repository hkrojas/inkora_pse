import io
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Image, Spacer, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.units import inch
from datetime import datetime
from dateutil.relativedelta import relativedelta
import models
import qrcode
from num2words import num2words

from decimal import Decimal, ROUND_HALF_UP, getcontext
import traceback

from calculations import (
    to_decimal,
    calculate_cotizacion_totals_v3,
    TOTAL_PRECISION,
)

getcontext().prec = 50

def monto_a_letras(amount, currency_symbol):
    """Convierte un monto numérico a su representación en palabras."""
    currency_name = "SOLES" if currency_symbol == "S/" else "DÓLARES AMERICANOS"
    try:
        amount_decimal = to_decimal(amount).quantize(TOTAL_PRECISION, rounding=ROUND_HALF_UP)
        integer_part_decimal = amount_decimal.to_integral_value(rounding='ROUND_DOWN')
        if integer_part_decimal < 0:
            integer_part_decimal = Decimal('0')
        integer_part = int(integer_part_decimal)

        decimal_part_num = abs(amount_decimal) % 1
        decimal_part_str = f"{decimal_part_num:.2f}"
        if '.' in decimal_part_str:
            decimal_part = decimal_part_str.split('.')[-1].ljust(2, '0')[:2]
        else:
            decimal_part = '00'

    except (ValueError, TypeError, Exception) as e:
        print(f"Error en monto_a_letras: {e}, amount: {amount}")
        return "MONTO INVÁLIDO"

    text_integer = num2words(integer_part, lang='es').upper()
    return f"SON: {text_integer} CON {decimal_part}/100 {currency_name}"

def obtener_etiqueta_tipo_doc(codigo):
    """Mapea el código de SUNAT al nombre legible (RUC, DNI, etc)."""
    mapeo = {
        "6": "RUC",
        "1": "DNI",
        "4": "C.E.",
        "7": "PASAPORTE",
        "0": "DOC.TRIB.NO.DOM."
    }
    return mapeo.get(str(codigo), "DOC")

def create_pdf_buffer(document_data, tenant: models.Tenant, document_type: str):
    buffer = io.BytesIO()

    # Configuración de márgenes para que coincida con tu diseño original
    margen_izq = 20
    margen_der = 20
    ancho_total = letter[0] - margen_izq - margen_der

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=margen_izq,
        rightMargin=margen_der,
        topMargin=20,
        bottomMargin=20,
    )

    styles = getSampleStyleSheet()
    header_text_style = ParagraphStyle(
        name='HeaderText',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=11
    )
    header_bold_style = ParagraphStyle(
        name='HeaderBold',
        parent=header_text_style,
        fontName='Helvetica-Bold'
    )

    body = styles['Normal']
    body_center = ParagraphStyle(name='BodyCenter', parent=body, alignment=TA_CENTER)
    body_bold = ParagraphStyle(name='BodyBold', parent=body, fontName='Helvetica-Bold')

    body_total_label_right = ParagraphStyle(name='BodyTotalLabelRight', parent=body, alignment=TA_RIGHT)
    body_total_value_center = ParagraphStyle(name='BodyTotalValueCenter', parent=body, alignment=TA_CENTER)
    body_bold_total_label_right = ParagraphStyle(name='BodyBoldTotalLabelRight', parent=body_bold, alignment=TA_RIGHT)
    body_bold_total_value_center = ParagraphStyle(name='BodyBoldTotalValueCenter', parent=body_bold, alignment=TA_CENTER)

    legal_text_style = ParagraphStyle(name='LegalText', parent=body, alignment=TA_CENTER, fontSize=7)

    # 5. Cliente
    cliente = getattr(document_data, "cliente", None)
    if cliente:
        nombre_cliente = getattr(cliente, "razon_social", "")
        tipo_doc_cliente_str = obtener_etiqueta_tipo_doc(getattr(cliente, "tipo_documento", "1"))
        nro_doc_cliente = str(getattr(cliente, "numero_documento", ""))
        direccion_cliente = str(getattr(cliente, "direccion", "") or "").replace('\n', '<br/>')
    else:
        nombre_cliente = "Cliente General"
        tipo_doc_cliente_str = "DOC"
        nro_doc_cliente = "00000000"
        direccion_cliente = "-"

    # --- Cálculo de Totales ---
    items = getattr(document_data, "items", [])
    for item in items:
        # Soporte para objeto SQLAlchemy o diccionario
        if isinstance(item, dict):
            p_desc = item.get("descripcion", "")
            p_cant = item.get("unidades", 0) or item.get("cantidad", 0)
            p_unit = item.get("precio_unitario", 0)
        else:
            p_desc = getattr(item, "descripcion", "")
            p_cant = getattr(item, "cantidad", 0)
            p_unit = getattr(item, "precio_unitario", 0)

        productos_fuente_dict.append({
            "unidades": p_cant,
            "precio_unitario": p_unit,
            "descripcion": p_desc
        })

    # 2. Moneda
    moneda_codigo = getattr(document_data, "moneda", "PEN")
    if isinstance(document_data, dict): moneda_codigo = document_data.get("moneda", "PEN")
    
    simbolo = "S/" if moneda_codigo == "PEN" else "$"
    moneda_texto = "SOLES" if moneda_codigo == "PEN" else "DÓLARES"

    # 3. Títulos y Series
    if is_comprobante:
        tipo_doc_sunat = getattr(document_data, "tipo_comprobante", "03")
        if tipo_doc_sunat == "01":
            doc_title_str = "FACTURA ELECTRÓNICA"
        elif tipo_doc_sunat == "07":
            doc_title_str = "NOTA DE CRÉDITO"
        elif tipo_doc_sunat == "08":
            doc_title_str = "NOTA DE DÉBITO"
        else:
            doc_title_str = "BOLETA DE VENTA ELECTRÓNICA"
    else:
        doc_title_str = "COTIZACIÓN"

    serie = getattr(document_data, "serie", "COT")
    correlativo = getattr(document_data, "correlativo", 0)
    doc_number_str = f"N° {serie}-{str(correlativo).zfill(6)}"

    # 4. Fechas
    raw_fecha = getattr(document_data, "fecha_emision", None) or getattr(document_data, "created_at", datetime.now())
    if isinstance(raw_fecha, str):
        try: raw_fecha = datetime.fromisoformat(raw_fecha.replace('Z', '+00:00'))
        except: raw_fecha = datetime.now()
    
    fecha_emision = raw_fecha.strftime("%d/%m/%Y")
    
    raw_venc = getattr(document_data, "fecha_vencimiento", None)
    if raw_venc:
        if isinstance(raw_venc, str):
             try: raw_venc = datetime.fromisoformat(raw_venc)
             except: raw_venc = raw_fecha + relativedelta(months=1)
        fecha_vencimiento = raw_venc.strftime("%d/%m/%Y")
    else:
        fecha_vencimiento = (raw_fecha + relativedelta(months=1)).strftime("%d/%m/%Y")

    # 5. Cliente
    cliente = getattr(document_data, "cliente", None)
    if cliente:
        nombre_cliente = getattr(cliente, "razon_social", "")
        tipo_doc_cliente_str = obtener_etiqueta_tipo_doc(getattr(cliente, "tipo_documento", "1"))
        nro_doc_cliente = str(getattr(cliente, "numero_documento", ""))
        direccion_cliente = str(getattr(cliente, "direccion", "") or "").replace('\n', '<br/>')
    else:
        nombre_cliente = "Cliente General"
        tipo_doc_cliente_str = "DOC"
        nro_doc_cliente = "00000000"
        direccion_cliente = "-"

    # --- Cálculo de Totales ---
    totals_v3 = calculate_cotizacion_totals_v3(productos_fuente_dict)
    total_gravado_d = totals_v3['total_gravado_v3']
    total_igv_d = totals_v3['total_igv_v3']
    monto_total_d = totals_v3['monto_total_v3']
    line_totals_v3_list = totals_v3['line_totals']

    productos_para_tabla_data = []
    for i, item_dict in enumerate(productos_fuente_dict):
        line_totals = line_totals_v3_list[i]
        productos_para_tabla_data.append({
            'descripcion': str(item_dict['descripcion']).replace('\n', '<br/>'),
            'cantidad': to_decimal(item_dict['unidades']),
            'p_unit_con_igv': line_totals['mto_precio_unitario_con_igv'],
            'igv_item': line_totals['igv_linea'],
            'precio_total_item': line_totals['precio_total_linea']
        })

    # --- Construcción del PDF (DISEÑO ORIGINAL) ---
    color_principal = colors.HexColor(tenant.primary_color or '#004aad')
    ruc_para_cuadro = tenant.business_ruc or ''
    
    logo = ""
    if tenant.logo_filename and os.path.exists(f"logos/{tenant.logo_filename}"):
        try:
            logo = Image(f"logos/{tenant.logo_filename}", width=151, height=76)
        except Exception:
            logo = ""

    business_name_p = Paragraph(tenant.business_name or "Nombre del Negocio", header_bold_style)
    business_address_p = Paragraph(str(tenant.business_address or "Dirección no especificada").replace('\n', '<br/>'), header_text_style)
    contact_info_p = Paragraph(f"{(tenant.business_phone or '').strip()}", header_text_style)
    
    # Textos para el cuadro RUC (renderizado luego con dibujar_rectangulo)
    ruc_p = Paragraph(f"RUC {ruc_para_cuadro}", header_text_style)
    titulo_p = Paragraph(doc_title_str.replace("ELECTRÓNICA", "<br/>ELECTRÓNICA"), header_bold_style)
    numero_p = Paragraph(doc_number_str, header_bold_style)

    data_principal = [
        [logo, business_name_p, ruc_p],
        ["", business_address_p, titulo_p],
        ["", contact_info_p, numero_p]
    ]
    tabla_principal = Table(data_principal, colWidths=[ancho_total * 0.3, ancho_total * 0.5, ancho_total * 0.2])
    tabla_principal.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('SPAN', (0, 0), (0, -1)), # Span para el logo hacia abajo
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0)
    ]))

    # Datos Cliente
    nombre_cliente_p = Paragraph(nombre_cliente, body)
    direccion_cliente_p = Paragraph(direccion_cliente, body)
    
    # Condicionales de visualización
    lbl_venc = " Vencimiento:" if not is_comprobante else ""
    val_venc = fecha_vencimiento if not is_comprobante else ""

    data_cliente = [
        ["Señores:", nombre_cliente_p, " Emisión:", fecha_emision],
        [f"{tipo_doc_cliente_str}:", nro_doc_cliente, lbl_venc, val_venc],
        ["Dirección:", direccion_cliente_p, " Moneda:", moneda_texto]
    ]
    
    tabla_cliente = Table(
        data_cliente,
        colWidths=[ancho_total * 0.1, ancho_total * 0.6, ancho_total * 0.15, ancho_total * 0.15]
    )
    tabla_cliente.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('LINEABOVE', (0, 0), (-1, 0), 1.5, color_principal),
        ('LINEBELOW', (0, -1), (-1, -1), 1.5, color_principal),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5)
    ]))

    # --- Tabla productos ---
    productos_para_pdf = []
    for item_data in productos_para_tabla_data:
        cantidad_decimal = item_data['cantidad']
        if cantidad_decimal % 1 == 0:
            cantidad_str = str(int(cantidad_decimal))
        else:
            cantidad_str = "{:f}".format(cantidad_decimal).rstrip('0').rstrip('.')

        productos_para_pdf.append([
            Paragraph(item_data['descripcion'], body),
            Paragraph(cantidad_str, body_center),
            Paragraph(f"{simbolo} {item_data['p_unit_con_igv']:.2f}", body_center),
            Paragraph(f"{simbolo} {item_data['igv_item']:.2f}", body_center),
            Paragraph(f"{simbolo} {item_data['precio_total_item']:.2f}", body_center)
        ])

    centered_header = ParagraphStyle(
        name='CenteredHeader',
        parent=body_bold,
        alignment=TA_CENTER,
        textColor=colors.white
    )
    header_productos = [
        Paragraph("Descripción", centered_header),
        Paragraph("Cantidad", centered_header),
        Paragraph("P.Unit", centered_header),
        Paragraph("IGV", centered_header),
        Paragraph("Precio", centered_header)
    ]
    data_productos = [header_productos] + productos_para_pdf

    tabla_productos = Table(
        data_productos,
        colWidths=[
            ancho_total * 0.4,
            ancho_total * 0.15,
            ancho_total * 0.15,
            ancho_total * 0.15,
            ancho_total * 0.15
        ],
        repeatRows=1
    )
    tabla_productos.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), color_principal),
        ('LINEBELOW', (0, -1), (-1, -1), 1.5, color_principal),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
    ]))

    # --- Totales ---
    data_total = [
        [Paragraph("Total Gravado", body_total_label_right), Paragraph(f"{simbolo} {total_gravado_d:.2f}", body_total_value_center)],
        [Paragraph("Total IGV ", body_total_label_right), Paragraph(f"{simbolo} {total_igv_d:.2f}", body_total_value_center)],
        [Paragraph("Importe Total", body_bold_total_label_right), Paragraph(f"{simbolo} {monto_total_d:.2f}", body_bold_total_value_center)]
    ]
    tabla_total = Table(data_total, colWidths=[ancho_total * 0.85, ancho_total * 0.15])
    tabla_total.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 2), (1, 2), 'Helvetica-Bold'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))

    # --- Monto en letras ---
    monto_en_letras_str = monto_a_letras(monto_total_d, simbolo)
    centered_bold_style = ParagraphStyle(name='CenteredBold', parent=body_bold, alignment=TA_CENTER)
    monto_letras_p = Paragraph(monto_en_letras_str, centered_bold_style)
    monto_numeros_p = Paragraph(f"IMPORTE TOTAL A PAGAR {simbolo} {monto_total_d:.2f}", centered_bold_style)

    tabla_monto = Table([[monto_numeros_p], [monto_letras_p]], colWidths=[ancho_total])
    tabla_monto.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEABOVE', (0, 0), (-1, 0), 1.5, color_principal),
        ('LINEBELOW', (0, -1), (-1, -1), 1.5, color_principal),
        ('TOPPADDING', (0, 0), (0, 0), 6),
        ('BOTTOMPADDING', (0, 0), (0, 0), 2),
        ('TOPPADDING', (0, 1), (0, 1), 2),
        ('BOTTOMPADDING', (0, 1), (0, 1), 6)
    ]))

    # --- PIE DE PÁGINA: QR E INFORMACIÓN BANCARIA ---
    # Generar QR
    qr_content = f"{ruc_para_cuadro}|{doc_title_str}|{serie}|{correlativo}|{total_igv_d}|{monto_total_d}|{fecha_emision}|{tipo_doc_cliente_str}|{nro_doc_cliente}"
    qr_img = qrcode.make(qr_content)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    qr_image_obj = Image(qr_buffer, width=1.6 * inch, height=1.6 * inch)

    # Tabla para centrar el QR
    t_qr_centered = Table([[qr_image_obj]], colWidths=[ancho_total])
    t_qr_centered.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    # Datos bancarios
    bank_info_text = "<b>Datos para la Transferencia</b><br/>"
    if getattr(tenant, "business_name", None):
        bank_info_text += f"Beneficiario: {str(tenant.business_name).upper()}<br/><br/>"

    if getattr(tenant, "bank_accounts", None) and isinstance(tenant.bank_accounts, list):
        for account in tenant.bank_accounts:
            banco = account.get('banco', '')
            tipo_cuenta = account.get('tipo_cuenta', 'Cta Ahorro')
            moneda_acc = account.get('moneda', 'Soles')
            cuenta = account.get('cuenta', '')
            cci = account.get('cci', '')
            if banco:
                bank_info_text += f"<b>{banco}</b><br/>"
                label_cuenta = f"Cuenta Detracción en {moneda_acc}" if 'nación' in banco.lower() else f"{tipo_cuenta} en {moneda_acc}"
                if cuenta and cci:
                    bank_info_text += f"{label_cuenta}: {cuenta} CCI: {cci}<br/>"
                elif cuenta:
                    bank_info_text += f"{label_cuenta}: {cuenta}<br/>"
                bank_info_text += "<br/>"

    bank_info_p = Paragraph(bank_info_text, body)

    # --- Footer condicional (Notas) ---
    footer_notes = []
    if not is_comprobante:
        note_1_color = colors.HexColor(getattr(tenant, "pdf_note_1_color", None) or "#FF0000")
        style_red_bold = ParagraphStyle(name='RedBold', parent=body, textColor=note_1_color, fontName='Helvetica-Bold')
        
        note_1_text = str(getattr(tenant, "pdf_note_1", "") or "").replace('\n', '<br/>')
        note_2_text = str(getattr(tenant, "pdf_note_2", "") or "").replace('\n', '<br/>')
        
        footer_notes.append(Paragraph(note_1_text, style_red_bold))
        footer_notes.append(Spacer(1, 5))
        footer_notes.append(Paragraph(note_2_text, body))
        footer_notes.append(Spacer(1, 10))

    final_legal = []
    if is_comprobante:
        legal_text = (
            f"Representación Impresa de la <b>{doc_title_str}</b>. "
            "El usuario puede consultar su validez en SUNAT Virtual: www.sunat.gob.pe"
        )
        legal_paragraph = Paragraph(legal_text, legal_text_style)
        tabla_legal = Table([[legal_paragraph]], colWidths=[ancho_total])
        tabla_legal.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5)
        ]))
        final_legal = [Spacer(1, 10), tabla_legal]

    # --- Función para dibujar el rectángulo del RUC (Diseño Original) ---
    def dibujar_rectangulo(canvas, doc_):
        canvas.saveState()
        # Coordenadas ajustadas para el rectángulo superior derecho
        x = margen_izq + (ancho_total * 0.80)
        y = doc_.height + doc_.topMargin - 82 # Ajuste vertical
        w = ancho_total * 0.20
        h = 80
        
        canvas.setStrokeColor(color_principal)
        canvas.setLineWidth(1.5)
        # Dibujamos el rectángulo redondeado como en el original
        canvas.roundRect(x, y, w, h, 5, stroke=1, fill=0)
        canvas.restoreState()

    # --- Ensamblaje ---
    # IMPORTANTE: Añadimos t_qr_centered al final de elements para que aparezca siempre
    elementos = [
        tabla_principal, Spacer(1, 20),
        tabla_cliente, Spacer(1, 20),
        tabla_productos, tabla_total, tabla_monto, Spacer(1, 15)
    ] + footer_notes + [bank_info_p, Spacer(1, 15), t_qr_centered] + final_legal

    try:
        doc.build(elementos, onFirstPage=dibujar_rectangulo, onLaterPages=dibujar_rectangulo)
    except Exception as build_err:
        print(f"ERROR: Falló la construcción del PDF: {build_err}")
        traceback.print_exc()
        raise

    buffer.seek(0)
    return buffer

def generar_pdf_cotizacion(cotizacion: models.Cotizacion, tenant: models.Tenant):
    return create_pdf_buffer(cotizacion, tenant, 'cotizacion')

def create_comprobante_pdf(comprobante, tenant: models.Tenant):
    return create_pdf_buffer(comprobante, tenant, 'comprobante')