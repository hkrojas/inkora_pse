import os
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List, Optional
import shutil
import requests
import json 

import models
import schemas
import crud
import security
import facturacion_service
import pdf_generator
from database import SessionLocal, engine
from config import settings

MASTER_APISPERU_TOKEN = os.getenv("MASTER_APISPERU_TOKEN", "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6Imtlbm5lZHlyb2phczAxMDY0QGdtYWlsLmNvbSJ9.3sopEO4OjTDovbXV46k8g48sxbP55W3MEbke16Im-uw")
BASE_URL_APISPERU = "https://dniruc.apisperu.com/api/v1"

os.makedirs("logos", exist_ok=True)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistema Cotizaciones SUNAT")

app.mount("/logos", StaticFiles(directory="logos"), name="logos")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = security.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    return user

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = security.authenticate_user(db, form_data.username, form_data.password)
    if not user: raise HTTPException(401, "Credenciales inválidas")
    access_token = security.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, user.email): raise HTTPException(400, "Email registrado")
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

@app.post("/users/upload-logo")
async def upload_logo(file: UploadFile = File(...), current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        ext = file.filename.split(".")[-1].lower()
        if ext not in ["png", "jpg", "jpeg"]: raise HTTPException(400, "Formato no válido")
        filename = f"logo_{current_user.id}.{ext}"
        with open(f"logos/{filename}", "wb+") as f: shutil.copyfileobj(file.file, f)
        current_user.logo_filename = filename
        db.commit()
        return {"filename": filename}
    except Exception as e: raise HTTPException(500, str(e))

@app.get("/consultar-ruc/{numero}")
def consultar_documento_sunat(numero: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    numero = numero.strip()
    tipo = "dni" if len(numero) == 8 else "ruc" if len(numero) == 11 else None
    if not tipo: raise HTTPException(400, "Longitud inválida")
    
    token = current_user.apisperu_token if current_user.apisperu_token else MASTER_APISPERU_TOKEN
    url = f"{BASE_URL_APISPERU}/{tipo}/{numero}?token={token}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success") is False: raise HTTPException(404, "No encontrado")
            res = {"documento": numero, "direccion": "", "estado": "ACTIVO", "condicion": "HABIDO"}
            if tipo == "ruc":
                res.update({"razon_social": data.get("razonSocial"), "direccion": data.get("direccion"), "estado": data.get("estado"), "condicion": data.get("condicion")})
            else:
                n = f"{data.get('nombres','')} {data.get('apellidoPaterno','')} {data.get('apellidoMaterno','')}".strip()
                res["razon_social"] = n
                res["direccion"] = "-"
            return res
        raise HTTPException(response.status_code, "Error API externa")
    except Exception as e: raise HTTPException(500, str(e))

# --- CRUD Básico ---
@app.get("/clientes/", response_model=List[schemas.ClienteResponse])
def read_clientes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.get_clientes(db, skip, limit)

@app.post("/clientes/", response_model=schemas.ClienteResponse)
def create_cliente(cliente: schemas.ClienteCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.create_cliente(db, cliente)

@app.put("/clientes/{cliente_id}", response_model=schemas.ClienteResponse)
def update_cliente(cliente_id: int, cliente: schemas.ClienteCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    res = crud.update_cliente(db, cliente_id, cliente)
    if not res: raise HTTPException(404)
    return res

@app.delete("/clientes/{cliente_id}")
def delete_cliente(cliente_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    res = crud.delete_cliente(db, cliente_id)
    if not res: raise HTTPException(404)
    return {"msg": "Eliminado"}

@app.get("/productos/", response_model=List[schemas.ProductoResponse])
def read_productos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.get_productos(db, skip, limit)

@app.post("/productos/", response_model=schemas.ProductoResponse)
def create_producto(producto: schemas.ProductoCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.create_producto(db, producto)

@app.put("/productos/{producto_id}", response_model=schemas.ProductoResponse)
def update_producto(producto_id: int, producto: schemas.ProductoCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    res = crud.update_producto(db, producto_id, producto)
    if not res: raise HTTPException(404)
    return res

@app.delete("/productos/{producto_id}")
def delete_producto(producto_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    res = crud.delete_producto(db, producto_id)
    if not res: raise HTTPException(404)
    return {"msg": "Eliminado"}

@app.get("/cotizaciones/", response_model=List[schemas.CotizacionResponse])
def read_cotizaciones(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.get_cotizaciones(db, current_user, skip, limit)

@app.post("/cotizaciones/", response_model=schemas.CotizacionResponse)
def create_cotizacion(cotizacion: schemas.CotizacionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.create_cotizacion(db, cotizacion, current_user.id)

@app.get("/cotizaciones/{cotizacion_id}", response_model=schemas.CotizacionResponse)
def read_cotizacion(cotizacion_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    res = crud.get_cotizacion(db, cotizacion_id, current_user)
    if not res: raise HTTPException(404)
    return res

@app.get("/cotizaciones/{cotizacion_id}/pdf")
def descargar_pdf_interno(cotizacion_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    cotizacion = crud.get_cotizacion(db, cotizacion_id, current_user)
    if not cotizacion: raise HTTPException(404)
    try:
        pdf = pdf_generator.generar_pdf_cotizacion(cotizacion, current_user)
        fname = f"Cotizacion_{cotizacion.serie}-{cotizacion.correlativo}.pdf"
        return StreamingResponse(pdf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={fname}"})
    except Exception as e:
        print(f"Error PDF: {e}")
        raise HTTPException(500)

# ==========================================
# ENDPOINTS DE FACTURACIÓN (NUEVOS)
# ==========================================

@app.post("/cotizaciones/{cotizacion_id}/facturar")
def emitir_comprobante(cotizacion_id: int, payload: schemas.FacturarPayload, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Emitir Factura (01) o Boleta (03) a partir de una cotización."""
    cotizacion = crud.get_cotizacion(db, cotizacion_id, current_user)
    if not cotizacion: raise HTTPException(404, "Documento no encontrado")
    if not cotizacion.cliente: raise HTTPException(400, "Cliente no asignado")

    # --- GUARDIA DE MÁQUINA DE ESTADOS ---
    if cotizacion.estado in ("facturada", "anulada"):
        raise HTTPException(
            400,
            f"Operación bloqueada: El documento {cotizacion.serie}-{cotizacion.correlativo} "
            f"ya fue procesado (estado actual: '{cotizacion.estado}'). "
            f"No se puede emitir un comprobante duplicado ante SUNAT."
        )

    try:
        resultado = facturacion_service.emitir_factura(cotizacion, db, current_user, tipo_doc_override=payload.tipo_comprobante)
        crud.guardar_respuesta_sunat(db, cotizacion_id, resultado)
        return resultado
    except facturacion_service.FacturacionException as fe:
        raise HTTPException(400, str(fe))
    except Exception as e:
        print(f"Error critico: {e}")
        raise HTTPException(500, "Error en el servicio de facturación")

@app.post("/notas/emitir")
def emitir_nota(nota_data: schemas.NotaCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Emitir Nota de Crédito/Débito."""
    doc_afectado = crud.get_cotizacion(db, nota_data.comprobante_afectado_id, current_user)
    if not doc_afectado: raise HTTPException(404, "Comprobante afectado no encontrado")

    # --- GUARDIA DE MÁQUINA DE ESTADOS ---
    # Solo se puede emitir una nota contra un comprobante que haya sido facturado exitosamente.
    # Un documento pendiente nunca fue enviado a SUNAT, y uno anulado ya no tiene vigencia tributaria.
    if doc_afectado.estado not in ("facturada",):
        raise HTTPException(
            400,
            f"Operación bloqueada: Solo se pueden emitir Notas de Crédito/Débito contra "
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

        # 2. Enviar a APIsPeru usando el registro recién creado
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
def anular_documento(data: schemas.AnulacionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Dar de baja (Facturas) o Resumen Diario (Boletas) para anulación."""
    comprobante = crud.get_cotizacion(db, data.comprobante_id, current_user)
    if not comprobante: raise HTTPException(404)

    # --- GUARDIA DE MÁQUINA DE ESTADOS ---
    # Solo se puede anular un comprobante que haya sido emitido exitosamente ante SUNAT.
    # Un documento pendiente no existe en SUNAT, y uno ya anulado no puede anularse dos veces.
    if comprobante.estado != "facturada":
        estado_msg = {
            "pendiente": "El documento aún no ha sido emitido ante SUNAT. No requiere anulación.",
            "anulada": "El documento ya fue anulado previamente. No se puede procesar dos veces."
        }
        raise HTTPException(
            400,
            f"Operación bloqueada: {estado_msg.get(comprobante.estado, f'Estado inválido: {comprobante.estado}')}"
        )
    
    try:
        res = facturacion_service.anular_comprobante(comprobante, data.motivo, current_user)
        # Persistir el cambio de estado en BD tras éxito de API
        crud.anular_cotizacion(db, comprobante.id)
        return res
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/facturacion/{tipo_archivo}")
def recuperar_archivo_api(tipo_archivo: str, payload: schemas.DescargaArchivoPayload, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Recuperar XML, PDF o CDR directamente desde la API."""
    if tipo_archivo not in ["xml", "pdf", "cdr"]: raise HTTPException(400, "Tipo inválido")
    
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