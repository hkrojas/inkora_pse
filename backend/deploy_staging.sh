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
if [ "${ENVIRONMENT:-}" != "staging" ] && [ "${ENVIRONMENT:-}" != "production" ]; then
    echo "[deploy] ADVERTENCIA: ENVIRONMENT='${ENVIRONMENT:-}' — esperado 'staging' o 'production'"
fi

if [ -z "${DATABASE_URL:-}" ]; then
    echo "[deploy] ERROR: DATABASE_URL no definida"
    exit 1
fi

echo "[deploy] ENVIRONMENT=${ENVIRONMENT}"
echo "[deploy] DATABASE_URL=***"

# ── 3. Migraciones en orden ───────────────────────────────────────────────────
echo ""
echo "[deploy] === Ejecutando migraciones ==="

run_migration() {
    local script="$1"
    if [ -f "$script" ]; then
        echo "[migrate] $script..."
        python "$script"
    else
        echo "[migrate] SKIP: $script no encontrado"
    fi
}

run_migration migrate_multitenancy.py
run_migration migrate_fases_1_7.py
run_migration migrate_document_flow_phase4.py
run_migration migrate_saas_phase5.py
run_migration migrate_phase6_launch_polish.py
run_migration migrate_pagos.py
run_migration migrate_phase9_beta.py
run_migration migrate_phase8_onboarding.py
run_migration migrate_analytics.py
# migrate_broker.py y migrate_mrp.py son dominios congelados — omitidos

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
"

# ── 5. Levantar servidor ──────────────────────────────────────────────────────
WORKERS="${UVICORN_WORKERS:-2}"
PORT="${PORT:-8000}"

echo ""
echo "[deploy] Levantando uvicorn — workers=$WORKERS port=$PORT"
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level "${LOG_LEVEL,,:-info}"
