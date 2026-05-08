# POST DEPLOY VALIDATION RESULTS — Inkora PSE

## 1. Datos generales
- Fecha/hora: 2026-05-08 15:34 America/Lima (20:34 GMT)
- Repo: `hkrojas/inkora_pse`
- Branch: `validation/post-deploy`
- Commit: `653e229 Update post-deploy validation evidence`
- Backend Railway URL: `https://inkorapse-production.up.railway.app`
- Frontend Vercel URL: `PENDIENTE POR CREDENCIALES / no proporcionada en el entorno`
- Supabase project/environment: `PENDIENTE POR CREDENCIALES`
- Responsable de validación: Codex

## 2. Resultado ejecutivo
- Estado general: PARTIAL
- Resumen: validación local backend focal PASS, frontend build/lint PASS y Railway health PASS. Backend completo conserva fallas fiscales/test-harness fuera de scope. Supabase, smoke API autenticado, Vercel UI, cola fiscal, logs y performance quedan pendientes por falta de credenciales/token/herramientas.
- Bloqueadores: no se puede declarar estabilidad end-to-end sin credenciales Supabase, token JWT tenant, acceso Railway/Vercel y validación de cola fiscal.
- Riesgos no bloqueantes: `pytest` completo falla en 3 tests fuera de scope; `npm ci` reporta 1 vulnerabilidad moderada en dependencias; backend Railway responde con `environment: "staging"` aunque la URL contiene `production`.
- Próximas acciones: ejecutar validaciones Supabase con owner/admin, obtener token JWT tenant de staging, validar Vercel UI/Network, revisar Railway variables/logs y ejecutar performance smoke con `k6`.

## 3. Validación local
### Backend focal
Comando:

```powershell
cd backend
python -m pytest test_tenant_page_endpoints.py test_scalability_indexes.py test_reportes.py -q
```

Resultado:

- `python` global falló por dependencia faltante: `ModuleNotFoundError: No module named 'slowapi'`.
- Se rerun usando el virtualenv existente como runtime, con `workdir` en el worktree limpio:

```powershell
C:\Users\HP\Desktop\inkora_smartpse\backend\venv\Scripts\python.exe -m pytest test_tenant_page_endpoints.py test_scalability_indexes.py test_reportes.py -q
```

- PASS: `24 passed in 9.60s`.

### Backend completo
Comando:

```powershell
C:\Users\HP\Desktop\inkora_smartpse\backend\venv\Scripts\python.exe -m pytest -q
```

Resultado:

- PARTIAL: `419 passed, 3 failed, 12 warnings in 95.00s`.

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

- El primer intento falló porque el worktree limpio no tenía `node_modules` y `vite` no estaba disponible.
- Se ejecutó `npm ci` en `frontend`; no generó cambios versionados.
- `npm ci` reportó 1 vulnerabilidad moderada.
- PASS: `vite v6.4.2`, `1670 modules transformed`, `built in 5.02s`.

### Frontend lint
Comando:

```powershell
cd frontend
npm run lint
```

Resultado:

- PASS: `eslint src --ext .js,.jsx` terminó con exit code 0.

## 4. Supabase
### 4.1 Backup/PITR
Resultado: PENDIENTE POR CREDENCIALES

No hay `DATABASE_URL` en el entorno y no hay acceso Supabase confirmado. No se verificó backup/PITR.

### 4.2 Migración core 001
Resultado: PENDIENTE POR CREDENCIALES
Evidencia: no se aplicó ni validó en DB real porque falta `DATABASE_URL` y autorización explícita del ambiente.

Comando pendiente:

```bash
psql "$DATABASE_URL" -f backend/migrations/001_scalability_indexes.sql
```

### 4.3 Migración opcional 002 pg_trgm
Resultado: PENDIENTE POR CREDENCIALES
Evidencia: no se aplicó ni validó en DB real porque falta `DATABASE_URL`, permisos y autorización explícita.

Comando pendiente:

```bash
psql "$DATABASE_URL" -f backend/migrations/002_optional_pg_trgm_indexes.sql
```

### 4.4 Índices visibles
Resultado: PENDIENTE POR CREDENCIALES
SQL ejecutado: no ejecutado.
Salida/resumen: pendiente.

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

### 4.5 EXPLAIN ANALYZE
Clientes documento: PENDIENTE POR CREDENCIALES
Clientes razón social: PENDIENTE POR CREDENCIALES
Productos SKU: PENDIENTE POR CREDENCIALES
Productos nombre: PENDIENTE POR CREDENCIALES
Cobranza resumen: PENDIENTE POR CREDENCIALES
Cobranza vencidas: PENDIENTE POR CREDENCIALES
Claim jobs: PENDIENTE POR CREDENCIALES

## 5. Railway
### 5.1 Variables críticas
Resultado: PENDIENTE POR CREDENCIALES
Observaciones:

- Railway CLI no está instalado en el entorno.
- No se accedió a dashboard.
- No se imprimieron secretos.

### 5.2 Health check
Comando:

```powershell
curl.exe -i https://inkorapse-production.up.railway.app/health
```

Resultado:

- PASS: `HTTP/1.1 200 OK`
- Fecha header: `Fri, 08 May 2026 20:34:22 GMT`
- Railway request id: `QndeM1WxSIGtEIrxwoOzXw`

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
Resultado: PENDIENTE POR CREDENCIALES
Estado de jobs: no consultado; falta acceso DB/Railway.
Riesgos:

- No se pudo confirmar si hay worker separado en Railway.
- No se pudo medir `queued`, `processing`, `retry`, `failed` ni jobs colgados.

### 5.5 Logs Railway
Resultado: PENDIENTE POR CREDENCIALES
Errores relevantes: no se revisaron logs porque no hay Railway CLI/dashboard.

## 6. Vercel
### 6.1 Variables frontend
Resultado: PENDIENTE POR CREDENCIALES

No hay Vercel CLI instalado ni acceso dashboard. Pendiente confirmar `VITE_API_URL=https://inkorapse-production.up.railway.app`.

### 6.2 Smoke UI
Login: PENDIENTE POR CREDENCIALES
Dashboard: PENDIENTE POR CREDENCIALES
Clientes: PENDIENTE POR CREDENCIALES
Productos: PENDIENTE POR CREDENCIALES
Cotizaciones: PENDIENTE POR CREDENCIALES
Autocomplete cliente: PENDIENTE POR CREDENCIALES
Autocomplete producto: PENDIENTE POR CREDENCIALES

Motivo: no se proporcionó URL frontend Vercel ni credenciales de usuario.

### 6.3 DevTools Network
/clientes/search: PENDIENTE POR CREDENCIALES
/productos/search: PENDIENTE POR CREDENCIALES
CORS: PENDIENTE POR CREDENCIALES
Errores consola: PENDIENTE POR CREDENCIALES
Requests duplicados: PENDIENTE POR CREDENCIALES

## 7. End-to-end funcional
Cliente/producto/cotización: PENDIENTE POR CREDENCIALES
Cobranza: PENDIENTE POR CREDENCIALES
Reporte mensual: PENDIENTE POR CREDENCIALES
Fiscal staging, si autorizado: PENDIENTE POR CREDENCIALES

No se ejecutó emisión fiscal real en producción.

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

## 9. Conclusión
- ¿Deploy estable? No se puede declarar estable de forma end-to-end con la evidencia disponible.
- ¿Apto para producción? PARTIAL. Health Railway, backend focal y frontend build/lint pasan; falta evidencia real de DB, endpoints autenticados, Vercel, cola fiscal, logs y performance.
- Pendientes obligatorios:
  - Validar migraciones e índices Supabase con `DATABASE_URL`.
  - Ejecutar smoke API autenticado con token tenant.
  - Confirmar variables Railway sin exponer secretos.
  - Validar Vercel `VITE_API_URL`, UI y Network.
  - Revisar cola fiscal y logs Railway.
- Pendientes recomendados:
  - Instalar/usar `k6` y ejecutar smoke performance.
  - Resolver o aislar formalmente los 3 tests fiscales/test-harness fuera de scope.
  - Revisar vulnerabilidad moderada reportada por `npm ci`.

## 10. Evidencia adjunta
- URLs:
  - `https://inkorapse-production.up.railway.app/health`
- Comandos:
  - `git status`
  - `git log -1 --oneline`
  - `python -m pytest test_tenant_page_endpoints.py test_scalability_indexes.py test_reportes.py -q`
  - `C:\Users\HP\Desktop\inkora_smartpse\backend\venv\Scripts\python.exe -m pytest test_tenant_page_endpoints.py test_scalability_indexes.py test_reportes.py -q`
  - `C:\Users\HP\Desktop\inkora_smartpse\backend\venv\Scripts\python.exe -m pytest -q`
  - `npm ci`
  - `npm run build`
  - `npm run lint`
  - `curl.exe -i https://inkorapse-production.up.railway.app/health`
- SQL:
  - No ejecutado por falta de `DATABASE_URL`.
- Logs resumidos:
  - Health Railway: `HTTP/1.1 200 OK`, body `{"status":"ok","environment":"staging"}`.
  - Backend focal: `24 passed in 9.60s`.
  - Backend completo: `419 passed, 3 failed, 12 warnings in 95.00s`.
  - Frontend build: PASS, `1670 modules transformed`, `built in 5.02s`.
  - Frontend lint: PASS.
