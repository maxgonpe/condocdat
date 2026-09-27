#!/usr/bin/env bash
set -euo pipefail

# Recrea únicamente Condocdat usando PostgreSQL histórico.
# No elimina ni recrea PostgreSQL, bases ni volúmenes.

CONDOCDAT_DIR="${CONDOCDAT_DIR:-/home/maxgonpe/max/myproject/condocdat}"
COMPOSE_FILE="$CONDOCDAT_DIR/docker-compose.prod.yml"
APP_CONTAINER="condocdat"
PG_CONTAINER="postgres_talleres"
DB_NAME="condocdat_db"
DB_USER="maxgonpe"
DB_PASSWORD="celsa1961"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

command -v docker >/dev/null || fail "Docker no está instalado"
[[ -d "$CONDOCDAT_DIR" ]] || fail "No existe $CONDOCDAT_DIR"
[[ -f "$COMPOSE_FILE" ]] || fail "No existe $COMPOSE_FILE"

cd "$CONDOCDAT_DIR"

printf '%s\n' '== Verificando PostgreSQL histórico =='
docker container inspect "$PG_CONTAINER" >/dev/null 2>&1 || fail "No existe $PG_CONTAINER"
[[ "$(docker inspect -f '{{.State.Running}}' "$PG_CONTAINER")" == "true" ]] || fail "$PG_CONTAINER no está ejecutándose"

if ! docker exec -e PGPASSWORD="$DB_PASSWORD" "$PG_CONTAINER" \
  psql -U "$DB_USER" -d postgres -Atc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';" | grep -q '^1$'; then
  fail "No existe la base $DB_NAME en $PG_CONTAINER"
fi

printf '%s\n' '== Configuración Compose efectiva =='
docker compose -f "$COMPOSE_FILE" config | grep -E 'DB_(ENGINE|NAME|USER|HOST|PORT)' || true

printf '%s\n' '== Recreando únicamente condocdat =='
docker compose -f "$COMPOSE_FILE" up -d --force-recreate --build condocdat

printf '%s\n' '== Variables reales del contenedor =='
docker inspect "$APP_CONTAINER" --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep -E '^DB_(ENGINE|NAME|USER|HOST|PORT)=' || true

printf '%s\n' '== Estado =='
docker ps --filter "name=^/${APP_CONTAINER}$"

printf '%s\n' '== Logs recientes =='
docker logs --tail 80 "$APP_CONTAINER"

printf '%s\n' '== Verificación de datos desde PostgreSQL =='
docker exec -e PGPASSWORD="$DB_PASSWORD" "$PG_CONTAINER" \
  psql -U "$DB_USER" -d "$DB_NAME" -c \
  'SELECT COUNT(*) AS carpetas FROM documents_folder; SELECT COUNT(*) AS documentos FROM documents_document;'

printf '%s\n' 'Condocdat recreado con la base histórica correcta.'
