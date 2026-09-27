# Actualizar Traefik en Producción

## Objetivo

Resolver el error de incompatibilidad entre Traefik y la API de Docker sin tocar los contenedores de Netgogo, PostgreSQL ni los demás proyectos.

## 1. Entrar al servidor

Ejecutar estos comandos directamente en el servidor de producción:

```bash
cd /home/max/traefik

docker version
docker info
env | grep DOCKER_API || true
docker ps --filter name=traefik
docker inspect traefik-traefik-1 --format '{{.Config.Image}}'
```

Si existe `DOCKER_API_VERSION=1.24`, eliminarla de la configuración del shell o del servicio que inicia Traefik antes de continuar.

## 2. Cambiar la versión de Traefik

Editar:

```text
/home/max/traefik/docker-compose.yml
```

Cambiar:

```yaml
image: traefik:v3.1
```

por una versión actual compatible, por ejemplo:

```yaml
image: traefik:v3.6
```

No modificar los puertos, volúmenes, red ni los parámetros ACME durante esta operación.

## 3. Descargar y recrear solo Traefik

```bash
cd /home/max/traefik

docker-compose pull traefik
docker-compose stop traefik
docker-compose rm -f traefik
docker-compose up -d traefik
```

Estos comandos afectan solo al contenedor llamado `traefik` de este Compose. No ejecutar `docker-compose down` desde otro directorio.

## 4. Verificar Traefik

```bash
docker ps --filter name=traefik
docker logs --tail 100 traefik-traefik-1
curl http://127.0.0.1:8080/api/http/routers
```

En los logs no debería repetirse:

```text
client version 1.24 is too old
```

La API debería devolver routers HTTP en formato JSON.

## 5. Verificar Netgogo

```bash
docker ps --filter name=netgogo_new
curl -I http://127.0.0.1:8000/
curl -I https://netgogo.cl
```

El primer comando debe devolver una respuesta HTTP de Django/Gunicorn y el segundo debe devolver una respuesta válida del sitio publicado.

## 6. Si Traefik sigue fallando

No detener otros contenedores. Recopilar:

```bash
docker version
docker logs --tail 200 traefik-traefik-1
docker inspect traefik-traefik-1 --format '{{json .Mounts}}'
docker inspect traefik-traefik-1 --format '{{json .NetworkSettings.Networks}}'
```

## Nota

El endpoint correcto para consultar routers HTTP es:

```text
/api/http/routers
```

No usar `/api/routers`, porque devuelve `404` en esta versión de Traefik.
