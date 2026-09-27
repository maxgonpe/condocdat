# Checklist de avance

## Estado

- [x] Fase 0: inventario operativo completado
- [x] Fase 1: estructura mínima definida
- [x] Fase 2: Docker y PostgreSQL funcionando
- [x] Fase 3: Traefik y HTTPS funcionando
- [ ] Fase 4: flujos principales funcionando
- [x] Fase 5: plantilla para proyectos futuros preparada
- [x] Sitio principal `netgogo.cl` operativo
- [x] Al menos un subdominio operativo
- [x] Alta manual documentada para una nueva aplicación
- [x] Diseño del panel de altas definido
- [x] Simulación local de alta validada

## Evidencias requeridas

- [x] Carpeta activa identificada
- [x] Compose activo identificado
- [x] Contenedores activos identificados
- [x] Red externa de Traefik confirmada
- [x] Base PostgreSQL principal confirmada
- [x] Variables de entorno documentadas sin exponer secretos
- [x] `docker compose config` válido
- [x] PostgreSQL responde al healthcheck
- [x] Django ejecuta `migrate` correctamente
- [x] Gunicorn responde en el puerto interno
- [x] Traefik publica `netgogo.cl`
- [x] HTTPS válido
- [x] Archivos estáticos y media responden
- [ ] Tienda carga correctamente
- [ ] Pago y webhook verificados
- [ ] Reinicio de Docker conserva datos
- [x] Una aplicación de prueba usa PostgreSQL independiente
- [x] Una aplicación de prueba se publica mediante Traefik

## Registro de decisiones

Registrar cada decisión relevante en `DECISIONS.md`, incluyendo fecha, archivo afectado y motivo. No registrar contraseñas, tokens ni claves privadas.

## Cierre de jornada

- [x] Sitio principal validado en producción.
- [x] Primer subdominio validado en producción.
- [x] Aplicación demo creada con PostgreSQL y Traefik.
- [x] Procedimiento general de alta documentado.
- [x] Aplicación real adicional validada con el procedimiento general.
- [x] Proyecto Nomina gemelo validado localmente.
- [x] Primer clon validado contra PostgreSQL central.
- [x] Panel protegido de administración construido.
- [x] Rollback real validado con clon descartable.
- [x] Operación real desde la interfaz detiene Nomina local.
- [x] Operación real desde la interfaz inicia Nomina local.
- [x] Operaciones reales del panel validadas sobre Nomina local.
- [x] Prueba manual completa desde el navegador.
- [x] Nomina desplegada y operativa en producción mediante el panel.
- [x] Login, superusuario, migraciones y Django Admin de Nomina validados en producción.
- [x] Estáticos y media de Nomina publicados correctamente detrás de Traefik.
