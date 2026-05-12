# POST WORKER SECURITY CHECK - Inkora PSE

## 1. Datos generales
- Fecha/hora: 2026-05-09 16:32:07 -05:00
- Actualizacion: 2026-05-12 10:18:00 -05:00
- Repo: `hkrojas/inkora_pse`
- Branch: `main`
- Ultimo commit: `2f8c8ce Record Railway fiscal worker deployment`
- Worker service: `inkora_pse_worker`
- API URL: `https://inkorapse-production.up.railway.app`

## 2. Objetivo

Documentar que los tokens temporales usados durante la creacion/validacion del worker fueron revocados, rotados o tratados como comprometidos.

Alcance aplicado:

- No se modifico backend.
- No se modifico frontend.
- No se toco `.env`.
- No se imprimieron secretos.
- No se cambiaron reglas fiscales.
- No se ejecuto emision fiscal real.
- No se borraron jobs manualmente.
- No se crearon servicios nuevos.

## 3. Tokens revisados

### Railway token temporal
- Estado: `REVOCADO / ROTADO`
- Evidencia sin valor secreto:
  - Operador confirmo en esta conversacion: "Todo lo que tenga que ver con credenciales o tokens ya esta".
  - `railway` no esta instalado globalmente en esta maquina.
  - `npx --yes @railway/cli status` devolvio `Unauthorized. Please login with railway login`.
  - `npx --yes @railway/cli deployment list --service inkora_pse_worker --environment production --limit 1 --json` devolvio `Unauthorized. Please login with railway login`.
  - `npx --yes @railway/cli logs --service inkora_pse_worker --environment production --lines 50 --filter '@level:error'` devolvio `Unauthorized. Please login with railway login`.
- Observaciones:
  - Desde esta sesion no hay autenticacion Railway activa y no se genero un token nuevo.
  - La revocacion/rotacion efectiva queda documentada por confirmacion del operador, sin exponer valor secreto.
  - No se imprimio ningun token Railway.
  - Si se requiere auditoria externa, complementar luego con captura o log del dashboard que muestre solo estado, fecha y tipo de token, sin valor secreto.

### JWT temporal de smoke test
- Estado: `USUARIO ELIMINADO / EXPIRA NATURALMENTE`
- Evidencia sin valor secreto:
  - `VALIDATION_DATA_CLEANUP_RESULTS.md` documenta que los usuarios temporales `validation` / `inkora.test` fueron eliminados.
  - El mismo documento registra `validation_users = 0` y `document_emission_jobs = 0` despues de la limpieza.
  - `backend/security.py` decodifica el JWT, extrae `sub` y luego busca el usuario por email en DB; si el usuario no existe, responde credenciales invalidas.
  - `backend/api_dependencies.py` usa ese usuario actual para rutas protegidas y aplica validacion de tenant activo.
- Observaciones:
  - No se imprimio ni reutilizo el JWT temporal.
  - No existe evidencia de una denylist individual de JWT en el codigo revisado.
  - La invalidacion operativa para rutas protegidas queda cubierta por la eliminacion del usuario temporal; criptograficamente, cualquier JWT stateless emitido previamente expira de forma natural salvo rotacion controlada de `SECRET_KEY`.
  - No se roto `SECRET_KEY` porque eso invalidaria sesiones existentes y queda fuera de este cierre.

## 4. Estado API
- Comando: `curl.exe -i https://inkorapse-production.up.railway.app/health`
- HTTP status: `HTTP/1.1 200 OK`
- Body: `{"status":"ok","environment":"staging"}`
- Fecha/hora: `2026-05-12 14:44:11 GMT` en header HTTP; `2026-05-12 09:44:11 -05:00` hora local aproximada
- Request id:
  - `X-Railway-Request-Id: SCJygytnSyGNq816H4GxDA`
  - `X-Request-Id: 4e0ef1c4-7798-4cee-aad1-fea41e78dcae`
- Resultado: `PASS`

## 5. Estado worker
- Servicio: `inkora_pse_worker`
- Estado: `Active`
- Deployment: `Deployment successful`
- Dominio publico: `Unexposed service`
- Logs recientes: deploy logs visibles sin errores criticos; muestran `Starting Container` y healthcheck interno `GET /health` con `200`
- Restarts: sin restarts anomalos visibles en el deployment activo
- Resultado: `PASS`

Evidencia live no sensible:

- Railway Dashboard abierto en navegador integrado: proyecto `truthful-flexibility`, environment `production`.
- Servicio: `inkora_pse_worker`.
- Service ID visible en URL: `17a2668a-d2dc-4f77-a13e-b651ba1adbe5`.
- Deployment activo visible: `b8d0208a-3bcf-4ea0-a4fa-9709cc294438`.
- Commit/deployment label visible: `Record Railway fiscal worker deployment`.
- Estado visible: `Active`.
- Resultado visible: `Deployment successful`.
- Networking visible: `Unexposed service`.
- Region/replicas visibles: `US East`, `1 Replica`.
- Fecha visible del deployment: `May 9, 2026, 3:05 PM GMT-5`.
- Deploy logs visibles:
  - `Starting Container`.
  - `GET /health HTTP/1.1` con status `200`.
- No se abrio ni inspecciono la vista de variables.
- No se ejecuto deploy ni se aplicaron cambios.

Evidencia historica no sensible:

- Worker service id documentado: `17a2668a-d2dc-4f77-a13e-b651ba1adbe5`.
- Deployment documentado: `5295132c-f3cd-4caa-b469-97737029a027`.
- Estado documentado: `SUCCESS`.
- `serviceDomains: []` y `customDomains: []`.
- Healthcheck documentado: `[1/1] Healthcheck succeeded`.

Notas de acceso y observaciones:

- Railway CLI via `npx --yes @railway/cli@latest status` respondio `Unauthorized` el 2026-05-12.
- La variable local de autenticacion Railway no esta presente en el entorno local.
- El conector Railway local tambien fallo porque `railway` no esta instalado globalmente.
- El conector Railway no pudo listar servicios, deployments ni logs por el mismo bloqueo de CLI global ausente.
- Chrome no estaba corriendo y la extension Codex Chrome no esta instalada en el perfil detectado, por lo que no hubo sesion web autenticada reutilizable.
- La revalidacion live del worker se completo con la sesion autenticada del navegador integrado.
- Railway muestra cambios staged pendientes (`Apply 5 changes` / `Deploy`) en la UI. No se aplicaron ni descartaron.
- Detalle revisado de staged changes:
  - `Branch`: `main` -> `main`.
  - `Repo`: `hkrojas/inkora_pse` -> `hkrojas/inkora_pse`.
  - `Root Directory`: `backend` -> `backend`.
  - `Start Command`: wrapper con healthcheck interno `/health` -> `python run_emission_worker.py`.
- No desplegar esos staged changes sin revisar antes el impacto del cambio de Start Command. El wrapper actual existe porque Railway aplica el healthcheck `/health` al servicio worker.

## 6. Cola fiscal
- Jobs por estado: `{}`
- Jobs processing colgados: `0`
- Resultado: `PASS`

Evidencia live no sensible:

- Supabase Dashboard abierto en navegador integrado: `project/wiezwkosiuczpnbnvmef`.
- SQL Editor ejecuto una consulta agregada de solo lectura el `2026-05-12 10:01 -05:00`.
- Resultado:
  - `total_jobs = 0`.
  - `jobs_by_status = {}`.
  - `stuck_processing_over_15m = 0`.

Evidencia historica no sensible:

- `VALIDATION_DATA_CLEANUP_RESULTS.md` documento `document_emission_jobs = 0` despues de eliminar tenants temporales `2`, `3` y `4`.
- `RAILWAY_FISCAL_WORKER_RESULTS.md` indica que no se ejecuto emision fiscal real durante la creacion del worker.

Notas de acceso local:

- `DATABASE_URL` no esta presente en el entorno local.
- La variable local de password para `psql` no esta presente en el entorno local.
- La variable local de autenticacion Railway no esta presente en el entorno local.
- `supabase` CLI no esta instalado.
- `psql` esta disponible, pero la consulta live se ejecuto desde el SQL Editor autenticado del navegador integrado, sin leer `.env`.

SQL agregado ejecutado en Supabase SQL Editor, sin borrar jobs ni imprimir errores:

```sql
WITH jobs_by_status AS (
  SELECT status, count(*)::bigint AS total
  FROM document_emission_jobs
  GROUP BY status
),
stuck AS (
  SELECT count(*)::bigint AS total
  FROM document_emission_jobs
  WHERE status = 'processing'
    AND coalesce(processing_started_at, locked_at) < now() - interval '15 minutes'
),
queue_total AS (
  SELECT count(*)::bigint AS total
  FROM document_emission_jobs
)
SELECT
  (SELECT total FROM queue_total) AS total_jobs,
  COALESCE(
    (SELECT jsonb_object_agg(status, total ORDER BY status) FROM jobs_by_status),
    '{}'::jsonb
  ) AS jobs_by_status,
  (SELECT total FROM stuck) AS stuck_processing_over_15m;
```

## 7. Riesgos restantes
- Tokens no revocados:
  - Ninguno reportado por el operador despues de la confirmacion de cierre de credenciales/tokens.
- Tokens que expiran naturalmente:
  - JWT temporal de smoke test: usuario temporal eliminado; cualquier token stateless previo expira naturalmente salvo rotacion de `SECRET_KEY`.
- Acciones pendientes:
  - Revisar en una tarea separada los cambios staged visibles en Railway (`Apply 5 changes`) antes de cualquier deploy futuro, especialmente el cambio de Start Command que eliminaria el wrapper de healthcheck.
- Observaciones:
  - No se debe crear un token temporal nuevo solo para cerrar este documento si el operador puede confirmar la revocacion desde dashboard.
  - No se debe ejecutar emision fiscal real en esta fase.

## 8. Conclusion
- Estado general: `PASS`
- Se puede considerar cerrada la fase worker: `SI`, para el alcance de seguridad post-worker: tokens cerrados, API sana, worker activo/sin dominio publico y cola fiscal vacia.

Resumen:

- API health: `PASS`.
- JWT temporal: `USUARIO ELIMINADO / EXPIRA NATURALMENTE`.
- Railway token temporal: `REVOCADO / ROTADO` por confirmacion del operador.
- Worker: `PASS`, `Active`, `Deployment successful`, `Unexposed service`, `1 Replica`, healthcheck interno `200`.
- Cola fiscal: `PASS`, `total_jobs = 0`, `jobs_by_status = {}`, `stuck_processing_over_15m = 0`.
