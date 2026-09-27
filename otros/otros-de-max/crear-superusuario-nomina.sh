#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${NOMINA_CONTAINER:-nomina_app}"
USERNAME="${NOMINA_ADMIN_USER:-adminomina}"
PASSWORD="${NOMINA_ADMIN_PASSWORD:-adminomina}"
EMAIL="${NOMINA_ADMIN_EMAIL:-adminomina@netgogo.cl}"

docker container inspect "$CONTAINER_NAME" >/dev/null 2>&1 || {
  printf 'ERROR: no existe el contenedor %s\n' "$CONTAINER_NAME" >&2
  exit 1
}

docker exec -i \
  -e NOMINA_ADMIN_USER="$USERNAME" \
  -e NOMINA_ADMIN_PASSWORD="$PASSWORD" \
  -e NOMINA_ADMIN_EMAIL="$EMAIL" \
  "$CONTAINER_NAME" python manage.py shell <<'PY'
import os

from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ["NOMINA_ADMIN_USER"]
password = os.environ["NOMINA_ADMIN_PASSWORD"]
email = os.environ["NOMINA_ADMIN_EMAIL"]

user, created = User.objects.get_or_create(
    username=username,
    defaults={"email": email},
)
user.email = email
user.is_staff = True
user.is_superuser = True
user.is_active = True
user.set_password(password)
user.save()

print(f"Superusuario {'creado' if created else 'actualizado'}: {username}")
PY
