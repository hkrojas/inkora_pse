import google.generativeai as genai
import json
from config import settings

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

def analizar_texto_cotizacion(texto: str) -> dict:
    """
    Toma un texto libre del cliente y devuelve una estructura JSON predictiva 
    con los probables items y cantidades para automatizar el Data Entry del cotizador.
    """
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = f"""
    Eres un asistente experto en industria gráfica e imprenta.
    El cliente me ha escrito el siguiente texto para pedirme una cotización:
    "{texto}"

    Extrae la información y devuélvela ESTRICTAMENTE en formato JSON válido con esta estructura:
    {{
        "cliente_sugerido": "Nombre del cliente o empresa si se menciona, sino null",
        "items": [
            {{
                "descripcion": "Descripción detallada del producto solicitado",
                "cantidad": número decimal o entero (default 1),
                "material": "Material sugerido si se menciona, sino vacío"
            }}
        ]
    }}
    NO agregues formato de Markdown (como ```json) a tu respuesta, solo retorna el JSON crudo y válido.
    """
    
    response = model.generate_content(prompt)
    texto_respuesta = response.text.strip()
    
    # Limpiar formato markdown residual si existe
    if texto_respuesta.startswith("```json"):
        texto_respuesta = texto_respuesta[7:]
    if texto_respuesta.startswith("```"):
        texto_respuesta = texto_respuesta[3:]
    if texto_respuesta.endswith("```"):
        texto_respuesta = texto_respuesta[:-3]
        
    return json.loads(texto_respuesta.strip())

def extraer_datos_factura(imagen_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """
    Lee una imagen de factura de proveedor y devuelve los insumos comprados 
    para facilitar la alimentación del stock.
    (Soporta Facturas físicas JPG/PNG/PDF)
    """
    # Gemini 1.5 es excelente para lectura multimodal de documentos anchos
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    prompt = """
    Eres un auditor contable automatizado en una imprenta. 
    Revisa la factura (o guía) visual adjunta y extrae exclusivamente los productos/insumos comprados y su respectiva cantidad recibida.
    
    Devuelve ESTRICTAMENTE un JSON válido con esta estructura exacta:
    {
        "insumos": [
            {
                "nombre": "Nombre y descripción del insumo facturado",
                "cantidad": número decimal
            }
        ]
    }
    NO agregues tags markdown ni texto explicativo, necesito parsear este JSON directamente.
    """
    
    documento = {
        "mime_type": mime_type,
        "data": imagen_bytes
    }
    
    response = model.generate_content([prompt, documento])
    texto_respuesta = response.text.strip()
    
    # Limpiar formato markdown residual si existe
    if texto_respuesta.startswith("```json"):
        texto_respuesta = texto_respuesta[7:]
    if texto_respuesta.startswith("```"):
        texto_respuesta = texto_respuesta[3:]
    if texto_respuesta.endswith("```"):
        texto_respuesta = texto_respuesta[:-3]
        
    return json.loads(texto_respuesta.strip())
