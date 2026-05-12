#!/usr/bin/env bash
# Volcado de la base Condocdat desde producción y restauración en PostgreSQL local.
# Requisitos: SYNC_METHOD=docker_local en el servidor → Docker. SYNC_METHOD=docker_ssh desde tu PC
# → ssh + Docker remoto. restore → psql y pg_restore en tu máquina (o LOCAL_USE_DOCKER).
#
# Configuración: scripts/condocdat_db_sync.env (ver condocdat_db_sync.env.example)
#   export CONDOCDAT_SYNC_ENV=/ruta/otro.env  # opcional

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${CONDOCDAT_SYNC_ENV:-${SCRIPT_DIR}/condocdat_db_sync.env}"

usage() {
  cat <<'EOF'
Volcado de la base Condocdat (producción) y restauración en PostgreSQL local.

Uso:
  ./scripts/condocdat_db_sync.sh dump [ruta_salida.pgdump]
  ./scripts/condocdat_db_sync.sh restore [--yes|-y] <archivo.pgdump>
  ./scripts/condocdat_db_sync.sh restore <archivo.pgdump> [--yes|-y]

  --yes / -y  Omitir la confirmación (útil en scripts).

Configuración: scripts/condocdat_db_sync.env (copia desde scripts/condocdat_db_sync.env.example).
Opcional: CONDOCDAT_SYNC_ENV=/ruta/otro.env

Restore local: LOCAL_RESTORE_MODE=clean (por defecto) no usa CREATE DATABASE; adecuado si tu
usuario Postgres no tiene CREATEDB (p. ej. maxgonpe con settings.py por defecto).
EOF
  exit "${1:-0}"
}

if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
  usage 0
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "No existe el archivo de configuración: $ENV_FILE" >&2
  echo "Copia scripts/condocdat_db_sync.env.example -> scripts/condocdat_db_sync.env y edítalo." >&2
  exit 1
fi

# shellcheck source=/dev/null
set -a
source "$ENV_FILE"
set +a

# Por defecto volcar con docker en ESTA máquina (servidor de producción). docker_ssh solo si el
# .env tiene un PROD_SSH_HOST real (no placeholder del ejemplo).
if [[ "${SYNC_METHOD:-docker_local}" == "docker_ssh" ]]; then
  if [[ -z "${PROD_SSH_HOST:-}" ]] || [[ "${PROD_SSH_HOST}" == *"ejemplo.cl"* ]]; then
    echo "Nota: SYNC_METHOD=docker_ssh pero PROD_SSH_HOST vacío o de ejemplo → uso docker_local." >&2
    SYNC_METHOD=docker_local
  fi
fi
SYNC_METHOD="${SYNC_METHOD:-docker_local}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Falta el comando en PATH: $1" >&2
    exit 1
  fi
}

default_outfile() {
  echo "${SCRIPT_DIR}/condocdat_prod_$(date +%Y%m%d_%H%M%S).pgdump"
}

cmd_dump() {
  local outfile="${1:-$(default_outfile)}"
  mkdir -p "$(dirname "$outfile")"

  case "${SYNC_METHOD}" in
    docker_local)
      if [[ -z "${PROD_PG_CONTAINER:-}" ]]; then
        echo "Para SYNC_METHOD=docker_local define PROD_PG_CONTAINER en $ENV_FILE" >&2
        exit 1
      fi
      require_cmd docker
      echo "Volcando (Docker en esta máquina) -> $outfile (contenedor: $PROD_PG_CONTAINER)..."
      local extra="${PROD_DOCKER_EXEC_EXTRA:-}"
      # shellcheck disable=SC2086
      docker exec -i $extra "$PROD_PG_CONTAINER" \
        pg_dump -U "${PROD_PG_USER:?definir PROD_PG_USER}" -d "${PROD_DB_NAME:?definir PROD_DB_NAME}" -F c \
        >"$outfile"
      ;;
    docker_ssh)
      if [[ -z "${PROD_SSH_HOST:-}" ]] || [[ -z "${PROD_PG_CONTAINER:-}" ]]; then
        echo "Para SYNC_METHOD=docker_ssh define PROD_SSH_HOST y PROD_PG_CONTAINER en $ENV_FILE" >&2
        exit 1
      fi
      require_cmd ssh
      echo "Volcando producción -> $outfile (SSH: $PROD_SSH_HOST, contenedor: $PROD_PG_CONTAINER)..."
      if [[ -n "${PROD_SSH_DUMP_COMMAND:-}" ]]; then
        ssh -o BatchMode=yes -o ConnectTimeout=30 "$PROD_SSH_HOST" "$PROD_SSH_DUMP_COMMAND" >"$outfile"
      else
        local extra="${PROD_DOCKER_EXEC_EXTRA:-}"
        # shellcheck disable=SC2086
        ssh -o BatchMode=yes -o ConnectTimeout=30 "$PROD_SSH_HOST" \
          docker exec -i $extra "$PROD_PG_CONTAINER" \
          pg_dump -U "${PROD_PG_USER:?definir PROD_PG_USER}" -d "${PROD_DB_NAME:?definir PROD_DB_NAME}" -F c \
          >"$outfile"
      fi
      ;;
    direct)
      require_cmd pg_dump
      export PGHOST="${PROD_PG_HOST:?definir PROD_PG_HOST}"
      export PGPORT="${PROD_PG_PORT:-5432}"
      export PGUSER="${PROD_PG_USER:?definir PROD_PG_USER}"
      export PGDATABASE="${PROD_DB_NAME:?definir PROD_DB_NAME}"
      export PGPASSWORD="${PROD_PG_PASSWORD:-}"
      echo "Volcando producción (directo $PGHOST:$PGPORT) -> $outfile..."
      pg_dump -F c -f "$outfile"
      ;;
    *)
      echo "SYNC_METHOD desconocido: ${SYNC_METHOD:-}" >&2
      exit 1
      ;;
  esac

  echo "Listo. Tamaño: $(du -h "$outfile" | cut -f1)"
  echo "Restaurar en local: $0 restore \"$outfile\""
}

psql_admin() {
  local -a args=(-v ON_ERROR_STOP=1 -d postgres -c "$1")
  if [[ "${LOCAL_USE_DOCKER:-false}" == "true" ]] || [[ "${LOCAL_USE_DOCKER:-false}" == "1" ]]; then
    require_cmd docker
    docker exec -i "${LOCAL_PG_CONTAINER:?definir LOCAL_PG_CONTAINER}" \
      psql -U "${LOCAL_PG_USER:?definir LOCAL_PG_USER}" "${args[@]}"
  else
    require_cmd psql
    export PGPASSWORD="${LOCAL_PG_PASSWORD:?definir LOCAL_PG_PASSWORD}"
    psql -h "${LOCAL_PG_HOST:?definir LOCAL_PG_HOST}" -p "${LOCAL_PG_PORT:-5432}" \
      -U "${LOCAL_PG_USER:?definir LOCAL_PG_USER}" "${args[@]}"
  fi
}

# Comprueba si existe la base $1 (consulta contra la base postgres).
local_db_exists() {
  local db="$1"
  local q="SELECT 1 FROM pg_database WHERE datname='${db}';"
  if [[ "${LOCAL_USE_DOCKER:-false}" == "true" ]] || [[ "${LOCAL_USE_DOCKER:-false}" == "1" ]]; then
    docker exec -i "${LOCAL_PG_CONTAINER:?}" psql -U "${LOCAL_PG_USER:?}" -d postgres -tAc "$q" | grep -q 1
  else
    export PGPASSWORD="${LOCAL_PG_PASSWORD:?}"
    psql -h "${LOCAL_PG_HOST:?}" -p "${LOCAL_PG_PORT:-5432}" -U "${LOCAL_PG_USER:?}" -d postgres -tAc "$q" | grep -q 1
  fi
}

cmd_restore() {
  local infile="${1:-}"
  if [[ -n "$infile" && "$infile" != /* ]]; then
    infile="$(pwd)/${infile#./}"
  fi
  if [[ -z "$infile" ]] || [[ ! -f "$infile" ]]; then
    echo "No encuentro el archivo de volcado." >&2
    echo "  Indicaste: ${1:-<vacío>}" >&2
    echo "  Resuelto a: ${infile:-}" >&2
    echo "  Directorio actual: $(pwd)" >&2
    echo "Uso: $0 restore [--yes|-y] <archivo.pgdump>   (también: restore <archivo> --yes)" >&2
    exit 1
  fi
  require_cmd pg_restore
  local db="${LOCAL_DB_NAME:?definir LOCAL_DB_NAME}"
  local mode="${LOCAL_RESTORE_MODE:-clean}"

  if [[ "$mode" == "recreate" ]]; then
    echo "ADVERTENCIA (recreate): DROP + CREATE de la base \"$db\" (requiere CREATEDB o superusuario)."
  else
    echo "ADVERTENCIA (clean): se reemplazan objetos del volcado dentro de la base \"$db\" (pg_restore --clean). Cierra Django u otras conexiones."
  fi
  if [[ "${CONDOCDAT_SYNC_RESTORE_YES:-0}" != "1" ]]; then
    read -r -p "¿Continuar? [s/N] " ans
    if [[ ! "${ans:-}" =~ ^[sSyY]$ ]]; then
      echo "Cancelado."
      exit 0
    fi
  fi

  if [[ "$mode" == "recreate" ]]; then
    echo "Recreando base local \"$db\"..."
    psql_admin "DROP DATABASE IF EXISTS \"${db}\" WITH (FORCE);"
    psql_admin "CREATE DATABASE \"${db}\" OWNER \"${LOCAL_PG_USER}\";"
  else
    if ! local_db_exists "$db"; then
      echo "La base \"$db\" no existe. Créala una vez con un rol superusuario (tu usuario Django no tiene CREATEDB), por ejemplo:" >&2
      echo "  sudo -u postgres psql -c \"CREATE DATABASE ${db} OWNER ${LOCAL_PG_USER} ENCODING 'UTF8';\"" >&2
      exit 1
    fi
  fi

  local -a rargs=(-d "$db" --no-owner --no-acl)
  if [[ "$mode" != "recreate" ]]; then
    rargs+=(--clean --if-exists)
  fi

  echo "Restaurando desde $infile (modo $mode)..."
  if [[ "${LOCAL_USE_DOCKER:-false}" == "true" ]] || [[ "${LOCAL_USE_DOCKER:-false}" == "1" ]]; then
    docker exec -i "${LOCAL_PG_CONTAINER:?}" \
      pg_restore -U "${LOCAL_PG_USER:?}" "${rargs[@]}" <"$infile"
  else
    export PGPASSWORD="${LOCAL_PG_PASSWORD:?}"
    pg_restore -h "${LOCAL_PG_HOST:?}" -p "${LOCAL_PG_PORT:-5432}" -U "${LOCAL_PG_USER:?}" \
      "${rargs[@]}" "$infile"
  fi

  echo "Restauración terminada. Apunta Django a esta base (DB_NAME=$db, mismo usuario que en settings / .env)."
}

case "${1:-}" in
  dump)
    shift || true
    cmd_dump "${1:-}"
    ;;
  restore)
    shift || true
    CONDOCDAT_SYNC_RESTORE_YES=0
    dump_path=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --yes | -y)
          CONDOCDAT_SYNC_RESTORE_YES=1
          ;;
        -*)
          echo "Opción desconocida: $1 (usa --yes o -y)" >&2
          exit 1
          ;;
        *)
          if [[ -n "$dump_path" ]]; then
            echo "Indica un solo archivo .pgdump; sobró: $1" >&2
            exit 1
          fi
          dump_path=$1
          ;;
      esac
      shift || true
    done
    cmd_restore "$dump_path"
    ;;
  *)
    usage 1
    ;;
esac
