# BETA PREPAID PASS REPORT - Inkora PSE

## 1. Datos generales

- Fecha/hora local: `2026-05-12 19:43:16 -05:00`
- Repo: `hkrojas/inkora_pse`
- Branch: `main`
- Commits de implementacion local:
  - `f8531ff Fix backend beta pass regressions`
  - `e6a2e53 Document beta prepaid pass gate`
  - `1a41aa1 Add beta demo smoke e2e`
  - Bloque final: upgrade lockfile `postcss` para cerrar audit npm.
- API URL: `https://inkorapse-production.up.railway.app`
- Worker service: `inkora_pse_worker`
- Alcance: demo completa para beta prepago controlada, maximo 20 usuarios nominales, sin SUNAT real.

## 2. Estado de criterios PASS

| Criterio | Estado | Evidencia sin secretos |
|---|---|---|
| Backend tests | PASS | `422 passed, 12 warnings` con `python -m pytest -q` en `backend`. |
| Frontend lint/build | PASS | `npm run lint` y `npm run build` ejecutados en `frontend`. |
| E2E demo | CREATED / PENDING RUN | `frontend/e2e/beta-demo-smoke.spec.js` creado y listado por Playwright; requiere credenciales E2E para ejecucion real. |
| API health | PASS | `HTTP/1.1 200 OK`, body `{"status":"ok","environment":"staging"}`. |
| API request id | PASS | `X-Railway-Request-Id: 6PJfRRBfQ--OZslEqmzx2A`; `X-Request-Id: 4e74d997-efc7-4da2-8426-19dd1a534344`. |
| Worker fiscal | PASS | Evidencia autenticada en `POST_WORKER_SECURITY_CHECK.md`: servicio activo, deployment successful, sin dominio publico, healthcheck interno 200. |
| Cola fiscal | PASS | Evidencia autenticada en `POST_WORKER_SECURITY_CHECK.md`: `total_jobs = 0`, `jobs_by_status = {}`, `stuck_processing_over_15m = 0`. |
| Backup verificable | PASS operativo | Dump logico existente fuera del repo validado con `pg_restore --list`: `738` lineas. |
| Backup hash | PASS | SHA256 `408A3A0A8AA0698306086A9B7F03C7E09DEEAC2FD7F56DD9E1CE4943C9893AF6`. |
| Alembic head local | PASS | `alembic heads` devuelve `0006_prod_security_perf (head)`. |
| Alembic head Supabase | PENDING | Requiere `SELECT version_num FROM alembic_version;` en Supabase SQL Editor o `psql` autenticado. |
| SUNAT real | PASS | No se ejecuto emision fiscal real. Beta usa `ENVIRONMENT=staging` y `FISCAL_ENV=beta`. |
| Secret hygiene | PASS | `Select-String` con patrones sensibles no encontro coincidencias en reporte, checklist ni spec E2E. |

## 3. Validaciones ejecutadas

### Backend

```powershell
cd C:\Users\HP\Desktop\inkora_pse_main_security\backend
& 'C:\Users\HP\Desktop\inkora_smartpse\backend\venv\Scripts\python.exe' -m pytest -q
```

Resultado:

```text
422 passed, 12 warnings in 295.10s
```

### API health

```powershell
curl.exe -i https://inkorapse-production.up.railway.app/health
```

Resultado:

```text
HTTP/1.1 200 OK
Date: Tue, 12 May 2026 23:43:57 GMT
X-Railway-Request-Id: 6PJfRRBfQ--OZslEqmzx2A
X-Request-Id: 4e74d997-efc7-4da2-8426-19dd1a534344

{"status":"ok","environment":"staging"}
```

### Backup logico

```powershell
& 'C:\Program Files\PostgreSQL\17\bin\pg_restore.exe' --list 'C:\Users\HP\Desktop\inkora_backups\inkora_pse_pre_indexes_20260508-165311.dump'
Get-FileHash 'C:\Users\HP\Desktop\inkora_backups\inkora_pse_pre_indexes_20260508-165311.dump' -Algorithm SHA256
```

Resultado:

```text
pg_restore --list: 738 lineas
SHA256: 408A3A0A8AA0698306086A9B7F03C7E09DEEAC2FD7F56DD9E1CE4943C9893AF6
```

### Alembic head local

```powershell
& 'C:\Users\HP\Desktop\inkora_smartpse\backend\venv\Scripts\python.exe' -m alembic -c alembic.ini heads
```

Resultado:

```text
0006_prod_security_perf (head)
```

### Frontend lint

```powershell
cd C:\Users\HP\Desktop\inkora_pse_main_security\frontend
npm run lint
```

Resultado:

```text
eslint src --ext .js,.jsx
exit code 0
```

### Frontend build

```powershell
npm run build
```

Resultado:

```text
vite v6.4.2 building for production...
1670 modules transformed.
built in 21.89s
```

### Playwright E2E demo

```powershell
npx playwright test e2e/beta-demo-smoke.spec.js --list
```

Resultado:

```text
[setup] auth.setup.js: login tenant por UI
[chromium] beta-demo-smoke.spec.js: demo beta prepago sin SUNAT real / tenant recorre el launch scope sin errores criticos ni mutaciones fiscales
Total: 2 tests in 2 files
```

Ejecucion real no realizada porque faltan variables locales:

```text
E2E_TENANT_EMAIL: false
E2E_TENANT_PASSWORD: false
E2E_API_URL: false
E2E_BASE_URL: false
```

### NPM audit

```powershell
npm audit --audit-level=moderate
```

Resultado:

```text
found 0 vulnerabilities
```

## 4. Consultas Supabase requeridas

Estas consultas son de solo lectura. No borran jobs ni imprimen secretos.

```sql
SELECT status, count(*) AS total
FROM document_emission_jobs
GROUP BY status
ORDER BY status;

SELECT id, tenant_id, resource_type, resource_id, action, status, attempts,
       locked_at, processing_started_at, left(last_error, 300) AS error
FROM document_emission_jobs
WHERE status = 'processing'
  AND coalesce(processing_started_at, locked_at) < now() - interval '15 minutes'
ORDER BY coalesce(processing_started_at, locked_at) ASC;

SELECT version_num
FROM alembic_version;
```

Estado actual:

- Cola fiscal: PASS por evidencia autenticada previa del mismo cierre operativo.
- `alembic_version` live: PENDING hasta ejecutar la tercera consulta en Supabase SQL Editor o `psql` autenticado.

## 5. Reglas de beta prepago

- Maximo 20 usuarios nominales.
- Tenants beta identificados y aprobados.
- Soporte por canal unico.
- Monitoreo diario de API, worker y cola fiscal.
- Rollback documentado antes de datos reales.
- `ENVIRONMENT=staging` y `FISCAL_ENV=beta` durante beta controlada.
- SUNAT real deshabilitado hasta go fiscal explicito y escrito.
- No imprimir tokens, passwords, certificados, JWT, URLs firmadas ni headers `Authorization`.

## 6. Riesgos restantes

- Completar cifrado de credenciales fiscales legacy antes de SUNAT real.
- Ejecutar E2E demo real cuando existan credenciales E2E del tenant beta.
- Confirmar `alembic_version` live en Supabase.
- Repetir backup justo antes de onboarding beta si se cargaran datos reales.
- Vulnerabilidad moderada npm cerrada con `postcss 8.5.14` en `package-lock.json`.
- Prueba de carga antes de ampliar fuera de 20 usuarios nominales.

## 7. Conclusion

- Estado general actual: PARTIAL.
- Se puede considerar PASS de backend y operacion base.
- Falta para PASS final de beta prepago: E2E demo real y confirmacion live de `alembic_version`.
