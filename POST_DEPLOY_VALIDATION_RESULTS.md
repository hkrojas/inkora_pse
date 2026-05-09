# POST DEPLOY VALIDATION RESULTS - Inkora PSE

## 1. Datos generales
- Fecha/hora: 2026-05-08 16:36:59 America/Lima (21:36:59 GMT); Supabase, Vercel y Railway revalidados durante la misma jornada.
- Repo: `hkrojas/inkora_pse`
- Branch: `validation/post-deploy`
- Commit validado local: rama `validation/post-deploy` con reporte actualizado; incluye base remota `653e229 Update post-deploy validation evidence`.
- Backend Railway URL: `https://inkorapse-production.up.railway.app`
- Frontend Vercel URL: `https://inkora-pse.vercel.app`
- Supabase project/environment: `inkora_pse` (`wiezwkosiuczpnbnvmef`), `ACTIVE_HEALTHY`, region `us-east-1`, PostgreSQL `17.6.1.113`
- Responsable de validacion: Codex

## 2. Resultado ejecutivo
- Estado general: PASS
- Resumen: backend focal PASS, frontend build/lint PASS, Railway `/health` PASS, Vercel production deploy PASS y CORS preflight desde Vercel hacia search endpoints PASS. Supabase fue validado desde el dashboard autenticado y via `psql`: el proyecto esta activo y `pg_trgm` esta instalado. Se genero un dump logico manual valido, el operador autorizo continuar manualmente sin PITR gestionado, y se aplicaron/validaron las migraciones `001` y `002` con los 14 indices core y 4 indices trigram esperados. Tambien se ejecuto smoke API autenticado, smoke UI Vercel autenticado, performance smoke con runner Node, revision Railway de variables visibles y revision Railway de logs recientes.
- Bloqueadores: ninguno para la validacion post-deploy operativa.
- Riesgos no bloqueantes: Supabase Free Plan no incluye backups/PITR gestionados; `pytest` completo falla en 3 tests fuera de scope; `npm ci` reporta 1 vulnerabilidad moderada en dependencias; backend Railway responde con `environment: "staging"` aunque el entorno Railway visible se llama `production`; Vercel ya tiene `VITE_API_URL` explicito en Production y Development, pero Preview no quedo configurado globalmente por requerimiento de rama de Vercel CLI; no se observo un worker fiscal separado en Railway; logs Railway muestran un warning no bloqueante de cache de tipo de cambio SUNAT.
- Proximas acciones: limpiar tenants temporales solo con autorizacion explicita de borrado; evaluar habilitar PITR/Pro antes de operar con clientes reales; revisar `ENVIRONMENT`/`FISCAL_ENV` de Railway como cambio coordinado, no aislado; evaluar worker fiscal separado antes de carga fiscal real; monitorear warning de tipo de cambio SUNAT.

## 3. Validacion local
### Backend focal
Comando:

```powershell
cd backend
C:\Users\HP\Desktop\inkora_smartpse\backend\venv\Scripts\python.exe -m pytest test_tenant_page_endpoints.py test_scalability_indexes.py test_reportes.py -q
```

Resultado:

- PASS: `24 passed in 10.48s`.
- Nota: `python` global fallo previamente por dependencia faltante (`ModuleNotFoundError: No module named 'slowapi'`), por eso se uso el virtualenv existente como runtime manteniendo `workdir` en el worktree limpio.

### Backend completo
Comando:

```powershell
C:\Users\HP\Desktop\inkora_smartpse\backend\venv\Scripts\python.exe -m pytest -q
```

Resultado:

- PARTIAL: `419 passed, 3 failed, 12 warnings in 91.21s`.

Fallas conocidas fuera de scope:

- `test_apisperu_documentos_matrix.py::TestApisPeruDocumentosMatrix::test_guia_remision_usa_despatch_send_y_status`: credenciales GRE Smart PSE faltantes en fixture/test.
- `test_facturacion_fiscal.py::TestNotasParcialesFiscalBalance::test_nota_contra_documento_otro_tenant_devuelve_404`: llamada directa a endpoint decorado con SlowAPI sin `Request`.
- `test_guias_router.py::test_emitir_guia_propaga_error_fiscal_con_gre_configurada`: llamada directa a endpoint decorado con SlowAPI sin `Request`.

### Frontend build
Comando:

```powershell
cd frontend
npm run build
```

Resultado:

- PASS: `vite v6.4.2`, `1670 modules transformed`, `built in 6.11s`.
- Nota: el primer intento fallo porque el worktree limpio no tenia `node_modules`; se ejecuto `npm ci` en `frontend`, sin cambios versionados.
- `npm ci` reporto 1 vulnerabilidad moderada.

### Frontend lint
Comando:

```powershell
cd frontend
npm run lint
```

Resultado:

- PASS: `eslint src --ext .js,.jsx` termino con exit code 0.

## 4. Supabase
### 4.1 Backup/PITR
Resultado: PASS operativo con dump logico manual autorizado; riesgo aceptado por ausencia de backup/PITR gestionado.

Evidencia:

- Dashboard autenticado: `Backups | Database | Supabase`, proyecto `inkora_pse`, branch `main Production`.
- La pagina `database/backups/scheduled` muestra: `Free Plan does not include project backups. Upgrade to the Pro Plan for up to 7 days of scheduled backups.`
- El overview tambien mostraba `Last backup: No backups`.
- Autorizacion del operador: 2026-05-08 17:10 America/Lima, se autorizo continuar manualmente usando el dump logico como resguardo pre-DDL.
- Dump logico manual pre-DDL:
  - Herramientas locales: `pg_dump` y `pg_restore` disponibles.
  - Entorno local: `DATABASE_URL` no esta configurado; se uso `PGPASSWORD` temporal en la sesion de PowerShell y se elimino al finalizar.
  - Supabase `Database Settings` indica: `The database password isn't viewable after creation. Resetting it will break any existing connections.`
  - Modal `Connect` muestra URI con placeholder: `postgresql://postgres:[YOUR-PASSWORD]@db.wiezwkosiuczpnbnvmef.supabase.co:5432/postgres`.
  - Direct connection no usable desde esta red local porque el host directo resuelve solo IPv6.
  - Session pooler IPv4 `aws-1-us-east-1.pooler.supabase.com:5432` usable con password vigente provista por el operador.
  - Archivo generado fuera del repo: `C:\Users\HP\Desktop\inkora_backups\inkora_pse_pre_indexes_20260508-165311.dump`.
  - Tamano: `338573` bytes.
  - Formato: `CUSTOM`, `Compression: gzip`, `Dumped from database version: 17.6`, `Dumped by pg_dump version: 17.4`.
  - `pg_restore --list` completo: PASS, exit code `0`, `738` lineas en `C:\Users\HP\Desktop\inkora_backups\inkora_pse_pre_indexes_20260508-165311.list`.
  - SHA256: `408A3A0A8AA0698306086A9B7F03C7E09DEEAC2FD7F56DD9E1CE4943C9893AF6`.
  - No se reseteo la password porque romperia conexiones existentes y no fue autorizado explicitamente.
- Se aplicaron migraciones DDL despues del dump manual y autorizacion explicita.

### 4.2 Migracion core 001
Resultado: PASS

Evidencia:

- Proyecto identificado: `inkora_pse`, host `db.wiezwkosiuczpnbnvmef.supabase.co`, PostgreSQL `17.6.1.113`.
- Migracion aplicada por `psql` via Session Pooler IPv4:
  - `backend/migrations/001_scalability_indexes.sql`
  - Output: `CREATE INDEX` x14.
  - Exit code: `0`.
- SQL read-only ejecutado desde SQL Editor autenticado y revalidado con `psql` por Session Pooler IPv4 despues de aplicar DDL.
- Resultado resumido:
  - `database`: `postgres`
  - `db_user`: `postgres`
  - `postgres_version`: `17.6`
  - `core_indexes_present`: `14`
  - `core_indexes_expected`: `14`
  - `core_indexes_missing`: `0`
- La migracion core esta aplicada con los nombres esperados del plan.

### 4.3 Migracion opcional 002 pg_trgm
Resultado: PASS

Evidencia:

- `pg_trgm_installed`: `true`.
- Migracion aplicada por `psql` via Session Pooler IPv4:
  - `backend/migrations/002_optional_pg_trgm_indexes.sql`
  - Output: `CREATE EXTENSION` con notice `extension "pg_trgm" already exists, skipping`, y `CREATE INDEX` x4.
  - Exit code: `0`.
- `optional_trgm_indexes_present`: `4` de `4` con los nombres esperados por `002_optional_pg_trgm_indexes.sql`.
- Tambien existen indices GIN legacy equivalentes con prefijo `ix_*`; se mantienen sin cambios en esta fase:
  - `ix_clientes_razon_social_trgm`
  - `ix_clientes_numero_documento_trgm`
  - `ix_productos_nombre_trgm`
  - `ix_productos_codigo_trgm`

### 4.4 Indices visibles
Resultado: PASS para los nombres esperados `idx_*`; existen indices legacy `ix_*` adicionales.

SQL ejecutado:

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

Salida/resumen:

- Validacion posterior a DDL:
  - `core_indexes_present`: `14`
  - `core_indexes_expected`: `14`
  - `core_indexes_missing`: `0`
  - `optional_trgm_indexes_present`: `4`
  - `optional_trgm_indexes_missing`: `0`
- Indices `idx_*` visibles:
  - `clientes`: `idx_clientes_numero_documento_trgm`, `idx_clientes_razon_social_trgm`, `idx_clientes_tenant_numero_documento`, `idx_clientes_tenant_razon_social`.
  - `productos`: `idx_productos_codigo_interno_trgm`, `idx_productos_nombre_trgm`, `idx_productos_tenant_codigo_interno`, `idx_productos_tenant_nombre`.
  - `cotizaciones`: `idx_cotizaciones_tenant_cliente`, `idx_cotizaciones_tenant_fecha_vencimiento`, `idx_cotizaciones_tenant_kind_estado_fecha`, `idx_cotizaciones_tenant_source_kind_estado`.
  - `cotizacion_items`: `idx_cotizacion_items_cotizacion_id`, `idx_cotizacion_items_producto_id`.
  - `pagos`: `idx_pagos_tenant_fecha_pago`, `idx_pagos_tenant_fiscal_document`, `idx_pagos_tenant_source_quote`.
  - `document_emission_jobs`: `idx_emission_jobs_claim`.
- Conteos de tablas posteriores al smoke autenticado:
  - `tenants`: `4`
  - `users`: `4`
  - `clientes`: `1`
  - `productos`: `1`
  - `cotizaciones`: `1`
  - `cotizacion_items`: `1`
  - `pagos`: `0`
  - `document_emission_jobs`: `0`

### 4.5 EXPLAIN ANALYZE
Clientes documento: N/A como metrica representativa; solo existe dato minimo temporal de validacion (`clientes = 1`); indices esperados ya presentes.
Clientes razon social: N/A como metrica representativa; solo existe dato minimo temporal de validacion (`clientes = 1`); indices esperados ya presentes.
Productos SKU: N/A como metrica representativa; solo existe dato minimo temporal de validacion (`productos = 1`); indices esperados ya presentes.
Productos nombre: N/A como metrica representativa; solo existe dato minimo temporal de validacion (`productos = 1`); indices esperados ya presentes.
Cobranza resumen: N/A como metrica representativa; existe una cotizacion no fiscal y `pagos = 0`; indices esperados ya presentes.
Cobranza vencidas: N/A como metrica representativa; existe una cotizacion no fiscal; indices esperados ya presentes.
Claim jobs: N/A por `document_emission_jobs = 0`; indice core esperado `idx_emission_jobs_claim` ya presente.

Nota: la validacion de performance DB queda sin metricas representativas porque solo hay datos temporales minimos de validacion.

## 5. Railway
### 5.1 Variables criticas
Resultado: PASS con observaciones

Observaciones:

- Dashboard Railway autenticado revisado en navegador integrado.
- Proyecto visible: `truthful-flexibility`, entorno Railway visible `production`.
- Servicio visible: `inkora_pse`, estado `Online`, dominio `inkorapse-production.up.railway.app`, region `US East`, `1 Replica`.
- Deployment activo visible: `Update post-deploy validation evidence`, via GitHub, estado `Deployment successful`.
- Variables de servicio visibles sin revelar valores: `16 Service Variables`.
- Variables presentes por nombre:
  - `BACKEND_URL`
  - `DATABASE_URL`
  - `DB_MAX_OVERFLOW`
  - `DB_POOL_RECYCLE_SECONDS`
  - `DB_POOL_SIZE`
  - `DB_POOL_TIMEOUT_SECONDS`
  - `EMISSION_WORKER_CONCURRENCY`
  - `ENVIRONMENT`
  - `FIELD_ENCRYPTION_KEY`
  - `FISCAL_ENV`
  - `SECRET_KEY`
  - `SMARTPSE_BASE_URL`
  - `SMARTPSE_TIMEOUT_SECONDS`
  - `SUPABASE_KEY`
  - `SUPABASE_STORAGE_BUCKET`
  - `SUPABASE_URL`
- Variables del checklist no visibles como variables explicitas de servicio: `CORS_ALLOW_ORIGINS`, `EMISSION_MODE_DEFAULT`, `EMISSION_WORKER_POLL_SECONDS`, `SMARTPSE_API_TOKEN`, `SUPABASE_SERVICE_ROLE_KEY`, `INIT_DB_ON_STARTUP`.
- Validaciones compensatorias:
  - `/health` reporta `environment: "staging"`.
  - `INIT_DB_ON_STARTUP` no esta visible en Railway y el default del codigo es `False`.
  - `EMISSION_MODE_DEFAULT` no esta visible en Railway y el default del codigo es `async`.
  - `EMISSION_WORKER_POLL_SECONDS` no esta visible en Railway y el default del codigo es `2`.
  - `CORS_ALLOW_ORIGINS` no esta visible en Railway, pero CORS preflight desde `https://inkora-pse.vercel.app` hacia `/clientes/search` y `/productos/search` fue PASS.
  - `SUPABASE_KEY` esta presente; el plan nombraba `SUPABASE_SERVICE_ROLE_KEY`, por lo que queda recomendado alinear nomenclatura operativa si aplica.
- No se imprimieron secretos.

### 5.2 Health check
Comando:

```powershell
curl.exe -i https://inkorapse-production.up.railway.app/health
```

Resultado:

- PASS: `HTTP/1.1 200 OK`
- Fecha local: `2026-05-08 16:08:46 -05:00`
- Fecha header: `Fri, 08 May 2026 21:08:46 GMT`
- Railway request id: `-Ql8EpHPS8aheEpPezItjw`
- X-Request-Id: `25d419fb-124a-493d-90b3-8db861c8c3f5`

Body:

```json
{"status":"ok","environment":"staging"}
```

### 5.3 Smoke API autenticado
Clientes page: PASS, `HTTP 200`, `count=1`.
Clientes search: PASS, documento `HTTP 200 count=1`; nombre `HTTP 200 count=1`.
Productos page: PASS, `HTTP 200`, `count=1`.
Productos search: PASS, SKU `HTTP 200 count=1`; nombre `HTTP 200 count=1`.
Cobranza resumen: PASS, `HTTP 200`.
Cobranza vencidas: PASS, `HTTP 200`, `count=0`.

Evidencia autenticada:

- Fecha local: `2026-05-08 17:23:54 -05:00`.
- Tenant temporal exitoso: `tenant_id=4`, `user_id=4`, `validation_email=validation-20260508172343@inkora.test`.
- Datos minimos no fiscales creados por API:
  - `cliente_id=1`, status create `201`.
  - `producto_id=1`, status create `201`.
  - `cotizacion_id=1`, status create `200`, `tipo_comprobante=00`.
- Login `/token`: PASS; token no impreso ni guardado.
- `/users/me/`: `HTTP 200`.
- `/cotizaciones/?limit=15`: `HTTP 200`, `count=1`.
- No se ejecuto emision fiscal real.

Validacion complementaria sin JWT:

- PASS CORS preflight `/clientes/search` desde `Origin: https://inkora-pse.vercel.app`: `HTTP/1.1 200 OK`, `Access-Control-Allow-Origin: https://inkora-pse.vercel.app`, `Access-Control-Allow-Credentials: true`.
- PASS CORS preflight `/productos/search` desde `Origin: https://inkora-pse.vercel.app`: `HTTP/1.1 200 OK`, `Access-Control-Allow-Origin: https://inkora-pse.vercel.app`, `Access-Control-Allow-Credentials: true`.
- PASS proteccion auth sin token en `/clientes/search`: `HTTP/1.1 401 Unauthorized`, body `{"detail":"Not authenticated"}`, sin 500.

### 5.4 Worker/cola fiscal
Resultado: PASS con riesgo no bloqueante
Estado de jobs: SQL Supabase confirma `document_emission_jobs = 0`; consulta por jobs agrupados devolvio `0 filas`, y consulta de jobs `processing` colgados sobre 15 minutos devolvio `0 filas`.
Riesgos:

- Railway Architecture mostro un solo servicio visible: `inkora_pse`; no se observo un servicio worker separado.
- No hay jobs para medir throughput real; la base esta sin datos operativos.
- Riesgo no bloqueante para esta validacion: si la emision/PDF corre en el mismo servicio, puede competir con requests API bajo carga fiscal real.

### 5.5 Logs Railway
Resultado: PASS con warning no bloqueante
Errores relevantes:

- Dashboard Railway Logs revisado en navegador integrado para la ventana visible `May 8 5:34-5:50 PM GMT-5`.
- Filtro `@level:error`: `No logs found for this filter`.
- Filtro `status_code=500`: `No logs found for this filter`.
- Logs visibles sin filtro mostraron requests `OPTIONS`/`GET` `200` para `/sunat/exchange-rate`.
- Warning visible no bloqueante: `sunat_exchange_rate_stale_cache`, contexto `SUNAT devolvio una estructura de tipo de cambio invalida.`
- En la muestra revisada no se observaron DB timeouts, pool agotado, errores Smart PSE, errores PDF/storage ni errores CORS.

## 6. Vercel
### 6.1 Variables frontend
Resultado: PASS para Production y Development; Preview global pendiente por politica de ramas

Evidencia:

- Vercel CLI via `npx` esta autenticado: `vercel whoami` respondio `kennedyrojas01064-5779`.
- Proyecto `inkora-pse` encontrado:
  - Project ID: `prj_n0pDzkSeFjBVqZkPryxwxSXTxwlu`
  - Latest Production URL: `https://inkora-pse.vercel.app`
  - Node Version: `24.x`
- Inicialmente `vercel api /v9/projects/prj_n0pDzkSeFjBVqZkPryxwxSXTxwlu/env --raw` devolvio `{"envs":[],"hiddenProductionEnvCount":0}`.
- Ajuste aplicado el 2026-05-08 18:58 America/Lima:
  - `VITE_API_URL=https://inkorapse-production.up.railway.app` agregado en `Production`.
  - `VITE_API_URL=https://inkorapse-production.up.railway.app` agregado en `Development`.
  - Intento de `Preview` global quedo pendiente porque Vercel CLI no interactivo pidio rama especifica y rechazo `main` por ser Production Branch.
- `vercel env ls` posterior mostro `VITE_API_URL` en `Production` y `Development`.
- Se ejecuto redeploy production para que Vite embeba la variable:
  - deployment id: `dpl_7zK8SiRNE1juxE32qBRhFCeUQRP9`
  - target: `production`
  - status: `Ready`
  - alias: `https://inkora-pse.vercel.app`
  - build desde `main`, commit `1954822`
  - `vite v6.4.2`, `1670 modules transformed`, `built in 5.13s`
  - `curl -I https://inkora-pse.vercel.app`: `HTTP/1.1 200 OK`
- El bundle previo contenia el fallback efectivo a `https://inkorapse-production.up.railway.app`:

```text
Ph="https://inkorapse-production.up.railway.app"
Sl=(zh.VITE_API_URL||Ph).replace(/\/$/,"")
```

Interpretacion:

- La variable real `VITE_API_URL` ya esta configurada para Production y Development en Vercel.
- Production fue redeployado despues de configurar la variable.
- Preview global queda como pendiente recomendado; para evitar ambiguedad, configurar una rama preview concreta cuando exista una rama staging o preview estable.

### 6.2 Smoke UI
Login: PASS
Dashboard: PASS
Clientes: PASS
Productos: PASS
Cotizaciones: PASS
Autocomplete cliente: PASS
Autocomplete producto: PASS

Evidencia login/public shell:

- `curl -I https://inkora-pse.vercel.app`: `HTTP/1.1 200 OK`, `Server: Vercel`, `X-Vercel-Cache: HIT`.
- Playwright headless cargo `https://inkora-pse.vercel.app`:
  - title: `Inkora`
  - texto visible incluye login: `Bienvenido de vuelta`, `Correo / Usuario`, `Contrasena`.
  - `consoleErrors: []`
  - `failedRequests: []`

Evidencia autenticada:

- Playwright headless con usuario temporal `validation-20260508172343@inkora.test`.
- Visitado: `/dashboard`, `/clientes`, `/productos`, `/cotizaciones`.
- En `/cotizaciones` se encontraron inputs de autocomplete:
  - cliente por nombre: `true`.
  - producto por codigo: `true`.
  - producto por nombre: `true`.
- Network observo `/clientes/search` y `/productos/search`.
- Respuestas search observadas: `HTTP 200`, `HTTP 200`, `HTTP 200`.
- `consoleErrorsCount=0`, `requestFailuresCount=0`, `responseErrorsCount=0`.
- Contraseña temporal y token no se imprimieron ni se guardaron.

### 6.3 DevTools Network
/clientes/search: PASS
/productos/search: PASS
CORS: PASS
Errores consola: PASS
Requests duplicados: PASS en smoke acotado; no se observaron errores ni failures durante autocomplete.

Evidencia:

- No se observaron errores de consola ni requests fallidos en carga publica de login ni en smoke autenticado de autocomplete.
- Los endpoints `/clientes/search` y `/productos/search` se dispararon desde Vercel con usuario autenticado.
- CORS preflight desde `https://inkora-pse.vercel.app` hacia Railway PASS para search endpoints.

### 6.4 Deploy y logs Vercel
Resultado: PASS

Evidencia:

- `vercel inspect inkora-pse.vercel.app`:
  - deployment id: `dpl_A5fMGVHX5ne9JZ9UJk85z3FumEZF`
  - target: `production`
  - status: `Ready`
  - created: `Fri May 08 2026 15:21:11 GMT-0500`
  - aliases: `https://inkora-pse.vercel.app`, `https://inkora-pse-git-main-kennedyrojas01064-gmailcoms-projects.vercel.app`
- Build logs:
  - cloned `github.com/hkrojas/inkora_pse`
  - branch `main`
  - commit `653e229`
  - `npm run build`
  - `vite v6.4.2`
  - `1670 modules transformed`
  - `built in 5.28s`
  - deployment completed
- Runtime logs:
  - `vercel logs --project inkora-pse --environment production --since 1h --no-branch --limit 20 --json` no devolvio errores.
  - `vercel logs --project inkora-pse --environment production --since 1h --no-branch --level error --limit 20 --json` no devolvio errores.

## 7. End-to-end funcional
Cliente/producto/cotizacion: PASS para flujo no fiscal minimo.
Cobranza: PASS para endpoints de resumen y vencidas con dataset minimo.
Reporte mensual: N/A por no existir documentos fiscales operativos.
Fiscal staging, si autorizado: NO EJECUTADO

Notas:

- No se ejecuto emision fiscal real.
- Se crearon datos temporales no fiscales en `tenant_id=4`: un cliente, un producto y una cotizacion.
- Tambien quedaron dos tenants temporales de intentos previos sin cliente/producto/cotizacion: `tenant_id=2` y `tenant_id=3`. No se eliminaron sin instruccion explicita.

## 8. Performance smoke
Herramienta: `k6` no instalado; se ejecuto runner equivalente con `node fetch` secuencial en un solo proceso.
Resultados: PASS smoke acotado, sin 5xx.
p95 search: clientes `341.6 ms`, productos `135.8 ms`.
p95 page: clientes `138.1 ms`, productos `135.4 ms`.
p95 cobranza: resumen `134.1 ms`, vencidas `138.3 ms`.
Errores 5xx: `0`.

Evidencia:

- Fecha: `2026-05-08T22:30:53.791Z`.
- `clientes_search`: `10/10` OK, status `200`.
- `productos_search`: `10/10` OK, status `200`.
- `clientes_page`: `5/5` OK, status `200`.
- `productos_page`: `5/5` OK, status `200`.
- `cobranza_resumen`: `5/5` OK, status `200`.
- `cobranza_vencidas`: `5/5` OK, status `200`.
- Nota: un smoke previo con `curl.exe` tambien tuvo `0` errores, pero no se uso como metrica principal porque cada muestra abre proceso/conexion nueva.

## 9. Conclusion
- Deploy estable? PASS operativo post-deploy. Supabase, API autenticada, Vercel UI autenticada, autocomplete remoto, performance smoke, Railway health, Railway variables visibles y Railway logs recientes quedaron validados con evidencia real.
- Apto para produccion? PASS operativo con riesgos no bloqueantes documentados. PITR/Pro sigue recomendado aunque esta fase fue autorizada manualmente con dump logico; no se ejecuto emision fiscal real; no se observo worker separado en Railway.
- Pendientes obligatorios:
  - Ninguno para esta validacion post-deploy operativa.
- Pendientes recomendados:
  - Configurar `VITE_API_URL` para una rama Preview concreta cuando exista staging/preview estable; Production y Development ya quedaron configurados.
  - Instalar/usar `k6` para carga moderada; el smoke secuencial con Node ya paso.
  - Limpiar tenants temporales de validacion `2`, `3` y `4` solo con autorizacion explicita de borrado.
  - Resolver o aislar formalmente los 3 tests fiscales/test-harness fuera de scope.
  - Revisar vulnerabilidad moderada reportada por `npm ci`.
  - Evaluar worker fiscal separado si se habilitara carga fiscal real.
  - Monitorear warning `sunat_exchange_rate_stale_cache`.
  - Revisar `ENVIRONMENT` y `FISCAL_ENV` en Railway como cambio conjunto; no cambiar solo `ENVIRONMENT` porque `config.py` exige `FISCAL_ENV=production` cuando `ENVIRONMENT=production`.

## 10. Evidencia adjunta
- URLs:
  - `https://inkorapse-production.up.railway.app/health`
  - `https://inkora-pse.vercel.app`
  - Railway dashboard autenticado: proyecto `truthful-flexibility`, servicio `inkora_pse`, entorno `production`.
- Comandos:
  - `git status`
  - `git log -3 --oneline`
  - `C:\Users\HP\Desktop\inkora_smartpse\backend\venv\Scripts\python.exe -m pytest test_tenant_page_endpoints.py test_scalability_indexes.py test_reportes.py -q`
  - `C:\Users\HP\Desktop\inkora_smartpse\backend\venv\Scripts\python.exe -m pytest -q`
  - `npm ci`
  - `npm run build`
  - `npm run lint`
  - `curl.exe -i https://inkorapse-production.up.railway.app/health`
  - `curl.exe -I https://inkora-pse.vercel.app`
  - `npx --yes vercel@latest whoami`
  - `npx --yes vercel@latest projects ls --json`
  - `npx --yes vercel@latest inspect inkora-pse.vercel.app`
  - `npx --yes vercel@latest inspect inkora-pse.vercel.app --logs`
  - `npx --yes vercel@latest api /v9/projects/prj_n0pDzkSeFjBVqZkPryxwxSXTxwlu/env --raw`
  - `npx --yes vercel@latest env add VITE_API_URL production --value https://inkorapse-production.up.railway.app --yes --no-sensitive`
  - `npx --yes vercel@latest env add VITE_API_URL development --value https://inkorapse-production.up.railway.app --yes --no-sensitive`
  - `npx --yes vercel@latest redeploy inkora-pse.vercel.app --target production`
  - `npx --yes vercel@latest logs --project inkora-pse --environment production --since 1h --no-branch --limit 20 --json`
  - `npx --yes vercel@latest logs --project inkora-pse --environment production --since 1h --no-branch --level error --limit 20 --json`
  - `pg_dump` manual por Session Pooler IPv4, archivo `C:\Users\HP\Desktop\inkora_backups\inkora_pse_pre_indexes_20260508-165311.dump`.
  - `pg_restore --list C:\Users\HP\Desktop\inkora_backups\inkora_pse_pre_indexes_20260508-165311.dump` con exit code `0`.
  - `Get-FileHash C:\Users\HP\Desktop\inkora_backups\inkora_pse_pre_indexes_20260508-165311.dump -Algorithm SHA256`.
  - `psql` via Session Pooler IPv4: `backend/migrations/001_scalability_indexes.sql`, exit code `0`.
  - `psql` via Session Pooler IPv4: `backend/migrations/002_optional_pg_trgm_indexes.sql`, exit code `0`.
  - `curl.exe` smoke API autenticado con usuario tenant temporal.
  - Playwright headless smoke UI Vercel autenticado.
  - `node fetch` sequential performance smoke.
- SQL:
  - SQL Editor Supabase autenticado ejecuto consulta read-only de resumen:
    - `core_indexes_present = 14`
    - `core_indexes_expected = 14`
    - `pg_trgm_installed = true`
    - `optional_trgm_indexes_present = 4` con nombres `idx_*`
    - `table_counts = {"tenants":4,"users":4,"clientes":1,"productos":1,"cotizaciones":1,"cotizacion_items":1,"pagos":0,"document_emission_jobs":0}`
    - `stuck_processing_jobs_over_15m = 0`
  - SQL Editor Supabase y `psql` listaron indices existentes; hay indices legacy `ix_*` y tambien los `idx_*` esperados por las migraciones del plan.
  - SQL Supabase listo tenants temporales de validacion:
    - `tenant_id=2`, sin clientes/productos/cotizaciones.
    - `tenant_id=3`, sin clientes/productos/cotizaciones.
    - `tenant_id=4`, con `1` cliente, `1` producto y `1` cotizacion no fiscal.
- Logs resumidos:
  - Railway health: `HTTP/1.1 200 OK`, body `{"status":"ok","environment":"staging"}`.
  - Backend focal: `24 passed in 10.48s`.
  - Backend completo: `419 passed, 3 failed, 12 warnings in 91.21s`.
  - Frontend build: PASS, `1670 modules transformed`, `built in 6.11s`.
  - Frontend lint: PASS.
  - Supabase dashboard: proyecto `inkora_pse` activo, `Backups` indica `Free Plan does not include project backups`.
  - Supabase connection settings: password DB no visible; URI de conexion usa placeholder `[YOUR-PASSWORD]`; Session Pooler IPv4 valido para `pg_dump` y consultas read-only con password vigente provista por el operador.
  - Supabase dump manual: `338573` bytes, `pg_restore --list` exit code `0`, SHA256 `408A3A0A8AA0698306086A9B7F03C7E09DEEAC2FD7F56DD9E1CE4943C9893AF6`.
  - Supabase SQL: migracion core `001` PASS con 14/14 indices; migracion opcional `002` PASS con 4/4 indices trigram; base con datos temporales minimos de validacion.
  - API autenticada: login PASS, cliente/producto/cotizacion no fiscal creados; endpoints page/search/cobranza respondieron `HTTP 200`.
  - Vercel UI autenticada: dashboard/clientes/productos/cotizaciones cargan; `/clientes/search` y `/productos/search` observados con `HTTP 200`; sin errores de consola ni request failures en el smoke.
  - Performance smoke Node: p95 search clientes `341.6 ms`, productos `135.8 ms`; p95 page clientes `138.1 ms`, productos `135.4 ms`; p95 cobranza resumen `134.1 ms`, vencidas `138.3 ms`; `0` errores 5xx.
  - Vercel deployment inicial: production `Ready`, built from `main` commit `653e229`, no runtime error logs in queried window.
  - Vercel env posterior: `VITE_API_URL` agregado en Production y Development.
  - Vercel redeploy posterior: production `Ready`, deployment `dpl_7zK8SiRNE1juxE32qBRhFCeUQRP9`, built from `main` commit `1954822`.
  - CORS preflight: PASS for `/clientes/search` and `/productos/search` from `https://inkora-pse.vercel.app`.
  - Railway dashboard:
    - Servicio `inkora_pse` `Online`, dominio `inkorapse-production.up.railway.app`, region `US East`, `1 Replica`.
    - Deployment activo `Update post-deploy validation evidence`, via GitHub, `Deployment successful`.
    - Variables visibles por nombre sin revelar valores: `BACKEND_URL`, `DATABASE_URL`, `DB_MAX_OVERFLOW`, `DB_POOL_RECYCLE_SECONDS`, `DB_POOL_SIZE`, `DB_POOL_TIMEOUT_SECONDS`, `EMISSION_WORKER_CONCURRENCY`, `ENVIRONMENT`, `FIELD_ENCRYPTION_KEY`, `FISCAL_ENV`, `SECRET_KEY`, `SMARTPSE_BASE_URL`, `SMARTPSE_TIMEOUT_SECONDS`, `SUPABASE_KEY`, `SUPABASE_STORAGE_BUCKET`, `SUPABASE_URL`.
    - Logs `May 8 5:34-5:50 PM GMT-5`: filtro `@level:error` sin resultados; filtro `status_code=500` sin resultados.
    - Warning no bloqueante visible: `sunat_exchange_rate_stale_cache` por estructura invalida de tipo de cambio SUNAT.
    - Architecture mostro un solo servicio visible; no se observo worker fiscal separado.
