# Conectar Condocdat a la base histórica

La base correcta es `condocdat_db`, ubicada en el contenedor PostgreSQL `postgres_talleres`.

Variables requeridas:

```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=condocdat_db
DB_USER=maxgonpe
DB_PASSWORD=celsa1961
DB_HOST=postgres_talleres
DB_PORT=5432
```

El contenedor PostgreSQL debe estar iniciado y `condocdat` debe compartir una red con él, actualmente `myproject_netgogo_default`.

Para recrear solo la aplicación:

```bash
bash /home/max/otros/recrear-condocdat-con-base-correcta.sh
```

Si el proyecto está en otra ruta:

```bash
CONDOCDAT_DIR=/ruta/real/condocdat bash /home/max/otros/recrear-condocdat-con-base-correcta.sh
```

El script no elimina ni recrea PostgreSQL ni sus volúmenes. Solo recrea el contenedor `condocdat`, aplica el Compose de producción y verifica los conteos históricos.
