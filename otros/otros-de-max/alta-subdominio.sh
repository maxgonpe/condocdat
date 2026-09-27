#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
CREATE_SCRIPT="$SCRIPT_DIR/crear-demo-subdominio.sh"

usage() {
  printf 'Uso: %s NOMBRE SUBDOMINIO [DIRECTORIO]\n' "$(basename "$0")"
  printf 'Ejemplo: %s inventario inventario.netgogo.cl /home/max/inventario\n' "$(basename "$0")"
}

[[ $# -ge 2 && $# -le 3 ]] || { usage >&2; exit 2; }
name="$1"
domain="$2"
app_dir="${3:-/home/max/$name}"

[[ "$name" =~ ^[a-z][a-z0-9_-]*$ ]] || { printf 'ERROR: nombre inválido.\n' >&2; exit 1; }
[[ "$domain" =~ ^[a-z0-9-]+\.netgogo\.cl$ ]] || { printf 'ERROR: subdominio inválido.\n' >&2; exit 1; }

APP_NAME="$name" DOMAIN="$domain" APP_DIR="$app_dir" \
DB_NAME="${name}_db" DB_USER="$name" "$CREATE_SCRIPT"

printf '\nAlta completada: https://%s\n' "$domain"
printf 'Salud DB: https://%s/health/database\n' "$domain"
