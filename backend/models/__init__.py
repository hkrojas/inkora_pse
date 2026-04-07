"""
models/__init__.py — Re-exporta todo el namespace de modelos de forma plana.

Importar todos los submódulos aquí garantiza que SQLAlchemy registre todas las
clases en el mapper registry antes de la primera consulta, resolviendo los
string-references en relationship("ClassName", ...).
"""

from database import Base

from models.tenants import (
    Tenant,
    User,
    AuditLog,
    Subscription,
    SubscriptionPayment,
    SUBSCRIPTION_STATUS_ACTIVE,
    SUBSCRIPTION_STATUS_SUSPENDED,
    SUBSCRIPTION_STATUS_TRIAL,
    SUBSCRIPTION_STATUS_EXPIRED,
    SUBSCRIPTION_STATUS_CANCELLED,
    ONBOARDING_STATUS_NOT_STARTED,
    ONBOARDING_STATUS_IN_PROGRESS,
    ONBOARDING_STATUS_COMPLETED,
)

from models.clientes import Cliente

from models.productos import Producto

from models.cotizaciones import Cotizacion, CotizacionItem

from models.guias import GuiaRemision, GuiaRemisionItem

from models.pagos import Pago

from models.frozen import (
    Insumo,
    RecetaBOM,
    Proveedor,
    OrdenProduccion,
    OrdenProduccionDetalle,
    AlertaInventario,
)

__all__ = [
    "Base",
    # tenants
    "Tenant",
    "User",
    "AuditLog",
    "Subscription",
    "SubscriptionPayment",
    "SUBSCRIPTION_STATUS_ACTIVE",
    "SUBSCRIPTION_STATUS_SUSPENDED",
    "SUBSCRIPTION_STATUS_TRIAL",
    "SUBSCRIPTION_STATUS_EXPIRED",
    "SUBSCRIPTION_STATUS_CANCELLED",
    "ONBOARDING_STATUS_NOT_STARTED",
    "ONBOARDING_STATUS_IN_PROGRESS",
    "ONBOARDING_STATUS_COMPLETED",
    # clientes
    "Cliente",
    # productos
    "Producto",
    # cotizaciones
    "Cotizacion",
    "CotizacionItem",
    # guias
    "GuiaRemision",
    "GuiaRemisionItem",
    # pagos
    "Pago",
    # frozen / MRP
    "Insumo",
    "RecetaBOM",
    "Proveedor",
    "OrdenProduccion",
    "OrdenProduccionDetalle",
    "AlertaInventario",
]
