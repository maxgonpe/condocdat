#!/usr/bin/env bash
#
# Actualiza Condocdat en producción:
#   - Reconstruye la imagen con el código actual (incluye migraciones y estáticos)
#   - Detiene el contenedor
#   - Vuelve a levantar con la nueva imagen
#
# Uso: ./update_condocdat.sh [nocache]
#   nocache = reconstruir imagen sin caché (más lento, útil si algo falla)
#
set -euo pipefail

# Directorio del proyecto = donde está este script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

COMPOSE_FILE="docker-compose.prod.yml"
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
$COMPOSE_CMD -f "$COMPOSE_FILE" build $BUILD_NO_CACHE

echo ""
echo "🛑 Deteniendo contenedor..."
$COMPOSE_CMD -f "$COMPOSE_FILE" down

echo ""
echo "🚀 Levantando con la nueva imagen..."
$COMPOSE_CMD -f "$COMPOSE_FILE" up -d

echo ""
echo "⏳ Esperando unos segundos a que arranque..."
sleep 3

echo ""
echo "📋 Últimas líneas del log (migraciones y collectstatic se ejecutan al iniciar):"
$COMPOSE_CMD -f "$COMPOSE_FILE" logs --tail=25 "$SERVICE_NAME"

echo ""
echo "✅ Listo. Sitio: https://condocdat.netgogo.cl"
echo "   Ver logs en vivo: $COMPOSE_CMD -f $COMPOSE_FILE logs -f $SERVICE_NAME"
echo ""
