"""
Plantilla para settings local — copia a settings_local.py y ajusta valores.

Uso: cp condocdat/settings_local.example.py condocdat/settings_local.py
Luego: export DJANGO_SETTINGS_MODULE=condocdat.settings_local
"""
from .settings import *  # noqa: F401, F403

# Misma conexión que Talleres; solo cambia el nombre de la base.
# HOST: 'localhost' si Postgres está en tu máquina; IP/host del servidor si es remoto.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'condocdat_db',
        'USER': 'tu_usuario',
        'PASSWORD': 'tu_password',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 60,
    }
}
