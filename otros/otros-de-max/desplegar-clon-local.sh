#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${1:-}"
DOMAIN="${2:-}"
APP_DIR="${3:-}"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
[[ "$APP_NAME" =~ ^[a-z][a-z0-9_]*$ ]] || fail "nombre inválido"
[[ "$DOMAIN" =~ ^[a-z0-9-]+\.netgogo\.cl$ ]] || fail "dominio inválido"
[[ -d "$APP_DIR" ]] || fail "directorio inexistente: $APP_DIR"
[[ -f "$APP_DIR/docker-compose.local.yml" ]] || fail "falta docker-compose.local.yml"

cd "$APP_DIR"
if docker compose version >/dev/null 2>&1; then
  compose() { docker compose -f docker-compose.local.yml "$@"; }
elif docker-compose version >/dev/null 2>&1; then
  compose() { docker-compose -f docker-compose.local.yml "$@"; }
else
  fail "no existe docker compose ni docker-compose"
fi

compose up -d --build
compose exec -T app python manage.py migrate --noinput
compose ps

printf 'Clon local desplegado: %s\n' "$DOMAIN"
printf 'Verificación: curl http://127.0.0.1:8005/health/\n'
