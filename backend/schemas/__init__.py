"""
schemas/__init__.py — Re-exporta todo el namespace de schemas de forma plana.

Todos los módulos del paquete son accesibles via `import schemas; schemas.X`
sin cambiar ningún caller externo.
"""

from schemas._base import StrictInputModel

from schemas.tenants import (
    TenantBase,
    TenantCreate,
    TenantUpdate,
    TenantAdminUpdate,
    TenantSummaryResponse,
    TenantResponse,
    TenantSaaSUpdate,
    SuperadminTenantCreate,
    SuperadminTenantResponse,
    ApisPeruTokenValidationRequest,
    ApisPeruTokenValidationResponse,
)

from schemas.auth import (
    UserIdentity,
    UserRegisterRequest,
    UserUpdateProfile,
    UserAdminUpdate,
    SuperadminUserCreate,
    UserResponse,
    Token,
    TokenData,
)

from schemas.clientes import (
    CONDICION_PAGO_VALORES,
    ClienteBase,
    ClienteCreate,
    ClienteUpdate,
    ClienteResponse,
)

from schemas.productos import (
    ProductoBase,
    ProductoCreate,
    ProductoResponse,
    InsumoBase,
    InsumoCreate,
    InsumoResponse,
    RecetaBOMBase,
    RecetaBOMCreate,
    RecetaBOMResponse,
    AlertaInventarioResponse,
    DashboardStatsResponse,
    ProveedorBase,
    ProveedorCreate,
    ProveedorUpdate,
    ProveedorResponse,
    OrdenProduccionDetalleResponse,
    OrdenProduccionResponse,
)

from schemas.cotizaciones import (
    CotizacionItemCreate,
    CotizacionItemResponse,
    CotizacionCreate,
    CotizacionResponse,
    PagoCreate,
    PagoResponse,
    CobranzaResumenResponse,
    CobranzaVencidaItem,
    FacturarPayload,
    NotaCreate,
    AnulacionCreate,
    DescargaArchivoPayload,
)

from schemas.guias import (
    GuiaRemisionItemCreate,
    GuiaRemisionCreate,
    GuiaRemisionItemResponse,
    EtiquetaGuiaResponse,
    GuiaRemisionResponse,
)

from schemas.ai import (
    AIItemCotizacion,
    AIParsedCotizacionResponse,
    AIInsumoFactura,
    AIParsedFacturaResponse,
)

from schemas.subscriptions import (
    SubscriptionResponse,
    SubscriptionPaymentCreate,
    SubscriptionPaymentResponse,
    ActivateTenantRequest,
    SuspendTenantRequest,
    ExtendAccessRequest,
    SetFounderPricingRequest,
    UpdateSubscriptionRequest,
    SuperadminTenantDetailResponse,
    UpdateNotasRequest,
    TenantActividadResponse,
    BetaTenantSummary,
)

from schemas.onboarding import (
    ImportErrorDetail,
    ImportResultResponse,
    OnboardingChecklistItem,
    OnboardingEstadoResponse,
)

__all__ = [
    "StrictInputModel",
    # tenants
    "TenantBase", "TenantCreate", "TenantUpdate", "TenantSummaryResponse",
    "TenantResponse", "TenantSaaSUpdate", "SuperadminTenantCreate", "SuperadminTenantResponse",
    "ApisPeruTokenValidationRequest", "ApisPeruTokenValidationResponse",
    # auth
    "UserIdentity", "UserRegisterRequest", "UserUpdateProfile", "UserAdminUpdate",
    "SuperadminUserCreate", "UserResponse", "Token", "TokenData",
    # clientes
    "CONDICION_PAGO_VALORES", "ClienteBase", "ClienteCreate", "ClienteUpdate", "ClienteResponse",
    # productos + MRP
    "ProductoBase", "ProductoCreate", "ProductoResponse",
    "InsumoBase", "InsumoCreate", "InsumoResponse",
    "RecetaBOMBase", "RecetaBOMCreate", "RecetaBOMResponse",
    "AlertaInventarioResponse", "DashboardStatsResponse",
    "ProveedorBase", "ProveedorCreate", "ProveedorUpdate", "ProveedorResponse",
    "OrdenProduccionDetalleResponse", "OrdenProduccionResponse",
    # cotizaciones + pagos
    "CotizacionItemCreate", "CotizacionItemResponse", "CotizacionCreate", "CotizacionResponse",
    "PagoCreate", "PagoResponse",
    "CobranzaResumenResponse", "CobranzaVencidaItem",
    "FacturarPayload", "NotaCreate", "AnulacionCreate", "DescargaArchivoPayload",
    # guias
    "GuiaRemisionItemCreate", "GuiaRemisionCreate", "GuiaRemisionItemResponse",
    "EtiquetaGuiaResponse", "GuiaRemisionResponse",
    # ai
    "AIItemCotizacion", "AIParsedCotizacionResponse",
    "AIInsumoFactura", "AIParsedFacturaResponse",
    # subscriptions / superadmin / beta
    "SubscriptionResponse", "SubscriptionPaymentCreate", "SubscriptionPaymentResponse",
    "ActivateTenantRequest", "SuspendTenantRequest", "ExtendAccessRequest",
    "SetFounderPricingRequest", "UpdateSubscriptionRequest", "SuperadminTenantDetailResponse",
    "UpdateNotasRequest", "TenantActividadResponse", "BetaTenantSummary",
    # onboarding
    "ImportErrorDetail", "ImportResultResponse",
    "OnboardingChecklistItem", "OnboardingEstadoResponse",
]
