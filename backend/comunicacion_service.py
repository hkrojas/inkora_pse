import urllib.parse
import re

def generar_link_whatsapp(cotizacion, telefono: str, url_pdf: str) -> str:
    """Genera un link de wa.me pre-llenado con mensaje formal."""
    if not telefono:
        return ""
    
    # Limpiar numero de telefono (solo digitos)
    telefono_limpio = re.sub(r'\D', '', telefono)
    
    # Prefix default Peru 51 if not present and len handles basic peru mobiles
    if len(telefono_limpio) == 9 and telefono_limpio.startswith('9'):
        telefono_limpio = '51' + telefono_limpio
        
    simbolo = "S/" if cotizacion.moneda == "PEN" else "$"
    
    mensaje = (
        f"Hola, te compartimos la cotización {cotizacion.serie}-{cotizacion.correlativo} "
        f"por un total de {simbolo} {cotizacion.total_venta}. "
        f"Puedes descargar el documento aquí: {url_pdf}"
    )
    
    mensaje_encoded = urllib.parse.quote(mensaje)
    return f"https://wa.me/{telefono_limpio}?text={mensaje_encoded}"

def generar_link_mailto(cotizacion, email_cliente: str, url_pdf: str, tenant) -> str:
    """Genera un enlace mailto pre-llenado con Asunto y Cuerpo formal."""
    if not email_cliente:
        return ""
        
    asunto = f"Cotización {cotizacion.serie}-{cotizacion.correlativo} - {tenant.business_name}"
    
    cuerpo = (
        f"Estimado cliente,\n\n"
        f"Adjunto le enviamos el enlace para descargar la Cotización {cotizacion.serie}-{cotizacion.correlativo}.\n\n"
        f"Puede revisar y descargar el documento ingresando al siguiente enlace:\n"
        f"{url_pdf}\n\n"
        f"Quedamos atentos a sus comentarios.\n\n"
        f"Saludos cordiales,\n"
        f"{tenant.business_name}"
    )
    
    asunto_encoded = urllib.parse.quote(asunto)
    cuerpo_encoded = urllib.parse.quote(cuerpo)
    
    # The format is mailto:email?subject=...&body=...
    return f"mailto:{email_cliente}?subject={asunto_encoded}&body={cuerpo_encoded}"
