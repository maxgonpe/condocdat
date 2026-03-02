# Despliegue Condocdat en producción (condocdat.netgogo.cl)

## Configuraciones adicionales necesarias

### 1. Red de Traefik

En el servidor debe existir la red que usa Traefik. El compose usa `traefik_default`:

```bash
docker network ls | grep traefik

# Si usas otro nombre (ej. traefik-network), edita docker-compose.prod.yml:
# networks: traefik_default -> traefik-network
# Y en la sección networks: external: true con ese nombre.

# Si no existe traefik_default:
docker network create traefik_default
```

### 2. Variables de entorno (.env)

En la **raíz del proyecto** (donde está `docker-compose.prod.yml`) crea un archivo `.env`:

```bash
# Obligatorio en producción
SECRET_KEY=tu-clave-secreta-muy-larga-y-aleatoria

# Opcional (ya tienen valor por defecto en el compose)
# ALLOWED_HOSTS=condocdat.netgogo.cl
# TZ=America/Santiago
```

**Generar SECRET_KEY:**
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

No subas `.env` a git (ya está en `.gitignore`).

### 3. Directorios para volúmenes

Crea los directorios que monta el compose (el entrypoint también los crea dentro del contenedor, pero es buena práctica tenerlos en el host con permisos correctos):

```bash
mkdir -p data media staticfiles
chmod 755 data media staticfiles
```

### 4. DNS

El dominio **condocdat.netgogo.cl** debe apuntar (A o CNAME) a la IP del servidor donde corre Traefik. Sin esto, Traefik no enrutará y Let's Encrypt no podrá validar el certificado.

### 5. Levantar el servicio

```bash
cd /ruta/donde/subiste/condocdat

docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d
```

(O con `docker-compose` si usas la versión antigua: `docker-compose -f docker-compose.prod.yml up -d`.)

Las migraciones y `collectstatic` se ejecutan solas al arrancar el contenedor (script `docker-entrypoint.sh`).

### 6. Crear superusuario (primera vez)

```bash
docker compose -f docker-compose.prod.yml exec condocdat python manage.py createsuperuser
```

### 7. Comandos útiles

```bash
# Logs
docker compose -f docker-compose.prod.yml logs -f condocdat

# Reiniciar
docker compose -f docker-compose.prod.yml restart condocdat

# Parar
docker compose -f docker-compose.prod.yml down

# Ejecutar comando Django
docker compose -f docker-compose.prod.yml exec condocdat python manage.py <comando>
```

---

## Checklist rápido

- [ ] Proyecto subido al servidor (sin `env/`, sin `db.sqlite3` si no quieres llevarte la base local)
- [ ] Archivo `.env` con `SECRET_KEY` generada
- [ ] Red `traefik_default` existe (o ajustado el nombre en el compose)
- [ ] Directorios `data`, `media`, `staticfiles` creados
- [ ] DNS: condocdat.netgogo.cl → IP del servidor
- [ ] `docker compose -f docker-compose.prod.yml up -d`
- [ ] `createsuperuser` ejecutado
- [ ] Probar https://condocdat.netgogo.cl

---

## Si Traefik usa otra red

Si en el servidor Traefik está en una red con otro nombre (por ejemplo `traefik-network`), en `docker-compose.prod.yml` cambia:

```yaml
networks:
  traefik_default:
    external: true
```

por:

```yaml
networks:
  traefik-network:
    external: true
```

y en el servicio `condocdat` cambia `traefik_default` por `traefik-network` en la sección `networks`.
