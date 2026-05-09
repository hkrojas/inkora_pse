# POST WORKER SECURITY CHECK - Inkora PSE

## 1. Datos generales
- Fecha/hora: 2026-05-09 16:32:07 -05:00
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
- Estado: `PENDIENTE`
- Evidencia sin valor secreto:
  - `railway` no esta instalado globalmente en esta maquina.
  - `npx --yes @railway/cli status` devolvio `Unauthorized. Please login with railway login`.
  - `npx --yes @railway/cli deployment list --service inkora_pse_worker --environment production --limit 1 --json` devolvio `Unauthorized. Please login with railway login`.
  - `npx --yes @railway/cli logs --service inkora_pse_worker --environment production --lines 50 --filter '@level:error'` devolvio `Unauthorized. Please login with railway login`.
- Observaciones:
  - Desde esta sesion no hay autenticacion Railway activa y no se genero un token nuevo.
  - No puedo confirmar revocacion efectiva en Railway Dashboard sin una sesion autenticada.
  - El operador debe revocar o rotar manualmente el token temporal usado durante la creacion del worker, segun corresponda: personal token, project token o token de automatizacion.
  - Despues de revocarlo, registrar en este documento solo evidencia no sensible: fecha/hora, tipo de token, estado revocado/rotado y responsable.

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
- Fecha/hora: `2026-05-09 21:29:40 GMT` en header HTTP; `2026-05-09 16:29:40 -05:00` hora local aproximada
- Request id:
  - `X-Railway-Request-Id: qM0Vi0JgQiqskyynCx5-qw`
  - `X-Request-Id: 4371e50d-d4b3-4161-910e-aa7302ec8961`
- Resultado: `PASS`

## 5. Estado worker
- Servicio: `inkora_pse_worker`
- Estado: `PARTIAL`
- Deployment: `SUCCESS` documentado en `RAILWAY_FISCAL_WORKER_RESULTS.md`
- Dominio publico: `sin dominio publico` documentado en `RAILWAY_FISCAL_WORKER_RESULTS.md`
- Logs recientes: no revalidados live por falta de autenticacion Railway en esta sesion
- Restarts: no revalidados live por falta de autenticacion Railway en esta sesion
- Resultado: `PARTIAL`

Evidencia historica no sensible:

- Worker service id documentado: `17a2668a-d2dc-4f77-a13e-b651ba1adbe5`.
- Deployment documentado: `5295132c-f3cd-4caa-b469-97737029a027`.
- Estado documentado: `SUCCESS`.
- `serviceDomains: []` y `customDomains: []`.
- Healthcheck documentado: `[1/1] Healthcheck succeeded`.

Bloqueo de revalidacion live:

- Railway CLI via `npx` respondio `Unauthorized`.
- Chrome no estaba corriendo y la extension Codex Chrome no esta instalada en el perfil detectado, por lo que no hubo sesion web autenticada reutilizable.
- No se creo ningun token nuevo para forzar la revision.

## 6. Cola fiscal
- Jobs por estado: no revalidado live por falta de credenciales DB en esta sesion
- Jobs processing colgados: no revalidado live por falta de credenciales DB en esta sesion
- Resultado: `PARTIAL`

Evidencia historica no sensible:

- `VALIDATION_DATA_CLEANUP_RESULTS.md` documento `document_emission_jobs = 0` despues de eliminar tenants temporales `2`, `3` y `4`.
- `RAILWAY_FISCAL_WORKER_RESULTS.md` indica que no se ejecuto emision fiscal real durante la creacion del worker.

Intento live:

- `DATABASE_URL` no esta presente en el entorno local.
- `supabase` CLI no esta instalado.
- `psql` esta disponible, pero no se ejecuto consulta remota porque no hay cadena de conexion en entorno y no se leyo `.env`.

SQL que debe ejecutar el operador en Supabase SQL Editor o una sesion `psql` autenticada, sin borrar jobs:

```sql
SELECT status, count(*) AS total
FROM document_emission_jobs
GROUP BY status
ORDER BY status;
```

```sql
SELECT id,
       tenant_id,
       resource_type,
       resource_id,
       action,
       status,
       attempts,
       locked_at,
       processing_started_at,
       left(last_error, 300) AS error
FROM document_emission_jobs
WHERE status = 'processing'
  AND coalesce(processing_started_at, locked_at) < now() - interval '15 minutes'
ORDER BY coalesce(processing_started_at, locked_at) ASC;
```

## 7. Riesgos restantes
- Tokens no revocados:
  - Railway token temporal: `PENDIENTE` de confirmacion por operador en Railway Dashboard.
- Tokens que expiran naturalmente:
  - JWT temporal de smoke test: usuario temporal eliminado; cualquier token stateless previo expira naturalmente salvo rotacion de `SECRET_KEY`.
- Acciones pendientes:
  - Confirmar en Railway Dashboard que el token temporal fue revocado o rotado.
  - Revalidar live `inkora_pse_worker`: running/healthy, ultimo deployment successful, sin dominio publico, logs sin errores criticos, sin restarts anomalos, sin DB timeouts y sin errores de import/config.
  - Ejecutar las dos consultas SQL de cola fiscal desde Supabase SQL Editor o `psql` autenticado.
- Observaciones:
  - No se debe crear un token temporal nuevo solo para cerrar este documento si el operador puede confirmar la revocacion desde dashboard.
  - No se debe ejecutar emision fiscal real en esta fase.

## 8. Conclusion
- Estado general: `PARTIAL`
- Se puede considerar cerrada la fase worker: `NO`, falta evidencia de revocacion/rotacion del token Railway temporal y revalidacion live del worker/cola fiscal desde una sesion autenticada.

Resumen:

- API health: `PASS`.
- JWT temporal: `USUARIO ELIMINADO / EXPIRA NATURALMENTE`.
- Railway token temporal: `PENDIENTE`.
- Worker: `PARTIAL`, con deployment historico `SUCCESS` y sin dominio publico documentado.
- Cola fiscal: `PARTIAL`, con evidencia historica `document_emission_jobs = 0`, pero sin consulta live en esta sesion.
