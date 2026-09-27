#!/usr/bin/env bash
set -euo pipefail

# Consulta de diagnóstico. Solo lee PostgreSQL; no crea, modifica ni elimina datos.

PG_CONTAINER="${PG_CONTAINER:-postgres_talleres}"
PG_USER="${PG_USER:-maxgonpe}"
PG_PASSWORD="${PG_PASSWORD:-celsa1961}"
TARGET_DB="${TARGET_DB:-condocdat_db}"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

command -v docker >/dev/null || fail "Docker no está instalado"
docker container inspect "$PG_CONTAINER" >/dev/null 2>&1 || fail "No existe el contenedor $PG_CONTAINER"

if [[ "$(docker inspect -f '{{.State.Running}}' "$PG_CONTAINER")" != "true" ]]; then
  fail "El contenedor $PG_CONTAINER no está ejecutándose"
fi

psql() {
  docker exec -e PGPASSWORD="$PG_PASSWORD" "$PG_CONTAINER" \
    psql -U "$PG_USER" "$@"
}

printf '%s\n' '== Contenedor PostgreSQL =='
docker ps --filter "name=^/${PG_CONTAINER}$"

printf '%s\n' '== Bases de datos disponibles =='
psql -d postgres -Atc "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;"

printf '%s\n' "== Conteos en ${TARGET_DB} =="
if ! psql -d postgres -Atc "SELECT 1 FROM pg_database WHERE datname = '${TARGET_DB}';" | grep -q '^1$'; then
  fail "La base ${TARGET_DB} no existe"
fi

psql -d "$TARGET_DB" -v ON_ERROR_STOP=1 <<'SQL'
SELECT 'documents_folder' AS tabla, COUNT(*) AS registros FROM documents_folder;
SELECT 'documents_document' AS tabla, COUNT(*) AS registros FROM documents_document;
SELECT 'documents_folderfile' AS tabla, COUNT(*) AS registros FROM documents_folderfile;
SELECT 'auth_user' AS tabla, COUNT(*) AS registros FROM auth_user;
SQL

printf '%s\n' '== Tablas documents_* y conteos =='
psql -d "$TARGET_DB" -Atc "
  SELECT format('SELECT %L AS tabla, COUNT(*) AS registros FROM %I;', tablename, tablename)
  FROM pg_tables
  WHERE schemaname = 'public' AND tablename LIKE 'documents_%'
  ORDER BY tablename;
" | psql -d "$TARGET_DB"

printf '%s\n' '== Volúmenes y redes del contenedor =='
docker inspect "$PG_CONTAINER" --format 'Mounts: {{json .Mounts}}'
docker inspect "$PG_CONTAINER" --format 'Networks: {{json .NetworkSettings.Networks}}'

printf '%s\n' 'Consulta terminada. No se modificaron datos.'
