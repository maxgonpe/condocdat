# Plantilla de clon

Esta plantilla representa el modelo definitivo: cada clon tiene su propio contenedor, base lógica, usuario PostgreSQL, volumen de archivos y subdominio, pero utiliza el PostgreSQL central del servidor.

```text
taller1.netgogo.cl -> taller1_app -> PostgreSQL/taller1_db
taller2.netgogo.cl -> taller2_app -> PostgreSQL/taller2_db
```

El contenedor PostgreSQL central debe estar conectado a `POSTGRES_NETWORK` y la aplicación también. Solo la aplicación se conecta a `traefik_default`; PostgreSQL nunca se publica por Traefik ni por puertos del host.

## Aplicación real

Reemplazar `app.py`, `requirements.txt` y el `Dockerfile` por el proyecto real, conservando las variables `DB_*` y escuchando en `0.0.0.0:8000`.

## Verificación

```bash
docker-compose config
docker-compose up -d --build
docker-compose ps
curl -k https://taller1.netgogo.cl/
curl -k https://taller1.netgogo.cl/health/database
```
