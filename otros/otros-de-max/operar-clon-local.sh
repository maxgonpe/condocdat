#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-}"
APP_DIR="${2:-}"
[[ "$ACTION" =~ ^(start|stop|restart|update|rollback|retire)$ ]] || { printf 'ERROR: acción no permitida\n' >&2; exit 1; }
[[ -d "$APP_DIR" && -f "$APP_DIR/docker-compose.local.yml" ]] || { printf 'ERROR: falta docker-compose.local.yml\n' >&2; exit 1; }

cd "$APP_DIR"
if docker compose version >/dev/null 2>&1; then
  compose() { docker compose -f docker-compose.local.yml "$@"; }
else
  compose() { docker-compose -f docker-compose.local.yml "$@"; }
fi

case "$ACTION" in
  start) compose up -d ;;
  stop) compose stop ;;
  restart) compose restart ;;
  update)
    image="$(docker inspect -f '{{.Config.Image}}' nomina_app 2>/dev/null || true)"
    [[ -n "$image" ]] || { printf 'ERROR: no se encontró nomina_app\n' >&2; exit 1; }
    docker tag "$image" "$(basename "$APP_DIR"):previous"
    compose up -d --build --force-recreate
    ;;
  rollback)
    docker image inspect "$(basename "$APP_DIR"):previous" >/dev/null 2>&1 || { printf 'ERROR: no existe imagen anterior\n' >&2; exit 1; }
    docker tag "$(basename "$APP_DIR"):previous" "$(docker inspect -f '{{.Config.Image}}' nomina_app)"
    compose up -d --no-build --force-recreate
    ;;
  retire) compose stop; compose rm -f app; printf 'Contenedor retirado; volumen PostgreSQL conservado.\n' ;;
esac
compose ps
printf 'Operación local %s completada.\n' "$ACTION"
