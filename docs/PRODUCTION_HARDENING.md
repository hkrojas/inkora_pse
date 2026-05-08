# Endurecimiento de Produccion Inkora PSE

## Runtime y Supabase

- Railway debe usar `DATABASE_URL` del pooler transaccional de Supabase, puerto `6543`.
- Valores conservadores para plan barato:
  - `DB_POOL_SIZE=3`
  - `DB_MAX_OVERFLOW=2`
  - `EMISSION_WORKER_CONCURRENCY=1`
- Vercel solo debe tener `VITE_API_URL`; nunca `DATABASE_URL` ni `SUPABASE_SERVICE_ROLE_KEY`.
- Railway es el unico runtime con `SUPABASE_SERVICE_ROLE_KEY` para Storage privado.

## Rol de aplicacion

Crear un usuario runtime distinto de `postgres` y usarlo en Railway:

```sql
create role inkora_app login password '<password-seguro>';

grant usage on schema public to inkora_app;
grant select, insert, update, delete on all tables in schema public to inkora_app;
grant usage, select, update on all sequences in schema public to inkora_app;

alter default privileges in schema public
  grant select, insert, update, delete on tables to inkora_app;

alter default privileges in schema public
  grant usage, select, update on sequences to inkora_app;
```

No conceder permisos de superusuario ni `bypassrls`. Las migraciones Alembic se pueden seguir ejecutando con una conexion administrativa controlada.

## Seguridad publica

La migracion `0006_prod_security_perf` revoca permisos de `anon` y `authenticated` sobre objetos `public`. Inkora usa auth propia FastAPI/JWT, por eso el frontend no debe consultar tablas Supabase directamente.

## Readiness

`GET /ops/readiness` requiere `X-Internal-Token` con `INTERNAL_PROVISIONING_TOKEN`. Valida DB, storage y configuracion critica sin exponer secretos.

## Storage y PDF

- Las subidas a Supabase Storage se ejecutan fuera del event loop.
- Los PDFs se generan en threadpool y registran duracion/tamano.
- El logo remoto se cachea por URL en proceso para evitar descargarlo en cada PDF.

## Pruebas de carga permitidas

Antes de llamar Smart PSE/SUNAT, medir solo flujos offline:

- Login concurrente.
- Dashboard/configuracion.
- Listas paginadas con 1000 registros seed.
- PDFs concurrentes.
- Jobs fake/offline.

Script base:

```powershell
python pruebas\load\offline_load.py --base-url https://inkorapse-production.up.railway.app --email usuario@empresa.pe --password "<clave>" --concurrency 10 --iterations 5
```

Para PDF, agregar `--pdf-cotizacion-id <id>` sobre un documento de prueba existente. El endpoint puede devolver `202` si el PDF queda generandose en background; eso debe medirse como comportamiento esperado, no como emision fiscal.
