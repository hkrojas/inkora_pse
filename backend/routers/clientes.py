from typing import List, Optional

import httpx
from cachetools import TTLCache
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

import crud
import models
import schemas
from api_dependencies import get_current_user, get_db_tenant
from api_utils import raise_internal_server_error, read_validated_upload
from config import settings
from rate_limit import limiter
from services.import_service import parse_clientes
from tenant_access import get_document_lookup_token

router = APIRouter(tags=["clientes"])

# Cache de resultados DNI/RUC: clave=(numero, token_hash), TTL=2h, max 500 entradas.
# Evita llamadas repetidas a ApísPeru para el mismo documento.
_doc_cache: TTLCache = TTLCache(maxsize=500, ttl=7200)


def _extract_provider_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict):
        for key in ("message", "error", "detail"):
            value = payload.get(key)
            if value:
                return str(value)
    text = (response.text or "").strip()
    if text:
        return text[:200]
    return f"HTTP {response.status_code}"


def _build_ruc_result(data: dict, numero: str) -> dict:
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


def _build_dni_result(data: dict, numero: str) -> dict:
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


async def _consultar_documento(numero: str, current_user: models.User):
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

    cache_key = (numero, token[-8:])
    cached = _doc_cache.get(cache_key)
    if cached is not None:
        return cached

    url = f"{settings.DNIRUC_API_URL}/{tipo}/{numero}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params={"token": token})

        if response.status_code != 200:
            provider_detail = _extract_provider_detail(response)
            raise HTTPException(
                502,
                f"El servicio de consulta documental respondio con error ({response.status_code}): {provider_detail}",
            )

        data = response.json()
        if data.get("success") is False:
            raise HTTPException(
                404,
                data.get("message", "Documento no encontrado en RENIEC/SUNAT."),
            )

        result = _build_ruc_result(data, numero) if tipo == "ruc" else _build_dni_result(data, numero)
        _doc_cache[cache_key] = result
        return result

    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(504, "Tiempo de espera agotado al consultar RENIEC/SUNAT.")
    except httpx.ConnectError:
        raise HTTPException(503, "No se pudo conectar con el servicio de consulta.")
    except Exception as exc:
        raise_internal_server_error(
            "consultar_documento",
            "Error interno al consultar el documento.",
            exc,
        )


@router.get("/consultar-documento/{numero}")
@limiter.limit("30/minute")
async def consultar_documento(
    request: Request,
    numero: str,
    current_user: models.User = Depends(get_current_user),
):
    return await _consultar_documento(numero, current_user)


@router.get("/consultar-ruc/{numero}")
@limiter.limit("30/minute")
async def consultar_ruc_legacy(
    request: Request,
    numero: str,
    current_user: models.User = Depends(get_current_user),
):
    return await _consultar_documento(numero, current_user)


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


@router.get("/clientes/count")
def count_clientes(
    q: Optional[str] = Query(default=None),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """Retorna el total de clientes del tenant (para paginación)."""
    return {"total": crud.count_clientes(db, current_user.tenant_id, q=q)}


def _cliente_search_filter(q: Optional[str]):
    if not q or not q.strip():
        return None
    term = f"%{q.strip()}%"
    return or_(
        models.Cliente.razon_social.ilike(term),
        models.Cliente.nombre_comercial.ilike(term),
        models.Cliente.numero_documento.ilike(term),
        models.Cliente.email.ilike(term),
        models.Cliente.telefono.ilike(term),
        models.Cliente.whatsapp.ilike(term),
    )


def _cliente_segment_filter(segment: Optional[str]):
    normalized = (segment or "all").strip().lower()
    if normalized == "empresa":
        return or_(
            models.Cliente.tipo_documento == "6",
            func.length(models.Cliente.numero_documento) == 11,
        )
    if normalized == "persona":
        return and_(
            models.Cliente.tipo_documento != "6",
            func.length(models.Cliente.numero_documento) != 11,
        )
    if normalized == "credito":
        return and_(
            models.Cliente.condicion_pago.isnot(None),
            models.Cliente.condicion_pago != "",
            models.Cliente.condicion_pago != "contado",
        )
    if normalized == "incompletos":
        return or_(
            models.Cliente.email.is_(None),
            models.Cliente.email == "",
            and_(
                or_(models.Cliente.telefono.is_(None), models.Cliente.telefono == ""),
                or_(models.Cliente.whatsapp.is_(None), models.Cliente.whatsapp == ""),
            ),
            models.Cliente.condicion_pago.is_(None),
            models.Cliente.condicion_pago == "",
        )
    return None


@router.get("/clientes/page", response_model=schemas.ClientePageResponse)
def read_clientes_page(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=100),
    q: Optional[str] = Query(default=None, max_length=80),
    segment: Optional[str] = Query(default="all", pattern="^(all|empresa|persona|credito|incompletos)$"),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    base = db.query(models.Cliente).filter(models.Cliente.tenant_id == current_user.tenant_id)
    search_filter = _cliente_search_filter(q)
    if search_filter is not None:
        base = base.filter(search_filter)

    def count_for(filter_expr=None) -> int:
        query = base.with_entities(func.count(models.Cliente.id))
        if filter_expr is not None:
            query = query.filter(filter_expr)
        return query.scalar() or 0

    counts = {
        "all": count_for(),
        "empresa": count_for(_cliente_segment_filter("empresa")),
        "persona": count_for(_cliente_segment_filter("persona")),
        "credito": count_for(_cliente_segment_filter("credito")),
        "incompletos": count_for(_cliente_segment_filter("incompletos")),
    }

    page_query = base
    segment_filter = _cliente_segment_filter(segment)
    if segment_filter is not None:
        page_query = page_query.filter(segment_filter)
    total = page_query.with_entities(func.count(models.Cliente.id)).scalar() or 0
    items = page_query.order_by(models.Cliente.razon_social).offset(skip).limit(limit).all()
    return {"items": items, "total": total, "skip": skip, "limit": limit, "counts": counts}


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
    response = Response(
        content=content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=plantilla_clientes.csv"},
    )
    response.headers["Cache-Control"] = "public, max-age=86400"  # 24h
    return response


@router.post(
    "/clientes/importar",
    response_model=schemas.ImportResultResponse,
    summary="Importar clientes desde CSV o Excel",
)
@limiter.limit("10/minute")
async def importar_clientes(
    request: Request,
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

    validas, errores_parse = await run_in_threadpool(parse_clientes, ext, raw_bytes)

    importados = 0
    omitidos = 0
    documentos = [fila.numero_documento for fila in validas if fila.numero_documento]
    existentes = set()
    if documentos:
        existentes = {
            value
            for (value,) in db.query(models.Cliente.numero_documento)
            .filter(
                models.Cliente.tenant_id == current_user.tenant_id,
                models.Cliente.numero_documento.in_(documentos),
            )
            .all()
        }

    vistos_archivo = set()
    nuevos = []
    for fila in validas:
        if fila.numero_documento in existentes or fila.numero_documento in vistos_archivo:
            omitidos += 1
            continue
        vistos_archivo.add(fila.numero_documento)

        nuevos.append(schemas.ClienteCreate(
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
        ))

    if nuevos:
        crud.create_clientes_bulk(db, nuevos, current_user.tenant_id)
        importados = len(nuevos)

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
