# RAILWAY FISCAL WORKER PLAN — Inkora PSE

## 1. Objetivo

Separar el worker fiscal de Inkora PSE en Railway para que la emision SUNAT/Smart PSE, generacion de PDF y persistencia de artifacts no compitan con los requests HTTP de la API bajo carga fiscal real.

La separacion busca:

- Evitar que operaciones fiscales lentas bloqueen o degraden la API.
- Controlar la concurrencia de emision de forma independiente.
- Aislar fallas del proveedor fiscal, PDF o storage.
- Preparar el sistema para operar con clientes reales y volumen fiscal gradual.

## 2. Estado actual

- Railway tiene un servicio visible: `inkora_pse`.
- No se observo un worker fiscal separado durante la validacion post-deploy.
- Despues de la limpieza de tenants temporales, `document_emission_jobs = 0`.
- API health sigue en PASS:

```powershell
curl.exe -i https://inkorapse-production.up.railway.app/health
```

Respuesta documentada:

```json
{"status":"ok","environment":"staging"}
```

- Riesgo actual: si worker y API corren en el mismo proceso o mismo servicio, emision/PDF puede competir con requests API cuando exista carga fiscal real.

## 3. Archivos involucrados

- `backend/run_emission_worker.py`: entrypoint del proceso worker. Ejecuta `run_worker_loop()` y finaliza limpio ante `KeyboardInterrupt`.
- `backend/services/emission_queue_service.py`: implementa el loop durable del worker, polling, concurrencia con `ThreadPoolExecutor`, recuperacion de jobs colgados, claim de jobs disponibles y procesamiento fiscal.
- `backend/crud/emission_jobs.py`: operaciones CRUD de cola fiscal: crear jobs, reclamar con lock, marcar intento, retry, succeeded, failed y recuperar jobs `processing` colgados.
- `backend/models/emission_jobs.py`: modelo `DocumentEmissionJob` y constantes de estados, acciones y tipos de recurso para la tabla `document_emission_jobs`.
- `backend/config.py`: configuracion por variables de entorno, defaults de emision, pool DB, storage, Smart PSE y validaciones de coherencia entre `ENVIRONMENT` y `FISCAL_ENV`.
- `backend/main.py`: API FastAPI y `/health`; no debe usarse como entrypoint del worker.

## 4. Comando Railway propuesto

Crear un servicio Railway separado:

```txt
inkora_pse_worker
```

Directorio de trabajo:

```txt
backend
```

Start command:

```bash
python run_emission_worker.py
```

El servicio worker no debe exponer HTTP publico ni dominio publico. Su estado se valida por logs, metricas del proceso y SQL de cola.

## 5. Variables requeridas

Copiar desde el servicio API al servicio worker solo los nombres requeridos, sin imprimir valores:

```txt
DATABASE_URL
SECRET_KEY
FIELD_ENCRYPTION_KEY
SUPABASE_URL
SUPABASE_KEY
SUPABASE_STORAGE_BUCKET
SMARTPSE_BASE_URL
SMARTPSE_TIMEOUT_SECONDS
FISCAL_ENV
ENVIRONMENT
BACKEND_URL
DB_POOL_SIZE
DB_MAX_OVERFLOW
DB_POOL_TIMEOUT_SECONDS
DB_POOL_RECYCLE_SECONDS
EMISSION_WORKER_CONCURRENCY
```

Revisar si existen o si deben agregarse explicitamente:

```txt
EMISSION_WORKER_POLL_SECONDS
EMISSION_MODE_DEFAULT
SMARTPSE_API_TOKEN
SUPABASE_SERVICE_ROLE_KEY
```

Notas operativas:

- `config.py` acepta storage con `SUPABASE_SERVICE_ROLE_KEY` o `SUPABASE_KEY`; se recomienda alinear nomenclatura antes de operar con clientes reales.
- No imprimir `DATABASE_URL`, tokens, keys ni secretos en logs, documentos o capturas.
- No cambiar `ENVIRONMENT` aisladamente: `config.py` exige `FISCAL_ENV=production` cuando `ENVIRONMENT=production`, y bloquea `FISCAL_ENV=production` en ambientes no production.

## 6. Configuracion recomendada inicial

Configuracion conservadora inicial:

```txt
EMISSION_WORKER_CONCURRENCY=1
EMISSION_WORKER_POLL_SECONDS=2
EMISSION_MODE_DEFAULT=async
DB_POOL_SIZE=2
DB_MAX_OVERFLOW=1
DB_POOL_TIMEOUT_SECONDS=30
DB_POOL_RECYCLE_SECONDS=1800
```

Subir concurrencia solo despues de medir:

- queue depth.
- oldest queued job age.
- errores del proveedor fiscal.
- uso del pool DB.
- latencia de jobs.
- rate limits de Smart PSE/SUNAT.
- errores de PDF/storage.

## 7. Validaciones antes de crear worker

Checklist previo:

- `document_emission_jobs` sin jobs colgados.
- API health PASS.
- Indices core aplicados, especialmente `idx_emission_jobs_claim`.
- Variables criticas presentes en el servicio API.
- No hay emision fiscal real pendiente no controlada.
- Railway puede correr un segundo servicio desde el mismo repo.
- Plan de rollback claro y aceptado.

SQL de cola:

```sql
SELECT status, count(*) AS total
FROM document_emission_jobs
GROUP BY status
ORDER BY status;
```

Jobs colgados:

```sql
SELECT id, tenant_id, resource_type, resource_id, action, status, attempts, locked_at, processing_started_at, left(last_error, 300) AS error
FROM document_emission_jobs
WHERE status = 'processing'
  AND coalesce(processing_started_at, locked_at) < now() - interval '15 minutes'
ORDER BY coalesce(processing_started_at, locked_at) ASC;
```

Indice de claim:

```sql
SELECT indexname, tablename
FROM pg_indexes
WHERE indexname = 'idx_emission_jobs_claim';
```

## 8. Pasos de creacion en Railway

Pasos manuales para la fase posterior:

1. Abrir Railway -> Project.
2. Crear `New Service`.
3. Seleccionar deploy desde GitHub repo `hkrojas/inkora_pse`.
4. Usar el mismo branch que el backend API.
5. Configurar root directory o working directory: `backend`.
6. Configurar start command: `python run_emission_worker.py`.
7. Copiar variables criticas desde el servicio API sin revelar valores.
8. No asignar dominio publico.
9. Deploy.
10. Revisar logs de arranque.

## 9. Smoke test del worker

No ejecutar emision fiscal real en produccion.

Validar:

- El worker inicia correctamente.
- Logs muestran evento de inicio o actividad de polling, por ejemplo `emission_worker_started`.
- No crashea por imports o configuracion.
- No consume CPU excesiva con cola vacia.
- No hay DB timeouts.
- No hay errores de Smart PSE, PDF o storage al estar la cola vacia.

SQL posterior al inicio:

```sql
SELECT status, count(*) AS total
FROM document_emission_jobs
GROUP BY status
ORDER BY status;
```

Estado esperado si no hay jobs:

- Tabla vacia o sin cambios.
- Worker vivo en logs.
- API `/health` sigue PASS.

## 10. Prueba controlada en staging

Solo con autorizacion explicita:

- Crear una cotizacion de prueba no productiva.
- Encolar emision async en ambiente demo/staging.
- Confirmar transicion del job:
  - `queued`
  - `processing`
  - `succeeded` o `failed` controlado
- Confirmar que no hay duplicacion por `idempotency_key`.
- Confirmar PDF/artifacts si aplica.
- Confirmar que no se reemite un documento ya asociado a fiscal.

No ejecutar SUNAT real en produccion sin autorizacion explicita.

## 11. Monitoreo

Metricas recomendadas:

- queue depth.
- oldest queued job age.
- jobs `retry`.
- jobs `failed`.
- jobs `processing` por mas de 15 minutos.
- worker restarts.
- DB pool timeout.
- Smart PSE timeout.
- provider error rate.
- tiempo promedio por job.
- errores PDF/storage.

SQL sugerido:

```sql
SELECT status,
       count(*) AS total,
       min(created_at) AS oldest_created_at,
       min(available_at) AS oldest_available_at
FROM document_emission_jobs
GROUP BY status
ORDER BY status;
```

Jobs colgados:

```sql
SELECT id, tenant_id, resource_type, resource_id, action, status, attempts, locked_at, processing_started_at, left(last_error, 300) AS error
FROM document_emission_jobs
WHERE status = 'processing'
  AND coalesce(processing_started_at, locked_at) < now() - interval '15 minutes'
ORDER BY coalesce(processing_started_at, locked_at) ASC;
```

## 12. Rollback

Si el worker falla:

- Detener el servicio worker en Railway.
- No tocar el servicio API.
- Revisar jobs en `processing`.
- Ejecutar recuperacion de jobs colgados solo si el sistema ya tiene funcion o servicio para ello.
- No borrar jobs manualmente.
- No reemitir documentos manualmente.
- Documentar errores con logs sanitizados.
- Revalidar `/health` de la API.

## 13. Riesgos

- Duplicar workers sin control puede aumentar presion sobre DB y proveedor fiscal.
- Variables mal copiadas pueden romper el arranque del worker.
- `ENVIRONMENT=production` exige revisar `FISCAL_ENV` en conjunto.
- Sin worker separado, la API puede competir con emision/PDF.
- Sin PITR gestionado, errores operativos en DB son mas riesgosos.
- Rate limits o latencia de Smart PSE/SUNAT pueden acumular retries.
- Fallas de PDF/storage no deben marcar incorrectamente emisiones fiscales aceptadas como fallidas.

## 14. Criterios para autorizar implementacion

Implementar solo si:

- El operador aprueba crear el servicio Railway worker.
- Variables revisadas por nombre y sin secretos expuestos.
- Cola fiscal limpia o controlada.
- `idx_emission_jobs_claim` existe.
- Rollback claro.
- No hay emision fiscal real pendiente no controlada.
- Se acepta configuracion inicial conservadora.
- Se acepta que cualquier prueba fiscal real requiere autorizacion separada.

## 15. Prompt de implementacion posterior

Usa este prompt en una fase posterior, no en esta:

```md
Implementa la separacion del worker fiscal en Railway siguiendo `RAILWAY_FISCAL_WORKER_PLAN.md`.

Reglas:
- No modificar codigo.
- No tocar `.env`.
- No imprimir secretos.
- No cambiar reglas fiscales.
- No ejecutar emision fiscal real sin autorizacion explicita.
- Crear un servicio Railway llamado `inkora_pse_worker`.
- Usar repo `hkrojas/inkora_pse`, mismo branch que API, working directory `backend`.
- Start command: `python run_emission_worker.py`.
- Copiar variables criticas desde el servicio API sin revelar valores.
- No asignar dominio publico al worker.
- Validar logs de arranque, cola vacia, ausencia de DB timeouts y API health.
- Documentar evidencia y rollback.
```
