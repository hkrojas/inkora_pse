# RAILWAY FISCAL WORKER RESULTS - Inkora PSE

## 1. Resumen

Se configuro un segundo servicio en Railway para separar el procesamiento fiscal async de la API principal.

El objetivo fue dejar un worker dedicado para `document_emission_jobs`, evitando que emision SUNAT/Smart PSE/PDF compita con requests HTTP de la API bajo carga fiscal real.

No se modifico codigo backend, frontend, `.env`, reglas fiscales ni jobs manualmente. No se ejecuto emision fiscal real.

## 2. Servicio creado/configurado

- Proyecto Railway: `truthful-flexibility`
- Environment Railway: `production`
- Servicio API existente: `inkora_pse`
- Servicio worker: `inkora_pse_worker`
- Service ID worker: `17a2668a-d2dc-4f77-a13e-b651ba1adbe5`
- Repo/source: `hkrojas/inkora_pse`
- Branch: `main`
- Root directory: `backend`
- Public domain: no asignado
- Replicas: `1`

## 3. Start command final

```bash
sh -c 'mkdir -p /tmp/worker-health && printf ok > /tmp/worker-health/health && (cd /tmp/worker-health && python -m http.server ${PORT:-8080} --bind 0.0.0.0) & exec python run_emission_worker.py'
```

Motivo: el repositorio tiene `railway.json` con `healthcheckPath=/health` para la API. Railway aplica esa configuracion al servicio, por lo que el worker necesita responder el healthcheck interno aunque no exponga dominio publico.

El comando levanta un servidor local minimo solo para `/health` y ejecuta `run_emission_worker.py` como proceso principal con `exec`.

## 4. Variables configuradas

Se configuraron variables por referencia al servicio API y overrides conservadores para el worker. No se registraron valores secretos en este documento.

Variables presentes en el worker:

```txt
BACKEND_URL
DATABASE_URL
DB_MAX_OVERFLOW
DB_POOL_RECYCLE_SECONDS
DB_POOL_SIZE
DB_POOL_TIMEOUT_SECONDS
EMISSION_MODE_DEFAULT
EMISSION_WORKER_CONCURRENCY
EMISSION_WORKER_POLL_SECONDS
ENVIRONMENT
FIELD_ENCRYPTION_KEY
FISCAL_ENV
SECRET_KEY
SMARTPSE_BASE_URL
SMARTPSE_TIMEOUT_SECONDS
SUPABASE_KEY
SUPABASE_STORAGE_BUCKET
SUPABASE_URL
```

Configuracion conservadora aplicada:

```txt
EMISSION_WORKER_CONCURRENCY=1
EMISSION_WORKER_POLL_SECONDS=2
EMISSION_MODE_DEFAULT=async
DB_POOL_SIZE=2
DB_MAX_OVERFLOW=1
DB_POOL_TIMEOUT_SECONDS=30
DB_POOL_RECYCLE_SECONDS=1800
```

## 5. Evidencia de deployment

Deployment exitoso:

```txt
Deployment ID: 5295132c-f3cd-4caa-b469-97737029a027
Status: SUCCESS
Created at: 2026-05-09T19:06:45.722Z
Updated at: 2026-05-09T19:07:15.161Z
Deployment stopped: false
Commit: 4dfc0f0d7ead9ad504a9b6520bc58832d759a8f8
Commit message: Add Railway fiscal worker plan
```

Build/runtime evidence:

```txt
Root directory: backend
Dockerfile: backend/Dockerfile
Healthcheck path aplicado por Railway: /health
Healthcheck result: [1/1] Healthcheck succeeded
Container: Starting Container
```

Dominios:

```txt
serviceDomains: []
customDomains: []
```

## 6. Validacion API principal

Health check API:

```bash
curl.exe -i https://inkorapse-production.up.railway.app/health
```

Resultado:

```txt
HTTP/1.1 200 OK
Body: {"status":"ok","environment":"staging"}
```

La API principal continuo operativa despues de configurar y desplegar el worker.

## 7. Intentos fallidos y causa raiz

Primer deploy fallido:

```txt
Deployment ID: e802d862-6f8a-4673-8566-538bc506626d
Status: FAILED
Causa: el worker no exponia HTTP y Railway aplico /health desde railway.json.
```

Segundo deploy fallido:

```txt
Deployment ID: f727cbef-2a74-4d23-907c-1024e786459f
Status: FAILED
Causa: se intento apuntar a /backend/railway.worker.json, pero ese archivo no existe en el repo.
```

La configuracion final evita modificar codigo o agregar archivos de config nuevos y mantiene el worker sin dominio publico.

## 8. Riesgos y siguientes pasos

- Revocar/rotar tokens Railway temporales usados durante la operacion.
- Monitorear logs del worker durante la primera emision fiscal real autorizada.
- Monitorear `document_emission_jobs`: `queued`, `processing`, `retry`, `failed`, `succeeded`.
- Vigilar `processing` por mas de 15 minutos.
- Vigilar DB pool timeout y errores Smart PSE/SUNAT.
- Considerar como mejora posterior agregar un `railway.worker.json` versionado para evitar el wrapper de healthcheck en el start command.

## 9. Resultado

Estado operativo: `PASS`

El worker fiscal separado quedo configurado y desplegado en Railway, sin dominio publico, sin cambios de codigo y sin ejecutar emision fiscal real.
