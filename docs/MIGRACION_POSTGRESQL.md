# Migración de SQLite a PostgreSQL — Condocdat

Esta guía describe los pasos para pasar Condocdat de SQLite a PostgreSQL de forma segura, manteniendo los datos existentes. La base PostgreSQL puede ser la misma instancia que ya usas (por ejemplo con Talleres), creando una **base de datos nueva** solo para Condocdat.

---

## Pasos en local (resumen ejecutivo)

Ya tienes en el proyecto:

- **condocdat_fixture.json** — exportación de tu SQLite (mismo contenido que producción).
- **.env.postgres.local** — variables para conectar a PostgreSQL local (misma config que el compose).

**1) Tener PostgreSQL con la base y el usuario**

- **Opción A — Contenedor del proyecto (misma config que producción):**
  ```bash
  docker compose -f docker-compose.postgres.yml up -d
  ```
  Crea `condocdat_db` y usuario `condocdat_user` con contraseña `condocdat_local`. No hace falta instalar Postgres en el sistema.

- **Opción B — PostgreSQL ya instalado (ej. el de Talleres):** crea la base y el usuario:
  ```sql
  CREATE USER condocdat_user WITH PASSWORD 'tu_password';
  CREATE DATABASE condocdat_db OWNER condocdat_user ENCODING 'UTF8';
  \c condocdat_db
  GRANT ALL ON SCHEMA public TO condocdat_user;
  ```
  Pon en `.env.postgres.local` la misma contraseña en `DB_PASSWORD`.

**2) Conectar Django a PostgreSQL y cargar datos**

En la raíz del proyecto, con el venv activado:

```bash
export $(grep -v '^#' .env.postgres.local | xargs)
python manage.py migrate --noinput
python manage.py loaddata condocdat_fixture.json
```

**3) Probar**

```bash
python manage.py runserver
```

Entra al sitio y revisa documentos, carpetas, Estatus Cartas y búsqueda. Para volver a SQLite, cierra la terminal o haz `unset DB_ENGINE DB_NAME DB_USER DB_PASSWORD DB_HOST DB_PORT`.

---

## Compatibilidad local ↔ producción

Para que tu **PostgreSQL local** sea **totalmente compatible** con el de producción:

- **Mismo nombre de base:** `condocdat_db`
- **Mismo usuario:** `condocdat_user`
- **Misma versión de PostgreSQL:** en el proyecto se usa **PostgreSQL 16** (imagen `postgres:16-alpine`) tanto en el compose local como la que deberías usar en el servidor
- **Mismo encoding:** UTF-8 (por defecto en la imagen)

En **local** no hace falta correr Django en Docker: solo levantas el contenedor de PostgreSQL y conectas tu Django del venv con las mismas variables que usará producción (cambiando solo `DB_HOST`: en local `127.0.0.1`, en producción el host del servidor o el nombre del servicio en la red Docker).

**Conexión local igual que Talleres (mismo Postgres, base distinta):**  
Si quieres usar en local la **misma instancia y usuario** que Talleres en producción (solo cambiando el nombre de la base a `condocdat_db`), usa el settings local sin variables de entorno:

```bash
# Usar settings_local (mismo usuario/contraseña que Talleres, base condocdat_db)
export DJANGO_SETTINGS_MODULE=condocdat.settings_local
python manage.py migrate
python manage.py runserver
```

El archivo `condocdat/settings_local.py` define la conexión fija (no usa env); está en `.gitignore`. Si clonas el repo, copia `condocdat/settings_local.example.py` a `condocdat/settings_local.py` y pon tu usuario/contraseña. En producción se sigue usando el `settings.py` normal con variables de entorno.

Así las migraciones, el esquema y el comportamiento (incluido full-text search) son idénticos en ambos entornos.

---

## PostgreSQL solo en local (mismo que producción)

Sin tocar tu flujo actual (SQLite por defecto, Django desde el venv):

1. **Levantar solo PostgreSQL** (misma config que producción):
   ```bash
   docker compose -f docker-compose.postgres.yml up -d
   ```

2. **Conectar Django a ese Postgres** solo cuando quieras probar con BD real:
   ```bash
   cp .env.postgres.local.example .env.postgres.local
   # Edita .env.postgres.local si cambiaste la contraseña en el compose
   export $(grep -v '^#' .env.postgres.local | xargs)
   python manage.py migrate
   python manage.py runserver
   ```

3. **Volver a SQLite** cuando quieras:
   ```bash
   unset DB_ENGINE DB_NAME DB_USER DB_PASSWORD DB_HOST DB_PORT
   # o cierra la terminal y abre otra
   ```

El archivo `.env.postgres.local` está en `.gitignore`; el ejemplo `.env.postgres.local.example` sí se puede subir. En producción usarás las mismas variables (`DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`) con `DB_HOST` apuntando al servidor PostgreSQL.

---

## Requisitos previos

- Servidor PostgreSQL accesible (el mismo que usa Talleres u otras apps).
- `psycopg2-binary` ya está en `requirements.txt`.
- El proyecto ya soporta PostgreSQL vía variables de entorno (ver más abajo).

---

## Resumen en 5 pasos

1. **Crear la base de datos y usuario** en el servidor PostgreSQL (solo una vez).
2. **Exportar datos desde SQLite** con `dumpdata` (con la app apuntando aún a SQLite).
3. **Apuntar Django a PostgreSQL** (env vars o settings).
4. **Crear tablas en PostgreSQL** con `migrate` y **cargar datos** con `loaddata`.
5. **Comprobar** que todo funciona y, si quieres, desactivar SQLite.

---

## Paso 1 — Crear base de datos y usuario en PostgreSQL

En el servidor donde corre PostgreSQL (el mismo que usas para Talleres u otras apps), crea una base **nueva** solo para Condocdat. Recomendable usar **PostgreSQL 16** (o la misma versión que en `docker-compose.postgres.yml`) para que el esquema y el full-text search coincidan con tu entorno local.

```sql
-- Conectar como superusuario (postgres o el usuario admin)

-- Opción A: Usuario dedicado para Condocdat (recomendado)
CREATE USER condocdat_user WITH PASSWORD 'tu_password_seguro';

-- Base de datos solo para Condocdat
CREATE DATABASE condocdat_db OWNER condocdat_user ENCODING 'UTF8';

-- Permisos
GRANT ALL PRIVILEGES ON DATABASE condocdat_db TO condocdat_user;
\c condocdat_db
GRANT ALL ON SCHEMA public TO condocdat_user;
-- Para secuencias y tablas que creará Django
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO condocdat_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO condocdat_user;
```

Si prefieres usar el **mismo usuario** que ya tiene otras bases (por ejemplo el de Talleres), basta con crear la base y dar permisos a ese usuario:

```sql
CREATE DATABASE condocdat_db OWNER tu_usuario_existente ENCODING 'UTF8';
```

Anota: **host**, **puerto**, **nombre de base** (`condocdat_db`), **usuario** y **contraseña** para el paso 3.

---

## Paso 2 — Exportar datos desde SQLite (sin cambiar nada aún)

Sigue usando SQLite (por defecto o con `DB_ENGINE` sin definir / SQLite). En el entorno del proyecto:

```bash
cd /ruta/al/proyecto/condocdat

# Opcional: activar venv si lo usas
# source .venv/bin/activate   # o env/bin/activate

# Exportar todos los datos a un único JSON (excluir sesiones si no te interesan)
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e sessions -o condocdat_fixture.json
```

- `--natural-foreign` y `--natural-primary` ayudan a que las FK se resuelvan bien al cargar en otra BD.
- Si quieres incluir también `sessions` y `contenttypes`, quita las `-e ...` (Django puede recrear contenttypes con `migrate`; si los incluyes, no suele haber problema).

Si la base SQLite es muy grande, puedes exportar por app:

```bash
python manage.py dumpdata documents --natural-foreign --natural-primary -o documents_fixture.json
python manage.py dumpdata auth --natural-foreign --natural-primary -o auth_fixture.json
```

Guarda **condocdat_fixture.json** (y los demás si los usas) en un lugar seguro; es tu respaldo antes de la migración.

---

## Paso 3 — Apuntar Django a PostgreSQL

El `settings.py` ya lee la base desde variables de entorno. Puedes hacer la migración de dos formas.

### Opción A — Variables de entorno (recomendado para Docker y producción)

Antes de ejecutar `migrate` y `loaddata`, configura:

```bash
export DB_ENGINE=django.db.backends.postgresql
export DB_NAME=condocdat_db
export DB_USER=condocdat_user
export DB_PASSWORD=tu_password_seguro
export DB_HOST=nombre_o_ip_del_servidor_postgres   # desde el contenedor: nombre del servicio si está en la misma red Docker
export DB_PORT=5432
```

En **Docker** (compose o Traefik), define las mismas variables en el servicio de Condocdat. Ejemplo en `docker-compose.yml`:

```yaml
environment:
  DB_ENGINE: django.db.backends.postgresql
  DB_NAME: condocdat_db
  DB_USER: condocdat_user
  DB_PASSWORD: ${CONDOCDAT_DB_PASSWORD}   # o el valor en claro si es solo desarrollo
  DB_HOST: postgres    # nombre del servicio PostgreSQL en la red
  DB_PORT: "5432"
```

Así la misma imagen sirve para desarrollo (SQLite) y producción (PostgreSQL) sin tocar código.

### Opción B — Settings local (mismo Postgres que Talleres, sin variables de entorno)

Para desarrollo en tu máquina usando la **misma conexión que Talleres** (mismo usuario, contraseña y servidor; base `condocdat_db`), usa el módulo de settings local:

```bash
export DJANGO_SETTINGS_MODULE=condocdat.settings_local
python manage.py migrate
python manage.py runserver
```

El archivo `condocdat/settings_local.py` (gitignored) tiene la conexión fija; la plantilla es `condocdat/settings_local.example.py`. No hace falta definir variables de entorno en local.

### Opción C — Editar `settings.py` (solo para pruebas puntuales)

Solo para pruebas en tu máquina puedes forzar PostgreSQL editando `condocdat/settings.py` y dejando algo como:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'condocdat_db',
        'USER': 'condocdat_user',
        'PASSWORD': 'tu_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

En producción es mejor usar siempre variables de entorno.

---

## Paso 4 — Crear tablas en PostgreSQL y cargar datos

Con las variables (o el settings) ya apuntando a PostgreSQL:

```bash
# 4.1 Crear todas las tablas
python manage.py migrate

# 4.2 Cargar el fixture exportado en el paso 2
python manage.py loaddata condocdat_fixture.json
```

Si usaste varios fixtures:

```bash
python manage.py loaddata auth_fixture.json documents_fixture.json
```

Si aparece algún error de dependencia (por ejemplo “ContentType no existe”), puedes:

- Cargar en este orden: `contenttypes`, `auth`, luego el resto; o  
- Usar el fixture único sin excluir contenttypes (sin `-e contenttypes`).

Los **archivos subidos** (media: PDFs, adjuntos) no van en la base de datos; viven en `media/`. Mientras esa carpeta sea la misma (mismo volumen en Docker o misma ruta en el servidor), no hace falta migrarlos. Solo se migran los registros de la BD.

---

## Paso 5 — Comprobar

1. Entrar al sitio y revisar:
   - Login, listado de documentos, carpetas, detalle de documento, Estatus Cartas, búsqueda.
2. En la shell de Django:
   ```bash
   python manage.py shell
   ```
   ```python
   from documents.models import Document, Folder
   print(Document.objects.count(), Folder.objects.count())
   ```
3. Si todo está bien, puedes borrar o renombrar el archivo SQLite (`db.sqlite3`) para evitar usarlo por error más adelante:
   ```bash
   mv db.sqlite3 db.sqlite3.backup
   ```

---

## Traspaso a producción (PostgreSQL en el servidor)

**Panorama:** En producción tienes **un solo servidor PostgreSQL** (contenedor `postgres_talleres` o el que use Talleres). Ese servidor puede tener **varias bases de datos**:

| Base de datos       | Proyecto   | Uso                                      |
|--------------------|------------|------------------------------------------|
| `netgogo_talleres` | Talleres   | Tablas de talleres (tu `settings.py` de myproject) |
| `condocdat_db`     | Condocdat  | Documentos, carpetas, transmittals, etc. |

Crear la base `condocdat_db` **no modifica** la base de Talleres. Es otra base en el mismo Postgres; el mismo usuario (`maxgonpe`) puede ser dueño de ambas. Talleres sigue conectado a `netgogo_talleres`; Condocdat se conecta a `condocdat_db` con `DB_HOST=postgres_talleres` (mismo host, otra base).

La opción recomendada es: **crear la base en el PostgreSQL de producción** (el mismo que usa Talleres) y **copiar los datos desde tu PostgreSQL local** (que ya tienes verificados) con `pg_dump` / `pg_restore`. Así producción queda igual que local y Condocdat en Docker usa esa base.

### 1. Crear la base `condocdat_db` en el PostgreSQL de producción

En el **servidor de producción**, según cómo tengas PostgreSQL:

**Si PostgreSQL corre en Docker (ej. contenedor `postgres_talleres`):**

```bash
# Conéctate por SSH al servidor, luego:
docker exec -it postgres_talleres psql -U postgres -c "CREATE DATABASE condocdat_db OWNER maxgonpe ENCODING 'UTF8';"
```

(Sustituye `postgres_talleres` por el nombre real del contenedor si es otro; el usuario `maxgonpe` es el mismo que Talleres — si en producción usas otro usuario, pon ese como `OWNER`.)

**Si PostgreSQL está instalado en el servidor (no Docker):**

```bash
ssh tu_servidor
sudo -u postgres psql -c "CREATE DATABASE condocdat_db OWNER maxgonpe ENCODING 'UTF8';"
```

### 2. Volcado desde tu PostgreSQL local (datos ya conformes)

En tu **máquina local**, con la base `condocdat_db` ya poblada y verificada:

```bash
cd ~/condocdat
pg_dump -h localhost -U maxgonpe -d condocdat_db -F c -f condocdat_dump.dump
```

(Te pedirá la contraseña de `maxgonpe`; o usa `PGPASSWORD=celsa1961` delante del comando si prefieres.)

### 3. Llevar el volcado al servidor y restaurar

**Opción A — Copiar el archivo al servidor y restaurar allí**

```bash
scp condocdat_dump.dump usuario@tu_servidor:/tmp/
```

En el servidor:

```bash
# Si Postgres está en Docker (contenedor postgres_talleres, puerto 5432 expuesto o red interna)
docker exec -i postgres_talleres pg_restore -U maxgonpe -d condocdat_db --no-owner --no-acl < /tmp/condocdat_dump.dump

# Si el dump está dentro del contenedor, primero cópialo al contenedor:
docker cp /tmp/condocdat_dump.dump postgres_talleres:/tmp/
docker exec -it postgres_talleres pg_restore -U maxgonpe -d condocdat_db --no-owner --no-acl /tmp/condocdat_dump.dump
```

**Opción B — Tubería por SSH (sin dejar el dump en el servidor)**

Desde tu **local**, si desde tu máquina puedes conectar por red al PostgreSQL del servidor (puerto 5432 abierto o túnel):

```bash
pg_dump -h localhost -U maxgonpe -d condocdat_db -F c | ssh usuario@tu_servidor "docker exec -i postgres_talleres pg_restore -U maxgonpe -d condocdat_db --no-owner --no-acl"
```

(En muchos casos el puerto 5432 de producción no está abierto; entonces usa la Opción A.)

Si `pg_restore` muestra avisos sobre “owner” o “privileges”, suelen ser inofensivos; lo importante es que no falle la restauración.

### 4. Configurar Condocdat en Docker para usar PostgreSQL

El `docker-compose` de producción debe pasar las variables de PostgreSQL y estar en la **misma red Docker** que el contenedor de PostgreSQL para poder usar el nombre del servicio como `DB_HOST` (ej. `postgres_talleres`).

En el repositorio está preparado `docker-compose.prod.yml` para que uses variables de entorno. Crea en el servidor un `.env` (o define las variables donde ejecutes `docker compose`) con algo como:

```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=condocdat_db
DB_USER=maxgonpe
DB_PASSWORD=celsa1961
DB_HOST=postgres_talleres
DB_PORT=5432
```

El servicio `condocdat` debe estar en la red donde está el PostgreSQL (ej. `traefik_default` si es la misma que usa el contenedor de Postgres, o la red interna del compose de Talleres si compartes ese compose). Si Condocdat y el Postgres están en composes distintos, une el servicio condocdat a la red del Postgres, por ejemplo:

```yaml
networks:
  traefik_default:
    external: true
  postgres_net:
    external: true   # nombre de la red del compose de Talleres/Postgres
```

y en el servicio `condocdat`:

```yaml
networks:
  - traefik_default
  - postgres_net
```

Así `DB_HOST=postgres_talleres` resolverá al contenedor de PostgreSQL.

### 5. Arrancar / reiniciar Condocdat en producción

```bash
cd /ruta/al/proyecto/condocdat
docker compose -f docker-compose.prod.yml up -d --build
```

Comprueba en https://condocdat.netgogo.cl que los documentos y carpetas coinciden con local. Los archivos en `media/` siguen en el volumen que ya montas; no hace falta migrarlos.

**Nota:** Si el contenedor Condocdat no puede resolver `postgres_talleres`, en el servidor ejecuta `docker network ls` y `docker network inspect <red_del_contenedor_postgres>` para ver el nombre de la red. Luego añade esa red como `external` en `docker-compose.prod.yml` y asígnala al servicio `condocdat` para que comparta red con el PostgreSQL.

---

## Docker y persistencia

- **Base de datos:** Los datos quedan en el servidor PostgreSQL (fuera del contenedor). No necesitas un volumen para la BD si siempre te conectas por red a ese PostgreSQL.
- **Media:** Para que los PDFs y adjuntos sean persistentes, monta un volumen en la ruta que use `MEDIA_ROOT` (por ejemplo `./media:/app/media`).
- **Traefik / subdominio:** No cambia; solo asegura que las variables de entorno del paso 3 estén definidas en el servicio que ejecuta Condocdat.

---

## Resumen de variables de entorno (producción)

| Variable     | Ejemplo                          | Descripción                          |
|-------------|-----------------------------------|--------------------------------------|
| `DB_ENGINE` | `django.db.backends.postgresql`   | Motor de BD                          |
| `DB_NAME`   | `condocdat_db`                   | Nombre de la base                    |
| `DB_USER`   | `condocdat_user`                 | Usuario PostgreSQL                   |
| `DB_PASSWORD` | (secreto)                      | Contraseña                           |
| `DB_HOST`   | `postgres` o IP/hostname         | Servidor (desde Docker: nombre red)  |
| `DB_PORT`   | `5432`                           | Puerto                               |

Con esto la migración queda segura, reversible (tienes el fixture y el SQLite de respaldo) y lista para usar búsqueda avanzada en PostgreSQL en el mismo código.

---

## Búsqueda mejorada con PostgreSQL

Tras la migración, el backend de búsqueda (`documents.search_backend`) usa automáticamente **full-text search** de PostgreSQL (configuración `spanish`):

- **Documentos:** SearchVector en código, título, descripción, revisión y contenido extraído; orden por relevancia (rank). Sigue buscando también por códigos de proyecto/empresa/proceso/tipo y por texto de adjuntos (icontains).
- **Carpetas:** SearchVector en código, título y descripción.
- **Archivos de carpeta:** SearchVector en nombre y texto extraído.

No hace falta cambiar nada en la interfaz; la misma pantalla «Buscar» aprovecha la mejora cuando `DB_ENGINE` es PostgreSQL.
