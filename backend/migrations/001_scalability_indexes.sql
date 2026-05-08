-- Inkora backend scalability indexes.
-- Safe to run more than once. Apply first in staging.

-- Clientes
CREATE INDEX IF NOT EXISTS idx_clientes_tenant_numero_documento
ON clientes (tenant_id, numero_documento);

CREATE INDEX IF NOT EXISTS idx_clientes_tenant_razon_social
ON clientes (tenant_id, razon_social);

-- Productos
CREATE INDEX IF NOT EXISTS idx_productos_tenant_codigo_interno
ON productos (tenant_id, codigo_interno);

CREATE INDEX IF NOT EXISTS idx_productos_tenant_nombre
ON productos (tenant_id, nombre);

-- Cotizaciones / documentos fiscales
CREATE INDEX IF NOT EXISTS idx_cotizaciones_tenant_kind_estado_fecha
ON cotizaciones (tenant_id, document_kind, estado, fecha_emision DESC);

CREATE INDEX IF NOT EXISTS idx_cotizaciones_tenant_source_kind_estado
ON cotizaciones (tenant_id, source_quote_id, document_kind, estado);

CREATE INDEX IF NOT EXISTS idx_cotizaciones_tenant_fecha_vencimiento
ON cotizaciones (tenant_id, fecha_vencimiento);

CREATE INDEX IF NOT EXISTS idx_cotizaciones_tenant_cliente
ON cotizaciones (tenant_id, cliente_id);

-- Items
CREATE INDEX IF NOT EXISTS idx_cotizacion_items_cotizacion_id
ON cotizacion_items (cotizacion_id);

CREATE INDEX IF NOT EXISTS idx_cotizacion_items_producto_id
ON cotizacion_items (producto_id);

-- Pagos
CREATE INDEX IF NOT EXISTS idx_pagos_tenant_fecha_pago
ON pagos (tenant_id, fecha_pago);

CREATE INDEX IF NOT EXISTS idx_pagos_tenant_fiscal_document
ON pagos (tenant_id, fiscal_document_id);

CREATE INDEX IF NOT EXISTS idx_pagos_tenant_source_quote
ON pagos (tenant_id, source_quote_id);

-- Cola de emision fiscal
CREATE INDEX IF NOT EXISTS idx_emission_jobs_claim
ON document_emission_jobs (status, available_at, priority, created_at);
