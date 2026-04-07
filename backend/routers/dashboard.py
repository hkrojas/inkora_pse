"""
routers/dashboard.py — Launch Scope: Simple Dashboard

Endpoint de dashboard simple para el tenant autenticado.
Forma parte del launch scope (Fase 6/7 del roadmap).

NOTA: Este router fue extraído de legacy_frozen.py en la Fase 10 porque
el dashboard es un feature explícito del launch product. Su implementación
utiliza modelos de launch scope (Cotizacion, Pago, Producto) más un campo
de orden de producción (costos_tercerizacion) que devuelve 0 si no existe.
No requiere que el módulo MRP esté activo para funcionar correctamente.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import crud
import models
import schemas
from api_dependencies import get_current_user, get_db_tenant

router = APIRouter(tags=["dashboard"])


@router.get(
    "/analytics/dashboard",
    response_model=schemas.DashboardStatsResponse,
    summary="Estadísticas del dashboard del tenant",
)
def read_dashboard_stats(
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """
    Devuelve las métricas principales para el dashboard del tenant:

    - ingresos_totales: suma de todos los pagos registrados
    - saldos_por_cobrar: saldo pendiente de cotizaciones activas
    - saldo_vencido: saldo de documentos con fecha de vencimiento pasada
    - documentos_emitidos_mes: facturas/boletas emitidas en el mes actual
    - documentos_vencidos: documentos con saldo sin cobrar y fecha pasada
    - top_productos: 5 productos más vendidos por volumen
    - costos_tercerizacion: suma de costos de producción tercerizada
      (retorna 0.00 si el módulo MRP no está en uso)
    """
    return crud.get_dashboard_stats(db, current_user.tenant_id)
