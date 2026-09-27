#!/usr/bin/env bash
set -u

APP="condocdat"
PG="postgres_talleres"
TRAEFIK="traefik-traefik-1"
DB_USER="maxgonpe"
DB_NAME="condocdat_db"
DB_PASSWORD="celsa1961"

section() {
  printf '\n===== %s =====\n' "$1"
}

section 'Contenedores'
docker ps --filter "name=^/${APP}$" --filter "name=^/${PG}$" --filter "name=^/${TRAEFIK}$"

section 'Logs recientes de Condocdat'
docker logs --tail 100 "$APP" 2>&1 || true

section 'Resolución DNS de PostgreSQL desde Condocdat'
docker exec "$APP" getent hosts "$PG" || true

section 'Conectividad PostgreSQL desde Condocdat'
docker exec -e PGPASSWORD="$DB_PASSWORD" "$APP" \
  pg_isready -h "$PG" -p 5432 -U "$DB_USER" -d "$DB_NAME" || true

section 'Variables DB reales'
docker inspect "$APP" --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep -E '^DB_(ENGINE|NAME|USER|HOST|PORT)=' || true

section 'Redes de Condocdat'
docker inspect "$APP" --format '{{json .NetworkSettings.Networks}}' || true

section 'Redes de PostgreSQL'
docker inspect "$PG" --format '{{json .NetworkSettings.Networks}}' || true

section 'Puerto 8000 dentro de Condocdat'
docker exec "$APP" sh -c 'if command -v curl >/dev/null; then curl -sS -o /dev/null -w "HTTP %{http_code}\\n" http://127.0.0.1:8000/; elif command -v wget >/dev/null; then wget -S --spider http://127.0.0.1:8000/ 2>&1; else python -c "import urllib.request; print(urllib.request.urlopen(\"http://127.0.0.1:8000/\").status)"; fi' || true

section 'Prueba desde Traefik hacia Condocdat'
docker exec "$TRAEFIK" sh -c 'if command -v wget >/dev/null; then wget -S --spider http://condocdat:8000/ 2>&1; elif command -v curl >/dev/null; then curl -sS -o /dev/null -w "HTTP %{http_code}\\n" http://condocdat:8000/; else getent hosts condocdat; fi' || true

section 'Datos en la base histórica'
docker exec -e PGPASSWORD="$DB_PASSWORD" "$PG" \
  psql -U "$DB_USER" -d "$DB_NAME" -c \
  'SELECT COUNT(*) AS carpetas FROM documents_folder; SELECT COUNT(*) AS documentos FROM documents_document;' || true

printf '\nDiagnóstico terminado. No se detuvieron contenedores ni se modificaron datos.\n'
