#!/usr/bin/env bash
#
# Actualiza Condocdat en producción (usa docker-compose.prod.yml de ESTE directorio).
# Ejecutar desde la raíz de Condocdat: cd /home/max/myproject/condocdat && ./update_condocdat.sh
#
#   - Reconstruye la imagen con el código actual (incluye migraciones y estáticos)
#   - Detiene el contenedor y vuelve a levantar
#
# Uso: ./update_condocdat.sh [nocache]
#
set -euo pipefail

# Este script debe estar en la raíz de Condocdat (junto a manage.py y docker-compose.prod.yml)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

COMPOSE_FILE="docker-compose.prod.yml"

# Cargar .env en ESTE shell antes de docker compose. Así ${EMAIL_HOST_PASSWORD} y demás se
# interpolan bien (si solo confías en env_file del YAML, según versión de Compose puede fallar).
# Quitar \r por si el archivo se editó en Windows (si no, sed no molesta).
if [[ -f "${SCRIPT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source <(sed 's/\r$//' "${SCRIPT_DIR}/.env")
  set +a
fi

# Docker Compose sustituye ${EMAIL_HOST_PASSWORD} etc. desde el entorno del HOST.
# Si solo haces `export` en una sesión SSH y luego otro proceso/sesión ejecuta este script,
# el contenedor puede quedar sin secretos. Solución estable: un .env SOLO en el servidor
# (no subir a git; ya está en .gitignore). Opcional: .env.secrets con lo mismo.
COMPOSE_EXTRA_FLAGS=()
for envname in .env .env.secrets; do
  if [[ -f "${SCRIPT_DIR}/${envname}" ]]; then
    COMPOSE_EXTRA_FLAGS+=(--env-file "${SCRIPT_DIR}/${envname}")
  fi
done

# Aviso si no hay contraseña de correo ni por archivo ni por variable de entorno
_email_from_file=""
if [[ -f "${SCRIPT_DIR}/.env" ]] && grep -q '^EMAIL_HOST_PASSWORD=.' "${SCRIPT_DIR}/.env" 2>/dev/null; then
  _email_from_file="1"
elif [[ -f "${SCRIPT_DIR}/.env.secrets" ]] && grep -q '^EMAIL_HOST_PASSWORD=.' "${SCRIPT_DIR}/.env.secrets" 2>/dev/null; then
  _email_from_file="1"
fi
if [[ -z "${EMAIL_HOST_PASSWORD:-}" && -z "${_email_from_file}" ]]; then
  echo "⚠️  EMAIL_HOST_PASSWORD no está definido."
  echo "   Crea ${SCRIPT_DIR}/.env en el servidor (nano) con EMAIL_HOST_PASSWORD=tu_clave y el resto de variables."
  echo "   Ese archivo no se sube a git. Luego vuelve a ejecutar este script."
  echo ""
fi
# Si el .env declara la clave pero tras source sigue vacía, suele ser sintaxis inválida o caracteres especiales sin comillas
if [[ -f "${SCRIPT_DIR}/.env" ]] && grep -q '^EMAIL_HOST_PASSWORD=.' "${SCRIPT_DIR}/.env" 2>/dev/null; then
  if [[ -z "${EMAIL_HOST_PASSWORD:-}" ]]; then
    echo "❌ El .env tiene EMAIL_HOST_PASSWORD=... pero no se cargó en el shell."
    echo "   Usa una sola línea: EMAIL_HOST_PASSWORD='tu_clave' (comillas simples si hay \$ # !)."
    exit 1
  fi
fi
unset _email_from_file
if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "❌ No se encuentra $COMPOSE_FILE en $SCRIPT_DIR"
  exit 1
fi
SERVICE_NAME="condocdat"
BUILD_NO_CACHE=""

# Usar "docker compose" (v2) o "docker-compose" (v1)
if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
else
  COMPOSE_CMD="docker-compose"
fi

if [[ "${1:-}" == "nocache" ]]; then
  BUILD_NO_CACHE="--no-cache"
  echo "🔧 Modo: reconstrucción completa (sin caché)"
fi

echo "📂 Proyecto: $SCRIPT_DIR"
echo ""

echo "📦 Reconstruyendo imagen Docker..."
$COMPOSE_CMD "${COMPOSE_EXTRA_FLAGS[@]}" -f "$COMPOSE_FILE" build $BUILD_NO_CACHE

echo ""
echo "🛑 Deteniendo contenedor..."
$COMPOSE_CMD "${COMPOSE_EXTRA_FLAGS[@]}" -f "$COMPOSE_FILE" down

echo ""
echo "🚀 Levantando con la nueva imagen..."
$COMPOSE_CMD "${COMPOSE_EXTRA_FLAGS[@]}" -f "$COMPOSE_FILE" up -d

echo ""
echo "⏳ Esperando unos segundos a que arranque..."
sleep 3

echo ""
echo "📋 Últimas líneas del log (migraciones y collectstatic se ejecutan al iniciar):"
$COMPOSE_CMD "${COMPOSE_EXTRA_FLAGS[@]}" -f "$COMPOSE_FILE" logs --tail=25 "$SERVICE_NAME"

echo ""
echo "✅ Listo. Sitio: https://condocdat.netgogo.cl"
echo "   Ver logs en vivo: $COMPOSE_CMD ${COMPOSE_EXTRA_FLAGS[*]:-} -f $COMPOSE_FILE logs -f $SERVICE_NAME"
echo ""
