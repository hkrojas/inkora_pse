# VALIDATION DATA CLEANUP PLAN - Inkora PSE

## 1. Objetivo

Preparar la limpieza segura de datos temporales de validacion antes de operar con clientes reales.

Esta fase solo documenta alcance, evidencia, dry-run y SQL propuesto. No ejecuta borrados. La limpieza real requiere un paso posterior con autorizacion explicita.

## 2. Alcance propuesto

Tenants candidatos:

- `tenant_id=2`
- `tenant_id=3`
- `tenant_id=4`

Evidencia actual desde `POST_DEPLOY_VALIDATION_RESULTS.md`:

| Tenant | Nombre | RUC | Usuarios | Clientes | Productos | Cotizaciones | Pagos | Jobs fiscales | Otros datos relacionados |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `2` | `Inkora Validation 20260508172203` | `20508172203` | 1 validation user | 0 | 0 | 0 | 0 | 0 | 1 subscription, 1 audit log |
| `3` | `Inkora Validation 20260508172256` | `20508172256` | 1 validation user | 0 | 0 | 0 | 0 | 0 | 1 subscription |
| `4` | `Inkora Validation 20260508172343` | `20508172343` | 1 validation user | 1 | 1 | 1 quotation no fiscal | 0 | 0 | 1 cotizacion item, 1 subscription, 8 audit logs |

Tablas incluidas en el alcance de auditoria:

- Core: `tenants`, `users`, `clientes`, `productos`, `cotizaciones`, `cotizacion_items`.
- Cobranza/fiscal: `pagos`, `document_emission_jobs`, `guias_remision`, `guia_remision_items`, `resumenes_diarios`, `reversiones_fiscales`, `retenciones_fiscales`, `percepciones_fiscales`.
- SaaS/metadata: `subscriptions`, `subscription_payments`, `usage_limits`, `audit_logs`.
- MRP / frozen: `insumos`, `recetas_bom`, `proveedores`, `ordenes_produccion`, `ordenes_produccion_detalle`, `alertas_inventario`.

## 3. Evidencia de que son temporales

- `POST_DEPLOY_VALIDATION_RESULTS.md` documenta que los tenants `2`, `3` y `4` fueron creados durante validacion post-deploy.
- `tenant_id=4` fue usado con el usuario temporal `validation-20260508172343@inkora.test`.
- `tenant_id=4` contiene datos minimos no fiscales: un cliente, un producto y una cotizacion.
- `tenant_id=2` y `tenant_id=3` quedaron como intentos previos sin clientes/productos/cotizaciones segun el reporte.
- El reporte indica que no se ejecuto emision fiscal real.
- `document_emission_jobs` fue reportado en `0` y sin jobs colgados durante la validacion.

Evidencia SQL real:

- Estado: `DRY-RUN SELECT EJECUTADO EN SUPABASE SQL EDITOR`.
- Fecha local de ejecucion: 2026-05-08 America/Lima.
- Rol visible en SQL Editor: `postgres`.
- Base visible: `Primary database`.
- No se ejecuto `DELETE`, `TRUNCATE` ni `UPDATE`.
- El primer intento de dry-run fallo de forma segura porque `users.created_at` no existe en el modelo real. Se corrigio la consulta para usar las columnas reales de `users`.

Resumen del resultado:

- Tenants encontrados:
  - `tenant_id=2`: `Inkora Validation 20260508172203`, RUC `20508172203`, activo.
  - `tenant_id=3`: `Inkora Validation 20260508172256`, RUC `20508172256`, activo.
  - `tenant_id=4`: `Inkora Validation 20260508172343`, RUC `20508172343`, activo.
- Usuarios temporales:
  - `validation+20260508172203@inkora.test`, tenant `2`, rol `admin`, activo.
  - `validation+20260508172256@inkora.test`, tenant `3`, rol `admin`, activo.
  - `validation-20260508172343@inkora.test`, tenant `4`, rol `admin`, activo.
- Conteos no cero:
  - tenant `2`: `subscriptions=1`, `audit_logs_by_validation_users=1`.
  - tenant `3`: `subscriptions=1`.
  - tenant `4`: `clientes=1`, `productos=1`, `cotizaciones=1`, `cotizacion_items=1`, `subscriptions=1`, `audit_logs_by_validation_users=8`.
- `quote_breakdown`: tenant `4` tiene `1` cotizacion `document_kind='quotation'`, `tipo_comprobante='00'`, `estado='pendiente'`.
- `fiscal_risk`: `[]`.
- `active_jobs`: `[]`.
- Las tablas incluidas en el dry-run ampliado que no aparecieron en el resultado tienen `0` filas para los tenants `2`, `3` y `4`.

## 4. Riesgos

- Eliminacion irreversible si no hay backup o dump logico reciente.
- Supabase Free Plan no incluye backups/PITR gestionados, segun el reporte post-deploy.
- Posibilidad de borrar datos reales si los IDs `2`, `3` y `4` no se confirman justo antes de ejecutar.
- Dependencia de tablas relacionadas y foreign keys, incluidas tablas MRP/congeladas.
- Posible existencia de documentos fiscales reales o jobs activos si la base cambio despues de la validacion.
- Audit logs pueden contener trazas utiles; deben revisarse antes de borrar.

## 5. Precondiciones antes de borrar

La limpieza real solo puede ejecutarse si se cumplen todas estas condiciones:

- Existe backup/PITR gestionado o dump logico reciente verificado con `pg_restore --list` y hash.
- El operador confirma por escrito: `Autorizo borrar tenants temporales 2, 3 y 4`.
- El dry-run SQL coincide con lo esperado.
- Los tenants `2`, `3` y `4` no son clientes reales.
- No hay documentos fiscales reales para esos tenants.
- No hay jobs fiscales activos en `queued`, `retry` o `processing`.
- No hay pagos, guias, resumenes, reversiones, retenciones, percepciones ni MRP real que pertenezca a esos tenants.
- El SQL destructivo se revisa inmediatamente antes de ejecutarlo.

## 6. Dry-run SQL

Ejecutar solo `SELECT`. No ejecutar `DELETE`, `TRUNCATE` ni `UPDATE`.

### 6.1 Tenants y usuarios

```sql
SELECT id, business_name, business_ruc, created_at, is_active
FROM tenants
WHERE id IN (2, 3, 4)
ORDER BY id;
```

```sql
SELECT id, tenant_id, email, rol, is_active, created_at
FROM users
WHERE tenant_id IN (2, 3, 4)
   OR email ILIKE '%validation%'
   OR email ILIKE '%inkora.test%'
ORDER BY tenant_id, id;
```

### 6.2 Datos core

```sql
SELECT tenant_id, count(*) AS clientes
FROM clientes
WHERE tenant_id IN (2, 3, 4)
GROUP BY tenant_id
ORDER BY tenant_id;
```

```sql
SELECT tenant_id, count(*) AS productos
FROM productos
WHERE tenant_id IN (2, 3, 4)
GROUP BY tenant_id
ORDER BY tenant_id;
```

```sql
SELECT tenant_id, document_kind, tipo_comprobante, estado, count(*) AS total
FROM cotizaciones
WHERE tenant_id IN (2, 3, 4)
GROUP BY tenant_id, document_kind, tipo_comprobante, estado
ORDER BY tenant_id, document_kind, tipo_comprobante, estado;
```

```sql
SELECT c.tenant_id, ci.cotizacion_id, count(*) AS items
FROM cotizacion_items ci
JOIN cotizaciones c ON c.id = ci.cotizacion_id
WHERE c.tenant_id IN (2, 3, 4)
GROUP BY c.tenant_id, ci.cotizacion_id
ORDER BY c.tenant_id, ci.cotizacion_id;
```

### 6.3 Cobranza y cola fiscal

```sql
SELECT tenant_id, count(*) AS pagos
FROM pagos
WHERE tenant_id IN (2, 3, 4)
GROUP BY tenant_id
ORDER BY tenant_id;
```

```sql
SELECT tenant_id, status, count(*) AS jobs
FROM document_emission_jobs
WHERE tenant_id IN (2, 3, 4)
GROUP BY tenant_id, status
ORDER BY tenant_id, status;
```

```sql
SELECT id, tenant_id, resource_type, resource_id, action, status, attempts, locked_at, processing_started_at, left(last_error, 300) AS error
FROM document_emission_jobs
WHERE tenant_id IN (2, 3, 4)
ORDER BY tenant_id, id;
```

### 6.4 Documentos fiscales y relacionados

```sql
SELECT tenant_id, id, document_kind, tipo_comprobante, estado, serie, correlativo,
       sunat_xml_url, sunat_pdf_url, sunat_cdr_url, sunat_error
FROM cotizaciones
WHERE tenant_id IN (2, 3, 4)
  AND (
    document_kind <> 'quotation'
    OR tipo_comprobante <> '00'
    OR sunat_xml_url IS NOT NULL
    OR sunat_pdf_url IS NOT NULL
    OR sunat_cdr_url IS NOT NULL
    OR sunat_error IS NOT NULL
  )
ORDER BY tenant_id, id;
```

```sql
SELECT tenant_id, estado, count(*) AS guias
FROM guias_remision
WHERE tenant_id IN (2, 3, 4)
GROUP BY tenant_id, estado
ORDER BY tenant_id, estado;
```

### 6.5 Dry-run ampliado de tablas relacionadas

```sql
SELECT 'cotizacion_items' AS table_name, count(*) AS rows
FROM cotizacion_items ci
JOIN cotizaciones c ON c.id = ci.cotizacion_id
WHERE c.tenant_id IN (2, 3, 4)
UNION ALL
SELECT 'guias_remision', count(*) FROM guias_remision WHERE tenant_id IN (2, 3, 4)
UNION ALL
SELECT 'guia_remision_items', count(*)
FROM guia_remision_items gi
JOIN guias_remision g ON g.id = gi.guia_id
WHERE g.tenant_id IN (2, 3, 4)
UNION ALL
SELECT 'subscriptions', count(*) FROM subscriptions WHERE tenant_id IN (2, 3, 4)
UNION ALL
SELECT 'subscription_payments', count(*) FROM subscription_payments WHERE tenant_id IN (2, 3, 4)
UNION ALL
SELECT 'usage_limits', count(*) FROM usage_limits WHERE tenant_id IN (2, 3, 4)
UNION ALL
SELECT 'audit_logs_by_validation_users', count(*)
FROM audit_logs al
JOIN users u ON u.id = al.user_id
WHERE u.tenant_id IN (2, 3, 4)
UNION ALL
SELECT 'resumenes_diarios', count(*) FROM resumenes_diarios WHERE tenant_id IN (2, 3, 4)
UNION ALL
SELECT 'reversiones_fiscales', count(*) FROM reversiones_fiscales WHERE tenant_id IN (2, 3, 4)
UNION ALL
SELECT 'retenciones_fiscales', count(*) FROM retenciones_fiscales WHERE tenant_id IN (2, 3, 4)
UNION ALL
SELECT 'percepciones_fiscales', count(*) FROM percepciones_fiscales WHERE tenant_id IN (2, 3, 4)
UNION ALL
SELECT 'insumos', count(*) FROM insumos WHERE tenant_id IN (2, 3, 4)
UNION ALL
SELECT 'recetas_bom', count(*) FROM recetas_bom WHERE tenant_id IN (2, 3, 4)
UNION ALL
SELECT 'proveedores', count(*) FROM proveedores WHERE tenant_id IN (2, 3, 4)
UNION ALL
SELECT 'ordenes_produccion', count(*) FROM ordenes_produccion WHERE tenant_id IN (2, 3, 4)
UNION ALL
SELECT 'ordenes_produccion_detalle', count(*)
FROM ordenes_produccion_detalle opd
JOIN ordenes_produccion op ON op.id = opd.orden_id
WHERE op.tenant_id IN (2, 3, 4)
UNION ALL
SELECT 'alertas_inventario', count(*) FROM alertas_inventario WHERE tenant_id IN (2, 3, 4);
```

## 7. SQL de limpieza propuesto, NO EJECUTAR

Este bloque es una propuesta para una fase futura. No ejecutar en esta fase.

```sql
-- NO EJECUTAR SIN AUTORIZACION EXPLICITA.
-- Requisito textual: "Autorizo borrar tenants temporales 2, 3 y 4"
-- Este bloque termina en ROLLBACK por seguridad. No cambiar a COMMIT sin nueva autorizacion.

BEGIN;

-- Auditoria asociada a usuarios temporales
DELETE FROM audit_logs
WHERE user_id IN (SELECT id FROM users WHERE tenant_id IN (2, 3, 4));

-- Hijos de guias/cotizaciones
DELETE FROM guia_remision_items
WHERE guia_id IN (SELECT id FROM guias_remision WHERE tenant_id IN (2, 3, 4));

DELETE FROM cotizacion_items
WHERE cotizacion_id IN (SELECT id FROM cotizaciones WHERE tenant_id IN (2, 3, 4));

-- MRP / frozen module
DELETE FROM ordenes_produccion_detalle
WHERE orden_id IN (
  SELECT id FROM ordenes_produccion WHERE tenant_id IN (2, 3, 4)
);

DELETE FROM alertas_inventario
WHERE tenant_id IN (2, 3, 4);

DELETE FROM ordenes_produccion
WHERE tenant_id IN (2, 3, 4);

DELETE FROM recetas_bom
WHERE tenant_id IN (2, 3, 4);

DELETE FROM proveedores
WHERE tenant_id IN (2, 3, 4);

DELETE FROM insumos
WHERE tenant_id IN (2, 3, 4);

-- Tablas operativas/fiscales por tenant
DELETE FROM pagos WHERE tenant_id IN (2, 3, 4);
DELETE FROM document_emission_jobs WHERE tenant_id IN (2, 3, 4);
DELETE FROM guias_remision WHERE tenant_id IN (2, 3, 4);
DELETE FROM resumenes_diarios WHERE tenant_id IN (2, 3, 4);
DELETE FROM reversiones_fiscales WHERE tenant_id IN (2, 3, 4);
DELETE FROM retenciones_fiscales WHERE tenant_id IN (2, 3, 4);
DELETE FROM percepciones_fiscales WHERE tenant_id IN (2, 3, 4);

-- SaaS/metadata tenant
DELETE FROM subscription_payments WHERE tenant_id IN (2, 3, 4);
DELETE FROM usage_limits WHERE tenant_id IN (2, 3, 4);
DELETE FROM subscriptions WHERE tenant_id IN (2, 3, 4);

-- Datos core
DELETE FROM cotizaciones WHERE tenant_id IN (2, 3, 4);
DELETE FROM clientes WHERE tenant_id IN (2, 3, 4);
DELETE FROM productos WHERE tenant_id IN (2, 3, 4);

-- Usuarios
DELETE FROM users WHERE tenant_id IN (2, 3, 4);

-- Padres
DELETE FROM tenants WHERE id IN (2, 3, 4);

-- Seguridad por defecto: no persistir en esta fase.
ROLLBACK;
```

## 8. Criterios para autorizar ejecucion real

La limpieza real solo puede pasar a ejecucion si:

- El operador confirma por escrito: `Autorizo borrar tenants temporales 2, 3 y 4`.
- Hay backup/PITR o dump logico reciente verificado.
- El dry-run coincide con lo esperado.
- No hay documentos fiscales reales.
- No hay jobs fiscales activos.
- No hay pagos reales ni datos MRP reales.
- La base sigue con superadmin real fuera del alcance de borrado.
- El SQL destructivo fue revisado nuevamente y sigue en orden hijo-padre.

## 9. Resultado esperado

Despues de una limpieza futura autorizada:

- Tenants temporales `2`, `3` y `4` no existen.
- Usuarios `validation` / `inkora.test` no existen.
- Clientes, productos y cotizaciones temporales no existen.
- `document_emission_jobs` temporal = `0`.
- Tablas MRP/congeladas temporales = `0`.
- Sistema conserva el superadmin real.
- `/health` sigue PASS.
