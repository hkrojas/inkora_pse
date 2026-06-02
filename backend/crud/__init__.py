"""
crud/__init__.py — Re-exporta todo el namespace CRUD de forma plana.

Todos los módulos del paquete son accesibles via `import crud; crud.X()`
sin cambiar ningún caller externo.
"""

from crud._base import (
    pwd_context,
    _get_tenant_resource,
    get_cliente_for_tenant,
    get_producto_for_tenant,
    _clone_cotizacion_items,
    _next_correlativo_for_series,
    _retry_on_correlativo_conflict,
    MAX_CORRELATIVO_RETRIES,
    get_source_quote,
    get_latest_fiscal_document_for_quote,
    resolve_fiscal_document_reference,
    resolve_payment_anchor_document,
)

from crud.auth import (
    get_user_by_email,
    get_user_by_email_global,
    get_user_by_id,
    create_user,
    change_user_password,
    generate_temp_password,
    log_auth_event,
)

from crud.tenants import (
    get_tenant,
    get_tenant_by_ruc,
    create_tenant,
    update_tenant,
    update_tenant_payment_qr,
    get_all_tenants,
    get_tenants_page,
    update_tenant_saas,
    delete_tenant,
    get_all_users,
    create_audit_log,
    get_audit_logs,
    get_subscription_by_tenant,
    get_or_create_subscription,
    update_subscription_fields,
    register_subscription_payment,
    get_subscription_payments,
    get_all_tenants_with_subscription,
    check_document_limit,
    get_tenant_actividad,
    get_beta_resumen_data,
)

from crud.clientes import (
    get_clientes,
    count_clientes,
    create_cliente,
    update_cliente,
    patch_cliente,
    delete_cliente,
)

from crud.productos import (
    ProductoEnUsoError,
    get_productos,
    count_productos,
    create_producto,
    update_producto,
    delete_producto,
)

from crud.cotizaciones import (
    get_cotizaciones,
    get_cotizacion,
    get_cotizacion_by_uuid,
    create_cotizacion,
    duplicate_cotizacion,
    delete_cotizacion,
    create_fiscal_document_from_quote,
    guardar_respuesta_sunat,
    guardar_error_sunat,
    anular_cotizacion,
    crear_nota_credito_debito,
)

from crud.guias import (
    get_guias_remision,
    get_guias_remision_page,
    get_guia_remision,
    create_guia_remision,
    guardar_respuesta_sunat_gre,
    guardar_error_sunat_gre,
)

from crud.resumenes import (
    list_resumenes_diarios,
    create_resumen_diario,
    mark_resumen_diario_sent,
    mark_resumen_diario_rejected,
)
from crud.reversiones import (
    list_reversiones,
    create_reversion,
    mark_reversion_sent,
    mark_reversion_rejected,
)
from crud.retenciones import (
    list_retenciones,
    create_retencion,
    mark_retencion_sent,
    mark_retencion_rejected,
)
from crud.percepciones import (
    list_percepciones,
    create_percepcion,
    mark_percepcion_sent,
    mark_percepcion_rejected,
)

from crud.emission_jobs import (
    get_emission_job,
    get_emission_jobs,
    get_active_emission_job_by_key,
    get_emission_job_by_key,
    create_emission_job,
    claim_next_emission_job,
    mark_emission_job_attempt_started,
    mark_emission_job_succeeded,
    mark_emission_job_retry,
    requeue_emission_job,
    recover_stale_processing_jobs,
    mark_emission_job_failed,
)

from crud.pagos import (
    apply_prefiscal_advances_to_fiscal_document,
    registrar_pago,
    get_pagos_cotizacion,
)

from crud.superadmin import (
    get_tenant_users_with_metrics,
    reset_user_password,
    toggle_user_active,
    get_tenant_emission_errors,
    check_apisperu_token_health,
    check_all_apisperu_tokens,
)

from crud.usage_limits import (
    QuotaExceededError,
    build_tenant_usage_report,
    check_emission_quota,
    count_usage_for_kind,
    delete_limit,
    get_active_limits,
    get_limit_by_id,
    get_tenant_limits,
    upsert_tenant_limits,
)

from crud.reportes import (
    get_dashboard_stats,
    get_cobranza_vencida,
    get_cobranza_resumen,
    get_reporte_mensual,
)

from crud.frozen import (
    get_proveedores,
    create_proveedor,
    update_proveedor,
    delete_proveedor,
    get_insumos,
    create_insumo,
    update_insumo,
    delete_insumo,
    get_recetas_producto,
    create_receta_bom,
    get_ordenes_produccion,
    generar_orden_produccion,
    update_orden_produccion_status,
    verificar_stock_y_generar_alertas,
)
