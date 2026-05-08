# POST DEPLOY VALIDATION RESULTS - Inkora PSE

## 1. Datos generales
- Fecha/hora: 2026-05-08 16:08:56 America/Lima (21:08:56 GMT)
- Repo: `hkrojas/inkora_pse`
- Branch: `validation/post-deploy`
- Commit validado local: `0e434c0 Update post-deploy validation results` (incluye base remota `653e229 Update post-deploy validation evidence`)
- Backend Railway URL: `https://inkorapse-production.up.railway.app`
- Frontend Vercel URL: `https://inkora-pse.vercel.app`
- Supabase project/environment: `inkora_pse` (`wiezwkosiuczpnbnvmef`), `ACTIVE_HEALTHY`, region `us-east-1`, PostgreSQL `17.6.1.113`
- Responsable de validacion: Codex

## 2. Resultado ejecutivo
- Estado general: PARTIAL
- Resumen: backend focal PASS, frontend build/lint PASS, Railway `/health` PASS, Vercel production deploy PASS y CORS preflight desde Vercel hacia search endpoints PASS. Supabase project fue identificado, pero las consultas SQL reales siguen bloqueadas por reautenticacion del conector. Smoke API autenticado, EXPLAIN, cola fiscal, Railway variables/logs y flujos UI autenticados siguen pendientes por credenciales especificas.
- Bloqueadores: no se puede declarar PASS sin acceso SQL Supabase efectivo, token JWT tenant, revision Railway variables/logs/worker y validacion UI autenticada.
- Riesgos no bloqueantes: `pytest` completo falla en 3 tests fuera de scope; `npm ci` reporta 1 vulnerabilidad moderada en dependencias; backend Railway responde con `environment: "staging"` aunque la URL contiene `production`; Vercel no tiene env vars configuradas y usa el fallback del bundle hacia Railway.
- Proximas acciones: reautenticar Supabase MCP o proveer `DATABASE_URL`; proveer token JWT tenant; revisar Railway CLI/dashboard; ejecutar smoke UI autenticado y performance con `k6`.

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
Resultado: PENDIENTE POR CREDENCIALES / REAUTENTICACION

Evidencia:

- El conector Supabase listo el proyecto `inkora_pse` (`wiezwkosiuczpnbnvmef`) como `ACTIVE_HEALTHY`.
- No hay `DATABASE_URL` en el entorno local.
- La verificacion de backup/PITR no esta disponible en las herramientas expuestas.
- No se aplicaron migraciones ni DDL.

### 4.2 Migracion core 001
Resultado: PENDIENTE POR CREDENCIALES / REAUTENTICACION

Evidencia:

- Proyecto identificado: `inkora_pse`, host `db.wiezwkosiuczpnbnvmef.supabase.co`, PostgreSQL `17.6.1.113`.
- Intento read-only de SQL:

```sql
SELECT current_database() AS database_name, current_user AS db_user, version() AS postgres_version;
```

- Resultado del conector: `UNAUTHORIZED; ReauthenticationRequired: 401: Reauthentication required`.
- No se aplico `backend/migrations/001_scalability_indexes.sql` porque esta ejecucion es de validacion y el SQL real no pudo autenticarse.

Comando pendiente:

```bash
psql "$DATABASE_URL" -f backend/migrations/001_scalability_indexes.sql
```

### 4.3 Migracion opcional 002 pg_trgm
Resultado: PENDIENTE POR CREDENCIALES / REAUTENTICACION

Evidencia:

- No se valido `pg_trgm` ni indices GIN por bloqueo de autenticacion SQL.
- No se aplico `backend/migrations/002_optional_pg_trgm_indexes.sql`.

Comando pendiente:

```bash
psql "$DATABASE_URL" -f backend/migrations/002_optional_pg_trgm_indexes.sql
```

### 4.4 Indices visibles
Resultado: PENDIENTE POR CREDENCIALES / REAUTENTICACION

SQL pendiente:

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

- No se pudo ejecutar por `ReauthenticationRequired: 401`.
- La base fue reportada por el usuario como casi vacia; sin SQL efectivo, los indices no pueden marcarse PASS.

### 4.5 EXPLAIN ANALYZE
Clientes documento: PENDIENTE POR CREDENCIALES / REAUTENTICACION
Clientes razon social: PENDIENTE POR CREDENCIALES / REAUTENTICACION
Productos SKU: PENDIENTE POR CREDENCIALES / REAUTENTICACION
Productos nombre: PENDIENTE POR CREDENCIALES / REAUTENTICACION
Cobranza resumen: PENDIENTE POR CREDENCIALES / REAUTENTICACION
Cobranza vencidas: PENDIENTE POR CREDENCIALES / REAUTENTICACION
Claim jobs: PENDIENTE POR CREDENCIALES / REAUTENTICACION

Nota: si la base no tiene datos operativos, los EXPLAIN con metricas reales deben documentarse como `N/A por base sin datos operativos`; aun asi se requiere SQL efectivo para confirmarlo.

## 5. Railway
### 5.1 Variables criticas
Resultado: PENDIENTE POR CREDENCIALES / HERRAMIENTA

Observaciones:

- Railway CLI no esta instalado en el entorno.
- El conector Railway disponible depende de CLI local; ejecuciones previas fallaron con `"railway" no se reconoce como un comando interno o externo`.
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
Clientes page: PENDIENTE POR CREDENCIALES
Clientes search: PENDIENTE POR CREDENCIALES
Productos page: PENDIENTE POR CREDENCIALES
Productos search: PENDIENTE POR CREDENCIALES
Cobranza resumen: PENDIENTE POR CREDENCIALES
Cobranza vencidas: PENDIENTE POR CREDENCIALES

Motivo: no hay token JWT tenant en el entorno.

Validacion complementaria sin JWT:

- PASS CORS preflight `/clientes/search` desde `Origin: https://inkora-pse.vercel.app`: `HTTP/1.1 200 OK`, `Access-Control-Allow-Origin: https://inkora-pse.vercel.app`, `Access-Control-Allow-Credentials: true`.
- PASS CORS preflight `/productos/search` desde `Origin: https://inkora-pse.vercel.app`: `HTTP/1.1 200 OK`, `Access-Control-Allow-Origin: https://inkora-pse.vercel.app`, `Access-Control-Allow-Credentials: true`.
- PASS proteccion auth sin token en `/clientes/search`: `HTTP/1.1 401 Unauthorized`, body `{"detail":"Not authenticated"}`, sin 500.

Comandos pendientes:

```powershell
$TOKEN="<TOKEN>"
$BASE="https://inkorapse-production.up.railway.app"

curl.exe -i -H "Authorization: Bearer $TOKEN" "$BASE/clientes/page?limit=15"
curl.exe -i -H "Authorization: Bearer $TOKEN" "$BASE/clientes/search?q=test&limit=20"
curl.exe -i -H "Authorization: Bearer $TOKEN" "$BASE/productos/page?limit=15"
curl.exe -i -H "Authorization: Bearer $TOKEN" "$BASE/productos/search?q=test&limit=20"
curl.exe -i -H "Authorization: Bearer $TOKEN" "$BASE/cobranza/resumen"
curl.exe -i -H "Authorization: Bearer $TOKEN" "$BASE/cobranza/vencidas?limit=5"
```

### 5.4 Worker/cola fiscal
Resultado: PENDIENTE POR CREDENCIALES / REAUTENTICACION SQL
Estado de jobs: no consultado; falta acceso SQL efectivo.
Riesgos:

- No se pudo confirmar si hay worker separado en Railway.
- No se pudo medir `queued`, `processing`, `retry`, `failed` ni jobs colgados.

### 5.5 Logs Railway
Resultado: PENDIENTE POR CREDENCIALES / HERRAMIENTA
Errores relevantes: no se revisaron logs Railway porque no hay CLI/dashboard disponible.

## 6. Vercel
### 6.1 Variables frontend
Resultado: PARTIAL

Evidencia:

- Vercel CLI via `npx` esta autenticado: `vercel whoami` respondio `kennedyrojas01064-5779`.
- Proyecto `inkora-pse` encontrado:
  - Project ID: `prj_n0pDzkSeFjBVqZkPryxwxSXTxwlu`
  - Latest Production URL: `https://inkora-pse.vercel.app`
  - Node Version: `24.x`
- `vercel api /v9/projects/prj_n0pDzkSeFjBVqZkPryxwxSXTxwlu/env --raw` devolvio `{"envs":[],"hiddenProductionEnvCount":0}`.
- El bundle publicado contiene el fallback efectivo a `https://inkorapse-production.up.railway.app`:

```text
Ph="https://inkorapse-production.up.railway.app"
Sl=(zh.VITE_API_URL||Ph).replace(/\/$/,"")
```

Interpretacion:

- La variable `VITE_API_URL` no esta configurada en Vercel.
- El frontend desplegado igualmente apunta al backend correcto por fallback de codigo.
- Esto no se marca PASS completo porque el plan pide validar la variable real, no solo el fallback efectivo.

### 6.2 Smoke UI
Login: PASS
Dashboard: PENDIENTE POR CREDENCIALES
Clientes: PENDIENTE POR CREDENCIALES
Productos: PENDIENTE POR CREDENCIALES
Cotizaciones: PENDIENTE POR CREDENCIALES
Autocomplete cliente: PENDIENTE POR CREDENCIALES
Autocomplete producto: PENDIENTE POR CREDENCIALES

Evidencia login/public shell:

- `curl -I https://inkora-pse.vercel.app`: `HTTP/1.1 200 OK`, `Server: Vercel`, `X-Vercel-Cache: HIT`.
- Playwright headless cargo `https://inkora-pse.vercel.app`:
  - title: `Inkora`
  - texto visible incluye login: `Bienvenido de vuelta`, `Correo / Usuario`, `Contrasena`.
  - `consoleErrors: []`
  - `failedRequests: []`

Motivo de pendientes autenticados: no se proporcionaron credenciales de usuario ni token JWT tenant. No se intento adivinar credenciales.

### 6.3 DevTools Network
/clientes/search: PENDIENTE POR CREDENCIALES
/productos/search: PENDIENTE POR CREDENCIALES
CORS: PASS
Errores consola: PASS en login/public shell
Requests duplicados: PENDIENTE POR CREDENCIALES

Evidencia:

- No se observaron errores de consola ni requests fallidos en carga publica de login.
- Los endpoints `/clientes/search` y `/productos/search` no se disparan antes de login; validar autocomplete requiere usuario autenticado.
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
Cliente/producto/cotizacion: PENDIENTE POR CREDENCIALES
Cobranza: PENDIENTE POR CREDENCIALES
Reporte mensual: PENDIENTE POR CREDENCIALES
Fiscal staging, si autorizado: NO EJECUTADO

Notas:

- No se ejecuto emision fiscal real.
- La base fue reportada por el usuario como casi vacia y sin datos operativos; aun con acceso SQL, varios flujos podrian quedar `N/A por base sin datos operativos`.

## 8. Performance smoke
Herramienta: `k6` no instalado.
Resultados: PENDIENTE POR CREDENCIALES / HERRAMIENTA
p95 search: PENDIENTE
p95 page: PENDIENTE
p95 cobranza: PENDIENTE
Errores 5xx: PENDIENTE

Comando pendiente:

```powershell
BASE_URL="https://inkorapse-production.up.railway.app" TOKEN="<TOKEN>" k6 run inkora-smoke.js
```

## 9. Conclusion
- Deploy estable? PARTIAL. La parte publica y build/deploy estan sanas, pero falta evidencia de DB, API autenticada, cola fiscal y UI autenticada.
- Apto para produccion? No declarable como PASS con la evidencia disponible. Se requiere cerrar credenciales SQL/JWT/Railway.
- Pendientes obligatorios:
  - Reautenticar Supabase MCP o proveer `DATABASE_URL`.
  - Validar/aplicar indices core y opcionales segun autorizacion.
  - Ejecutar smoke API autenticado con token tenant.
  - Confirmar Railway variables/logs/worker.
  - Validar Vercel UI autenticada y Network de autocomplete.
- Pendientes recomendados:
  - Configurar explicitamente `VITE_API_URL=https://inkorapse-production.up.railway.app` en Vercel para no depender del fallback.
  - Instalar/usar `k6` y ejecutar smoke performance.
  - Resolver o aislar formalmente los 3 tests fiscales/test-harness fuera de scope.
  - Revisar vulnerabilidad moderada reportada por `npm ci`.

## 10. Evidencia adjunta
- URLs:
  - `https://inkorapse-production.up.railway.app/health`
  - `https://inkora-pse.vercel.app`
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
  - `npx --yes vercel@latest logs --project inkora-pse --environment production --since 1h --no-branch --limit 20 --json`
  - `npx --yes vercel@latest logs --project inkora-pse --environment production --since 1h --no-branch --level error --limit 20 --json`
- SQL:
  - Intento read-only Supabase bloqueado por `ReauthenticationRequired: 401`.
- Logs resumidos:
  - Railway health: `HTTP/1.1 200 OK`, body `{"status":"ok","environment":"staging"}`.
  - Backend focal: `24 passed in 10.48s`.
  - Backend completo: `419 passed, 3 failed, 12 warnings in 91.21s`.
  - Frontend build: PASS, `1670 modules transformed`, `built in 6.11s`.
  - Frontend lint: PASS.
  - Supabase connector: project `inkora_pse` found, SQL blocked by reauthentication.
  - Vercel deployment: production `Ready`, built from `main` commit `653e229`, no runtime error logs in queried window.
  - CORS preflight: PASS for `/clientes/search` and `/productos/search` from `https://inkora-pse.vercel.app`.
