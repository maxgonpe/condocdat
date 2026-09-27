# Alta de clones con PostgreSQL central

El script crea una base y un usuario PostgreSQL independientes dentro de `postgres_talleres`, y luego despliega una aplicación con su propio subdominio.

```bash
chmod +x /home/max/otros/alta-clon-postgres-central.sh
PG_ADMIN_PASSWORD='CLAVE_DEL_USUARIO_ADMIN' \
/home/max/otros/alta-clon-postgres-central.sh taller1 taller1.netgogo.cl /home/max/taller1
```

Antes de ejecutar, crear el registro DNS `taller1.netgogo.cl` apuntando al servidor.

El script no elimina bases, roles, contenedores ni volúmenes. Si el nombre ya existe, se detiene antes de cambiar nada. La contraseña del clon se genera automáticamente y queda solo en `.env` con permisos `600`.

Si fue interrumpido después de crear la base, reanudar explícitamente con:

```bash
RESUME_EXISTING=1 PG_ADMIN_PASSWORD='CLAVE_DEL_USUARIO_ADMIN' \
/home/max/otros/alta-clon-postgres-central.sh taller1 taller1.netgogo.cl /home/max/taller1
```

El modo de reanudación exige que existan tanto el usuario como la base y establece una nueva contraseña para registrarla en el `.env`.

La operación `retire` detiene y retira únicamente el contenedor de la aplicación. No elimina la base PostgreSQL, el volumen de media ni otros datos; la publicación puede restaurarse ejecutando nuevamente `start` desde la carpeta del clon.

Para usar una aplicación real, sustituir los archivos de la plantilla por el código de la aplicación conservando las variables `DB_*`, el puerto interno `8000` y la red `traefik_default`.
