#!/usr/bin/env bash
# Instalación inicial del Centro de Evaluación Cutervo en un VPS limpio (Ubuntu/Debian).
# Uso: bash install.sh
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Ejecuta como root: sudo bash install.sh"; exit 1
fi

APP_DIR=${APP_DIR:-/opt/cutervo}
REPO_URL=${REPO_URL:-}

echo "==> Actualizando paquetes"
apt-get update -y
apt-get install -y git curl ca-certificates ufw

if ! command -v docker >/dev/null; then
  echo "==> Instalando Docker"
  curl -fsSL https://get.docker.com | sh
fi

echo "==> Configurando firewall"
ufw allow OpenSSH || true
ufw allow 80/tcp  || true
ufw allow 443/tcp || true
ufw --force enable || true

mkdir -p "$APP_DIR"
cd "$APP_DIR"

if [ ! -d .git ]; then
  if [ -z "$REPO_URL" ]; then
    echo "Define REPO_URL=https://github.com/USUARIO/cutervo-eval-portal.git"
    echo "Ejemplo: REPO_URL=... bash install.sh"
    exit 1
  fi
  echo "==> Clonando repositorio"
  git clone "$REPO_URL" .
fi

if [ ! -f .env ]; then
  echo "==> Creando .env (RECUERDA EDITARLO con tus credenciales)"
  cp .env.example .env
  SECRET=$(python3 -c "import secrets;print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
  sed -i "s|cambia-esto-por-una-clave-aleatoria-larga|$SECRET|" .env
  echo
  echo "Edita ahora: nano .env (DOMAIN, ADMIN_PASS, ADMIN_EMAIL)"
  echo "Luego vuelve a ejecutar:  cd $APP_DIR && docker compose up -d --build"
  exit 0
fi

echo "==> Construyendo y levantando contenedores"
docker compose up -d --build

echo
echo "==> Listo. Visita https://$(grep -E '^DOMAIN=' .env | cut -d= -f2)"
docker compose ps
