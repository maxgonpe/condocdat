#!/usr/bin/env bash
#
# Actualiza Condocdat en producción (PostgreSQL).
# Usa docker-compose.prod.yml de esta carpeta (modo-prod-condocdat).
#
# Uso (desde la raíz de Condocdat):
#   cd /home/max/myproject/condocdat
#   ./modo-prod-condocdat/update_condocdat.sh [nocache]
#
# nocache = reconstruir imagen sin caché (más lento)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

COMPOSE_FILE="modo-prod-condocdat/docker-compose.prod.yml"
SERVICE_NAME="condocdat"
BUILD_NO_CACHE=""

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "❌ No se encuentra $COMPOSE_FILE"
  echo "   Ejecuta este script desde la raíz de Condocdat: cd /home/max/myproject/condocdat && ./modo-prod-condocdat/update_condocdat.sh"
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
else
  COMPOSE_CMD="docker-compose"
fi

if [[ "${1:-}" == "nocache" ]]; then
  BUILD_NO_CACHE="--no-cache"
  echo "🔧 Modo: reconstrucción completa (sin caché)"
fi

echo "📂 Proyecto: $PROJECT_ROOT"
echo "📄 Compose:  $COMPOSE_FILE"
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
echo "📋 Últimas líneas del log:"
$COMPOSE_CMD -f "$COMPOSE_FILE" logs --tail=25 "$SERVICE_NAME"

echo ""
echo "✅ Listo. Sitio: https://condocdat.netgogo.cl"
echo "   Logs en vivo: $COMPOSE_CMD -f $COMPOSE_FILE logs -f $SERVICE_NAME"
echo ""
