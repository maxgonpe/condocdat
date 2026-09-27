#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-}"
APP_DIR="${2:-}"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
[[ "$ACTION" =~ ^(start|stop|restart|update|rollback|retire)$ ]] || fail "Acción no permitida"
[[ -n "$APP_DIR" && -d "$APP_DIR" ]] || fail "Directorio inválido"
[[ -f "$APP_DIR/docker-compose.yml" ]] || fail "No existe docker-compose.yml en $APP_DIR"

if docker compose version >/dev/null 2>&1; then
  compose() { docker compose "$@"; }
elif docker-compose version >/dev/null 2>&1; then
  COMPOSE_BIN="$(command -v docker-compose)"
  compose() { "$COMPOSE_BIN" "$@"; }
else
  fail "No está disponible docker compose ni docker-compose"
fi

cd "$APP_DIR"
case "$ACTION" in
  start)   compose up -d ;;
  stop)    compose stop ;;
  restart) compose restart ;;
  update)
    container="$(basename "$APP_DIR")_app"
    image="$(docker inspect -f '{{.Config.Image}}' "$container" 2>/dev/null || true)"
    [[ -n "$image" ]] || fail "No se encontró la imagen actual de $container"
    docker tag "$image" "$(basename "$APP_DIR"):previous"
    compose up -d --build --force-recreate
    ;;
  rollback)
    container="$(basename "$APP_DIR")_app"
    current_image="$(docker inspect -f '{{.Config.Image}}' "$container" 2>/dev/null || true)"
    [[ -n "$current_image" ]] || fail "No se encontró $container"
    docker image inspect "$(basename "$APP_DIR"):previous" >/dev/null 2>&1 || fail "No existe imagen anterior"
    docker tag "$(basename "$APP_DIR"):previous" "$current_image"
    compose up -d --no-build --force-recreate
    ;;
  retire)  compose stop; compose rm -f app static 2>/dev/null || compose rm -f app; printf 'Contenedores retirados; datos y volúmenes conservados.\n' ;;
esac

compose ps
printf 'Operación %s completada para %s.\n' "$ACTION" "$APP_DIR"
