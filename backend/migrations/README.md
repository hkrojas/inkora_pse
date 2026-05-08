# Backend Manual Migrations

Manual SQL migrations for launch/staging operations that must be applied
explicitly in Supabase or with `psql`. Files are idempotent and should be run
first in staging.

## 001_scalability_indexes.sql

Purpose:

- Add tenant-scoped lookup indexes for clientes, productos, cotizaciones,
  cotizacion_items, pagos, and document_emission_jobs.

Apply in Supabase SQL Editor or with:

```bash
psql "$DATABASE_URL" -f backend/migrations/001_scalability_indexes.sql
```

Validation:

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

This validation only confirms the indexes are visible after applying the SQL.
The repository test `test_scalability_indexes.py` is static validation of the
SQL files and is not proof that Supabase accepted the migration.

## 002_optional_pg_trgm_indexes.sql

Purpose:

- Enable `pg_trgm` and add optional GIN indexes for `ILIKE` search workloads.
- Improve remote search for cliente razon social/documento and producto
  nombre/codigo.

Apply only after `001_scalability_indexes.sql`, and only in environments where
the database role can create extensions or a DB owner has already enabled
`pg_trgm`:

```bash
psql "$DATABASE_URL" -f backend/migrations/002_optional_pg_trgm_indexes.sql
```

Validation:

```sql
SELECT * FROM pg_extension WHERE extname = 'pg_trgm';

SELECT indexname, tablename
FROM pg_indexes
WHERE indexname IN (
  'idx_clientes_razon_social_trgm',
  'idx_clientes_numero_documento_trgm',
  'idx_productos_nombre_trgm',
  'idx_productos_codigo_interno_trgm'
)
ORDER BY tablename, indexname;
```

If `CREATE EXTENSION IF NOT EXISTS pg_trgm` fails because the role lacks
permission, keep only the core btree indexes from `001` and ask a database
owner to enable `pg_trgm` before applying `002`.
