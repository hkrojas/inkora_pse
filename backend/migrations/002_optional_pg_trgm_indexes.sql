-- Optional trigram indexes for ILIKE search.
-- Safe to run more than once. Apply only if the target Postgres role can
-- create extensions or pg_trgm is already enabled by a DB owner.

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_clientes_razon_social_trgm
ON clientes USING gin (razon_social gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_clientes_numero_documento_trgm
ON clientes USING gin (numero_documento gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_productos_nombre_trgm
ON productos USING gin (nombre gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_productos_codigo_interno_trgm
ON productos USING gin (codigo_interno gin_trgm_ops);
