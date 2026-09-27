# Plantilla de aplicación con subdominio

Esta plantilla define el patrón estándar para una aplicación Python nueva en el servidor. Incluye una demo mínima para validar el circuito completo:

- PostgreSQL propio por aplicación.
- Base de datos aislada en una red interna.
- Aplicación conectada a la red interna y a `traefik_default`.
- HTTPS automático mediante Traefik y Let's Encrypt.
- Un subdominio por aplicación.
- Endpoint `/health/database` para comprobar la conexión PostgreSQL.

## Uso manual

1. Copiar esta carpeta a una ubicación propia para la aplicación.
2. Crear `.env` a partir de `.env.example` y cambiar todos sus valores.
3. Cambiar el código de `app.py` por la aplicación real o usar la demo incluida.
4. Confirmar que la aplicación escuche en `0.0.0.0:8000`.
5. Validar la configuración:

```bash
docker compose config
```

6. Iniciar:

```bash
docker compose up -d --build
```

7. Verificar:

```bash
docker compose ps
docker compose logs --tail 100 app
curl -k -I https://mi-aplicacion.netgogo.cl/
curl -k https://mi-aplicacion.netgogo.cl/health/database
```

No publicar PostgreSQL en puertos del host. La red `traefik_default` solo debe usarse para el servicio HTTP.
