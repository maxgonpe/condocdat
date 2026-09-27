#!/usr/bin/env bash
set -euo pipefail

# Recupera PostgreSQL de Talleres sin borrar contenedores ni volúmenes.
# Ejecutar en producción como root o con permisos Docker.

CONTAINER="postgres_talleres"
COMPOSE_FILE="/home/max/netgogo_temp/docker-compose.yml"
NETWORK="traefik_default"
DB_NAME="condocdat_db"
DB_USER="maxgonpe"
DB_PASSWORD="celsa1961"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

command -v docker >/dev/null || fail "Docker no está instalado"

printf '%s\n' '== PostgreSQL Talleres =='

if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
  printf '%s\n' 'El contenedor existe. Se iniciará sin recrearlo ni tocar su volumen.'
  docker start "$CONTAINER" >/dev/null || true
else
  printf '%s\n' 'El contenedor no existe. Se intentará crearlo usando el Compose histórico:'
  printf '  %s\n' "$COMPOSE_FILE"
  [[ -f "$COMPOSE_FILE" ]] || fail "No existe el Compose histórico"
  docker compose -f "$COMPOSE_FILE" up -d db
fi

printf '%s\n' '== Esperando PostgreSQL =='
for attempt in $(seq 1 30); do
  if docker exec "$CONTAINER" pg_isready -U "$DB_USER" >/dev/null 2>&1; then
    printf '%s\n' 'PostgreSQL acepta conexiones.'
    break
  fi
  if [[ "$attempt" == 30 ]]; then
    docker logs --tail 80 "$CONTAINER" || true
    fail 'PostgreSQL no quedó disponible.'
  fi
  sleep 2
done

printf '%s\n' '== Bases disponibles =='
PGPASSWORD="$DB_PASSWORD" docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER" \
  psql -U "$DB_USER" -d postgres -Atc "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;"

printf '%s\n' '== Verificación de condocdat_db =='
if PGPASSWORD="$DB_PASSWORD" docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER" \
  psql -U "$DB_USER" -d postgres -Atc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';" | grep -q '^1$'; then
  printf 'La base %s existe.\n' "$DB_NAME"
else
  printf 'ADVERTENCIA: la base %s no existe. No se creará automáticamente.\n' "$DB_NAME" >&2
fi

printf '%s\n' '== Red del contenedor =='
docker inspect "$CONTAINER" --format '{{range $name, $value := .NetworkSettings.Networks}}{{println $name}}{{end}}'

printf '%s\n' '== Estado final =='
docker ps --filter "name=^/${CONTAINER}$"

printf '%s\n' 'PostgreSQL Talleres quedó iniciado. Ahora puede reiniciarse condocdat.'
