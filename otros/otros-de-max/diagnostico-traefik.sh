#!/usr/bin/env bash
set -u

APP="${APP:-taller1_app}"
DOMAIN="${DOMAIN:-taller1.netgogo.cl}"
TRAEFIK="${TRAEFIK:-traefik-traefik-1}"
PG="${PG:-postgres_talleres}"

section() { printf '\n===== %s =====\n' "$1"; }
run() { "$@" 2>&1 || true; }

section 'Contenedores relevantes'
run docker ps --filter "name=^/${APP}$" --filter "name=^/${TRAEFIK}$" --filter "name=^/${PG}$"

section 'Estado detallado de la aplicación'
run docker inspect "$APP" --format 'Status={{.State.Status}} Running={{.State.Running}} Started={{.State.StartedAt}}'

section 'Etiquetas Traefik reales'
run docker inspect "$APP" --format '{{range $k,$v := .Config.Labels}}{{println $k "=" $v}}{{end}}'

section 'Redes de la aplicación'
run docker inspect "$APP" --format '{{json .NetworkSettings.Networks}}'

section 'Redes de Traefik'
run docker inspect "$TRAEFIK" --format '{{json .NetworkSettings.Networks}}'

section 'Resolución de la aplicación desde Traefik'
run docker exec "$TRAEFIK" getent hosts "$APP"

section 'Respuesta directa aplicación -> HTTP'
run docker exec "$TRAEFIK" wget --header="Host: $DOMAIN" -S -O- "http://$APP:8000/"

section 'Respuesta HTTPS externa con Host'
run curl -k -i --max-time 15 --resolve "$DOMAIN:443:127.0.0.1" "https://$DOMAIN/"

section 'Routers y servicios detectados por Traefik API'
run curl -sS --max-time 10 http://127.0.0.1:8080/api/http/routers
run curl -sS --max-time 10 http://127.0.0.1:8080/api/http/services

section 'Logs recientes de Traefik'
run docker logs --tail 150 "$TRAEFIK"

section 'Logs recientes de la aplicación'
run docker logs --tail 100 "$APP"

section 'Resultado'
printf 'Diagnóstico terminado para %s. No se reiniciaron contenedores ni se modificaron datos.\n' "$DOMAIN"
