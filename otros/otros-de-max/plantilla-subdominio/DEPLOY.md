# Demo `demo.netgogo.cl`

Antes de ejecutar el alta, crear en el proveedor DNS:

```text
Tipo: A
Nombre: demo
Valor: IP_PUBLICA_DEL_SERVIDOR
```

Copiar `plantilla-subdominio` y `crear-demo-subdominio.sh` al servidor. Ejecutar:

```bash
chmod +x /home/max/otros/crear-demo-subdominio.sh
DOMAIN=demo.netgogo.cl /home/max/otros/crear-demo-subdominio.sh
```

El script no toca `netgogo_new_*`, `condocdat`, `postgres_talleres` ni sus volúmenes. Crea una carpeta y un volumen PostgreSQL nuevos para la demo.
