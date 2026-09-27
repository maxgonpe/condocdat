#!/usr/bin/env bash
set -euo pipefail

# Actualiza únicamente Traefik para Docker Engine >= 29 / API >= 1.40.
# Ejecutar en el servidor de producción como root o con permisos Docker.

TRAEFIK_DIR="/home/max/traefik"
COMPOSE_FILE="$TRAEFIK_DIR/docker-compose.yml"
SERVICE="traefik"
CONTAINER="traefik-traefik-1"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

printf '%s\n' '== Verificación inicial =='
[[ -d "$TRAEFIK_DIR" ]] || fail "No existe $TRAEFIK_DIR"
[[ -f "$COMPOSE_FILE" ]] || fail "No existe $COMPOSE_FILE"
command -v docker >/dev/null || fail "Docker no está instalado"

cd "$TRAEFIK_DIR"

printf '%s\n' 'Docker:'
docker version --format 'Client API: {{.Client.APIVersion}} | Server API: {{.Server.APIVersion}} (mínima {{.Server.MinAPIVersion}})'

printf '%s\n' '== Actualizando configuración de Traefik =='

# Conserva el resto del Compose y modifica solo la imagen y la variable API.
sed -i 's#^[[:space:]]*image: traefik:v3\.[0-9][0-9]*[[:space:]]*$#    image: traefik:v3.6#' "$COMPOSE_FILE"

printf '%s\n' '== Validando Compose =='
docker compose config >/dev/null

printf '%s\n' '== Descargando imagen =='
docker compose pull "$SERVICE"

printf '%s\n' '== Recreando únicamente Traefik =='
docker compose up -d --force-recreate "$SERVICE"

printf '%s\n' '== Estado =='
docker ps --filter "name=$CONTAINER"

printf '%s\n' '== Últimos logs =='
docker logs --tail 50 "$CONTAINER" || true

printf '%s\n' '== Routers HTTP detectados =='
curl --fail --silent --show-error http://127.0.0.1:8080/api/http/routers
printf '\n'

printf '%s\n' '== Prueba del sitio =='
curl --fail --silent --show-error --head https://netgogo.cl

printf '%s\n' 'Traefik actualizado y verificado.'
