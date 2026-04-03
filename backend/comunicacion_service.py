import urllib.parse
import re

def generar_link_whatsapp(cotizacion, telefono: str, url_publica: str) -> str:
    """Genera un link de wa.me pre-llenado con mensaje formal y PIN (Fase 3)."""
    if not telefono:
        return ""
    
    # Limpiar numero de telefono (solo digitos)
    telefono_limpio = re.sub(r'\D', '', telefono)
    
    # Prefix default Peru 51 if not present
    if len(telefono_limpio) == 9 and telefono_limpio.startswith('9'):
        telefono_limpio = '51' + telefono_limpio
        
    simbolo = "S/" if cotizacion.moneda == "PEN" else "$"
    pin = cotizacion.cliente.numero_documento if cotizacion.cliente else "N/A"
    
    mensaje = (
        f"Hola, te compartimos la cotización {cotizacion.serie}-{cotizacion.correlativo} "
        f"por un total de {simbolo} {cotizacion.total_venta}. "
        f"Puedes descargar el documento aquí: {url_publica}\n\n"
        f"Tu PIN de seguridad para descargar el documento es tu número de DNI/RUC: {pin}"
    )
    
    mensaje_encoded = urllib.parse.quote(mensaje)
    return f"https://wa.me/{telefono_limpio}?text={mensaje_encoded}"

def generar_link_mailto(cotizacion, email_cliente: str, url_publica: str, tenant) -> str:
    """Genera un enlace mailto pre-llenado con Asunto, Cuerpo formal y PIN (Fase 3)."""
    if not email_cliente:
        return ""
        
    asunto = f"Cotización {cotizacion.serie}-{cotizacion.correlativo} - {tenant.business_name}"
    pin = cotizacion.cliente.numero_documento if cotizacion.cliente else "N/A"
    
    cuerpo = (
        f"Estimado cliente,\n\n"
        f"Le enviamos el enlace para descargar la Cotización {cotizacion.serie}-{cotizacion.correlativo}.\n\n"
        f"Enlace de descarga:\n{url_publica}\n\n"
        f"SEGURIDAD: Su PIN para descargar el documento es su número de DNI o RUC: {pin}\n\n"
        f"Quedamos atentos a sus comentarios.\n\n"
        f"Saludos cordiales,\n"
        f"{tenant.business_name}"
    )
    
    asunto_encoded = urllib.parse.quote(asunto)
    cuerpo_encoded = urllib.parse.quote(cuerpo)
    
    return f"mailto:{email_cliente}?subject={asunto_encoded}&body={cuerpo_encoded}"
