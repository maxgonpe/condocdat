#!/bin/bash
set -e

echo "🚀 Iniciando aplicación Condocdat..."

mkdir -p /app/data
mkdir -p /app/media
mkdir -p /app/staticfiles

if [ "$DB_ENGINE" = "django.db.backends.postgresql" ]; then
    echo "⏳ Esperando a PostgreSQL..."
    python -c "
import socket
import sys
import time
host = '${DB_HOST}'
port = int('${DB_PORT}')
while True:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            break
    except:
        pass
    time.sleep(0.5)
"
    echo "✅ PostgreSQL está listo"
fi

echo "📦 Ejecutando migraciones..."
python manage.py migrate --noinput

echo "📁 Recopilando archivos estáticos..."
python manage.py collectstatic --noinput

echo "✅ Aplicación lista para iniciar"

exec "$@"
