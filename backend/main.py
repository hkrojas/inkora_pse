import uuid
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
import requests
import json 

import models
import schemas
import crud
import security
import facturacion_service
import pdf_generator
import comunicacion_service
from services import storage_service, pdf_storage_service, sunat_service
from config import settings
from database import SessionLocal, engine
from sqlalchemy import text



# Infraestructura: Todo migrado a Supabase Storage
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistema Cotizaciones SUNAT")

# app.mount("/logos", StaticFiles(directory="logos"), name="logos") # Migrado a Supabase Storage

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://localhost:5174",
        "http://localhost:3000", 
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def process_direct_sunat_emission_bg(cotizacion_id: int, tenant_id: int):
    """
    Pipeline completo de emisión directa a SUNAT en segundo plano.
    """
    db = SessionLocal()
    try:
        # Inyectar tenant_id para RLS
        db.execute(text("SELECT set_config('app.current_tenant_id', :tid, true)"), {"tid": str(tenant_id)})
        
        cotizacion = db.query(models.Cotizacion).filter(models.Cotizacion.id == cotizacion_id).first()
        tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
        
        if not cotizacion or not tenant or not tenant.sunat_usuario_sol or not tenant.sunat_cert_url:
            print(f"Error: Credenciales incompletas para tenant {tenant_id}")
            return

        # 1. Preparar datos para el UBL
        emisor_data = {
            "ruc": tenant.ruc or "12345678901",
            "nombre": tenant.name or "Empresa Test",
            "direccion": tenant.address or "Calle Real 123",
            "ubigeo": tenant.ubigeo or "150101"
        }
        
        cliente = cotizacion.cliente
        cliente_data = {
            "numero_documento": cliente.numero_documento,
            "tipo_documento": facturacion_service.obtener_tipo_documento_codigo(cliente.tipo_documento),
            "nombre": cliente.razon_social or "-"
        }
        
        items_data = []
        for item in cotizacion.items:
            # Reutilizamos cálculos de facturacion_service
            calc = facturacion_service.calculations.calcular_item(item.cantidad, item.precio_unitario)
            items_data.append({
                "descripcion": item.descripcion,
                "cantidad": item.cantidad,
                "valor_unitario": calc["valor_unitario"],
                "precio_unitario": item.precio_unitario,
                "valor_venta": calc["total_base_igv"],
                "igv": calc["total_igv"]
            })

        ubl_payload = {
            "serie": cotizacion.serie or ("F001" if cotizacion.tipo_comprobante == "01" else "B001"),
            "correlativo": str(cotizacion.id).zfill(6),
            "fecha_emision": datetime.now().strftime("%Y-%m-%d"),
            "tipo_comprobante": cotizacion.tipo_comprobante or "01",
            "monto_letras": facturacion_service.numero_a_letras(cotizacion.total),
            "emisor": emisor_data,
            "cliente": cliente_data,
            "items": items_data,
            "total_gravada": cotizacion.total / facturacion_service.calculations.FACTOR_IGV,
            "total_igv": cotizacion.total - (cotizacion.total / facturacion_service.calculations.FACTOR_IGV),
            "total_venta": cotizacion.total
        }

        # 2. Descargar certificado
        cert_data = sunat_service.SUNATService.get_cert_from_storage(tenant.sunat_cert_url)
        
        # 3. Instanciar servicio y procesar
        sunat = sunat_service.SUNATService(
            ruc=tenant.ruc,
            usuario_sol=tenant.sunat_usuario_sol,
            clave_sol=tenant.sunat_clave_sol,
            cert_data=cert_data,
            cert_password=tenant.sunat_cert_password
        )
        
        # Generar -> Firmar -> Enviar
        xml_raw = sunat.generate_invoice_ubl(ubl_payload)
        xml_signed = sunat.sign_xml(xml_raw)
        
        resultado = sunat.send_bill(f"{ubl_payload['serie']}-{ubl_payload['correlativo']}", xml_signed)
        
        if resultado["success"]:
            # Guardar CDR en Storage y actualizar estado en BD
            cdr_path = f"comprobantes/{tenant_id}/{ubl_payload['serie']}-{ubl_payload['correlativo']}.zip"
            # Omitimos upload a storage por ahora, lo guardamos como respuesta crud
            crud.guardar_respuesta_sunat(db, cotizacion_id, {
                "success": True,
                "sunat_response": {
                    "success": True,
                    "cdrResponse": {"description": "Aceptado por SUNAT (Procesamiento Directo)"},
                    "links": {"cdr": "stored_locally"}
                }
            })
            print(f"Emisión directa exitosa para {cotizacion_id}")
        else:
            print(f"Error en emisión SUNAT: {resultado.get('error')}")

    except Exception as e:
        print(f"Error en pipeline SUNAT: {e}")
    finally:
        db.close()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    """Valida el JWT y retorna el usuario actual."""
    return security.get_current_user(db, token)

def get_db_tenant(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Dependencia crÃ­tica: Sincroniza el tenant_id del JWT con la sesiÃ³n de Postgres
    usando set_config(..., true) para que sea local a la transacciÃ³n.
    """
    db.execute(text("SELECT set_config('app.current_tenant_id', :tid, true)"), {"tid": str(current_user.tenant_id)})
    yield db

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = security.authenticate_user(db, form_data.username, form_data.password)
    if not user: raise HTTPException(401, "Credenciales invÃ¡lidas")
    access_token = security.create_access_token_with_claims(user)
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, user.email): raise HTTPException(400, "Email registrado")
    # Verificar que el tenant existe
    tenant = crud.get_tenant(db, user.tenant_id)
    if not tenant: raise HTTPException(400, "Empresa (tenant) no encontrada")
    return crud.create_user(db=db, user=user)

@app.get("/users/me/", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@app.put("/users/profile", response_model=schemas.UserResponse)
async def update_user_profile(data: schemas.UserUpdateProfile, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)
    try:
        db.commit()
        db.refresh(current_user)
        return current_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar: {str(e)}")

# ==========================================
# TENANT (Empresa) Management
# ==========================================

@app.get("/tenant/", response_model=schemas.TenantResponse)
def get_my_tenant(db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """Obtener datos de la empresa del usuario autenticado."""
    tenant = crud.get_tenant(db, current_user.tenant_id)
    if not tenant: raise HTTPException(404, "Empresa no encontrada")
    return tenant

@app.put("/tenant/", response_model=schemas.TenantResponse)
def update_my_tenant(data: schemas.TenantUpdate, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """Actualizar datos de la empresa (solo admins)."""
    if current_user.rol not in ["admin", "superadmin"]:
        raise HTTPException(403, "Solo administradores pueden modificar datos de la empresa")
    tenant = crud.update_tenant(db, current_user.tenant_id, data)
    if not tenant: raise HTTPException(404)
    return tenant

@app.post("/tenants/", response_model=schemas.TenantResponse)
def create_tenant(tenant: schemas.TenantCreate, db: Session = Depends(get_db)):
    """Registrar una nueva empresa (onboarding)."""
    try:
        return crud.create_tenant(db, tenant)
    except Exception as e:
        raise HTTPException(400, f"Error al crear empresa: {str(e)}")

@app.post("/users/upload-logo")
async def upload_logo(file: UploadFile = File(...), db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    try:
        ext = file.filename.split(".")[-1].lower()
        if ext not in ["png", "jpg", "jpeg", "webp"]: raise HTTPException(400, "Formato no vÃ¡lido")
        
        # Leer el contenido del archivo
        file_content = await file.read()
        
        # Generar nombre Ãºnico con UUID (Fase 2)
        unique_filename = f"logo_{uuid.uuid4()}.{ext}"
        
        # Subir a Supabase Storage (Bucket 'printflow-archivos', Folder 'logos')
        public_url = await storage_service.upload_to_storage(
            file_bytes=file_content,
            folder_name="logos",
            filename=unique_filename,
            content_type=file.content_type
        )
        
        # Guardar la URL pÃºblica en el Tenant
        tenant = crud.get_tenant(db, current_user.tenant_id)
        if tenant:
            tenant.logo_filename = public_url
            db.commit()
        
        return {"url": public_url}
    except Exception as e: raise HTTPException(500, f"Error en Cloud Storage: {str(e)}")

@app.get("/consultar-documento/{numero}")
def consultar_documento(numero: str, current_user: models.User = Depends(get_current_user)):
    """
    Consulta DNI (8 dÃ­gitos) o RUC (11 dÃ­gitos) en APIsPeru.
    API Docs: https://dniruc.apisperu.com/api/v1
    """
    numero = numero.strip()
    if len(numero) == 8:
        tipo = "dni"
    elif len(numero) == 11:
        tipo = "ruc"
    else:
        raise HTTPException(400, "NÃºmero invÃ¡lido. Ingrese 8 dÃ­gitos (DNI) u 11 dÃ­gitos (RUC).")
    
    # Token: preferir el del usuario, fallback al global en config
    token = current_user.apisperu_token or settings.DNIRUC_TOKEN
    if not token:
        raise HTTPException(500, "No hay token de consulta configurado. Configure DNIRUC_TOKEN o su token personal.")
    
    url = f"{settings.DNIRUC_API_URL}/{tipo}/{numero}"
    
    try:
        response = requests.get(url, params={"token": token}, timeout=10)
        
        if response.status_code != 200:
            raise HTTPException(response.status_code, f"Error en API externa: {response.text}")
        
        data = response.json()
        
        # La API retorna {"success": false, "message": "..."} si falla
        if data.get("success") is False:
            raise HTTPException(404, data.get("message", "Documento no encontrado en RENIEC/SUNAT."))
        
        if tipo == "ruc":
            return {
                "tipo": "RUC",
                "documento": data.get("ruc", numero),
                "razon_social": data.get("razonSocial", ""),
                "nombre_comercial": data.get("nombreComercial", ""),
                "direccion": data.get("direccion", "-"),
                "departamento": data.get("departamento", ""),
                "provincia": data.get("provincia", ""),
                "distrito": data.get("distrito", ""),
                "ubigeo": data.get("ubigeo", ""),
                "estado": data.get("estado", ""),
                "condicion": data.get("condicion", ""),
                "telefonos": data.get("telefonos", []),
                "capital": data.get("capital", "")
            }
        else:  # DNI
            nombres = data.get("nombres", "")
            ap_paterno = data.get("apellidoPaterno", "")
            ap_materno = data.get("apellidoMaterno", "")
            nombre_completo = f"{nombres} {ap_paterno} {ap_materno}".strip()
            return {
                "tipo": "DNI",
                "documento": data.get("dni", numero),
                "razon_social": nombre_completo,
                "nombres": nombres,
                "apellido_paterno": ap_paterno,
                "apellido_materno": ap_materno,
                "cod_verifica": data.get("codVerifica", ""),
                "direccion": "-",
                "estado": "ACTIVO",
                "condicion": "HABIDO"
            }
    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        raise HTTPException(504, "Tiempo de espera agotado al consultar RENIEC/SUNAT.")
    except requests.exceptions.ConnectionError:
        raise HTTPException(503, "No se pudo conectar con el servicio de consulta.")
    except Exception as e:
        raise HTTPException(500, f"Error inesperado: {str(e)}")

# Mantener ruta legacy para compatibilidad
@app.get("/consultar-ruc/{numero}")
def consultar_ruc_legacy(numero: str, current_user: models.User = Depends(get_current_user)):
    """Ruta legacy â€” redirige a /consultar-documento/{numero}."""
    return consultar_documento(numero, current_user)

# --- CRUD BÃ¡sico ---
@app.get("/clientes/", response_model=List[schemas.ClienteResponse])
def read_clientes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db_tenant)):
    return crud.get_clientes(db, skip, limit)

@app.post("/clientes/", response_model=schemas.ClienteResponse)
def create_cliente(cliente: schemas.ClienteCreate, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    return crud.create_cliente(db, cliente, current_user.tenant_id)

@app.put("/clientes/{cliente_id}", response_model=schemas.ClienteResponse)
def update_cliente(cliente_id: int, cliente: schemas.ClienteCreate, db: Session = Depends(get_db_tenant)):
    res = crud.update_cliente(db, cliente_id, cliente)
    if not res: raise HTTPException(404)
    return res

@app.delete("/clientes/{cliente_id}")
def delete_cliente(cliente_id: int, db: Session = Depends(get_db_tenant)):
    res = crud.delete_cliente(db, cliente_id)
    if not res: raise HTTPException(404)
    return {"msg": "Eliminado"}

@app.get("/productos/", response_model=List[schemas.ProductoResponse])
def read_productos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db_tenant)):
    return crud.get_productos(db, skip, limit)

@app.post("/productos/", response_model=schemas.ProductoResponse)
def create_producto(producto: schemas.ProductoCreate, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    return crud.create_producto(db, producto, current_user.tenant_id)

@app.put("/productos/{producto_id}", response_model=schemas.ProductoResponse)
def update_producto(producto_id: int, producto: schemas.ProductoCreate, db: Session = Depends(get_db_tenant)):
    res = crud.update_producto(db, producto_id, producto)
    if not res: raise HTTPException(404)
    return res

@app.delete("/productos/{producto_id}")
def delete_producto(producto_id: int, db: Session = Depends(get_db_tenant)):
    res = crud.delete_producto(db, producto_id)
    if not res: raise HTTPException(404)
    return {"msg": "Eliminado"}

@app.get("/cotizaciones/", response_model=List[schemas.CotizacionResponse])
def read_cotizaciones(skip: int = 0, limit: int = 100, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    return crud.get_cotizaciones(db, current_user, skip, limit)

@app.post("/cotizaciones/", response_model=schemas.CotizacionResponse)
def create_cotizacion(
    cotizacion: schemas.CotizacionCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_tenant), 
    current_user: models.User = Depends(get_current_user)
):
    db_cotizacion = crud.create_cotizacion(db, cotizacion, current_user.id, current_user.tenant_id)
    
    # Fase 4: Generar PDF en segundo plano inmediatamente al crear
    background_tasks.add_task(pdf_storage_service.process_pdf_background, db_cotizacion.id)
    
    return db_cotizacion

@app.get("/cotizaciones/{cotizacion_id}", response_model=schemas.CotizacionResponse)
def read_cotizacion(cotizacion_id: int, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    res = crud.get_cotizacion(db, cotizacion_id, current_user)
    if not res: raise HTTPException(404)
    return res

# ==========================================
# ENDPOINTS PÃšBLICOS (ACCESO SIN AUTH - FASE 3)
# ==========================================

@app.get("/public/cotizaciones/{uuid_publico}/pdf")
async def descargar_pdf_publico(uuid_publico: str, pin: str, db: Session = Depends(get_db)):
    """
    Endpoint para que el cliente final descargue su PDF usando un UUID y un PIN (DNI/RUC).
    No requiere JWT (get_current_user).
    """
    cotizacion = crud.get_cotizacion_by_uuid(db, uuid_publico)
    if not cotizacion:
        raise HTTPException(404, "Enlace no vÃ¡lido o expirado.")
    
    # Validar PIN (NÃºmero de documento del cliente)
    if not cotizacion.cliente or str(cotizacion.cliente.numero_documento).strip() != pin.strip():
        raise HTTPException(401, "PIN de seguridad incorrecto.")
    
    # Si ya tenemos la URL persistida en BD, redirigimos o devolvemos
    if cotizacion.sunat_pdf_url:
        return {"url": cotizacion.sunat_pdf_url}
    
    # Si no existe, avisamos que estÃ¡ en proceso (Fase 4)
    raise HTTPException(202, "El documento se estÃ¡ generando en la nube, por favor intente en unos segundos.")

@app.get("/cotizaciones/{cotizacion_id}/pdf")
async def descargar_pdf_interno(
    cotizacion_id: int, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_tenant), 
    current_user: models.User = Depends(get_current_user)
):
    cotizacion = crud.get_cotizacion(db, cotizacion_id, current_user)
    if not cotizacion: raise HTTPException(404)
    
    if cotizacion.sunat_pdf_url:
        return {"url": cotizacion.sunat_pdf_url}
    
    # Forzar generaciÃ³n asÃ­ncrona si no existe y devolver espera
    background_tasks.add_task(pdf_storage_service.process_pdf_background, cotizacion.id)
    raise HTTPException(202, "Generando PDF en segundo plano... Reintente en un momento.")

@app.get("/cotizaciones/{cotizacion_id}/compartir")
async def compartir_cotizacion(cotizacion_id: int, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """Genera links para compartir la cotizaciÃ³n mediante acceso pÃºblico seguro (Fase 3)."""
    cotizacion = crud.get_cotizacion(db, cotizacion_id, current_user)
    if not cotizacion: 
        raise HTTPException(404, "Documento no encontrado o sin acceso")
    
    # Generar URL pÃºblica (Backend + UUID)
    base_url = settings.BACKEND_URL.rstrip('/')
    url_publica = f"{base_url}/public/cotizaciones/{cotizacion.uuid_publico}/pdf"
    
    cliente = cotizacion.cliente
    telefono_cliente = getattr(cliente, "telefono", "") if cliente else ""
    email_cliente = getattr(cliente, "email", "") if cliente else ""
    
    wp_link = comunicacion_service.generar_link_whatsapp(cotizacion, telefono_cliente, url_publica)
    mailto_link = comunicacion_service.generar_link_mailto(cotizacion, email_cliente, url_publica, current_user.tenant)
    
    return {
        "url_compartir": url_publica,
        "whatsapp_link": wp_link,
        "mailto_link": mailto_link
    }

# ==========================================
# MOTOR FINANCIERO (PAGOS Y ADELANTOS)
# ==========================================

@app.post("/cotizaciones/{cotizacion_id}/pagos", response_model=schemas.PagoResponse)
def registrar_adelanto_pago(
    cotizacion_id: int, 
    pago_data: schemas.PagoCreate, 
    db: Session = Depends(get_db_tenant), 
    current_user: models.User = Depends(get_current_user)
):
    """Registra un pago para una cotizaciÃ³n/comprobante."""
    # Verificar acceso a la cotizaciÃ³n
    cotizacion = crud.get_cotizacion(db, cotizacion_id, current_user)
    if not cotizacion: 
        raise HTTPException(404, "Documento no encontrado o sin acceso")
    
    try:
        # Registrar usando la lÃ³gica centralizada de caja (transaccional)
        return crud.registrar_pago(
            db=db, 
            cotizacion_id=cotizacion_id, 
            pago_data=pago_data, 
            tenant_id=current_user.tenant_id
        )
    except ValueError as ve:
        raise HTTPException(400, str(ve))
    except Exception as e:
        raise HTTPException(500, f"Error al registrar el pago: {str(e)}")

@app.get("/cotizaciones/{cotizacion_id}/pagos", response_model=List[schemas.PagoResponse])
def listar_pagos(
    cotizacion_id: int, 
    db: Session = Depends(get_db_tenant), 
    current_user: models.User = Depends(get_current_user)
):
    """Obtiene el historial de pagos de un documento."""
    cotizacion = crud.get_cotizacion(db, cotizacion_id, current_user)
    if not cotizacion: 
        raise HTTPException(404, "Documento no encontrado o sin acceso")
    return crud.get_pagos_cotizacion(db, cotizacion_id)

# ==========================================
# ENDPOINTS DE FACTURACIÃ“N (NUEVOS)
# ==========================================

@app.post("/cotizaciones/{cotizacion_id}/facturar")
def emitir_comprobante(
    cotizacion_id: int, 
    payload: schemas.FacturarPayload, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_tenant), 
    current_user: models.User = Depends(get_current_user)
):
    """Emitir Factura (01) o Boleta (03) a partir de una cotizaciÃ³n."""
    cotizacion = crud.get_cotizacion(db, cotizacion_id, current_user)
    if not cotizacion: raise HTTPException(404, "Documento no encontrado")
    if not cotizacion.cliente: raise HTTPException(400, "Cliente no asignado")

    # --- GUARDIA DE MÃQUINA DE ESTADOS ---
    if cotizacion.estado in ("facturada", "anulada"):
        raise HTTPException(
            400,
            f"OperaciÃ³n bloqueada: El documento {cotizacion.serie}-{cotizacion.correlativo} "
            f"ya fue procesado (estado actual: '{cotizacion.estado}'). "
            f"No se puede emitir un comprobante duplicado ante SUNAT."
        )

    try:
        # --- LÃ“GICA DE ELECCIÃ“N DE MOTOR (Fase 14) ---
        tenant = db.query(models.Tenant).filter(models.Tenant.id == current_user.tenant_id).first()
        
        if tenant and tenant.sunat_usuario_sol and tenant.sunat_cert_url:
            # OpciÃ³n A: EmisiÃ³n Directa (Fase 14)
            # Marcamos como procesando y delegamos al background
            cotizacion.estado = "facturada" # Bloqueo inmediato
            db.commit()
            
            background_tasks.add_task(process_direct_sunat_emission_bg, cotizacion_id, current_user.tenant_id)
            background_tasks.add_task(pdf_storage_service.process_pdf_background, cotizacion_id)
            
            return {
                "success": True, 
                "message": "EmisiÃ³n directa iniciada. El comprobante se procesarÃ¡ en segundo plano.",
                "sunat_response": {"success": True, "cdrResponse": {"description": "En cola para envÃ­o directo"}}
            }
        else:
            # OpciÃ³n B: Fallback a ApisPeru (Original)
            resultado = facturacion_service.emitir_factura(cotizacion, db, current_user, tipo_doc_override=payload.tipo_comprobante)
            crud.guardar_respuesta_sunat(db, cotizacion_id, resultado)
            
            # Fase 4: Regenerar el PDF
            background_tasks.add_task(pdf_storage_service.process_pdf_background, cotizacion_id)
            
            return resultado
            
    except facturacion_service.FacturacionException as fe:
        raise HTTPException(400, str(fe))
    except Exception as e:
        print(f"Error critico facturaciÃ³n: {e}")
        raise HTTPException(500, f"Error en el servicio de facturaciÃ³n: {str(e)}")

@app.post("/notas/emitir")
def emitir_nota(nota_data: schemas.NotaCreate, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """Emitir Nota de CrÃ©dito/DÃ©bito."""
    doc_afectado = crud.get_cotizacion(db, nota_data.comprobante_afectado_id, current_user)
    if not doc_afectado: raise HTTPException(404, "Comprobante afectado no encontrado")

    # --- GUARDIA DE MÃQUINA DE ESTADOS ---
    # Solo se puede emitir una nota contra un comprobante que haya sido facturado exitosamente.
    # Un documento pendiente nunca fue enviado a SUNAT, y uno anulado ya no tiene vigencia tributaria.
    if doc_afectado.estado not in ("facturada",):
        raise HTTPException(
            400,
            f"OperaciÃ³n bloqueada: Solo se pueden emitir Notas de CrÃ©dito/DÃ©bito contra "
            f"comprobantes en estado 'facturada'. Estado actual del documento "
            f"{doc_afectado.serie}-{doc_afectado.correlativo}: '{doc_afectado.estado}'."
        )
    
    try:
        # 1. Crear registro persistente de la Nota en BD (clona items del doc afectado)
        db_nota = crud.crear_nota_credito_debito(
            db=db,
            doc_afectado=doc_afectado,
            usuario_id=current_user.id,
            tipo_nota=nota_data.tipo_nota,
            cod_motivo=nota_data.cod_motivo,
            descripcion_motivo=nota_data.descripcion_motivo
        )

        # 2. Enviar a APIsPeru usando el registro reciÃ©n creado
        resultado = facturacion_service.emitir_nota(
            nota=db_nota,
            doc_afectado=doc_afectado,
            user=current_user,
            cod_motivo=nota_data.cod_motivo,
            descripcion=nota_data.descripcion_motivo,
            tipo_nota=nota_data.tipo_nota
        )

        # 3. Guardar respuesta SUNAT en el registro de la nota
        crud.guardar_respuesta_sunat(db, db_nota.id, resultado)

        return resultado
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/bajas/anular")
def anular_documento(data: schemas.AnulacionCreate, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """Dar de baja (Facturas) o Resumen Diario (Boletas) para anulaciÃ³n."""
    comprobante = crud.get_cotizacion(db, data.comprobante_id, current_user)
    if not comprobante: raise HTTPException(404)

    # --- GUARDIA DE MÃQUINA DE ESTADOS ---
    # Solo se puede anular un comprobante que haya sido emitido exitosamente ante SUNAT.
    # Un documento pendiente no existe en SUNAT, y uno ya anulado no puede anularse dos veces.
    if comprobante.estado != "facturada":
        estado_msg = {
            "pendiente": "El documento aÃºn no ha sido emitido ante SUNAT. No requiere anulaciÃ³n.",
            "anulada": "El documento ya fue anulado previamente. No se puede procesar dos veces."
        }
        raise HTTPException(
            400,
            f"OperaciÃ³n bloqueada: {estado_msg.get(comprobante.estado, f'Estado invÃ¡lido: {comprobante.estado}')}"
        )
    
    try:
        res = facturacion_service.anular_comprobante(comprobante, data.motivo, current_user)
        # Persistir el cambio de estado en BD tras Ã©xito de API
        crud.anular_cotizacion(db, comprobante.id)
        return res
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/facturacion/{tipo_archivo}")
def recuperar_archivo_api(tipo_archivo: str, payload: schemas.DescargaArchivoPayload, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """Recuperar XML, PDF o CDR directamente desde la API."""
    if tipo_archivo not in ["xml", "pdf", "cdr"]: raise HTTPException(400, "Tipo invÃ¡lido")
    
    comprobante = crud.get_cotizacion(db, payload.comprobante_id, current_user)
    if not comprobante: raise HTTPException(404)
    
    try:
        contenido = facturacion_service.descargar_archivo(tipo_archivo, comprobante, current_user)
        
        media_type = "application/pdf" if tipo_archivo == "pdf" else "application/xml"
        if tipo_archivo == "cdr": media_type = "application/zip"
        
        ext = tipo_archivo if tipo_archivo != "cdr" else "zip"
        filename = f"{comprobante.serie}-{comprobante.correlativo}.{ext}"
        
        return Response(content=contenido, media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"})
    except Exception as e:
        raise HTTPException(400, str(e))

# ==========================================
# GUÃAS DE REMISIÃ“N ELECTRÃ“NICAS (GRE)
# ==========================================

@app.post("/guias-remision/", response_model=schemas.GuiaRemisionResponse)
def crear_guia_remision(guia_data: schemas.GuiaRemisionCreate, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """Crear y guardar una GuÃ­a de RemisiÃ³n en BD (sin enviar a SUNAT)."""
    data = guia_data.model_dump()
    
    # Serializar items
    items_raw = data.pop("items", [])
    data["items"] = [item for item in items_raw]
    
    try:
        return crud.create_guia_remision(db, data, current_user.id, current_user.tenant_id)
    except Exception as e:
        raise HTTPException(400, f"Error al crear guÃ­a: {str(e)}")

@app.get("/guias-remision/", response_model=List[schemas.GuiaRemisionResponse])
def listar_guias_remision(skip: int = 0, limit: int = 100, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """Listar GuÃ­as de RemisiÃ³n del usuario."""
    return crud.get_guias_remision(db, current_user, skip, limit)

@app.post("/guias-remision/{guia_id}/emitir")
def emitir_guia_remision_endpoint(guia_id: int, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """Emitir GuÃ­a de RemisiÃ³n a SUNAT (endpoint /despatch/send)."""
    guia = crud.get_guia_remision(db, guia_id, current_user)
    if not guia:
        raise HTTPException(404, "GuÃ­a de RemisiÃ³n no encontrada.")
    
    # --- GUARDIA DE MÃQUINA DE ESTADOS ---
    if guia.estado in ("emitida", "anulada"):
        raise HTTPException(
            400,
            f"OperaciÃ³n bloqueada: La guÃ­a {guia.serie}-{str(guia.correlativo).zfill(6)} "
            f"ya fue procesada (estado actual: '{guia.estado}'). "
            f"No se puede emitir una guÃ­a duplicada ante SUNAT."
        )
    
    try:
        resultado = facturacion_service.emitir_guia_remision(guia, current_user)
        crud.guardar_respuesta_sunat_gre(db, guia.id, resultado)
        return resultado
        raise HTTPException(400, str(fe))
    except Exception as e:
        print(f"Error critico GRE: {e}")
        raise HTTPException(500, "Error en el servicio de guÃ­as de remisiÃ³n.")

# ==========================================
# GESTIÃ“N DE PROVEEDORES (BROKER)
# ==========================================

@app.get("/proveedores/", response_model=List[schemas.ProveedorResponse])
def listar_proveedores(skip: int = 0, limit: int = 100, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """Listar Proveedores/Talleres Externos del Tenant"""
    return crud.get_proveedores(db, current_user.tenant_id, skip, limit)

@app.post("/proveedores/", response_model=schemas.ProveedorResponse)
def crear_proveedor(proveedor: schemas.ProveedorCreate, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """Crear nuevo Proveedor"""
    return crud.create_proveedor(db, proveedor, current_user.tenant_id)

@app.put("/proveedores/{proveedor_id}", response_model=schemas.ProveedorResponse)
def actualizar_proveedor(proveedor_id: int, proveedor: schemas.ProveedorUpdate, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """Actualizar Proveedor Existente"""
    res = crud.update_proveedor(db, proveedor_id, proveedor, current_user.tenant_id)
    if not res: raise HTTPException(404, "Proveedor no encontrado")
    return res

@app.delete("/proveedores/{proveedor_id}")
def eliminar_proveedor(proveedor_id: int, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """Eliminar Proveedor"""
    res = crud.delete_proveedor(db, proveedor_id, current_user.tenant_id)
    if not res: raise HTTPException(404, "Proveedor no encontrado")
    return {"status": "success"}

# ==========================================
# MOTOR DE PRODUCCIÃ“N (MRP / BOM)
# ==========================================

@app.get("/insumos/", response_model=List[schemas.InsumoResponse])
def read_insumos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """CatÃ¡logo General de Materias Primas / Insumos"""
    return crud.get_insumos(db, current_user.tenant_id, skip, limit)

@app.post("/insumos/", response_model=schemas.InsumoResponse)
def create_insumo(insumo: schemas.InsumoCreate, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """Registra nueva Materia Prima / Insumo"""
    return crud.create_insumo(db, insumo, current_user.tenant_id)

@app.get("/productos/{producto_id}/bom", response_model=List[schemas.RecetaBOMResponse])
def read_bom_producto(producto_id: int, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """Obtiene la Lista de Materiales (BOM) para un producto especÃ­fico"""
    return crud.get_recetas_producto(db, producto_id)

@app.post("/productos/{producto_id}/bom", response_model=schemas.RecetaBOMResponse)
def create_bom_item(producto_id: int, receta: schemas.RecetaBOMBase, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """Asigna un insumo y su cantidad necesaria para fabricar este producto"""
    receta_create = schemas.RecetaBOMCreate(**receta.model_dump(), producto_id=producto_id)
    return crud.create_receta_bom(db, receta_create, current_user.tenant_id)

from pydantic import BaseModel
from decimal import Decimal

class OrdenProduccionParams(BaseModel):
    tipo_produccion: str = "interna"
    proveedor_id: Optional[int] = None
    costo_tercerizado: Optional[Decimal] = None

def check_stock_bg(tenant_id: int):
    """Abre una sesiÃ³n transaccional paralela independiente para la BackgroundTask"""
    db_bg = SessionLocal()
    try:
        # IMPORTANTE: Inyectar tenant_id en la sesiÃ³n de background para RLS
        db_bg.execute(text("SELECT set_config('app.current_tenant_id', :tid, true)"), {"tid": str(tenant_id)})
        crud.verificar_stock_y_generar_alertas(db_bg, tenant_id)
    finally:
        db_bg.close()

@app.get("/ordenes-produccion", response_model=List[schemas.OrdenProduccionResponse])
def listar_ordenes_produccion(skip: int = 0, limit: int = 100, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """API CrÃ­tica para renderizar el Taller (Grid Interna y Externa)."""
    return crud.get_ordenes_produccion(db, current_user.tenant_id, skip, limit)

@app.patch("/ordenes-produccion/{orden_id}/status", response_model=schemas.OrdenProduccionResponse)
def update_orden_status_endpoint(orden_id: int, nuevo_estado: str, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """Cambia el estado de una orden (en_cola -> en_proceso -> finalizada)."""
    orden = crud.update_orden_produccion_status(db, orden_id, nuevo_estado, current_user.tenant_id)
    if not orden:
        raise HTTPException(404, "Orden de producciÃ³n no encontrada.")
    return orden

@app.post("/cotizaciones/{cotizacion_id}/orden-produccion", response_model=schemas.OrdenProduccionResponse)
def generar_orden_produccion_endpoint(cotizacion_id: int, background_tasks: BackgroundTasks, params: Optional[OrdenProduccionParams] = None, db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """
    Ruta CrÃ­tica MRP: Carga la cotizaciÃ³n y explota automÃ¡ticamente las Listas 
    de Materiales (BOM) para calcular quÃ© insumos y quÃ© cantidades se imprimirÃ¡n, 
    incluyendo sus respectivas mermas calculadas.
    Soporta asignaciÃ³n y delegaciÃ³n de Ã³rdenes a talleres tercerizados.
    """
    p_tipo = params.tipo_produccion if params else "interna"
    p_prov = params.proveedor_id if params else None
    p_costo = params.costo_tercerizado if params else None

    try:
        orden = crud.generar_orden_produccion(db, cotizacion_id, current_user.tenant_id, p_tipo, p_prov, p_costo)
        background_tasks.add_task(check_stock_bg, current_user.tenant_id)
        return orden
    except ValueError as ve:
        raise HTTPException(400, str(ve))
    except Exception as e:
        raise HTTPException(500, f"Error al generar la orden de producciÃ³n: {str(e)}")

# ==========================================
# FASE 8: BUSINESS INTELLIGENCE Y ALERTAS
# ==========================================

@app.get("/analytics/dashboard", response_model=schemas.DashboardStatsResponse)
def read_dashboard_stats(db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """Obtiene analÃ­tica clave (Ingresos, Saldos, Outsourcing, Top Productos) en vivo."""
    return crud.get_dashboard_stats(db, current_user.tenant_id)

@app.get("/alertas/inventario", response_model=List[schemas.AlertaInventarioResponse])
def read_alertas_inventario(db: Session = Depends(get_db_tenant), current_user: models.User = Depends(get_current_user)):
    """Retorna las alertas de inventario activo/agotado no resueltas"""
    return db.query(models.AlertaInventario).filter(
        models.AlertaInventario.tenant_id == current_user.tenant_id,
        models.AlertaInventario.resuelta == False
    ).order_by(models.AlertaInventario.fecha_creacion.desc()).all()

# ==========================================
# FASE 9: INTELIGENCIA ARTIFICIAL (GEMINI)
# ==========================================

import ai_service

class CotizarTextoParams(BaseModel):
    texto: str

@app.post("/ai/cotizar-texto", response_model=schemas.AIParsedCotizacionResponse)
def ai_cotizar_texto(params: CotizarTextoParams, current_user: models.User = Depends(get_current_user)):
    """Extrae estructura de items de una cotizaciÃ³n cruda dictada por el cliente"""
    try:
        resultado = ai_service.analizar_texto_cotizacion(params.texto)
        return resultado
    except Exception as e:
        print(f"Error AI Texto: {e}")
        raise HTTPException(500, "Error procesando el texto con Inteligencia Artificial. Verifique su GEMINI_API_KEY o la cuota de su servicio.")

@app.post("/ai/leer-factura-proveedor", response_model=schemas.AIParsedFacturaResponse)
def ai_leer_factura(file: UploadFile = File(...), current_user: models.User = Depends(get_current_user)):
    """Sube una imagen/PDF de una factura de proveedor y extrae automÃ¡ticamente los insumos comprados."""
    try:
        bytes_data = file.file.read()
        resultado = ai_service.extraer_datos_factura(bytes_data, mime_type=file.content_type)
        return resultado
    except Exception as e:
        print(f"Error AI VisiÃ³n: {e}")
        raise HTTPException(500, "Error procesando el documento con IA Multimodal. Verifica imagen legible y config GEMINI_API_KEY.")

# ==========================================
# FASE 13: SUPERADMIN CONTROL TOWER
# ==========================================

def get_superadmin(current_user: models.User = Depends(get_current_user)):
    """Valida que el usuario tenga privilegios de Superadmin Global."""
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Acceso denegado: Se requieren privilegios de Superadmin.")
    return current_user

@app.get("/superadmin/tenants", response_model=List[schemas.SuperadminTenantResponse])
def list_all_tenants_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), admin: models.User = Depends(get_superadmin)):
    """(Control Tower) Lista todas las imprentas en el SaaS sin restricciones de RLS."""
    return crud.get_all_tenants(db, skip, limit)

@app.patch("/superadmin/tenants/{tenant_id}", response_model=schemas.SuperadminTenantResponse)
def update_tenant_saas_endpoint(tenant_id: int, updates: schemas.TenantSaaSUpdate, db: Session = Depends(get_db), admin: models.User = Depends(get_superadmin)):
    """(Control Tower) Actualiza planes, límites y credenciales SUNAT del Tenant."""
    updated_tenant = crud.update_tenant_saas(db, tenant_id, updates.model_dump(exclude_unset=True))
    if not updated_tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")
    return updated_tenant

@app.delete("/superadmin/tenants/{tenant_id}")
def delete_tenant_endpoint(tenant_id: int, db: Session = Depends(get_db), admin: models.User = Depends(get_superadmin)):
    """(Control Tower) Elimina un tenant y todos sus datos."""
    result = crud.delete_tenant(db, tenant_id)
    if not result:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")
    return {"message": "Tenant eliminado correctamente"}

@app.get("/superadmin/usuarios", response_model=List[schemas.UserResponse])
def list_all_users_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), admin: models.User = Depends(get_superadmin)):
    """(Control Tower) Lista todos los usuarios del sistema."""
    return crud.get_all_users(db, skip, limit)

@app.patch("/users/{user_id}", response_model=schemas.UserResponse)
def update_user_endpoint(user_id: int, updates: schemas.UserAdminUpdate, db: Session = Depends(get_db), admin: models.User = Depends(get_superadmin)):
    """(Control Tower) Actualiza un usuario del sistema."""
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    return user

@app.delete("/users/{user_id}")
def delete_user_endpoint(user_id: int, db: Session = Depends(get_db), admin: models.User = Depends(get_superadmin)):
    """(Control Tower) Elimina un usuario del sistema."""
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    try:
        db.delete(user)
        db.commit()
        return {"message": "Usuario eliminado correctamente"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error al eliminar usuario: {str(e)}")

# ==========================================
# AUDITORÍA
# ==========================================

class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    user_id: Optional[int] = None
    action: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

@app.get("/superadmin/audit-logs", response_model=List[AuditLogResponse])
def list_audit_logs_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), admin: models.User = Depends(get_superadmin)):
    """(Control Tower) Lista todos los logs de auditoría."""
    return crud.get_audit_logs(db, skip, limit)
