# Alta de una nueva aplicación

Crear primero un registro DNS tipo `A`, por ejemplo `inventario.netgogo.cl`, apuntando a la IP pública del servidor.

Después ejecutar en producción:

```bash
chmod +x /home/max/otros/alta-subdominio.sh
/home/max/otros/alta-subdominio.sh inventario inventario.netgogo.cl /home/max/inventario
```

El comando crea PostgreSQL, volumen, red interna, router HTTPS y credenciales independientes. La aplicación también se conecta a `traefik_default`; PostgreSQL no se publica al exterior.

Verificar:

```bash
docker compose -f /home/max/inventario/docker-compose.yml ps
curl -k https://inventario.netgogo.cl/
curl -k https://inventario.netgogo.cl/health/database
```

El futuro panel debe invocar este flujo con permisos restringidos y nunca aceptar comandos Docker arbitrarios ni borrar volúmenes desde la interfaz.
