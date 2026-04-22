from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

import crud
import models
import schemas
from api_dependencies import get_current_user, get_db_tenant
from api_utils import read_validated_upload
from services.import_service import parse_productos

router = APIRouter(tags=["productos"])


@router.get("/productos/", response_model=List[schemas.ProductoResponse])
def read_productos(
    skip: int = 0,
    limit: int = 100,
    q: Optional[str] = Query(default=None, description="Búsqueda por nombre, código o descripción"),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """Lista productos del catálogo. Soporta búsqueda por ?q=término."""
    return crud.get_productos(db, current_user.tenant_id, skip, limit, q=q)


@router.get("/productos/count")
def count_productos(
    q: Optional[str] = Query(default=None),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """Retorna el total de productos del tenant (para paginación)."""
    return {"total": crud.count_productos(db, current_user.tenant_id, q=q)}


# ============================================================
# FASE 8: IMPORTACIÓN MASIVA DE PRODUCTOS
# IMPORTANTE: Estas rutas literales deben declararse ANTES de
# /productos/{producto_id} para que FastAPI no las confunda con IDs.
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
    "/productos/plantilla-importacion",
    summary="Descargar plantilla CSV para importar productos",
)
def descargar_plantilla_productos():
    """
    Descarga una plantilla CSV de ejemplo con todas las columnas admitidas.
    Úsala como base para preparar tu archivo de importación masiva.
    """
    header = (
        "nombre,precio_unitario,precio_incluye_igv,codigo_interno,descripcion,"
        "unidad_medida,tipo_afectacion_igv"
    )
    ejemplo1 = (
        "Impresión A4 Full Color,5.90,true,IMP-A4-FC,"
        "Impresión a color en papel A4 80gr,NIU,10"
    )
    ejemplo2 = (
        "Plastificado Mate A4,2.12,false,PLAST-A4,"
        "Laminado mate tamaño A4,NIU,10"
    )
    ejemplo3 = (
        "Diseño Gráfico por hora,80.00,true,DIS-HR,"
        "Servicio de diseño gráfico por hora,ZZ,10"
    )
    content = "\n".join([header, ejemplo1, ejemplo2, ejemplo3]) + "\n"
    response = Response(
        content=content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=plantilla_productos.csv"},
    )
    response.headers["Cache-Control"] = "public, max-age=86400"  # 24h
    return response


@router.post(
    "/productos/importar",
    response_model=schemas.ImportResultResponse,
    summary="Importar productos desde CSV o Excel",
)
async def importar_productos(
    file: UploadFile = File(..., description="Archivo CSV o Excel (.xlsx)"),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """
    Importa productos masivamente desde un archivo CSV o Excel (.xlsx).

    Columnas requeridas: nombre, precio_unitario
    Columnas opcionales: precio_incluye_igv, codigo_interno, descripcion, unidad_medida, tipo_afectacion_igv

    - Los productos con nombre duplicado en el tenant se omiten.
    - Los errores por fila se reportan sin interrumpir el resto.
    - Descarga la plantilla con GET /productos/plantilla-importacion.
    """
    ext, raw_bytes = await read_validated_upload(
        file,
        allowed_extensions=_IMPORT_ALLOWED_EXTENSIONS,
        allowed_content_types=_IMPORT_ALLOWED_CONTENT_TYPES,
        max_size_bytes=_IMPORT_MAX_SIZE,
    )

    validas, errores_parse = parse_productos(ext, raw_bytes)

    importados = 0
    omitidos = 0
    for fila in validas:
        existente = (
            db.query(models.Producto)
            .filter(
                models.Producto.tenant_id == current_user.tenant_id,
                models.Producto.nombre == fila.nombre,
            )
            .first()
        )
        if existente:
            omitidos += 1
            continue

        producto_data = schemas.ProductoCreate(
            nombre=fila.nombre,
            precio_unitario=fila.precio_unitario,
            precio_incluye_igv=fila.precio_incluye_igv,
            codigo_interno=fila.codigo_interno,
            descripcion=fila.descripcion,
            unidad_medida=fila.unidad_medida,
            tipo_afectacion_igv=fila.tipo_afectacion_igv,
        )
        crud.create_producto(db, producto_data, current_user.tenant_id)
        importados += 1

    return schemas.ImportResultResponse(
        importados=importados,
        omitidos=omitidos,
        errores=[schemas.ImportErrorDetail(**e) for e in errores_parse],
    )


@router.get(
    "/productos/codigo-sugerido",
    summary="Genera un código único para un nuevo producto",
)
def codigo_sugerido(
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """Devuelve un codigo_interno aleatorio que no existe en el tenant."""
    import secrets
    for _ in range(8):
        candidate = f"PROD-{secrets.token_hex(3).upper()}"
        exists = (
            db.query(models.Producto)
            .filter(
                models.Producto.tenant_id == current_user.tenant_id,
                models.Producto.codigo_interno == candidate,
            )
            .first()
        )
        if not exists:
            return {"codigo": candidate}
    raise HTTPException(500, "No se pudo generar un código único. Ingrésalo manualmente.")


# ============================================================
# CRUD ESTÁNDAR (rutas con {id} van DESPUÉS de las literales)
# ============================================================

@router.get("/productos/{producto_id}", response_model=schemas.ProductoResponse)
def read_producto(
    producto_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """Obtiene un producto por ID."""
    result = crud.get_producto_for_tenant(db, producto_id, current_user.tenant_id)
    if not result:
        raise HTTPException(404, "Producto no encontrado")
    return result


@router.post("/productos/", response_model=schemas.ProductoResponse, status_code=201)
def create_producto(
    producto: schemas.ProductoCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    return crud.create_producto(db, producto, current_user.tenant_id)


@router.put("/productos/{producto_id}", response_model=schemas.ProductoResponse)
def update_producto(
    producto_id: int,
    producto: schemas.ProductoCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    result = crud.update_producto(db, producto_id, producto, current_user.tenant_id)
    if not result:
        raise HTTPException(404, "Producto no encontrado")
    return result


@router.delete("/productos/{producto_id}")
def delete_producto(
    producto_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    result = crud.delete_producto(db, producto_id, current_user.tenant_id)
    if not result:
        raise HTTPException(404, "Producto no encontrado")
    return {"msg": "Eliminado"}
