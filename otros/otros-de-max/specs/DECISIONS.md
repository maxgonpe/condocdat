# Registro de decisiones

## 2026-09-02

- Se inicia una reorganización manual del proyecto principal.
- El alcance inicial se limita a Netgogo; los proyectos secundarios quedan fuera.
- Los archivos descartados se moverán temporalmente a `/home/maxgonpe/max/old` en lugar de eliminarse.
- No se usará Git durante esta etapa inicial.
- `myproject_netgogo` es el candidato inicial, pendiente de confirmación operativa.
- La red `traefik_default` existe, pero no hay contenedores actualmente conectados a ella.
- No se levantaron ni reiniciaron servicios durante el inventario.
- El Compose candidato tiene una configuración denominada `new` y no debe considerarse producción confirmada todavía.

## 2026-09-03

- El objetivo prioritario es operar `netgogo.cl` y al menos un subdominio antes de ampliar la plataforma.
- Las aplicaciones nuevas serán contenedores independientes, con PostgreSQL y variables propias, publicados por Traefik.
- No se reorganizarán ni eliminarán ahora los sistemas existentes del servidor.
- Primero se validará manualmente el patrón de incorporación de una aplicación; después se evaluará un panel protegido para automatizar altas y operaciones básicas.
- Se validó en producción `netgogo.cl` con HTTPS y estáticos, y `condocdat.netgogo.cl` como primer subdominio operativo. Traefik publica ambos servicios usando explícitamente `traefik_default`.
- Se validó `demo.netgogo.cl` como primera aplicación creada desde la plantilla; su endpoint `/health/database` confirmó PostgreSQL independiente.
- Se estableció `traefik.docker.network=traefik_default` como requisito obligatorio para servicios conectados a más de una red Docker.
- Se estableció `alta-subdominio.sh` como procedimiento inicial para nuevas aplicaciones. El panel queda para una fase posterior, después de validar otra aplicación real.
- Se validó el primer clon centralizado `taller1`: responde por HTTPS y conecta a `taller1_db` dentro de `postgres_talleres`.
- Se decidió cerrar la jornada sin habilitar producción desde el panel: la operación `stop` de Nomina aún debe validarse en local con `dry_run=false` confirmado por `/health`.

## 2026-09-04

- La estructura heredada se reemplazará gradualmente por proyectos independientes bajo `/home/max/projects/` en producción y `/home/maxgonpe/max/projects/` en desarrollo.
- El orden de migración será: Nomina primero, luego Condocdat y posteriormente los demás proyectos Django.
- Nomina será el primer proyecto real publicado y operado completamente mediante el panel.
- El Condocdat antiguo se detendrá antes de publicar su nueva copia; sus datos se conservarán durante la validación.
- La limpieza definitiva de ambientes virtuales, contenedores y carpetas heredadas queda condicionada a la validación exitosa de cada aplicación.

## 2026-09-06

- Nomina fue desplegada exitosamente en producción como `nomina.netgogo.cl` mediante el panel.
- Se validó el patrón completo: proyecto independiente, Docker, PostgreSQL, migraciones, superusuario, login, Django Admin, estáticos, media, HTTPS y operaciones desde el panel.
- Se considera confirmado que el mismo procedimiento puede repetirse con otros proyectos Django, sujeto a auditar sus particularidades antes de migrarlos.
- La siguiente aplicación será Condocdat: primero se detendrá su Docker actual y se conservarán sus datos/estructura como respaldo; luego se preparará una copia limpia bajo `/home/max/projects/condocdat` y se desplegará mediante el panel.
