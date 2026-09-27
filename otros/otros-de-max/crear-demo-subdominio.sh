#!/usr/bin/env bash
set -euo pipefail

TEMPLATE_DIR="${TEMPLATE_DIR:-/home/max/otros/plantilla-subdominio}"
APP_DIR="${APP_DIR:-/home/max/demo-netgogo}"
APP_NAME="${APP_NAME:-demo_netgogo}"
DOMAIN="${DOMAIN:-demo.netgogo.cl}"
DB_NAME="${DB_NAME:-demo_netgogo_db}"
DB_USER="${DB_USER:-demo_netgogo}"
DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -hex 24)}"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[[ -d "$TEMPLATE_DIR" ]] || fail "No existe la plantilla: $TEMPLATE_DIR"
[[ ! -e "$APP_DIR" ]] || fail "Ya existe $APP_DIR; no se sobrescribirá"
command -v docker >/dev/null || fail "Docker no está instalado"
docker network inspect traefik_default >/dev/null 2>&1 || fail "No existe la red traefik_default"

mkdir -p "$APP_DIR"
cp "$TEMPLATE_DIR/Dockerfile" "$TEMPLATE_DIR/requirements.txt" "$TEMPLATE_DIR/app.py" \
  "$TEMPLATE_DIR/docker-compose.yml" "$APP_DIR/"

cat > "$APP_DIR/.env" <<EOF
APP_NAME=$APP_NAME
DOMAIN=$DOMAIN
APP_PORT=8000
POSTGRES_DB=$DB_NAME
POSTGRES_USER=$DB_USER
POSTGRES_PASSWORD=$DB_PASSWORD
EOF
chmod 600 "$APP_DIR/.env"

cd "$APP_DIR"
docker compose config >/dev/null
docker compose up -d --build

printf '\nAplicación creada en %s\n' "$APP_DIR"
printf 'Subdominio: %s\n' "$DOMAIN"
printf 'Verificación: curl -k https://%s/health/database\n' "$DOMAIN"
