# Backend Manual Migrations

Manual SQL migrations for launch/staging operations that must be applied
explicitly in Supabase or with `psql`. Files are idempotent and should be run
first in staging.

## 001_scalability_indexes.sql

Purpose:

- Add tenant-scoped lookup indexes for clientes, productos, cotizaciones,
  cotizacion_items, pagos, and document_emission_jobs.
- Add optional `pg_trgm` indexes for remote search endpoints and `ILIKE`
  workloads.

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

If `CREATE EXTENSION IF NOT EXISTS pg_trgm` fails because the role lacks
permission, keep the core btree indexes and ask a database owner to enable the
extension before applying the trigram block.
