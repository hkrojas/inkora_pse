#!/usr/bin/env bash
# deploy_staging.sh
# Ejecuta migraciones en orden y levanta el servidor FastAPI.
# Uso: bash deploy_staging.sh
#
# Prerequisitos:
#   - .env configurado con ENVIRONMENT=staging y resto de variables
#   - pip install -r requirements-lock.txt (o requirements.txt) ya ejecutado
#   - Postgres accesible desde este servidor
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── 1. Cargar .env ────────────────────────────────────────────────────────────
if [ -f .env ]; then
    set -a; source .env; set +a
    echo "[deploy] .env cargado"
else
    echo "[deploy] ERROR: .env no encontrado en $SCRIPT_DIR"
    exit 1
fi

# ── 2. Validar entorno ────────────────────────────────────────────────────────
if [ "${ENVIRONMENT:-}" != "staging" ]; then
    echo "[deploy] ERROR: este script solo admite ENVIRONMENT=staging"
    exit 1
fi

if [ -z "${DATABASE_URL:-}" ]; then
    echo "[deploy] ERROR: DATABASE_URL no definida"
    exit 1
fi

if [ "${STAGING_DEPLOY_CONFIRMATION:-}" != "INKORA_STAGING" ]; then
    echo "[deploy] ERROR: define STAGING_DEPLOY_CONFIRMATION=INKORA_STAGING para esta ejecucion"
    exit 1
fi

if [ -z "${STAGING_BACKUP_ID:-}" ]; then
    echo "[deploy] ERROR: crea un snapshot y define STAGING_BACKUP_ID con su identificador"
    exit 1
fi

if [ -z "${STAGING_TARGET_ID:-}" ]; then
    echo "[deploy] ERROR: define STAGING_TARGET_ID con el project ref/identificador exclusivo de staging"
    exit 1
fi

if [ -z "${RELEASE_ID:-}" ]; then
    echo "[deploy] ERROR: define RELEASE_ID con la huella comun de backend, worker y frontend"
    exit 1
fi

if [ -n "${PRODUCTION_DATABASE_URL:-}" ] && [ "$DATABASE_URL" = "$PRODUCTION_DATABASE_URL" ]; then
    echo "[deploy] ERROR: DATABASE_URL coincide con PRODUCTION_DATABASE_URL"
    exit 1
fi

python - "$DATABASE_URL" "$STAGING_TARGET_ID" <<'PY'
import sys
from urllib.parse import urlparse

database_url, target_id = sys.argv[1], sys.argv[2].strip().lower()
if len(target_id) < 6 or target_id in {"staging", "production", "postgres"}:
    raise SystemExit("[deploy] ERROR: STAGING_TARGET_ID debe ser un identificador concreto de al menos 6 caracteres")
parsed = urlparse(database_url)
identity = f"{parsed.username or ''}@{parsed.hostname or ''}/{parsed.path.lstrip('/')}".lower()
if target_id not in identity:
    raise SystemExit("[deploy] ERROR: DATABASE_URL no contiene el STAGING_TARGET_ID declarado")
PY

echo "[deploy] ENVIRONMENT=${ENVIRONMENT}"
echo "[deploy] DATABASE_URL=***"
echo "[deploy] STAGING_BACKUP_ID=${STAGING_BACKUP_ID}"
echo "[deploy] STAGING_TARGET_ID=${STAGING_TARGET_ID}"
echo "[deploy] RELEASE_ID=${RELEASE_ID}"

# ── 3. Migraciones en orden ───────────────────────────────────────────────────
echo ""
echo "[deploy] === Validando cadena launch ==="
python run_launch_migrations.py --dry-run --strict

echo "[deploy] === Verificando grafo y baseline Alembic antes de escribir ==="
if ! ALEMBIC_HEADS="$(alembic -c alembic.ini heads 2>&1)"; then
    printf '%s\n' "$ALEMBIC_HEADS"
    echo "[deploy] ERROR: no se pudo resolver el grafo Alembic"
    exit 1
fi
HEAD_COUNT="$(printf '%s\n' "$ALEMBIC_HEADS" | grep -Ec '\(head\)$' || true)"
if [ "$HEAD_COUNT" -ne 1 ]; then
    printf '%s\n' "$ALEMBIC_HEADS"
    echo "[deploy] ERROR: se esperaba exactamente un head Alembic y se encontraron $HEAD_COUNT"
    exit 1
fi
printf '%s\n' "$ALEMBIC_HEADS"
EXPECTED_ALEMBIC_HEAD="0025_emission_worker_events"
if ! printf '%s\n' "$ALEMBIC_HEADS" | grep -Eq "^${EXPECTED_ALEMBIC_HEAD} \(head\)$"; then
    echo "[deploy] ERROR: la cabeza esperada es ${EXPECTED_ALEMBIC_HEAD}"
    exit 1
fi

if ! ALEMBIC_CURRENT="$(alembic -c alembic.ini current 2>&1)"; then
    printf '%s\n' "$ALEMBIC_CURRENT"
    echo "[deploy] ERROR: no se pudo consultar la revision Alembic de staging"
    exit 1
fi
if ! printf '%s' "$ALEMBIC_CURRENT" | grep -Eq '[0-9]{4}_[a-z0-9_]+'; then
    echo "[deploy] ERROR: base sin revision Alembic. Ejecuta el bootstrap manual del runbook; no se aplicara stamp automaticamente."
    exit 1
fi
printf '%s\n' "$ALEMBIC_CURRENT"

echo "[deploy] === Ejecutando cadena launch ==="
python run_launch_migrations.py --strict
# El runner mantiene la cadena canonica launch/staging y omite dominios congelados.

# migrate_broker.py y migrate_mrp.py son dominios congelados — omitidos

echo "[deploy] === Verificando integridad beta ==="
python migrate_beta_integrity.py --dry-run
python migrate_beta_integrity.py --apply
python migrate_beta_integrity.py --dry-run

echo "[deploy] === Aplicando revisiones Alembic ==="
alembic -c alembic.ini upgrade head
ALEMBIC_CURRENT_AFTER="$(alembic -c alembic.ini current)"
printf '%s\n' "$ALEMBIC_CURRENT_AFTER"
if ! printf '%s\n' "$ALEMBIC_CURRENT_AFTER" | grep -Eq "^${EXPECTED_ALEMBIC_HEAD} \(head\)$"; then
    echo "[deploy] ERROR: staging no quedo en ${EXPECTED_ALEMBIC_HEAD}"
    exit 1
fi
alembic -c alembic.ini heads

echo "[deploy] === Migraciones completadas ==="

# ── 4. Smoke test de configuración ───────────────────────────────────────────
echo ""
echo "[deploy] Validando configuración..."
python -c "
from config import settings
print(f'  ENVIRONMENT : {settings.ENVIRONMENT}')
print(f'  BACKEND_URL : {settings.BACKEND_URL}')
print(f'  HAS_SUPABASE: {settings.has_supabase_storage}')
print(f'  INIT_DB_ON_STARTUP: {settings.INIT_DB_ON_STARTUP}')
print(f'  EMISSION_MODE_DEFAULT: {settings.EMISSION_MODE_DEFAULT}')
"

# ── 5. Levantar servidor ──────────────────────────────────────────────────────
WORKERS="${UVICORN_WORKERS:-1}"
PORT="${PORT:-8000}"

echo ""
echo "[deploy] Levantando uvicorn — workers=$WORKERS port=$PORT"
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level "${LOG_LEVEL,,:-info}"
