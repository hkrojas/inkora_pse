"""
routers/legacy_frozen.py — DOMINIOS CONGELADOS

Este router agrupa endpoints de dominios NO pertenecientes al launch scope.
Están mantenidos por compatibilidad y porque los modelos/datos ya existen,
pero NO deben expandirse ni profundizarse comercialmente sin instrucción explícita.

Dominios congelados aquí:
  - proveedores    : catálogo de proveedores/talleres externos (Broker)
  - insumos        : materia prima / inventario de insumos
  - BOM / recetas  : lista de materiales por producto (MRP ligero)
  - órdenes de producción : motor MRP, descuento de stock, outsourcing
  - alertas de inventario : alertas de quiebre de stock (ligadas a Insumo)
  - AI             : parsing de texto/imagen con Gemini (feature premium futuro)

REGLAS:
  - No agregar nuevos endpoints aquí sin instrucción explícita.
  - No expandir la lógica de negocio de estos dominios.
  - Si un dominio se decide activar como feature de launch o premium,
    moverlo a su propio router dedicado (ej: routers/mrp.py, routers/ai.py).
  - Todos los endpoints están marcados deprecated=True en OpenAPI para
    dejar claro que no forman parte del flujo de launch actual.

Dominio movido a launch scope (Fase 10):
  - GET /analytics/dashboard → routers/dashboard.py
"""

from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

import crud
import models
import schemas
from api_dependencies import get_current_user, get_db_tenant
from api_utils import log_unexpected_error, raise_internal_server_error, read_validated_upload
from config import settings
from database import SessionLocal, apply_tenant_context, reset_tenant_context

router = APIRouter(tags=["frozen-non-launch"])


# ============================================================
# PROVEEDORES — Dominio congelado: catálogo de talleres externos
# ============================================================

@router.get(
    "/proveedores/",
    response_model=List[schemas.ProveedorResponse],
    deprecated=True,
    summary="[FROZEN] Listar proveedores/talleres",
)
def listar_proveedores(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """
    DOMINIO CONGELADO. Catálogo de proveedores/talleres tercerizados.
    No forma parte del launch workflow actual.
    Se mantiene para tenants que ya tienen datos cargados.
    """
    return crud.get_proveedores(db, current_user.tenant_id, skip, limit)


@router.post(
    "/proveedores/",
    response_model=schemas.ProveedorResponse,
    deprecated=True,
    summary="[FROZEN] Crear proveedor",
)
def crear_proveedor(
    proveedor: schemas.ProveedorCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """DOMINIO CONGELADO. Registro de proveedores/talleres externos."""
    return crud.create_proveedor(db, proveedor, current_user.tenant_id)


@router.put(
    "/proveedores/{proveedor_id}",
    response_model=schemas.ProveedorResponse,
    deprecated=True,
    summary="[FROZEN] Actualizar proveedor",
)
def actualizar_proveedor(
    proveedor_id: int,
    proveedor: schemas.ProveedorUpdate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """DOMINIO CONGELADO."""
    result = crud.update_proveedor(db, proveedor_id, proveedor, current_user.tenant_id)
    if not result:
        raise HTTPException(404, "Proveedor no encontrado")
    return result


@router.delete(
    "/proveedores/{proveedor_id}",
    deprecated=True,
    summary="[FROZEN] Eliminar proveedor",
)
def eliminar_proveedor(
    proveedor_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """DOMINIO CONGELADO."""
    result = crud.delete_proveedor(db, proveedor_id, current_user.tenant_id)
    if not result:
        raise HTTPException(404, "Proveedor no encontrado")
    return {"status": "success"}


# ============================================================
# INSUMOS — Dominio congelado: inventario de materia prima
# ============================================================

@router.get(
    "/insumos/",
    response_model=List[schemas.InsumoResponse],
    deprecated=True,
    summary="[FROZEN] Listar insumos",
)
def read_insumos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """
    DOMINIO CONGELADO. Catálogo de insumos/materia prima.
    Ligado al módulo MRP que no está activo en el launch scope.
    """
    return crud.get_insumos(db, current_user.tenant_id, skip, limit)


@router.post(
    "/insumos/",
    response_model=schemas.InsumoResponse,
    deprecated=True,
    summary="[FROZEN] Crear insumo",
)
def create_insumo(
    insumo: schemas.InsumoCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """DOMINIO CONGELADO."""
    return crud.create_insumo(db, insumo, current_user.tenant_id)


@router.put(
    "/insumos/{insumo_id}",
    response_model=schemas.InsumoResponse,
    deprecated=True,
    summary="[FROZEN] Actualizar insumo",
)
def update_insumo(
    insumo_id: int,
    insumo: schemas.InsumoCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """DOMINIO CONGELADO."""
    result = crud.update_insumo(db, insumo_id, insumo, current_user.tenant_id)
    if not result:
        raise HTTPException(404, "Insumo no encontrado")
    return result


@router.delete(
    "/insumos/{insumo_id}",
    deprecated=True,
    summary="[FROZEN] Eliminar insumo",
)
def delete_insumo(
    insumo_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """DOMINIO CONGELADO."""
    result = crud.delete_insumo(db, insumo_id, current_user.tenant_id)
    if not result:
        raise HTTPException(404, "Insumo no encontrado")
    return {"msg": "Eliminado"}


# ============================================================
# BOM / RECETAS — Dominio congelado: lista de materiales
# Nota: rutas bajo /productos/{id}/ por diseño original.
# La aislación de tenant fue corregida en Fase 10.
# ============================================================

@router.get(
    "/productos/{producto_id}/bom",
    response_model=List[schemas.RecetaBOMResponse],
    deprecated=True,
    summary="[FROZEN] Ver BOM de un producto",
)
def read_bom_producto(
    producto_id: int,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """
    DOMINIO CONGELADO. Bill of Materials de un producto.
    Solo devuelve recetas de productos que pertenezcan al tenant actual.
    """
    return crud.get_recetas_producto(db, producto_id, current_user.tenant_id)


@router.post(
    "/productos/{producto_id}/bom",
    response_model=schemas.RecetaBOMResponse,
    deprecated=True,
    summary="[FROZEN] Agregar insumo a BOM",
)
def create_bom_item(
    producto_id: int,
    receta: schemas.RecetaBOMBase,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """DOMINIO CONGELADO. Agrega un insumo a la lista de materiales de un producto."""
    receta_create = schemas.RecetaBOMCreate(
        **receta.model_dump(),
        producto_id=producto_id,
    )
    return crud.create_receta_bom(db, receta_create, current_user.tenant_id)


# ============================================================
# ÓRDENES DE PRODUCCIÓN — Dominio congelado: motor MRP
# Nota: el endpoint de generación usa /cotizaciones/{id}/...
# Este acoplamiento de namespace es conocido y debe resolverse
# si el módulo MRP se activa formalmente en el futuro.
# ============================================================

class OrdenProduccionParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tipo_produccion: str = "interna"
    proveedor_id: Optional[int] = None
    costo_tercerizado: Optional[Decimal] = None


def _check_stock_background(tenant_id: int) -> None:
    """
    Tarea de fondo: verifica stock de insumos y genera alertas.
    Interna al dominio MRP — no usar fuera de este módulo.
    """
    db_bg = SessionLocal()
    tenant_token = None
    try:
        tenant_token = apply_tenant_context(db_bg, tenant_id)
        crud.verificar_stock_y_generar_alertas(db_bg, tenant_id)
    finally:
        if tenant_token is not None:
            reset_tenant_context(tenant_token)
        db_bg.close()


@router.get(
    "/ordenes-produccion",
    response_model=List[schemas.OrdenProduccionResponse],
    deprecated=True,
    summary="[FROZEN] Listar órdenes de producción",
)
def listar_ordenes_produccion(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """
    DOMINIO CONGELADO. Lista órdenes de producción/trabajo del tenant.
    Parte del módulo MRP ligero. No activo en el launch scope.
    """
    return crud.get_ordenes_produccion(db, current_user.tenant_id, skip, limit)


@router.patch(
    "/ordenes-produccion/{orden_id}/status",
    response_model=schemas.OrdenProduccionResponse,
    deprecated=True,
    summary="[FROZEN] Cambiar estado de orden de producción",
)
def update_orden_status_endpoint(
    orden_id: int,
    nuevo_estado: str,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """DOMINIO CONGELADO."""
    orden = crud.update_orden_produccion_status(
        db,
        orden_id,
        nuevo_estado,
        current_user.tenant_id,
    )
    if not orden:
        raise HTTPException(404, "Orden de produccion no encontrada.")
    return orden


@router.post(
    "/cotizaciones/{cotizacion_id}/orden-produccion",
    response_model=schemas.OrdenProduccionResponse,
    deprecated=True,
    summary="[FROZEN] Generar orden de producción desde cotización",
)
def generar_orden_produccion_endpoint(
    cotizacion_id: int,
    background_tasks: BackgroundTasks,
    params: Optional[OrdenProduccionParams] = None,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """
    DOMINIO CONGELADO. Genera una orden de trabajo/producción calculando
    los requerimientos de material según la BOM del producto.

    ACOPLAMIENTO CONOCIDO: Esta ruta usa el prefijo /cotizaciones/ del
    launch scope. Si el módulo MRP se activa formalmente, debe moverse
    a un router propio (ej: routers/mrp.py) con prefijo /mrp/.
    """
    p_tipo = params.tipo_produccion if params else "interna"
    p_prov = params.proveedor_id if params else None
    p_costo = params.costo_tercerizado if params else None

    try:
        orden = crud.generar_orden_produccion(
            db,
            cotizacion_id,
            current_user.tenant_id,
            p_tipo,
            p_prov,
            p_costo,
        )
        background_tasks.add_task(_check_stock_background, current_user.tenant_id)
        return orden
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise_internal_server_error(
            "generar_orden_produccion",
            "No se pudo generar la orden de produccion.",
            exc,
        )


# ============================================================
# ALERTAS DE INVENTARIO — Dominio congelado: stock alerts
# ============================================================

@router.get(
    "/alertas/inventario",
    response_model=List[schemas.AlertaInventarioResponse],
    deprecated=True,
    summary="[FROZEN] Ver alertas de inventario activas",
)
def read_alertas_inventario(
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """
    DOMINIO CONGELADO. Alertas de quiebre de stock generadas por el motor MRP.
    Ligado a los modelos Insumo/AlertaInventario del módulo congelado.
    """
    return (
        db.query(models.AlertaInventario)
        .filter(
            models.AlertaInventario.tenant_id == current_user.tenant_id,
            models.AlertaInventario.resuelta == False,  # noqa: E712
        )
        .order_by(models.AlertaInventario.fecha_creacion.desc())
        .all()
    )


# ============================================================
# AI — Dominio congelado: parsing con Gemini
# ============================================================

class CotizarTextoParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    texto: str


@router.post(
    "/ai/cotizar-texto",
    response_model=schemas.AIParsedCotizacionResponse,
    deprecated=True,
    summary="[FROZEN] AI: parsear texto a ítems de cotización",
)
def ai_cotizar_texto(
    params: CotizarTextoParams,
    current_user: models.User = Depends(get_current_user),
):
    """
    DOMINIO CONGELADO. Usa Gemini para extraer ítems cotizables de texto libre.
    Requiere GEMINI_API_KEY configurado. No forma parte del launch scope.
    """
    try:
        from services import ai_service
        return ai_service.analizar_texto_cotizacion(params.texto)
    except Exception as exc:
        log_unexpected_error("ai_cotizar_texto", exc)
        raise HTTPException(
            500,
            (
                "Error procesando el texto con Inteligencia Artificial. "
                "Verifique su GEMINI_API_KEY o la cuota de su servicio."
            ),
        )


@router.post(
    "/ai/leer-factura-proveedor",
    response_model=schemas.AIParsedFacturaResponse,
    deprecated=True,
    summary="[FROZEN] AI: extraer datos de factura de proveedor",
)
async def ai_leer_factura(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
):
    """
    DOMINIO CONGELADO. Usa Gemini Multimodal para extraer insumos de una
    factura de proveedor (PDF o imagen). Requiere GEMINI_API_KEY.
    No forma parte del launch scope.
    """
    try:
        from services import ai_service
        _, bytes_data = await read_validated_upload(
            file,
            allowed_extensions={"pdf", "png", "jpg", "jpeg", "webp"},
            allowed_content_types={
                "application/pdf",
                "image/png",
                "image/jpeg",
                "image/webp",
            },
            max_size_bytes=settings.MAX_AI_UPLOAD_BYTES,
        )
        return ai_service.extraer_datos_factura(
            bytes_data,
            mime_type=file.content_type,
        )
    except HTTPException:
        raise
    except Exception as exc:
        log_unexpected_error("ai_leer_factura", exc)
        raise HTTPException(
            500,
            (
                "Error procesando el documento con IA Multimodal. "
                "Verifica imagen legible y config GEMINI_API_KEY."
            ),
        )
