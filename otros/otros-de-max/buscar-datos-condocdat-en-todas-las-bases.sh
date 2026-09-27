#!/usr/bin/env bash
set -euo pipefail

# Busca las tablas de Condocdat en todas las bases del PostgreSQL indicado.
# Solo lectura: no crea bases, tablas ni datos.

PG_CONTAINER="${PG_CONTAINER:-postgres_talleres}"
PG_USER="${PG_USER:-maxgonpe}"
PG_PASSWORD="${PG_PASSWORD:-celsa1961}"

command -v docker >/dev/null || { printf 'ERROR: Docker no está instalado.\n' >&2; exit 1; }
docker container inspect "$PG_CONTAINER" >/dev/null 2>&1 || {
  printf 'ERROR: no existe el contenedor %s.\n' "$PG_CONTAINER" >&2
  exit 1
}

psql_db() {
  local database="$1"
  shift
  docker exec -e PGPASSWORD="$PG_PASSWORD" "$PG_CONTAINER" \
    psql -U "$PG_USER" -d "$database" -Atc "$*"
}

printf '%-30s %10s %12s %10s\n' 'BASE' 'CARPETAS' 'DOCUMENTOS' 'USUARIOS'
printf '%-30s %10s %12s %10s\n' '------------------------------' '----------' '------------' '----------'

while IFS= read -r database; do
  [[ -n "$database" ]] || continue

  if [[ -n "$(psql_db "$database" "SELECT to_regclass('public.documents_folder');")" ]]; then
    folders="$(psql_db "$database" "SELECT COUNT(*) FROM documents_folder;")"
  else
    folders="-"
  fi
  if [[ -n "$(psql_db "$database" "SELECT to_regclass('public.documents_document');")" ]]; then
    documents="$(psql_db "$database" "SELECT COUNT(*) FROM documents_document;")"
  else
    documents="-"
  fi
  if [[ -n "$(psql_db "$database" "SELECT to_regclass('public.auth_user');")" ]]; then
    users="$(psql_db "$database" "SELECT COUNT(*) FROM auth_user;")"
  else
    users="-"
  fi

  printf '%-30s %10s %12s %10s\n' "$database" "$folders" "$documents" "$users"
done < <(psql_db postgres "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;")

printf '\nVolumen y redes del PostgreSQL:\n'
docker inspect "$PG_CONTAINER" --format 'Mounts: {{json .Mounts}}'
docker inspect "$PG_CONTAINER" --format 'Networks: {{json .NetworkSettings.Networks}}'
