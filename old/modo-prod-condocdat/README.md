# Modo producción — Condocdat con PostgreSQL

Estos archivos configuran Condocdat en producción para usar la base **condocdat_db** en el mismo PostgreSQL que Talleres (`postgres_talleres`).

## Pasos en el servidor

1. **Red Docker**  
   El contenedor Condocdat debe estar en la **misma red** que `postgres_talleres` para que `DB_HOST=postgres_talleres` resuelva.  
   En producción se usa la red **`myproject_netgogo_default`** (ya configurada en los compose).  
   Para ver las redes del contenedor Postgres:
   ```bash
   docker inspect postgres_talleres --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}'
   ```

2. **Variables de entorno**  
   En el directorio del proyecto Condocdat (no dentro de modo-prod-condocdat), crea `.env` a partir del ejemplo:
   ```bash
   cp modo-prod-condocdat/.env.example .env
   ```
   Edita `.env` y pon la contraseña real en `DB_PASSWORD` y, si hace falta, `SECRET_KEY` y `ALLOWED_HOSTS`.

3. **Levantar**  
   Desde el directorio raíz del proyecto Condocdat (donde está `manage.py`):
   ```bash
   docker compose -f modo-prod-condocdat/docker-compose.prod.yml up -d
   ```

4. **Actualizar (script)**  
   Si usas el script de actualización, desde el directorio donde está el script:
   ```bash
   ./update_condocdat.sh
   ```
   Asegúrate de que el script se ejecute desde el directorio raíz del proyecto si usa rutas relativas; si está dentro de `modo-prod-condocdat`, en el script `SCRIPT_DIR` será ese subdirectorio. Si sueles correr desde la raíz del proyecto, puedes ejecutar:
   ```bash
   cd /home/max/myproject/condocdat && ./modo-prod-condocdat/update_condocdat.sh
   ```
   y adaptar el script para que `cd` vaya a la raíz del proyecto (parent del script) si hace falta.

## Archivos modificados

- **docker-compose.prod.yml** / **docker-compose.yml**: variables `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`; red `postgres_net` para conectar con el PostgreSQL.
- **settings.py**: mismo contenido que el de `condocdat/settings.py` con soporte PostgreSQL por env y `CONN_MAX_AGE`. Sustituye o mantén alineado con `condocdat/settings.py` del proyecto.
- **.env.example**: plantilla para `.env` en producción con PostgreSQL.
