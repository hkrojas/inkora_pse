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
    UsageLimit,
    SUBSCRIPTION_STATUS_ACTIVE,
    SUBSCRIPTION_STATUS_SUSPENDED,
    SUBSCRIPTION_STATUS_TRIAL,
    SUBSCRIPTION_STATUS_EXPIRED,
    SUBSCRIPTION_STATUS_CANCELLED,
    ONBOARDING_STATUS_NOT_STARTED,
    ONBOARDING_STATUS_IN_PROGRESS,
    ONBOARDING_STATUS_COMPLETED,
    USAGE_LIMIT_KIND_FACTURA,
    USAGE_LIMIT_KIND_BOLETA,
    USAGE_LIMIT_KIND_GUIA,
    USAGE_LIMIT_KIND_NOTA_CREDITO,
    USAGE_LIMIT_KIND_NOTA_DEBITO,
    USAGE_LIMIT_KINDS,
    USAGE_LIMIT_PERIOD_MONTH,
    USAGE_LIMIT_PERIOD_DAY,
    USAGE_LIMIT_PERIOD_TOTAL,
    USAGE_LIMIT_PERIODS,
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
from models.emission_jobs import (
    DocumentEmissionJob,
    EMISSION_JOB_STATUS_QUEUED,
    EMISSION_JOB_STATUS_PROCESSING,
    EMISSION_JOB_STATUS_RETRY,
    EMISSION_JOB_STATUS_SUCCEEDED,
    EMISSION_JOB_STATUS_FAILED,
    EMISSION_JOB_ACTION_EMIT_FISCAL,
    EMISSION_JOB_ACTION_EMIT_NOTE,
    EMISSION_JOB_ACTION_VOID_FISCAL,
    EMISSION_JOB_ACTION_EMIT_GUIDE,
    EMISSION_JOB_RESOURCE_COTIZACION,
    EMISSION_JOB_RESOURCE_GUIA,
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
    "UsageLimit",
    "USAGE_LIMIT_KIND_FACTURA",
    "USAGE_LIMIT_KIND_BOLETA",
    "USAGE_LIMIT_KIND_GUIA",
    "USAGE_LIMIT_KIND_NOTA_CREDITO",
    "USAGE_LIMIT_KIND_NOTA_DEBITO",
    "USAGE_LIMIT_KINDS",
    "USAGE_LIMIT_PERIOD_MONTH",
    "USAGE_LIMIT_PERIOD_DAY",
    "USAGE_LIMIT_PERIOD_TOTAL",
    "USAGE_LIMIT_PERIODS",
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
    "DocumentEmissionJob",
    "EMISSION_JOB_STATUS_QUEUED",
    "EMISSION_JOB_STATUS_PROCESSING",
    "EMISSION_JOB_STATUS_RETRY",
    "EMISSION_JOB_STATUS_SUCCEEDED",
    "EMISSION_JOB_STATUS_FAILED",
    "EMISSION_JOB_ACTION_EMIT_FISCAL",
    "EMISSION_JOB_ACTION_EMIT_NOTE",
    "EMISSION_JOB_ACTION_VOID_FISCAL",
    "EMISSION_JOB_ACTION_EMIT_GUIDE",
    "EMISSION_JOB_RESOURCE_COTIZACION",
    "EMISSION_JOB_RESOURCE_GUIA",
    # frozen / MRP
    "Insumo",
    "RecetaBOM",
    "Proveedor",
    "OrdenProduccion",
    "OrdenProduccionDetalle",
    "AlertaInventario",
]
