"""
schemas/__init__.py — Re-exporta todo el namespace de schemas de forma plana.

Todos los módulos del paquete son accesibles via `import schemas; schemas.X`
sin cambiar ningún caller externo.
"""

from schemas._base import StrictInputModel
from schemas.productos import ProductoInventarioInicial
from schemas.access_requests import (
    AccessRequestCreate, AccessRequestCreated, AccessRequestRucLookup,
    AccessRequestStatusLookup, AccessRequestPublicStatus, AccessRequestReview,
    AccessRequestAdminResponse, AccessRequestPageResponse,
)
from schemas.catalog import (
    CatalogEntitlementUpdate,
    CatalogThemeConfig,
    CatalogSiteCreate,
    CatalogSiteUpdate,
    CatalogCategoryCreate,
    CatalogItemCreate,
    CatalogCollectionCreate,
    CatalogCollectionItemsUpdate,
    CatalogItemAssetsUpdate,
    CatalogEntitlementResponse,
    CatalogSiteResponse,
    CatalogItemResponse,
    CatalogPublicItemResponse,
    normalize_catalog_slug,
)

from schemas.tenants import (
    TenantBase,
    TenantCreate,
    TenantUpdate,
    TenantAdminUpdate,
    TenantSummaryResponse,
    TenantResponse,
    TenantSaaSUpdate,
    TenantFiscalSeriesUpdate,
    SuperadminTenantCreate,
    SuperadminTenantResponse,
    ApisPeruTokenValidationRequest,
    ApisPeruTokenValidationResponse,
    SmartPSECredentialsValidationRequest,
    SmartPSECredentialsValidationResponse,
    SmartPSEProvisionRequest,
    SmartPSECompanyCreate,
    SmartPSECompanyUpdate,
    SmartPSETenantCredentialsUpdate,
    SmartPSECompanyResponse,
    SmartPSECompanyPageResponse,
    SmartPSESyncAllResponse,
    SmartPSEDeleteResponse,
    SmartPSEGreCredentialsUpdate,
    SmartPSEGreCredentialsValidationResponse,
    SuperadminTenantPageMetrics,
    SuperadminTenantPageResponse,
    EmissionErrorResponse,
    TokenHealthResponse,
    FiscalContingencyUpdate,
    FiscalContingencyResponse,
)

from schemas.auth import (
    UserIdentity,
    UserRegisterRequest,
    UserUpdateProfile,
    UserAdminUpdate,
    SuperadminTenantUserUpdate,
    SuperadminUserCreate,
    UserResponse,
    UserMetrics,
    UserDetailResponse,
    ResetPasswordResponse,
    ToggleUserActiveRequest,
    Token,
    TokenData,
    ChangePasswordRequest,
    CreateUserWithPasswordResponse,
)

from schemas.clientes import (
    CONDICION_PAGO_VALORES,
    ClienteBase,
    ClienteCreate,
    ClienteUpdate,
    ClienteResponse,
    ClienteSearchResponse,
    ClientePageResponse,
)

from schemas.productos import (
    ProductoBase,
    ProductoCreate,
    ProductoResponse,
    ProductoSearchResponse,
    ProductoPageResponse,
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
    CuotaPagoCreate,
    ClienteSnapshot,
    CotizacionCreate,
    CotizacionUpdate,
    CotizacionListResponse,
    CotizacionPageResponse,
    CotizacionResponse,
    ClienteDocumentoListResponse,
    FiscalDocumentListResponse,
    FiscalDocumentPageResponse,
    NoteReferenceDocumentListResponse,
    FiscalNoteListResponse,
    FiscalNotePageResponse,
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
    GuiaRemisionListResponse,
    GuiaRemisionCountsResponse,
    GuiaRemisionPageResponse,
    SmartPSEGuideReconcileRequest,
    DispatchLineSelection,
    SaleDispatchGuideData,
    SaleDispatchFromInvoiceCreate,
    SaleDispatchFromDocumentCreate,
    SaleDispatchUpdate,
    ExternalDocumentReferenceInput,
    TransportGuideCreate,
    GuideExternalRegistration,
    ExternalGuideVerification,
    GuideExternalReferenceResponse,
    DispatchDepartureConfirm,
    HistoricalDispatchReconciliation,
    SaleDispatchLineResponse,
    SaleDispatchResponse,
    GuideActionAvailability,
    GuideEmissionJobSummary,
    GuiaRemisionDetailResponse,
)

from schemas.inventory import (
    WarehouseCreate,
    WarehouseResponse,
    WarehouseUpdate,
    WarehouseFiscalVerify,
    InventoryActivation,
    StockResponse,
    InventoryAdjustmentCreate,
    MovementResponse,
    TransferLine,
    TransferCreate,
    ProductInventoryConfig,
    AvailabilityRequest,
    AvailabilityLine,
    ReturnReceiptLine,
    ReturnReceiptCreate,
)
from schemas.internal_transfers import (
    EstablishmentCreate,
    EstablishmentUpdate,
    EstablishmentVerify,
    EstablishmentResponse,
    InternalTransferLineCreate,
    InternalTransferCreate,
    InternalTransferUpdate,
    InternalTransferDispatchLineCreate,
    InternalTransferDispatchCreate,
    InternalTransferGuideCreate,
    InternalTransferDepartureConfirm,
    InternalTransferReceiptLineCreate,
    InternalTransferReceiptCreate,
)

from schemas.resumenes import (
    ResumenDiarioDocReferencia,
    ResumenDiarioPercepcion,
    ResumenDiarioDetalleCreate,
    ResumenDiarioCreate,
    ResumenDiarioResponse,
    ResumenDiarioPageResponse,
)
from schemas.reversiones import (
    ReversionDetalleCreate,
    ReversionCreate,
    ReversionResponse,
    ReversionPageResponse,
)
from schemas.retenciones import (
    RetencionClientCreate,
    RetencionPaymentCreate,
    RetencionExchangeCreate,
    RetencionDetalleCreate,
    RetencionCreate,
    RetencionResponse,
    RetencionPageResponse,
)
from schemas.percepciones import (
    PercepcionClientCreate,
    PercepcionPaymentCreate,
    PercepcionExchangeCreate,
    PercepcionDetalleCreate,
    PercepcionCreate,
    PercepcionResponse,
    PercepcionPageResponse,
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
    FiscalFeatureFlagDefinitionResponse,
    FiscalFeatureFlagsResponse,
    UpdateFiscalFeatureFlagsRequest,
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
from schemas.emission_jobs import EmissionJobResponse
from schemas.notes import (
    NoteAdjustmentLine,
    FiscalNoteDraftCreate,
    FiscalNoteDraftUpdate,
)

from schemas.usage_limits import (
    UsageLimitBase,
    UsageLimitCreate,
    UsageLimitResponse,
    UsageLimitsBulkUpsert,
    UsageLimitUsageItem,
    UsageLimitsWithUsage,
)

__all__ = [
    "ProductoInventarioInicial",
    "SmartPSECompanyCreate", "SmartPSECompanyUpdate", "SmartPSETenantCredentialsUpdate",
    "SmartPSECompanyResponse", "SmartPSECompanyPageResponse", "SmartPSESyncAllResponse",
    "SmartPSEDeleteResponse",
    "AccessRequestCreate", "AccessRequestCreated", "AccessRequestRucLookup",
    "AccessRequestStatusLookup", "AccessRequestPublicStatus", "AccessRequestReview",
    "AccessRequestAdminResponse", "AccessRequestPageResponse",
    "StrictInputModel",
    "CatalogEntitlementUpdate", "CatalogThemeConfig", "CatalogSiteCreate", "CatalogSiteUpdate",
    "CatalogCategoryCreate", "CatalogItemCreate", "CatalogCollectionCreate", "CatalogCollectionItemsUpdate", "CatalogItemAssetsUpdate", "CatalogEntitlementResponse",
    "CatalogSiteResponse", "CatalogItemResponse", "CatalogPublicItemResponse", "normalize_catalog_slug",
    # tenants
    "TenantBase", "TenantCreate", "TenantUpdate", "TenantSummaryResponse",
    "TenantResponse", "TenantSaaSUpdate", "TenantFiscalSeriesUpdate", "SuperadminTenantCreate", "SuperadminTenantResponse",
    "SuperadminTenantPageMetrics", "SuperadminTenantPageResponse",
    "ApisPeruTokenValidationRequest", "ApisPeruTokenValidationResponse",
    "SmartPSECredentialsValidationRequest", "SmartPSECredentialsValidationResponse",
    "SmartPSEProvisionRequest", "SmartPSEGreCredentialsUpdate",
    "SmartPSEGreCredentialsValidationResponse",
    "EmissionErrorResponse", "TokenHealthResponse",
    "FiscalContingencyUpdate", "FiscalContingencyResponse",
    # auth
    "UserIdentity", "UserRegisterRequest", "UserUpdateProfile", "UserAdminUpdate",
    "SuperadminUserCreate", "UserResponse", "UserMetrics", "UserDetailResponse",
    "ResetPasswordResponse", "ToggleUserActiveRequest", "Token", "TokenData",
    "ChangePasswordRequest", "CreateUserWithPasswordResponse",
    # clientes
    "CONDICION_PAGO_VALORES", "ClienteBase", "ClienteCreate", "ClienteUpdate", "ClienteResponse", "ClienteSearchResponse", "ClientePageResponse",
    # productos + MRP
    "ProductoBase", "ProductoCreate", "ProductoResponse", "ProductoSearchResponse", "ProductoPageResponse",
    "InsumoBase", "InsumoCreate", "InsumoResponse",
    "RecetaBOMBase", "RecetaBOMCreate", "RecetaBOMResponse",
    "AlertaInventarioResponse", "DashboardStatsResponse",
    "ProveedorBase", "ProveedorCreate", "ProveedorUpdate", "ProveedorResponse",
    "OrdenProduccionDetalleResponse", "OrdenProduccionResponse",
    # cotizaciones + pagos
    "CotizacionItemCreate", "CotizacionItemResponse", "CuotaPagoCreate", "ClienteSnapshot", "CotizacionCreate", "CotizacionUpdate", "CotizacionListResponse", "CotizacionPageResponse", "CotizacionResponse",
    "ClienteDocumentoListResponse", "FiscalDocumentListResponse", "FiscalDocumentPageResponse",
    "NoteReferenceDocumentListResponse", "FiscalNoteListResponse", "FiscalNotePageResponse",
    "PagoCreate", "PagoResponse",
    "CobranzaResumenResponse", "CobranzaVencidaItem",
    "FacturarPayload", "NotaCreate", "AnulacionCreate", "DescargaArchivoPayload",
    # guias
    "GuiaRemisionItemCreate", "GuiaRemisionCreate", "GuiaRemisionItemResponse",
    "EtiquetaGuiaResponse", "GuiaRemisionResponse", "GuiaRemisionListResponse",
    "GuiaRemisionCountsResponse", "GuiaRemisionPageResponse", "SmartPSEGuideReconcileRequest",
    "DispatchLineSelection", "SaleDispatchGuideData", "SaleDispatchFromInvoiceCreate",
    "SaleDispatchUpdate", "ExternalDocumentReferenceInput", "TransportGuideCreate",
    "GuideExternalRegistration", "ExternalGuideVerification", "GuideExternalReferenceResponse",
    "DispatchDepartureConfirm", "HistoricalDispatchReconciliation", "SaleDispatchLineResponse",
    "SaleDispatchResponse", "GuideActionAvailability", "GuideEmissionJobSummary", "GuiaRemisionDetailResponse",
    # resumen diario
    "ResumenDiarioDocReferencia", "ResumenDiarioPercepcion",
    "ResumenDiarioDetalleCreate", "ResumenDiarioCreate", "ResumenDiarioResponse", "ResumenDiarioPageResponse",
    # reversiones
    "ReversionDetalleCreate", "ReversionCreate", "ReversionResponse", "ReversionPageResponse",
    # retenciones
    "RetencionClientCreate", "RetencionPaymentCreate", "RetencionExchangeCreate",
    "RetencionDetalleCreate", "RetencionCreate", "RetencionResponse", "RetencionPageResponse",
    # percepciones
    "PercepcionClientCreate", "PercepcionPaymentCreate", "PercepcionExchangeCreate",
    "PercepcionDetalleCreate", "PercepcionCreate", "PercepcionResponse", "PercepcionPageResponse",
    # ai
    "AIItemCotizacion", "AIParsedCotizacionResponse",
    "AIInsumoFactura", "AIParsedFacturaResponse",
    # subscriptions / superadmin / beta
    "SubscriptionResponse", "SubscriptionPaymentCreate", "SubscriptionPaymentResponse",
    "FiscalFeatureFlagDefinitionResponse", "FiscalFeatureFlagsResponse",
    "UpdateFiscalFeatureFlagsRequest",
    "ActivateTenantRequest", "SuspendTenantRequest", "ExtendAccessRequest",
    "SetFounderPricingRequest", "UpdateSubscriptionRequest", "SuperadminTenantDetailResponse",
    "UpdateNotasRequest", "TenantActividadResponse", "BetaTenantSummary",
    # onboarding
    "ImportErrorDetail", "ImportResultResponse",
    "OnboardingChecklistItem", "OnboardingEstadoResponse",
    # emission jobs
    "EmissionJobResponse",
    "NoteAdjustmentLine", "FiscalNoteDraftCreate", "FiscalNoteDraftUpdate",
    # usage limits
    "UsageLimitBase", "UsageLimitCreate", "UsageLimitResponse",
    "UsageLimitsBulkUpsert", "UsageLimitUsageItem", "UsageLimitsWithUsage",
]
