# CODEX TASK — Escalabilidad Inkora PSE

Repositorio: `hkrojas/inkora_pse`
Objetivo: resolver primero los problemas críticos de escalabilidad del **backend**, luego ajustar el **frontend** para consumir las mejoras, y finalmente validar en **Supabase + Railway + Vercel**.

> Importante: no hagas un rediseño visual ni una reescritura completa. Prioriza cambios pequeños, medibles, reversibles e incrementales. Mantén el scope del launch product: SaaS vertical para imprentas en Perú con flujo cliente → cotización → comprobante → guía → cobranza → reporte.

---

## 0. Regla principal de ejecución

Trabaja en este orden exacto:

1. Backend.
2. Pruebas backend locales.
3. Frontend solo para consumir nuevas APIs o reducir carga.
4. Pruebas frontend locales.
5. Validación en Supabase.
6. Validación en Railway.
7. Validación en Vercel.
8. Reporte final con evidencia.

No empieces por UI. No optimices estilos. No agregues features nuevas si no reducen carga, latencia o riesgo operativo.

---

## 1. Contexto técnico conocido

Backend:
- FastAPI
- SQLAlchemy
- PostgreSQL/Supabase
- Cola durable de emisión fiscal
- Integración Smart PSE / SUNAT / ApisPeru
- Generación PDF y reportes Excel

Frontend:
- React 18
- Vite
- Tailwind
- SPA con React Router

Problemas críticos identificados:
- Dashboard/cobranza con N+1 queries y carga completa en memoria.
- Endpoints `/clientes/page` y `/productos/page` hacen múltiples `COUNT` por request.
- Búsquedas con `ILIKE '%term%'` sin estrategia clara de índices.
- Autocompletados de clientes/productos filtran en memoria.
- Correlativos pueden volverse hotspot bajo concurrencia.
- Cola de emisión fiscal existe, pero PDF/artifacts siguen mezclados con request/background tasks.
- Falta validación final real en ambientes Railway, Supabase y Vercel.

---

# FASE 1 — Backend: base de datos e índices

## 1.1 Revisar modelos y queries críticas

Inspecciona estos archivos primero:

- `backend/crud/reportes.py`
- `backend/routers/reportes.py`
- `backend/routers/dashboard.py`
- `backend/routers/clientes.py`
- `backend/routers/productos.py`
- `backend/crud/clientes.py`
- `backend/crud/productos.py`
- `backend/crud/_cotizaciones_shared.py`
- `backend/crud/emission_jobs.py`
- `backend/models/cotizaciones.py`
- `backend/models/clientes.py`
- `backend/models/productos.py`
- `backend/models/emission_jobs.py`

Entrega un diagnóstico corto antes de tocar código:
- Qué queries son más caras.
- Qué endpoints escalan peor.
- Qué índices faltan.
- Qué cambios harás primero.

## 1.2 Crear migraciones SQL idempotentes

Si el proyecto no tiene Alembic configurado, no actives `INIT_DB_ON_STARTUP` en producción.

Crea una carpeta clara para migraciones SQL manuales, por ejemplo:

```txt
backend/migrations/
  001_scalability_indexes.sql
  README.md
```

La migración debe ser idempotente usando `CREATE INDEX IF NOT EXISTS`.

Agregar, como mínimo, índices para:

```sql
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

-- Cola de emisión
CREATE INDEX IF NOT EXISTS idx_emission_jobs_claim
ON document_emission_jobs (status, available_at, priority, created_at);
```

Si PostgreSQL permite `pg_trgm`, agregar opcionalmente:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_clientes_razon_social_trgm
ON clientes USING gin (razon_social gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_clientes_numero_documento_trgm
ON clientes USING gin (numero_documento gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_productos_nombre_trgm
ON productos USING gin (nombre gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_productos_codigo_interno_trgm
ON productos USING gin (codigo_interno gin_trgm_ops);
```

Si Supabase no permite alguna extensión o índice, documenta el error y deja fallback seguro.

## Criterios de aceptación Fase 1

- Existe migración SQL idempotente.
- No se usa `create_all` en producción.
- Los índices están alineados a queries reales.
- Hay instrucciones claras para aplicar en Supabase.

---

# FASE 2 — Backend: eliminar N+1 en cobranza/dashboard

## 2.1 Refactor de `get_cobranza_resumen`

Actualmente el resumen carga documentos y calcula balances por documento. Reemplázalo por queries agregadas en SQL.

Objetivo del endpoint:

```txt
GET /cobranza/resumen
```

Debe devolver:
- `total_por_cobrar`
- `total_vencido`
- `total_pagado_mes`
- `documentos_pendientes`
- `documentos_vencidos`
- `documentos_pagados_mes`
- `clientes_con_deuda`

Hazlo con agregaciones, joins y subqueries, no con loops sobre todos los documentos.

## 2.2 Refactor de `get_cobranza_vencida`

Actualmente pagina en memoria. Debe paginar en SQL.

Objetivo:

```txt
GET /cobranza/vencidas?skip=0&limit=25&q=&scope=overdue
```

Debe:
- Filtrar por tenant en DB.
- Calcular saldo en DB o mediante subquery agregada.
- Aplicar `ORDER BY fecha_vencimiento ASC`.
- Aplicar `OFFSET/LIMIT` en DB.
- No recorrer todos los comprobantes del tenant en Python.

## 2.3 Mantener compatibilidad de respuesta

No rompas los schemas existentes:
- `CobranzaResumenResponse`
- `CobranzaVencidaItem`

Si necesitas agregar campos, que sean opcionales.

## Criterios de aceptación Fase 2

- No hay loops Python sobre todos los documentos fiscales para resumen.
- No hay paginación en memoria para vencidas.
- Los tests cubren documentos:
  - pagados
  - parcialmente pagados
  - vencidos
  - no vencidos
  - notas de crédito/débito si afectan saldo
- El dashboard sigue cargando.

---

# FASE 3 — Backend: clientes/productos page y search

## 3.1 Reducir múltiples COUNT

Refactoriza:

```txt
GET /clientes/page
GET /productos/page
```

Problema actual:
- Cada request calcula varios contadores con queries separadas.
- Luego calcula total.
- Luego trae items.

Objetivo:
- Una query para `counts` usando agregación condicional.
- Una query para `items`.
- Evitar repetir filtros.
- Mantener respuesta compatible.

Ejemplo conceptual PostgreSQL:

```sql
COUNT(*) FILTER (WHERE condicion) AS campo
```

Si necesitas compatibilidad SQLAlchemy portable, usa `func.sum(case(...))`.

## 3.2 Crear endpoints de búsqueda remota

Agregar endpoints nuevos, sin romper los existentes:

```txt
GET /clientes/search?q=...&limit=20
GET /productos/search?q=...&limit=20
```

Reglas:
- `q` máximo 80 caracteres.
- `limit` máximo 50.
- Si `q` tiene menos de 2 caracteres, devolver lista vacía.
- Filtrar siempre por `tenant_id`.
- Ordenar por coincidencia útil:
  - documento/código exacto primero
  - prefijo después
  - nombre/razón social después
- No devolver más campos de los necesarios para autocompletado.

Clientes:
- `id`
- `tipo_documento`
- `numero_documento`
- `razon_social`
- `nombre_comercial`
- `email`
- `telefono`
- `whatsapp`
- `direccion`
- `ubigeo`
- `condicion_pago`

Productos:
- `id`
- `codigo_interno`
- `nombre`
- `descripcion`
- `precio_unitario`
- `valor_unitario`
- `moneda`
- `unidad_medida`
- `tipo_afectacion_igv`

## Criterios de aceptación Fase 3

- `/clientes/page` y `/productos/page` siguen funcionando.
- Nuevos endpoints search funcionan con tenant isolation.
- Tests cubren:
  - búsqueda vacía
  - búsqueda corta
  - búsqueda por documento/código
  - búsqueda por nombre
  - límite máximo
  - aislamiento por tenant

---

# FASE 4 — Backend: correlativos y cola fiscal

## 4.1 Evaluar correlativos

Revisa uso de:

```txt
_next_quote_identity
_next_correlativo_for_series
_next_note_correlativo
```

Actualmente se usa patrón `ORDER BY correlativo DESC WITH FOR UPDATE`.

Propuesta preferida:
- Crear tabla de contadores por `tenant_id + serie`.
- Usar `UPDATE ... RETURNING` para reservar correlativo.
- Mantener unique constraint actual como última defensa.

Tabla sugerida:

```sql
CREATE TABLE IF NOT EXISTS tenant_document_counters (
  tenant_id INTEGER NOT NULL,
  serie VARCHAR NOT NULL,
  next_correlativo INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  PRIMARY KEY (tenant_id, serie)
);
```

Reserva sugerida:

```sql
INSERT INTO tenant_document_counters (tenant_id, serie, next_correlativo)
VALUES (:tenant_id, :serie, 2)
ON CONFLICT (tenant_id, serie)
DO UPDATE SET
  next_correlativo = tenant_document_counters.next_correlativo + 1,
  updated_at = now()
RETURNING next_correlativo - 1;
```

Si haces este cambio, incluye migración y tests de concurrencia.

Si no lo haces en esta iteración, deja issue documentado y al menos agrega índices que reduzcan el costo del patrón actual.

## 4.2 Cola de emisión

No reescribas toda la cola si ya funciona. Revisa:

```txt
backend/services/emission_queue_service.py
backend/crud/emission_jobs.py
```

Asegura:
- `claim_next_emission_job` aprovecha índice compuesto.
- No se bloquean jobs innecesariamente.
- Hay métricas o endpoint de inspección para:
  - cantidad queued
  - cantidad retry
  - oldest queued job age
  - processing colgados

Si agregas endpoint, protegerlo para superadmin/ops.

## 4.3 Separar PDF/artifacts de request cuando sea posible

Donde veas:

```python
background_tasks.add_task(pdf_storage_service.process_pdf_background, ...)
```

Evalúa moverlo a job durable. Si es mucho cambio, no lo fuerces ahora; deja el diseño y migra solo lo más seguro.

## Criterios de aceptación Fase 4

- Correlativos no empeoran.
- La cola usa índice compuesto.
- No se rompe emisión fiscal.
- Si se modifica correlativo, hay test concurrente.

---

# FASE 5 — Backend: pruebas locales

Ejecutar:

```bash
cd backend
pytest
```

Agregar o actualizar tests para:

```txt
test_cobranza_resumen_scalable.py
test_cobranza_vencidas_pagination.py
test_clientes_search.py
test_productos_search.py
test_page_counts_optimized.py
test_emission_jobs_claim.py
```

Pruebas mínimas:
- Crear dos tenants.
- Crear clientes/productos/documentos para ambos tenants.
- Confirmar que endpoints no cruzan datos.
- Confirmar paginación.
- Confirmar saldos.
- Confirmar que búsqueda no devuelve todo con query corta.
- Confirmar que endpoints responden con schemas compatibles.

Si existen pruebas previas, no las dupliques innecesariamente; extiéndelas.

---

# FASE 6 — Frontend: consumir backend optimizado

Solo después de backend.

## 6.1 Cambiar autocompletados a búsqueda remota

Actualizar:

```txt
frontend/src/components/ui/ClientCombobox.jsx
frontend/src/components/ui/ProductLineCell.jsx
```

Objetivo:
- No depender de cargar todos los clientes/productos.
- Buscar remoto con debounce.
- Cancelar request anterior.
- Cachear resultados por query simple si no agregas TanStack Query.
- Mantener compatibilidad con props existentes si otras pantallas las usan.

Servicios nuevos:

```txt
frontend/src/services/clientes.js
frontend/src/services/productos.js
```

Agregar:

```js
search: (q, limit = 20) => api.get(`/clientes/search?q=${encodeURIComponent(q)}&limit=${limit}`)
```

y equivalente para productos.

## 6.2 Cancelar requests obsoletos en páginas de listas

Actualizar:

```txt
ClientesPage.jsx
ProductosPage.jsx
```

Pasar `AbortController.signal` a `api.get` para cancelar búsquedas anteriores.

## 6.3 Dashboard

Ideal:
- Si backend agrega endpoint agregado `/dashboard/summary`, usarlo.
- Si no, evitar retry inmediato duplicado.
- Mantener estado parcial.

## Criterios de aceptación Fase 6

- Crear cotización no requiere cargar todo el catálogo.
- Autocompletados funcionan con 2+ caracteres.
- No hay requests viejos activos al tipear rápido.
- Build Vite pasa.

---

# FASE 7 — Frontend: pruebas locales

Ejecutar:

```bash
cd frontend
npm install
npm run build
npm run lint
```

Si hay Playwright configurado, agregar smoke tests básicos:

- Login.
- Ir a clientes.
- Buscar cliente.
- Ir a productos.
- Buscar producto.
- Crear cotización o abrir pantalla de cotización.
- Verificar que autocompletado remoto responde.

No agregar pruebas frágiles de estilo visual.

---

# FASE 8 — Validación en Supabase

## 8.1 Antes de aplicar cambios

Confirmar:
- Backup disponible.
- Proyecto correcto.
- Ambiente correcto: staging antes que producción.
- `DATABASE_URL` no apunta a base equivocada.
- Si se usa Supavisor/PgBouncer, confirmar modo de conexión.

## 8.2 Aplicar migraciones

Ejecutar SQL idempotente en Supabase SQL Editor o vía CLI.

Validar:

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

Si se agregó `pg_trgm`:

```sql
SELECT * FROM pg_extension WHERE extname = 'pg_trgm';
```

## 8.3 EXPLAIN ANALYZE

Ejecutar `EXPLAIN ANALYZE` para:
- búsqueda clientes
- búsqueda productos
- cobranza resumen
- cobranza vencidas
- claim de emission jobs

Documentar antes/después si hay datos suficientes.

## Criterios Supabase

- Migración aplicada sin error.
- Índices visibles.
- Queries críticas usan índices o al menos reducen costo.
- No se afectó tenant isolation.

---

# FASE 9 — Validación en Railway

## 9.1 Variables de entorno

Confirmar en Railway backend:

```txt
ENVIRONMENT=staging|production
DATABASE_URL=...
SECRET_KEY=...
BACKEND_URL=...
CORS_ALLOW_ORIGINS=...
EMISSION_MODE_DEFAULT=async
EMISSION_WORKER_CONCURRENCY=...
EMISSION_WORKER_POLL_SECONDS=...
SMARTPSE_BASE_URL=...
SMARTPSE_API_TOKEN=...
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_STORAGE_BUCKET=...
```

Reglas:
- No activar `INIT_DB_ON_STARTUP` en producción.
- No imprimir secretos.
- No commitear `.env`.

## 9.2 Servicios Railway

Idealmente separar:
- API backend
- Worker de emisión fiscal

Si solo existe un servicio, documentar limitación y riesgo.

## 9.3 Smoke tests Railway

Con backend desplegado:

```bash
curl -i https://<backend-railway-url>/health
```

Luego probar endpoints autenticados con token real de staging:

```bash
curl -i https://<backend>/clientes/page?limit=15
curl -i "https://<backend>/clientes/search?q=test&limit=20"
curl -i "https://<backend>/productos/search?q=test&limit=20"
curl -i https://<backend>/cobranza/resumen
curl -i https://<backend>/cobranza/vencidas?limit=5
```

Validar en logs Railway:
- No hay errores 500.
- No hay timeouts.
- No hay saturación de DB pool.
- No hay errores de CORS.

## 9.4 Worker

Si existe worker:
- Encolar job de prueba controlado si staging lo permite.
- Verificar que cambia de `queued` a `processing` y luego `succeeded` o `failed` con error claro.
- Verificar que no queda colgado.

## Criterios Railway

- Backend responde health.
- Endpoints críticos responden.
- Logs limpios.
- Worker operativo o limitación documentada.
- Latencia razonable para dashboard/cobranza.

---

# FASE 10 — Validación en Vercel

## 10.1 Variables Vercel

Confirmar:

```txt
VITE_API_BASE_URL=https://<backend-railway-url>
```

o la variable real usada por `frontend/src/lib/utils/config.js`.

## 10.2 Build

Ejecutar build local y verificar build Vercel.

```bash
cd frontend
npm run build
```

## 10.3 Smoke tests Vercel

En URL de Vercel:
- Abrir login.
- Login con usuario staging.
- Abrir dashboard.
- Abrir clientes.
- Buscar cliente.
- Abrir productos.
- Buscar producto.
- Abrir cotizaciones.
- Probar autocompletado remoto cliente/producto.
- Confirmar que no hay errores CORS.
- Confirmar que no hay requests duplicados excesivos al tipear.

Usar DevTools:
- Network
- Console
- Performance básico

## Criterios Vercel

- Build exitoso.
- Login exitoso.
- Dashboard carga.
- Autocompletados usan endpoints remotos.
- No hay errores CORS.
- No hay errores JS visibles.
- No se carga catálogo completo innecesariamente.

---

# FASE 11 — Reporte final obligatorio

Al terminar, entrega un resumen con:

## Cambios realizados

Formato:

```txt
Backend:
- ...
Frontend:
- ...
DB/Supabase:
- ...
Deploy:
- ...
```

## Archivos modificados

Listar archivos.

## Pruebas ejecutadas

Incluir comandos y resultado:

```txt
pytest: PASS/FAIL
npm run build: PASS/FAIL
npm run lint: PASS/FAIL
Railway health: PASS/FAIL
Supabase migration: PASS/FAIL
Vercel smoke: PASS/FAIL
```

## Evidencia

Incluir:
- URLs de deploy usadas.
- Capturas de logs o resumen textual.
- Resultados relevantes de EXPLAIN si se obtuvieron.
- Latencia antes/después si se midió.

## Riesgos pendientes

No ocultar pendientes. Ejemplos:
- Correlativos aún usan patrón anterior.
- PDF generation sigue usando BackgroundTasks.
- Falta cache distribuido.
- Falta Alembic formal.
- Falta worker separado en Railway.

---

# Notas importantes para Codex

- No tocar secretos.
- No cambiar reglas fiscales sin tests.
- No romper tenant isolation.
- No cambiar schemas públicos salvo que sea necesario y compatible.
- No hacer refactor masivo.
- Preferir SQL claro y testeable.
- Mantener errores claros para operaciones fiscales.
- Cualquier migración debe ser idempotente.
- Si algo requiere credenciales Railway/Supabase/Vercel y no tienes acceso, deja instrucciones exactas y comandos para que el dueño las ejecute.

---

# ¿Hace falta una skill?

No es necesario crear una skill para esta tarea.

Usa este Markdown como prompt operativo para Codex.
Una skill tendría sentido solo si vas a repetir muchas veces el mismo tipo de trabajo en varios repositorios o si quieres estandarizar una metodología permanente.

Para este caso, lo más útil es:

1. Guardar este archivo como `CODEX_BACKEND_SCALABILITY_TASK.md`.
2. Pasárselo a Codex.
3. Si quieres reglas permanentes del repo, resumir las reglas más importantes dentro de `AGENTS.md`.
4. Mantener este archivo como plan de ejecución puntual, no como documentación eterna del producto.
