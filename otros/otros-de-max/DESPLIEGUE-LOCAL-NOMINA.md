# Despliegue local de Nomina

El panel local puede probar Nomina usando el adaptador local, sin PostgreSQL productivo:

```bash
DEPLOY_SCRIPT=/home/maxgonpe/max/otros/desplegar-clon-local.sh \
PANEL_DEPLOY_ENABLED=true PANEL_DRY_RUN=false \
PANEL_TOKEN='token-local-seguro' ./run-local.sh
```

La aplicación registrada debe tener como directorio:

```text
/home/maxgonpe/max/projects/nomina
```

La aplicación queda en `http://127.0.0.1:8005/`. Este flujo usa `docker-compose.local.yml`, PostgreSQL `nomina_local_docker` y el volumen `nomina_local_pgdata`.
