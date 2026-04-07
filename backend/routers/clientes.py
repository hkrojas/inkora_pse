from typing import List, Optional

import requests
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

import crud
import models
import schemas
from api_dependencies import get_current_user, get_db_tenant
from api_utils import raise_internal_server_error, read_validated_upload
from config import settings
from services.import_service import parse_clientes
from tenant_access import get_document_lookup_token

router = APIRouter(tags=["clientes"])


def _consultar_documento(numero: str, current_user: models.User):
    numero = numero.strip()
    if len(numero) == 8:
        tipo = "dni"
    elif len(numero) == 11:
        tipo = "ruc"
    else:
        raise HTTPException(
            400,
            "Numero invalido. Ingrese 8 digitos (DNI) u 11 digitos (RUC).",
        )

    token = get_document_lookup_token(current_user)
    if not token:
        raise HTTPException(
            500,
            "No hay token de consulta configurado. Configure DNIRUC_TOKEN o el token del tenant.",
        )

    url = f"{settings.DNIRUC_API_URL}/{tipo}/{numero}"

    try:
        response = requests.get(url, params={"token": token}, timeout=10)
        if response.status_code != 200:
            raise HTTPException(
                502,
                "El servicio de consulta documental respondio con error.",
            )

        data = response.json()
        if data.get("success") is False:
            raise HTTPException(
                404,
                data.get("message", "Documento no encontrado en RENIEC/SUNAT."),
            )

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
                "capital": data.get("capital", ""),
            }

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
            "condicion": "HABIDO",
        }
    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        raise HTTPException(504, "Tiempo de espera agotado al consultar RENIEC/SUNAT.")
    except requests.exceptions.ConnectionError:
        raise HTTPException(503, "No se pudo conectar con el servicio de consulta.")
    except Exception as exc:
        raise_internal_server_error(
            "consultar_documento",
            "Error interno al consultar el documento.",
            exc,
        )


@router.get("/consultar-documento/{numero}")
def consultar_documento(
    numero: str,
    current_user: models.User = Depends(get_current_user),
):
    return _consultar_documento(numero, current_user)


@router.get("/consultar-ruc/{numero}")
def consultar_ruc_legacy(
    numero: str,
    current_user: models.User = Depends(get_current_user),
):
    return _consultar_documento(numero, current_user)


@router.get("/clientes/", response_model=List[schemas.ClienteResponse])
def read_clientes(
    skip: int = 0,
    limit: int = 100,
    q: Optional[str] = Query(default=None, description="Búsqueda por nombre, documento o contacto"),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """Lista clientes del tenant. Soporta búsqueda por ?q=término."""
    return crud.get_clientes(db, current_user.tenant_id, skip, limit, q=q)


# ============================================================
# FASE 8: IMPORTACIÓN MASIVA DE CLIENTES
# IMPORTANTE: Estas rutas literales deben declararse ANTES de
# /clientes/{cliente_id} para que FastAPI no las confunda con IDs.
# ============================================================

_IMPORT_ALLOWED_EXTENSIONS = {"csv", "xlsx"}
_IMPORT_ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",
}
_IMPORT_MAX_SIZE = 2 * 1024 * 1024  # 2 MB


@router.get(
    "/clientes/plantilla-importacion",
    summary="Descargar plantilla CSV para importar clientes",
)
def descargar_plantilla_clientes():
    """
    Descarga una plantilla CSV de ejemplo con todas las columnas admitidas.
    Úsala como base para preparar tu archivo de importación masiva.
    """
    header = (
        "numero_documento,razon_social,tipo_documento,nombre_comercial,"
        "direccion,email,telefono,whatsapp,contacto,condicion_pago,"
        "direccion_entrega,observaciones"
    )
    ejemplo_ruc = (
        "20100100100,Empresa Ejemplo SAC,6,Ejemplo SA,"
        "Av. Lima 123 Lima,contacto@ejemplo.com,01-2345678,987654321,"
        "Juan Pérez,contado,Av. Lima 123 Almacén,Importado via plantilla"
    )
    ejemplo_dni = (
        "12345678,García Pérez Juan,1,,"
        ",,,987000000,,,,Persona natural"
    )
    content = "\n".join([header, ejemplo_ruc, ejemplo_dni]) + "\n"
    return Response(
        content=content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=plantilla_clientes.csv"},
    )


@router.post(
    "/clientes/importar",
    response_model=schemas.ImportResultResponse,
    summary="Importar clientes desde CSV o Excel",
)
async def importar_clientes(
    file: UploadFile = File(..., description="Archivo CSV o Excel (.xlsx)"),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """
    Importa clientes masivamente desde un archivo CSV o Excel (.xlsx).

    Columnas requeridas: numero_documento, razon_social
    Columnas opcionales: tipo_documento, nombre_comercial, direccion, email,
                         telefono, whatsapp, contacto, condicion_pago,
                         direccion_entrega, observaciones

    - Los clientes con numero_documento duplicado en el tenant se omiten.
    - Los errores por fila se reportan sin interrumpir el resto.
    - Descarga la plantilla con GET /clientes/plantilla-importacion.
    """
    ext, raw_bytes = await read_validated_upload(
        file,
        allowed_extensions=_IMPORT_ALLOWED_EXTENSIONS,
        allowed_content_types=_IMPORT_ALLOWED_CONTENT_TYPES,
        max_size_bytes=_IMPORT_MAX_SIZE,
    )

    validas, errores_parse = parse_clientes(ext, raw_bytes)

    importados = 0
    omitidos = 0
    for fila in validas:
        existente = (
            db.query(models.Cliente)
            .filter(
                models.Cliente.tenant_id == current_user.tenant_id,
                models.Cliente.numero_documento == fila.numero_documento,
            )
            .first()
        )
        if existente:
            omitidos += 1
            continue

        cliente_data = schemas.ClienteCreate(
            tipo_documento=fila.tipo_documento,
            numero_documento=fila.numero_documento,
            razon_social=fila.razon_social,
            nombre_comercial=fila.nombre_comercial,
            direccion=fila.direccion,
            email=fila.email,
            telefono=fila.telefono,
            whatsapp=fila.whatsapp,
            contacto=fila.contacto,
            condicion_pago=fila.condicion_pago,
            direccion_entrega=fila.direccion_entrega,
            observaciones=fila.observaciones,
        )
        crud.create_cliente(db, cliente_data, current_user.tenant_id)
        importados += 1

    return schemas.ImportResultResponse(
        importados=importados,
        omitidos=omitidos,
        errores=[schemas.ImportErrorDetail(**e) for e in errores_parse],
    )


# ============================================================
# CRUD ESTÁNDAR (rutas con {id} van DESPUÉS de las literales)
# ============================================================

@router.get("/clientes/{cliente_id}", response_model=schemas.ClienteResponse)
def read_cliente(
    cliente_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """Obtiene un cliente por ID."""
    result = crud.get_cliente_for_tenant(db, cliente_id, current_user.tenant_id)
    if not result:
        raise HTTPException(404, "Cliente no encontrado")
    return result


@router.post("/clientes/", response_model=schemas.ClienteResponse, status_code=201)
def create_cliente(
    cliente: schemas.ClienteCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    return crud.create_cliente(db, cliente, current_user.tenant_id)


@router.put("/clientes/{cliente_id}", response_model=schemas.ClienteResponse)
def update_cliente(
    cliente_id: int,
    cliente: schemas.ClienteCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """Actualización completa del cliente (PUT). Todos los campos requeridos."""
    result = crud.update_cliente(db, cliente_id, cliente, current_user.tenant_id)
    if not result:
        raise HTTPException(404, "Cliente no encontrado")
    return result


@router.patch("/clientes/{cliente_id}", response_model=schemas.ClienteResponse)
def patch_cliente(
    cliente_id: int,
    updates: schemas.ClienteUpdate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """Actualización parcial del cliente (PATCH). Solo campos enviados."""
    result = crud.patch_cliente(
        db,
        cliente_id,
        updates.model_dump(exclude_unset=True),
        current_user.tenant_id,
    )
    if not result:
        raise HTTPException(404, "Cliente no encontrado")
    return result


@router.delete("/clientes/{cliente_id}")
def delete_cliente(
    cliente_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    result = crud.delete_cliente(db, cliente_id, current_user.tenant_id)
    if not result:
        raise HTTPException(404, "Cliente no encontrado")
    return {"msg": "Eliminado"}
