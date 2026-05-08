# 1. Resumen ejecutivo

Ya está desplegado en `main` el bloque de escalabilidad con commit `5270d8c Optimize catalog autocomplete search`: índices core, migración opcional `pg_trgm`, optimizaciones de cobranza/dashboard, `/clientes/page`, `/productos/page`, `/clientes/search`, `/productos/search` y autocomplete remoto con debounce/cache/`AbortController`.

Se debe validar en producción o staging real: migraciones en Supabase, salud de Railway, endpoints críticos autenticados, Vercel apuntando al backend correcto, flujo cliente/producto/cotización, cobranza y, solo con autorización, emisión fiscal async.

Riesgos principales: `pytest` completo aún tiene 5 fallas fuera de scope, `pg_trgm` puede fallar por permisos, emisión/PDF puede competir con API si no hay worker separado, correlativos pueden ser hotspot, caches DNI/RUC/Smart PSE son en memoria, validación fiscal real requiere credenciales.

Declarar estable solo si: migración core aplicada, health OK, endpoints search/page/cobranza sin 500/timeouts, frontend usa API correcta, no hay CORS, autocomplete remoto funciona, logs limpios por 24h o una jornada operativa, cotización funciona y rollback está documentado.

# 2. Estado actual del repo

Branch inspeccionado: `codex/smartpse-backend`, sincronizado con `inkora_pse/main`.

Último commit: `5270d8c Optimize catalog autocomplete search`.

Archivos confirmados:

- `backend/migrations/001_scalability_indexes.sql`: índices core idempotentes.
- `backend/migrations/002_optional_pg_trgm_indexes.sql`: `pg_trgm` e índices GIN solo para campos principales.
- `backend/migrations/README.md`: flujo 001 primero, 002 opcional, y aclaración de validación estática.
- Backend: `/health`, `/clientes/page`, `/clientes/search`, `/productos/page`, `/productos/search`, `/cobranza/resumen`, `/cobranza/vencidas`, emisión fiscal y `emission-jobs`.
- Frontend: `ClientCombobox.jsx`, `ProductLineCell.jsx`, `frontend/src/services/clientes.js`, `frontend/src/services/productos.js`.
- Variable frontend real: `VITE_API_URL` en `frontend/src/lib/utils/config.js`.

Pruebas locales conocidas:

- Backend focal: `24 passed`.
- Frontend build/lint: pasaron.
- Backend completo: `417 passed, 5 failed`, fallas fuera de scope.

Fallas conocidas fuera de scope:

- GRE Smart PSE en test matrix falla por credenciales GRE de test no configuradas.
- `test_critical_template.py` falla por SQLite legacy sin columna `users.is_active`.
- Dos tests de rutas fiscales/guías fallan por llamadas directas a endpoints decorados con SlowAPI sin `Request`.
- No resolver estas fallas dentro de este plan sin una fase fiscal/test-harness dedicada.

# 3. Plan de validación Supabase

## 3.1 Validar migración core

Aplicar primero en staging, luego producción:

```bash
psql "$DATABASE_URL" -f backend/migrations/001_scalability_indexes.sql
```

Validar índices:

```sql
SELECT indexname, tablename
FROM pg_indexes
WHERE tablename IN (
  'clientes',
  'productos',
  'cotizaciones',
  'cotizacion_items',
  'pagos',
  'document_emission_jobs'
)
ORDER BY tablename, indexname;
```

Índices esperados:

- `idx_clientes_tenant_numero_documento`
- `idx_clientes_tenant_razon_social`
- `idx_productos_tenant_codigo_interno`
- `idx_productos_tenant_nombre`
- `idx_cotizaciones_tenant_kind_estado_fecha`
- `idx_cotizaciones_tenant_source_kind_estado`
- `idx_cotizaciones_tenant_fecha_vencimiento`
- `idx_cotizaciones_tenant_cliente`
- `idx_cotizacion_items_cotizacion_id`
- `idx_cotizacion_items_producto_id`
- `idx_pagos_tenant_fecha_pago`
- `idx_pagos_tenant_fiscal_document`
- `idx_pagos_tenant_source_quote`
- `idx_emission_jobs_claim`

## 3.2 Validar migración opcional pg_trgm

Aplicar solo después de `001`:

```bash
psql "$DATABASE_URL" -f backend/migrations/002_optional_pg_trgm_indexes.sql
```

Validar:

```sql
SELECT * FROM pg_extension WHERE extname = 'pg_trgm';

SELECT indexname, tablename
FROM pg_indexes
WHERE indexname IN (
  'idx_clientes_razon_social_trgm',
  'idx_clientes_numero_documento_trgm',
  'idx_productos_nombre_trgm',
  'idx_productos_codigo_interno_trgm'
)
ORDER BY tablename, indexname;
```

Si `pg_trgm` falla por permisos:

- No insistir con permisos desde la app.
- Mantener solo `001_scalability_indexes.sql`.
- Pedir a un owner/admin de Supabase habilitar `pg_trgm`.
- Reintentar `002_optional_pg_trgm_indexes.sql`.
- Mientras tanto, monitorear p95 de `/clientes/search` y `/productos/search`.

## 3.3 EXPLAIN ANALYZE

Reemplazar `<TENANT_ID>` y términos reales. No inventar métricas; pegar resultados reales bajo cada bloque.

Búsqueda por documento de cliente:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, tipo_documento, numero_documento, razon_social, nombre_comercial, email
FROM clientes
WHERE tenant_id = <TENANT_ID>
  AND numero_documento ILIKE '%<DOCUMENTO>%'
ORDER BY
  CASE
    WHEN lower(coalesce(numero_documento, '')) = lower('<DOCUMENTO>') THEN 0
    WHEN lower(coalesce(numero_documento, '')) LIKE lower('<DOCUMENTO>%') THEN 1
    WHEN lower(coalesce(razon_social, '')) LIKE lower('<DOCUMENTO>%') THEN 2
    ELSE 3
  END,
  razon_social ASC,
  id ASC
LIMIT 20;
```

Búsqueda por razón social:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, tipo_documento, numero_documento, razon_social, nombre_comercial, email
FROM clientes
WHERE tenant_id = <TENANT_ID>
  AND razon_social ILIKE '%<RAZON_SOCIAL>%'
ORDER BY razon_social ASC, id ASC
LIMIT 20;
```

Búsqueda por SKU:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, codigo_interno, nombre, descripcion, precio_unitario
FROM productos
WHERE tenant_id = <TENANT_ID>
  AND codigo_interno ILIKE '%<SKU>%'
ORDER BY
  CASE
    WHEN lower(coalesce(codigo_interno, '')) = lower('<SKU>') THEN 0
    WHEN lower(coalesce(codigo_interno, '')) LIKE lower('<SKU>%') THEN 1
    WHEN lower(coalesce(nombre, '')) LIKE lower('<SKU>%') THEN 2
    ELSE 3
  END,
  nombre ASC,
  id ASC
LIMIT 20;
```

Búsqueda por nombre de producto:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, codigo_interno, nombre, descripcion, precio_unitario
FROM productos
WHERE tenant_id = <TENANT_ID>
  AND nombre ILIKE '%<NOMBRE_PRODUCTO>%'
ORDER BY nombre ASC, id ASC
LIMIT 20;
```

Cobranza resumen:

```sql
EXPLAIN (ANALYZE, BUFFERS)
WITH pagos_doc AS (
  SELECT fiscal_document_id, sum(monto_pagado) AS total
  FROM pagos
  WHERE tenant_id = <TENANT_ID>
    AND fiscal_document_id IS NOT NULL
  GROUP BY fiscal_document_id
)
SELECT count(*), sum(c.total_venta), sum(coalesce(p.total, 0))
FROM cotizaciones c
LEFT JOIN pagos_doc p ON p.fiscal_document_id = c.id
WHERE c.tenant_id = <TENANT_ID>
  AND c.document_kind IN ('fiscal_document', 'credit_note', 'debit_note')
  AND c.estado = 'facturada';
```

Cobranza vencidas:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT c.id, c.fecha_vencimiento, c.total_venta, c.monto_pagado, c.cliente_id
FROM cotizaciones c
WHERE c.tenant_id = <TENANT_ID>
  AND c.document_kind IN ('fiscal_document', 'credit_note', 'debit_note')
  AND c.estado = 'facturada'
  AND c.fecha_vencimiento IS NOT NULL
  AND c.fecha_vencimiento < now()
ORDER BY c.fecha_vencimiento ASC, c.id ASC
LIMIT 25;
```

Claim de jobs de emisión:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, status, available_at, priority, created_at
FROM document_emission_jobs
WHERE status IN ('queued', 'retry')
  AND available_at <= now()
ORDER BY priority ASC, created_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED;
```

Espacios para resultados reales:

- Clientes documento: `pegar EXPLAIN aquí`.
- Clientes razón social: `pegar EXPLAIN aquí`.
- Productos SKU: `pegar EXPLAIN aquí`.
- Productos nombre: `pegar EXPLAIN aquí`.
- Cobranza resumen: `pegar EXPLAIN aquí`.
- Cobranza vencidas: `pegar EXPLAIN aquí`.
- Claim jobs: `pegar EXPLAIN aquí`.

## 3.4 Backups y rollback Supabase

Antes de migrar:

- Confirmar backup/PITR activo en Supabase Dashboard.
- Exportar backup lógico si aplica:

```bash
pg_dump "$DATABASE_URL" --format=custom --no-owner --file "pre-scalability-indexes.dump"
```

Si un índice degrada performance:

- Dropear primero índices opcionales, uno por uno, fuera de transacción:

```sql
DROP INDEX CONCURRENTLY IF EXISTS idx_clientes_razon_social_trgm;
DROP INDEX CONCURRENTLY IF EXISTS idx_clientes_numero_documento_trgm;
DROP INDEX CONCURRENTLY IF EXISTS idx_productos_nombre_trgm;
DROP INDEX CONCURRENTLY IF EXISTS idx_productos_codigo_interno_trgm;
```

- No dropear `pg_trgm` salvo confirmación de que ninguna otra feature lo usa.
- Dropear índices core solo si se demuestra degradación y hay ventana de mantenimiento.

Qué NO hacer:

- No borrar datos.
- No truncar tablas.
- No correr `create_all`.
- No modificar columnas fiscales.
- No ejecutar migraciones manuales no revisadas.

# 4. Plan de validación Railway

## 4.1 Variables de entorno críticas

Revisar en Railway Dashboard sin imprimir secretos completos:

```txt
ENVIRONMENT
DATABASE_URL
SECRET_KEY
BACKEND_URL
CORS_ALLOW_ORIGINS
EMISSION_MODE_DEFAULT
EMISSION_WORKER_CONCURRENCY
EMISSION_WORKER_POLL_SECONDS
SMARTPSE_BASE_URL
SMARTPSE_API_TOKEN
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_STORAGE_BUCKET
INIT_DB_ON_STARTUP
```

Reglas:

- `INIT_DB_ON_STARTUP` debe estar apagado o falso en producción.
- `EMISSION_MODE_DEFAULT` debería ser `async`.
- No imprimir `DATABASE_URL`, `SECRET_KEY`, tokens ni service role key.
- `CORS_ALLOW_ORIGINS` debe incluir el dominio actual de Vercel.
- `ENVIRONMENT` debe ser `production` o equivalente, no `local`.

CLI seguro si Railway está autenticado:

```bash
railway variables --json \
  | jq 'with_entries(if (.key|test("SECRET|TOKEN|KEY|DATABASE_URL")) then .value="<redacted>" else . end)'
```

## 4.2 Health check

```bash
curl -i https://<RAILWAY_BACKEND_URL>/health
```

Criterio:

- HTTP 200.
- JSON con `status: "ok"`.
- `environment` esperado.
- Sin errores nuevos en logs Railway.

## 4.3 Smoke tests API autenticados

```bash
curl -i -H "Authorization: Bearer <TOKEN>" "https://<RAILWAY_BACKEND_URL>/clientes/page?limit=15"
curl -i -H "Authorization: Bearer <TOKEN>" "https://<RAILWAY_BACKEND_URL>/clientes/search?q=test&limit=20"
curl -i -H "Authorization: Bearer <TOKEN>" "https://<RAILWAY_BACKEND_URL>/productos/page?limit=15"
curl -i -H "Authorization: Bearer <TOKEN>" "https://<RAILWAY_BACKEND_URL>/productos/search?q=test&limit=20"
curl -i -H "Authorization: Bearer <TOKEN>" "https://<RAILWAY_BACKEND_URL>/cobranza/resumen"
curl -i -H "Authorization: Bearer <TOKEN>" "https://<RAILWAY_BACKEND_URL>/cobranza/vencidas?limit=5"
```

Criterios:

- No 500.
- No timeouts.
- No errores de tenant isolation.
- Respuestas compatibles con frontend.
- `search` devuelve `[]` con query corta si aplica.
- Logs limpios tras cada request.

## 4.4 Worker/cola fiscal

Validar si existe servicio separado en Railway:

- Revisar servicios del proyecto: API backend y worker.
- Si no hay worker separado, documentar riesgo: emisión/PDF compite con requests API.

SQL de cola:

```sql
SELECT status, count(*) AS total, min(created_at) AS oldest_created_at, min(available_at) AS oldest_available_at
FROM document_emission_jobs
GROUP BY status
ORDER BY status;
```

Jobs colgados:

```sql
SELECT id, tenant_id, resource_type, resource_id, action, status, attempts, locked_at, processing_started_at, last_error
FROM document_emission_jobs
WHERE status = 'processing'
  AND coalesce(processing_started_at, locked_at) < now() - interval '15 minutes'
ORDER BY coalesce(processing_started_at, locked_at) ASC;
```

Errores recientes:

```sql
SELECT id, tenant_id, action, status, attempts, max_attempts, updated_at, left(last_error, 300) AS error
FROM document_emission_jobs
WHERE status IN ('retry', 'failed')
ORDER BY updated_at DESC
LIMIT 50;
```

Métricas:

- `queued` count.
- `retry` count.
- `failed` count.
- oldest queued age.
- oldest processing age.
- attempts promedio.
- tiempo enqueue -> succeeded.
- errores Smart PSE/SUNAT.

## 4.5 Logs y alertas Railway

Checklist:

- errores 500.
- timeouts DB.
- pool agotado.
- errores Smart PSE.
- errores de generación PDF.
- errores Supabase Storage.
- errores CORS.
- reinicios del servicio.
- memoria alta sostenida.
- workers sin logs de procesamiento.

# 5. Plan de validación Vercel

## 5.1 Variables frontend

Validar variable real usada por `frontend/src/lib/utils/config.js`:

```txt
VITE_API_URL=https://<RAILWAY_BACKEND_URL>
```

Nota: si existe `VITE_API_BASE_URL`, no basta; el código actual lee `VITE_API_URL`.

Validar en Vercel Dashboard:

- Production env var `VITE_API_URL`.
- Preview env var si se usa staging.
- Último deploy construido después de configurar la variable.

## 5.2 Smoke test UI

Checklist manual:

1. Abrir login.
2. Iniciar sesión.
3. Abrir dashboard.
4. Abrir clientes.
5. Buscar cliente.
6. Abrir productos.
7. Buscar producto.
8. Abrir cotizaciones.
9. Crear/editar cotización.
10. Buscar cliente por documento o razón social.
11. Buscar producto por SKU o nombre.
12. Confirmar que se llaman `/clientes/search` y `/productos/search`.
13. Confirmar que no se carga todo el catálogo innecesariamente.
14. Confirmar que no hay errores en consola.
15. Confirmar que no hay errores CORS.
16. Confirmar que al tipear rápido no se disparan requests excesivos.

## 5.3 DevTools Network

Revisar:

- Status codes 2xx/4xx esperados, cero 500.
- Payloads no contienen datos de otro tenant.
- Headers CORS permiten el dominio Vercel.
- No hay duplicación excesiva de requests.
- Requests anteriores aparecen cancelados/reemplazados al tipear rápido.
- Tiempos de respuesta de autocomplete idealmente bajo 500 ms p95.
- `/clientes/page` y `/productos/page` usan `limit=15` salvo pantallas específicas.

## 5.4 Rollback Vercel

Plan:

- En Vercel Dashboard, abrir Project -> Deployments.
- Identificar deploy estable anterior al commit `5270d8c`.
- Usar "Promote to Production" o rollback del deploy anterior.
- Validar después del rollback:
  - login.
  - dashboard.
  - cotizaciones.
  - CORS.
  - llamadas API apuntan al backend esperado.
  - no errores JS.

# 6. Plan de validación funcional end-to-end

## 6.1 Flujo cliente/producto/cotización

- Login con usuario tenant normal.
- Crear cliente.
- Buscar cliente en cotización por documento.
- Buscar cliente en cotización por razón social.
- Crear producto.
- Buscar producto en línea de cotización por SKU.
- Buscar producto en línea de cotización por nombre.
- Crear cotización.
- Ver PDF o generación de PDF si aplica.
- Confirmar que datos visibles pertenecen al tenant autenticado.

## 6.2 Flujo fiscal básico

Solo si hay ambiente staging preparado:

- Convertir cotización a factura/boleta con autorización explícita.
- Confirmar job async en `document_emission_jobs`.
- Confirmar transición `queued` -> `processing` -> `succeeded` o error controlado.
- Confirmar estado fiscal del documento.
- Confirmar artifact/PDF/XML.
- Confirmar que no duplica correlativo.
- Confirmar que no reemite si ya tiene fiscal asociado.

No ejecutar emisión real en producción sin autorización explícita.

## 6.3 Flujo cobranza

- Ver dashboard.
- Ver `/cobranza/resumen`.
- Ver `/cobranza/vencidas`.
- Registrar pago solo si staging lo permite.
- Confirmar saldo, estado parcial/pagado/vencido y que no afecta pagos SaaS del tenant.

## 6.4 Flujo reportes

- Descargar reporte mensual.
- Confirmar que contiene documentos fiscales correctos.
- Confirmar notas de crédito/débito con signo fiscal correcto.
- Confirmar que filtros respetan tenant.

# 7. Plan de pruebas de performance

## Nivel 1: Smoke performance

Ejecutar manualmente y registrar tiempos:

- 10 búsquedas de cliente.
- 10 búsquedas de producto.
- Dashboard 5 veces.
- Cobranza resumen 5 veces.

Registrar:

- p50/p95 aproximado.
- errores 5xx.
- timeouts.
- logs DB.

## Nivel 2: Carga moderada

Usar `k6` con token de staging:

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '3m',
  thresholds: {
    'http_req_failed': ['rate<0.01'],
    'http_req_duration{type:search}': ['p(95)<500'],
    'http_req_duration{type:page}': ['p(95)<800'],
    'http_req_duration{type:cobranza}': ['p(95)<1200'],
  },
};

const base = __ENV.BASE_URL;
const token = __ENV.TOKEN;

export default function () {
  const headers = { Authorization: `Bearer ${token}` };

  http.get(`${base}/clientes/search?q=test&limit=20`, { headers, tags: { type: 'search' } });
  http.get(`${base}/productos/search?q=test&limit=20`, { headers, tags: { type: 'search' } });
  http.get(`${base}/clientes/page?limit=15`, { headers, tags: { type: 'page' } });
  http.get(`${base}/productos/page?limit=15`, { headers, tags: { type: 'page' } });
  http.get(`${base}/cobranza/resumen`, { headers, tags: { type: 'cobranza' } });
  http.get(`${base}/cobranza/vencidas?limit=5`, { headers, tags: { type: 'cobranza' } });

  sleep(1);
}
```

Ejecutar:

```bash
BASE_URL="https://<RAILWAY_BACKEND_URL>" TOKEN="<TOKEN>" k6 run inkora-smoke.js
```

Thresholds sugeridos:

- p95 search < 500 ms.
- p95 page < 800 ms.
- p95 cobranza resumen < 1200 ms.
- sin errores 5xx.
- sin saturación de DB/pool.

No inventar resultados.

# 8. Plan de monitoreo

Backend:

- request duration p50/p95/p99.
- status codes.
- DB pool usage.
- DB query latency.
- cola fiscal depth.
- oldest queued job age.
- failed/retry jobs.
- errores proveedor fiscal.
- errores PDF/storage.

Frontend:

- errores JS.
- API failures.
- tiempo de carga dashboard.
- errores CORS.
- tiempos autocomplete.

Supabase:

- CPU.
- RAM.
- conexiones.
- queries lentas.
- locks.
- tamaño DB.
- índices usados/no usados.

Railway:

- CPU.
- memoria.
- restart count.
- logs 500.
- DB timeout.
- worker health.

Vercel:

- build status.
- runtime errors.
- deployment rollbacks.

# 9. Plan de rollback general

Vercel:

- Promover deploy anterior estable.
- Validar login, dashboard, cotizaciones, autocomplete y consola.

Railway:

- Redeploy del build anterior desde Railway.
- Validar `/health`.
- Validar endpoints autenticados.
- Revisar logs por 30 minutos.

Migraciones opcionales:

- Dropear índices `pg_trgm` opcionales con `DROP INDEX CONCURRENTLY IF EXISTS`.
- No dropear extensión sin revisar dependencias.

Si fallan endpoints search:

- Confirmar backend logs.
- Confirmar SQL/indexes.
- Rollback Railway si hay 500/timeouts.
- El frontend conserva fallback local parcial, pero no debe considerarse solución estable.

Si dashboard/cobranza se vuelve lento:

- Ejecutar `EXPLAIN ANALYZE`.
- Revisar Supabase slow queries.
- Verificar índices core.
- Rollback backend si el endpoint degrada producción.

Si hay error fiscal:

- Detener pruebas fiscales.
- No reemitir manualmente.
- Revisar `document_emission_jobs`, correlativo, estado del documento y respuesta proveedor.
- Escalar con payload/logs sanitizados.

Si CORS falla:

- Validar `CORS_ALLOW_ORIGINS` en Railway.
- Validar dominio exacto de Vercel.
- Redeploy backend si la variable cambió.
- No abrir CORS con `*` en producción si hay credenciales.

# 10. Riesgos pendientes

- `pytest` completo aún tiene 5 fallas fuera de scope.
- `pg_trgm` depende de permisos en Supabase.
- PDF/artifacts pueden seguir usando BackgroundTasks en algunas rutas.
- Correlativos aún pueden ser hotspot si no se migraron a tabla contador.
- Cache DNI/RUC y Smart PSE sigue siendo en memoria si no se cambió.
- Si no hay worker separado en Railway, emisión/PDF puede competir con API.
- Validación fiscal real requiere credenciales y autorización.
- Worktree local inspeccionado tiene cambios no relacionados; no deben mezclarse con validación/deploy.

# 11. Criterios de éxito

Se puede declarar estable cuando:

- Migración core aplicada y validada.
- Backend Railway health OK.
- Endpoints search/page/cobranza OK.
- Frontend Vercel consume API correcta (`VITE_API_URL`).
- Autocomplete remoto funciona.
- No hay errores CORS.
- No hay errores 500 relevantes.
- Logs limpios durante 24h o una jornada operativa.
- Flujo cotización funciona.
- Si staging fiscal existe, emisión async validada.
- Plan de rollback documentado y probado al menos en staging.

# 12. Entregable final

Este documento es el entregable operativo `POST_DEPLOY_VALIDATION_PLAN.md`.

Resumen del plan:

- Validar Supabase primero: backups, `001`, opcional `002`, índices y `EXPLAIN`.
- Validar Railway: variables, health, endpoints críticos, worker/cola y logs.
- Validar Vercel: `VITE_API_URL`, UI smoke, Network y rollback.
- Ejecutar flujos end-to-end y pruebas de performance.
- Activar monitoreo y criterios de estabilidad.

Comandos principales:

```bash
psql "$DATABASE_URL" -f backend/migrations/001_scalability_indexes.sql
psql "$DATABASE_URL" -f backend/migrations/002_optional_pg_trgm_indexes.sql
curl -i https://<RAILWAY_BACKEND_URL>/health
curl -i -H "Authorization: Bearer <TOKEN>" "https://<RAILWAY_BACKEND_URL>/clientes/page?limit=15"
curl -i -H "Authorization: Bearer <TOKEN>" "https://<RAILWAY_BACKEND_URL>/clientes/search?q=test&limit=20"
curl -i -H "Authorization: Bearer <TOKEN>" "https://<RAILWAY_BACKEND_URL>/productos/page?limit=15"
curl -i -H "Authorization: Bearer <TOKEN>" "https://<RAILWAY_BACKEND_URL>/productos/search?q=test&limit=20"
curl -i -H "Authorization: Bearer <TOKEN>" "https://<RAILWAY_BACKEND_URL>/cobranza/resumen"
curl -i -H "Authorization: Bearer <TOKEN>" "https://<RAILWAY_BACKEND_URL>/cobranza/vencidas?limit=5"
BASE_URL="https://<RAILWAY_BACKEND_URL>" TOKEN="<TOKEN>" k6 run inkora-smoke.js
```

Validaciones que requieren credenciales:

- Supabase SQL/backup/EXPLAIN.
- Railway variables/logs.
- Token JWT tenant para smoke tests API.
- Vercel env vars/deploy rollback.
- Smart PSE/SUNAT y Supabase Storage para flujo fiscal real.

Ejecutar primero:

1. Backup Supabase.
2. Validar/aplicar `001_scalability_indexes.sql`.
3. Validar health Railway.
4. Smoke API autenticado.
5. Smoke UI Vercel.
6. Performance smoke.
7. Monitoreo 24h.

Riesgos que bloquearían producción:

- Health Railway falla.
- Migración core incompleta.
- 500/timeouts en search/page/cobranza.
- Tenant isolation incorrecto.
- CORS roto en Vercel.
- Worker fiscal ausente o cola acumulándose sin procesamiento.
- Errores fiscales reales sin diagnóstico seguro.
- Logs con pool agotado o DB timeouts sostenidos.
