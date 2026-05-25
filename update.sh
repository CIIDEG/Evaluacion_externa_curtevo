#!/usr/bin/env bash
# Actualización manual del Centro de Evaluación Cutervo.
# Uso: bash update.sh
set -euo pipefail

APP_DIR=${APP_DIR:-/opt/cutervo}
cd "$APP_DIR"

echo "==> Pull desde GitHub"
git fetch --all
git reset --hard origin/main

echo "==> Re-construyendo y reiniciando contenedores"
docker compose up -d --build
docker image prune -f

echo "==> Estado"
docker compose ps
