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
