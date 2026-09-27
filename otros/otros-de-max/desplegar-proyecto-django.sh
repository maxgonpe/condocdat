#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${1:-}"
DOMAIN="${2:-}"
APP_DIR="${3:-}"
PG_CONTAINER="${PG_CONTAINER:-postgres_talleres}"
PG_ADMIN_USER="${PG_ADMIN_USER:-maxgonpe}"
PG_ADMIN_PASSWORD="${PG_ADMIN_PASSWORD:-}"
PG_NETWORK="${PG_NETWORK:-myproject_netgogo_default}"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
[[ "$APP_NAME" =~ ^[a-z][a-z0-9_]*$ ]] || fail "nombre inválido"
[[ "$DOMAIN" =~ ^[a-z0-9-]+\.netgogo\.cl$ ]] || fail "dominio inválido"
[[ -d "$APP_DIR" ]] || fail "directorio inexistente: $APP_DIR"
[[ "$APP_DIR" == /home/max/* ]] || fail "en producción el proyecto debe estar bajo /home/max/"
[[ -f "$APP_DIR/docker-compose.yml" ]] || fail "falta docker-compose.yml"
[[ -f "$APP_DIR/Dockerfile" ]] || fail "falta Dockerfile"
[[ -f "$APP_DIR/requirements.txt" ]] || fail "falta requirements.txt"
command -v docker >/dev/null || fail "Docker no está instalado"
docker container inspect "$PG_CONTAINER" >/dev/null 2>&1 || fail "no existe $PG_CONTAINER"
[[ "$(docker inspect -f '{{.State.Running}}' "$PG_CONTAINER")" == true ]] || fail "$PG_CONTAINER no está activo"
docker network inspect traefik_default >/dev/null 2>&1 || fail "no existe traefik_default"
docker network inspect "$PG_NETWORK" >/dev/null 2>&1 || fail "no existe $PG_NETWORK"

DB_NAME="${APP_NAME}_db"
DB_USER="${DB_USER:-$PG_ADMIN_USER}"
DB_PASSWORD="${DB_PASSWORD:-$PG_ADMIN_PASSWORD}"
INITIAL_SUPERUSER="${INITIAL_SUPERUSER:-maxgonpe}"
INITIAL_SUPERUSER_PASSWORD="${INITIAL_SUPERUSER_PASSWORD:-celsa1961}"
INITIAL_SUPERUSER_EMAIL="${INITIAL_SUPERUSER_EMAIL:-maxgonpe@netgogo.cl}"
[[ -n "$PG_ADMIN_PASSWORD" ]] || fail "Define PG_ADMIN_PASSWORD con la contraseña PostgreSQL existente"
psql_admin() {
  docker exec -e PGPASSWORD="$PG_ADMIN_PASSWORD" "$PG_CONTAINER" psql -v ON_ERROR_STOP=1 -U "$PG_ADMIN_USER" -d postgres "$@"
}

role_exists="$(psql_admin -Atc "SELECT 1 FROM pg_roles WHERE rolname = '$DB_USER';")"
db_exists="$(psql_admin -Atc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';")"
[[ -n "$role_exists" ]] || fail "No existe el usuario PostgreSQL existente: $DB_USER"
if [[ -z "$db_exists" ]]; then
  psql_admin -c "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\";"
fi

mkdir -p "$APP_DIR/media"
cat > "$APP_DIR/.env" <<EOF
APP_NAME=$APP_NAME
DOMAIN=$DOMAIN
DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY:-django-insecure-local-migration-key}
DJANGO_DEBUG=False
DB_ENGINE=django.db.backends.postgresql
DB_HOST=$PG_CONTAINER
DB_PORT=5432
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
POSTGRES_NETWORK=$PG_NETWORK
EOF
chmod 600 "$APP_DIR/.env"

cd "$APP_DIR"
if docker compose version >/dev/null 2>&1; then compose() { docker compose "$@"; }
elif docker-compose version >/dev/null 2>&1; then compose() { docker-compose "$@"; }
else fail "no existe docker compose ni docker-compose"; fi
compose config >/dev/null
compose up -d --build --force-recreate
compose exec -T app python manage.py migrate --noinput
compose exec -T \
  -e INITIAL_SUPERUSER="$INITIAL_SUPERUSER" \
  -e INITIAL_SUPERUSER_PASSWORD="$INITIAL_SUPERUSER_PASSWORD" \
  -e INITIAL_SUPERUSER_EMAIL="$INITIAL_SUPERUSER_EMAIL" \
  app python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ["INITIAL_SUPERUSER"]
user, created = User.objects.get_or_create(
    username=username,
    defaults={"email": os.environ["INITIAL_SUPERUSER_EMAIL"]},
)
user.email = os.environ["INITIAL_SUPERUSER_EMAIL"]
user.is_active = True
user.is_staff = True
user.is_superuser = True
user.set_password(os.environ["INITIAL_SUPERUSER_PASSWORD"])
user.save()
print(f"Superusuario {'creado' if created else 'actualizado'}: {username}")
PY
compose exec -T app python manage.py collectstatic --noinput

pending="$(compose exec -T app python manage.py showmigrations --plan | grep -E '^\s*\[ \]' || true)"
if [[ -n "$pending" ]]; then
  printf 'ERROR: quedaron migraciones pendientes:\n%s\n' "$pending" >&2
  exit 1
fi

compose ps
printf 'Proyecto desplegado: https://%s/\n' "$DOMAIN"
