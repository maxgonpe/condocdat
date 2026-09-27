#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
TEMPLATE_DIR="${TEMPLATE_DIR:-$SCRIPT_DIR/plantilla-clon}"
PG_CONTAINER="${PG_CONTAINER:-postgres_talleres}"
PG_ADMIN_USER="${PG_ADMIN_USER:-maxgonpe}"
PG_ADMIN_PASSWORD="${PG_ADMIN_PASSWORD:-}"
PG_NETWORK="${PG_NETWORK:-myproject_netgogo_default}"
APP_ROOT="${APP_ROOT:-/home/max}"

usage() {
  printf 'Uso: %s NOMBRE SUBDOMINIO [DIRECTORIO]\n' "$(basename "$0")"
  printf 'Ejemplo: %s taller1 taller1.netgogo.cl /home/max/taller1\n' "$(basename "$0")"
}
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[[ $# -ge 2 && $# -le 3 ]] || { usage >&2; exit 2; }
APP_NAME="$1"
DOMAIN="$2"
APP_DIR="${3:-$APP_ROOT/$APP_NAME}"
DB_NAME="${APP_NAME}_db"
DB_USER="$APP_NAME"
DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -hex 24)}"
RESUME_EXISTING="${RESUME_EXISTING:-0}"

[[ "$APP_NAME" =~ ^[a-z][a-z0-9_]*$ ]] || fail "NOMBRE inválido"
[[ "$DOMAIN" =~ ^[a-z0-9-]+\.netgogo\.cl$ ]] || fail "SUBDOMINIO inválido"
if [[ -e "$APP_DIR" && "$RESUME_EXISTING" != 1 ]]; then
  fail "Ya existe $APP_DIR; no se sobrescribirá"
fi
[[ -d "$TEMPLATE_DIR" ]] || fail "No existe la plantilla $TEMPLATE_DIR"
command -v docker >/dev/null || fail "Docker no está instalado"
command -v openssl >/dev/null || fail "OpenSSL no está instalado"
docker container inspect "$PG_CONTAINER" >/dev/null 2>&1 || fail "No existe $PG_CONTAINER"
[[ "$(docker inspect -f '{{.State.Running}}' "$PG_CONTAINER")" == true ]] || fail "$PG_CONTAINER no está activo"
docker network inspect traefik_default >/dev/null 2>&1 || fail "No existe traefik_default"
docker network inspect "$PG_NETWORK" >/dev/null 2>&1 || fail "No existe $PG_NETWORK"

[[ -n "$PG_ADMIN_PASSWORD" ]] || {
  printf 'Introduce la contraseña PostgreSQL de %s: ' "$PG_ADMIN_USER" >&2
  read -r -s PG_ADMIN_PASSWORD
  printf '\n' >&2
}

psql_admin() {
  docker exec -e PGPASSWORD="$PG_ADMIN_PASSWORD" "$PG_CONTAINER" \
    psql -v ON_ERROR_STOP=1 -U "$PG_ADMIN_USER" -d postgres "$@"
}

existing_role="$(psql_admin -Atc "SELECT 1 FROM pg_roles WHERE rolname = '$DB_USER';")"
existing_db="$(psql_admin -Atc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';")"
if [[ -n "$existing_role" || -n "$existing_db" ]]; then
  [[ "$RESUME_EXISTING" == 1 && -n "$existing_role" && -n "$existing_db" ]] || \
    fail "Ya existe parte del clon; usa RESUME_EXISTING=1 para reanudarlo explícitamente"
  printf '== Reanudando clon existente %s ==\n' "$APP_NAME"
  psql_admin -c "ALTER ROLE \"$DB_USER\" WITH LOGIN PASSWORD '$DB_PASSWORD';"
else
  printf '== Creando usuario y base %s ==\n' "$APP_NAME"
  psql_admin -c "CREATE ROLE \"$DB_USER\" LOGIN PASSWORD '$DB_PASSWORD';"
  psql_admin -c "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\";"
fi

mkdir -p "$APP_DIR"
cp "$TEMPLATE_DIR/Dockerfile" "$TEMPLATE_DIR/requirements.txt" "$TEMPLATE_DIR/app.py" \
  "$TEMPLATE_DIR/docker-compose.yml" "$APP_DIR/"
cat > "$APP_DIR/.env" <<EOF
APP_NAME=$APP_NAME
DOMAIN=$DOMAIN
APP_PORT=8000
DB_HOST=$PG_CONTAINER
DB_PORT=5432
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
POSTGRES_NETWORK=$PG_NETWORK
EOF
chmod 600 "$APP_DIR/.env"

cd "$APP_DIR"
if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif docker-compose version >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  fail "No está disponible docker compose ni docker-compose"
fi
"${COMPOSE[@]}" config >/dev/null
"${COMPOSE[@]}" up -d --build

printf '\nClon creado correctamente: %s\n' "$DOMAIN"
printf 'Base: %s (en %s)\n' "$DB_NAME" "$PG_CONTAINER"
printf 'Verificación: curl -k https://%s/health/database\n' "$DOMAIN"
