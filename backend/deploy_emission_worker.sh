#!/usr/bin/env bash
# deploy_emission_worker.sh
# Levanta el worker de cola durable de emisión fiscal.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f .env ]; then
    set -a; source .env; set +a
    echo "[worker] .env cargado"
else
    echo "[worker] ERROR: .env no encontrado en $SCRIPT_DIR"
    exit 1
fi

echo "[worker] ENVIRONMENT=${ENVIRONMENT:-development}"
echo "[worker] Iniciando worker de emisión..."
exec python run_emission_worker.py
