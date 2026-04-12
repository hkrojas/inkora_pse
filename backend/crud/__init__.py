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
    get_source_quote,
    get_latest_fiscal_document_for_quote,
    resolve_fiscal_document_reference,
    resolve_payment_anchor_document,
)

from crud.auth import (
    get_user_by_email,
    get_user_by_id,
    create_user,
)

from crud.tenants import (
    get_tenant,
    get_tenant_by_ruc,
    create_tenant,
    update_tenant,
    get_all_tenants,
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
    create_cliente,
    update_cliente,
    patch_cliente,
    delete_cliente,
)

from crud.productos import (
    get_productos,
    create_producto,
    update_producto,
    delete_producto,
)

from crud.cotizaciones import (
    get_cotizaciones,
    get_cotizacion,
    get_cotizacion_by_uuid,
    create_cotizacion,
    create_fiscal_document_from_quote,
    guardar_respuesta_sunat,
    guardar_error_sunat,
    anular_cotizacion,
    crear_nota_credito_debito,
)

from crud.guias import (
    get_guias_remision,
    get_guia_remision,
    create_guia_remision,
    guardar_respuesta_sunat_gre,
    guardar_error_sunat_gre,
)

from crud.pagos import (
    registrar_pago,
    get_pagos_cotizacion,
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
