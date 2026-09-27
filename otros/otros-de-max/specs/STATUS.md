# Estado actual

## Fase activa

Fase 7: migración de aplicaciones reales. Nomina ya fue validada en producción mediante el panel; el siguiente objetivo es migrar Condocdat al mismo modelo independiente.

## Observaciones iniciales

- La raíz contiene varias copias o etapas del proyecto principal.
- Existen configuraciones Docker y Traefik en más de una ubicación.
- Hay proyectos secundarios dentro y fuera de la estructura principal.
- La limpieza local movió los archivos auxiliares de la raíz a `/home/max/old/`; no se eliminó información.
- Actualmente `docker ps` no muestra contenedores en ejecución.
- La red externa `traefik_default` existe.
- También existen redes locales `myproject_netgogo_default` y `myproject_netgogo_local_network`.
- `myproject_netgogo/docker-compose.yml` define `db`, `web` y `static`.
- El Compose de `myproject_netgogo` usa nombres `netgogo_new_*` y valores por defecto asociados a una configuración `new`.
- El Compose conecta `web` y `static` a `traefik_default`; PostgreSQL queda en la red interna por defecto.
- El proyecto contiene un `.env`; sus secretos no se copiarán ni se mostrarán en documentación.
- Hay credenciales sensibles escritas como valores fallback en el Compose. Deben reemplazarse por variables externas antes de un despliegue real.
- PostgreSQL local está escuchando en `127.0.0.1:5432`.
- La autenticación local con el usuario `maxgonpe` y la contraseña indicada funciona.
- Las bases locales detectadas son `extintoresreal_local`, `netgogo_talleres`, `netgogo_tienda` y `postgres`.
- `virtualmarket`, que figura en el `.env` actual, no existe en el PostgreSQL local.
- `netgogo_tienda` y `netgogo_talleres` no contienen tablas Django actualmente.
- Existen contenedores PostgreSQL detenidos o creados (`postgres_local`, `tienda_db_local`, `postgres_talleres` y otros), con volúmenes distintos.
- El `.env` actual apunta a `POSTGRES_HOST=db`, válido dentro de Docker, pero no para ejecutar Django directamente en el host.
- El código confirma que `shop` administra catálogo, precios, imágenes, videos y `Product.stock`.
- `cart` administra el carrito y la creación de preferencias de pago; `orders` administra órdenes, estados, referencias y `payment_id`.
- El webhook de Mercado Pago descuenta `Product.stock` cuando el pago es confirmado.
- `virtualmarket` aparece como nombre heredado/configurado de la base principal de la tienda, pero no se puede confirmar como base de datos local porque no existe en el servidor PostgreSQL local.
- Se creó la base local vacía `virtualmarket`.
- Se instaló el `requirements.txt` en el entorno local `myprojectenv`.
- `manage.py check` terminó correctamente.
- Las migraciones Django se aplicaron correctamente sobre `virtualmarket`.
- `collectstatic` terminó correctamente; reportó duplicados esperables de archivos estáticos.
- Se ajustó el logging local para no depender de la ruta de contenedor `/app/django_webhook.log`.
- Antes de esta prueba no se habían levantado los servicios Docker ni validado Traefik.
- Se confirmó que existe `docker-compose` clásico (`/usr/bin/docker-compose`).
- Se corrigió el host PostgreSQL dentro del contenedor web para usar `db`, conservando `127.0.0.1` para ejecución local en el host.
- `docker-compose config` es válido.
- La imagen `myproject_netgogo_web` se construyó correctamente.
- Se levantaron `netgogo_new_db`, `netgogo_new_web` y `netgogo_new_static`.
- PostgreSQL Docker quedó saludable y las migraciones se aplicaron dentro del contenedor.
- La aplicación Docker responde `200` en `http://127.0.0.1:8000/`.
- Traefik todavía no está ejecutándose, por lo que el dominio HTTPS aún no fue validado.
- Se habilitó `DJANGO_SECURE_COOKIES` para poder usar cookies seguras en producción y desactivarlas en HTTP local.
- Se añadieron orígenes CSRF HTTP para `localhost` y `127.0.0.1`.
- El Compose se reconstruyó y los servicios Docker continúan activos.
- La prueba inicial contra el puerto Docker tuvo que esperar a que Gunicorn terminara el arranque; luego `/` respondió `200`.
- `makemigrations --check --dry-run` detecta cambios de campos `id` en aplicaciones existentes; no se generaron migraciones nuevas.
- Se creó una configuración local de Traefik en `traefik/docker-compose.local.yml` con HTTP en `localhost:8081` y dashboard en `localhost:8082`.
- Se creó un override local de Netgogo con routers HTTP para `localhost`.
- La aplicación responde `200` mediante Traefik en `http://localhost:8081/`.
- Los archivos estáticos responden `200` mediante Traefik en `http://localhost:8081/static/...`.
- El override local conserva labels históricos de producción, que Traefik local ignora por no tener esos entrypoints; deben limpiarse cuando se consolide la separación local/producción.
- La prueba confirmó que el Traefik local solo escuchaba en `8081/8082`; no ocupaba `80/443`.
- El Traefik productivo no estaba ejecutándose durante la comprobación.
- Se detuvo y eliminó únicamente el contenedor temporal de Traefik local; la red externa y los servicios Netgogo no fueron eliminados.
- Se creó la guía manual `otros/actualizar-traefik-produccion.md` para actualizar Traefik sin afectar los demás servicios.
- Se creó el script `otros/parche-traefik-docker-api.sh` para aplicar el parche de Traefik de forma rápida y limitada al servicio `traefik`.
- Se creó `otros/arrancar-postgres-talleres.sh` para recuperar PostgreSQL Talleres sin borrar su volumen y verificar `condocdat_db`.
- Se creó `otros/consultar-bases-condocdat.sh` para listar bases y contar registros de carpetas/documentos sin modificar datos.
- Consulta definitiva en producción: `condocdat_db` contiene 847 carpetas, 848 documentos y 12 usuarios.
- La base correcta está en el volumen `netgogo_temp_postgres_data`, dentro del contenedor `postgres_talleres`.
- `postgres_talleres` está conectado a `myproject_netgogo_default` y `traefik_default`.
- La conexión válida de Condocdat es `DB_HOST=postgres_talleres`, `DB_NAME=condocdat_db`, `DB_USER=maxgonpe`, puerto `5432`.
- El resultado anterior de 112 registros correspondía a una consulta/configuración distinta o a un estado anterior de la base; no representa la base histórica correcta.
- Se creó `otros/recrear-condocdat-con-base-correcta.sh` para recrear solo la aplicación con `condocdat_db` y verificar sus datos históricos.
- La aplicación local respondió `200` en `/` y `/admin/login/` usando Django sobre `127.0.0.1:8001`.
- El endpoint de estáticos devolvió `404` porque `DEBUG` está fijado en `False` en `settings.py`; `DJANGO_DEBUG` no se procesa actualmente.
- Docker está instalado, pero el plugin/comando `docker compose` no está disponible en este entorno.
- Validación de producción completada: `netgogo.cl` responde `HTTP/2 200` mediante Traefik y HTTPS.
- Los estáticos de Netgogo responden `HTTP/2 200` desde `netgogo.cl/static/...` mediante nginx.
- `condocdat.netgogo.cl` responde correctamente como primer subdominio operativo.
- La infraestructura base para comenzar a incorporar nuevas aplicaciones quedó validada.
- Se creó `otros/plantilla-subdominio` con Compose, PostgreSQL aislado y publicación HTTPS por Traefik.
- Demo desplegada y validada: `demo.netgogo.cl` responde por HTTPS y `/health/database` confirma PostgreSQL operativo.
- La demo creó su PostgreSQL independiente (`demo-netgogo-db-1`) y volumen `demo-netgogo_db_data`, sin afectar los servicios existentes.
- Se corrigió la plantilla para inyectar `APP_NAME` y `DOMAIN` dentro del contenedor, evitando respuestas genéricas de identidad.
- Se creó `otros/alta-subdominio.sh` y `otros/ALTA-APLICACION.md` para convertir la plantilla validada en un procedimiento general de alta.
- Se creó `otros/plantilla-clon` para el modelo definitivo: aplicación independiente conectada a una base lógica propia del PostgreSQL central.
- Primer alta de `taller1` quedó parcialmente ejecutada: el usuario y la base fueron creados, pero el script se detuvo al encontrar que producción no tiene `docker-compose`. El script ahora detecta `docker compose` o `docker-compose` y permite reanudar con `RESUME_EXISTING=1`.
- Primer clon centralizado validado: `taller1.netgogo.cl` responde HTTPS, usa el router individual `taller1` y `/health/database` confirma `taller1_db` en `postgres_talleres`.
- Se creó `otros/alta-clon-postgres-central.sh` y su guía para aprovisionar automáticamente usuario/base PostgreSQL, `.env`, contenedor y subdominio Traefik sin acciones destructivas.
- Se inició `subdomain-panel`, un panel local de registro y vista previa; todavía no ejecuta comandos ni accede a producción.
- El panel incorporó un endpoint de ejecución controlada, deshabilitado por defecto, protegido por token y limitado al script autorizado de alta de clones.
- El panel ahora usa `PANEL_DRY_RUN=true` por defecto: permite probar el flujo local sin buscar `postgres_talleres`, ejecutar Docker ni modificar bases.
- Se localizó el proyecto real `/home/maxgonpe/nomina` y se creó el gemelo de trabajo en `/home/maxgonpe/max/projects/nomina`, sin modificar el original.
- El gemelo de Nomina quedó preparado para SQLite en desarrollo directo (`run-local.sh`) y PostgreSQL en Docker mediante `DB_*`.
- Se añadieron `Dockerfile`, Compose compatible con el PostgreSQL central, Gunicorn, psycopg y `.env.production.example`.
- El gemelo supera `manage.py check` y `docker-compose config`.
- `nomina` gemela inició en local sobre SQLite en `127.0.0.1:8003`.
- La suite del gemelo pasó: 311 tests OK en 236 segundos.
- Se creó `nomina_local_db` en el PostgreSQL físico local y se aplicaron todas sus migraciones.
- La suite de Nomina contra PostgreSQL pasó: 311 tests OK en 251 segundos.
- Se añadió `projects/nomina/run-postgres-local.sh` para ejecutar Nomina en `127.0.0.1:8004` usando `nomina_local_db`.
- Se añadió `projects/nomina/docker-compose.local.yml` para probar Nomina con PostgreSQL Docker aislado.
- Se creó `otros/desplegar-clon-local.sh` para que el panel pueda desplegar Nomina localmente usando su Compose de prueba, sin contactar producción.
- Nomina Docker local levantó correctamente con PostgreSQL propio, migraciones aplicadas y Gunicorn en `127.0.0.1:8005`.
- `/cuentas/login/` y `/health/` responden HTTP 200; las rutas protegidas redirigen al login.
- El adaptador local fue corregido para usar exclusivamente `docker-compose.local.yml`; Nomina fue reconstruida y quedó operativa con `nomina_app` y `nomina_db_1`.
- El panel local desplegó Nomina mediante `desplegar-clon-local.sh`: operación `deployed`, contenedor `nomina_app` en ejecución y estado real confirmado por la API.
- Se añadió `operar-clon-local.sh`; el panel local ahora apunta por defecto a los adaptadores locales para `start`, `stop`, `restart`, `update` y `retire`, sin riesgo de invocar el Compose productivo.
- `operar-clon.sh update` conserva la imagen anterior como `nombre:previous` y `rollback` puede restaurarla; queda pendiente validarlo con un clon de prueba antes de producción.
- Rollback real validado con `subdomain-panel/test-clone`: `update` y `rollback` recrearon el contenedor correctamente sin tocar volúmenes.
- Se añadió `subdomain-panel/test-clone` como contenedor descartable para validar operaciones reales del panel sin usar bases ni servicios de negocio.
- Simulación local del despliegue validada para `taller2`: el panel generó el comando esperado y respondió `status=simulated` sin modificar Docker ni PostgreSQL.
- Se añadió `subdomain-panel/run-local.sh` para iniciar el panel siempre en `127.0.0.1:8090`, autenticado y en simulación segura.
- `operar-clon.sh retire` ahora detiene y retira el contenedor de aplicación conservando explícitamente sus volúmenes y datos.
- Cierre de jornada: sitio principal, primer subdominio y subdominio demo validados en producción.

## Estado comprobado al cierre

- `netgogo.cl` responde por HTTPS mediante Traefik con HTTP 200.
- Los archivos estáticos de `netgogo.cl` responden correctamente mediante nginx.
- `condocdat.netgogo.cl` funciona con la base histórica `condocdat_db`.
- `condocdat_db` contiene 847 carpetas, 848 documentos y 12 usuarios.
- `demo.netgogo.cl` funciona por HTTPS y confirma conexión con su PostgreSQL propio.
- La demo usa el volumen `demo-netgogo_db_data` y no afecta las bases existentes.
- La selección explícita de `traefik_default` evita el problema de Traefik cuando un contenedor pertenece a varias redes.
- El alta general está disponible mediante `alta-subdominio.sh`.
- Reanudación: los contenedores locales `netgogo_new_web`, `netgogo_new_db` y `netgogo_new_static` están activos.
- `docker-compose -f myproject_netgogo/docker-compose.yml config` continúa válido.
- Pruebas locales de Netgogo: `/`, `/admin/login/`, `/shop/`, `/cart/` y `/orders/` responden HTTP 200.
- Gunicorn escucha en `0.0.0.0:8000` y la aplicación mantiene conexión con PostgreSQL `virtualmarket`.
- Sigue pendiente una revisión controlada de cambios de modelos sin migración en `django_summernote`, `orders`, `shop` y `user`; no se generarán migraciones automáticamente.
- `manage.py showmigrations --plan` confirma que todas las migraciones existentes están aplicadas.
- `manage.py check --deploy` no encontró errores bloqueantes, pero reportó advertencias de HSTS, redirección HTTPS y cookies seguras que deben revisarse antes de endurecer producción.
- PostgreSQL local responde `accepting connections`; `/` y `/admin/login/` siguen respondiendo HTTP 200.
- Se normalizó el desarrollo directo con `myproject_netgogo/run-local.sh`: usa el PostgreSQL físico local en `127.0.0.1:5432` y sirve en `127.0.0.1:8001`, separado de Docker.

## Pendiente

- Probar el alta general con una aplicación real distinta de la demo.
- Completar pruebas funcionales de Netgogo: login, catálogo, carrito, órdenes, Mercado Pago y webhook.
- Verificar persistencia después de reiniciar los servicios, sin eliminar volúmenes.
- Revisar y corregir migraciones pendientes detectadas en Netgogo antes de modificar modelos.
- Revisar secretos escritos como valores fallback en Compose y moverlos a `.env` seguro o un mecanismo de secretos.
- Definir backup y recuperación antes de una operación continua, respetando la decisión de no crear backups durante el inventario inicial.
- Construir un panel protegido que invoque únicamente altas y operaciones permitidas.
- Añadir registro de aplicaciones, estado, logs y validaciones al panel.

## Punto de reanudación

Retomar desde la validación de una aplicación real usando `otros/alta-subdominio.sh`. No tocar `netgogo_new_db`, `postgres_talleres`, `condocdat_db` ni los volúmenes existentes sin una decisión explícita.

## Cierre de jornada - 2026-09-04

- El proyecto real `nomina` fue localizado en `/home/maxgonpe/nomina` y su gemelo quedó en `/home/maxgonpe/max/projects/nomina`.
- El gemelo conserva SQLite para desarrollo directo y tiene configuración PostgreSQL mediante variables `DB_*`.
- Se creó `nomina_local_db` en el PostgreSQL físico local y todas las migraciones se aplicaron correctamente.
- La suite de Nomina pasó 311 tests contra SQLite y 311 tests contra PostgreSQL local.
- Se construyó la imagen Docker `nomina-local:test` correctamente.
- `nomina` funciona en Docker local con PostgreSQL aislado en `127.0.0.1:8005`.
- El panel local funciona en `127.0.0.1:8090`, con login, registro, simulación, estado, logs, historial, operaciones y versiones.
- El panel registró `nomina` con la base lógica corregida `nomina_db`.
- Se creó un adaptador local para desplegar Nomina sin tocar producción.
- Se probaron localmente `restart`, `stop`, `start`, `update` y `retire` con un clon descartable.
- La prueba de despliegue real desde el panel dejó Nomina en estado `deployed` y el contenedor `nomina_app` operativo.
- La acción `stop` desde la interfaz de Nomina todavía no quedó validada: el historial más reciente muestra `SIMULACIÓN LOCAL`, por lo que el contenedor siguió activo.
- Limpieza local inicial realizada: `myproject_motos` y `backups` fueron movidos intactos a `/home/max/old/`; no se eliminó información.
- Se conservaron fuera de `old` los proyectos y recursos actualmente necesarios: `myproject_netgogo`, `myproject`, `netgogo_temp`, `projects`, `subdomain-panel`, `traefik`, `clientes`, `otros` y `nginx-static.conf`.
- Validación final completada en local con el panel en `dry_run=false`: `stop` detuvo realmente `nomina_app` y `nomina_db_1` (puerto 8005 dejó de responder); `start` los levantó nuevamente y `/health/` volvió a HTTP 200.
- Funcionalidad completa validada desde el panel local en modo real sobre Nomina: `restart`, `stop`, `start`, `update`, `rollback` y `retire`; después de retirar se restauró con `start`, el contenedor quedó activo y los logs respondieron.
- Prueba manual desde el navegador completada: todas las acciones del panel respondieron correctamente sobre Nomina Docker local y se comprobó el efecto real en el servicio.
- El endpoint `/health` ahora informa explícitamente `mode` y `dry_run` para evitar confundir simulación con ejecución real.
- El rollback real quedó implementado en el script general y validado con el clon descartable; el rollback local específico de Nomina sigue pendiente.
- Nomina quedó preparada para producción como proyecto subido completo: el Compose ya no copia una plantilla, genera/monta estáticos mediante un contenedor Nginx, conserva `media/` en la carpeta del proyecto y ejecuta `migrate`/`collectstatic` al arrancar.
- Se creó `otros/desplegar-proyecto-django.sh` para que el panel configure la base/usuario, genere `.env` productivo en el directorio ya subido y levante ese proyecto sin sobrescribir su código.
- Se ajustó el panel para autorizar `desplegar-proyecto-django.sh` como script productivo y se validaron sintaxis, Python y `docker-compose config` de Nomina.
- El despliegue productivo Django ahora crea o actualiza automáticamente el superusuario inicial `maxgonpe` con la contraseña operativa definida por el usuario.
- Se corrigieron `STATIC_URL`/`MEDIA_URL` a rutas absolutas y se dio prioridad Traefik al router Nginx de `/static/` y `/media/`, para que Django Admin cargue sus estilos y scripts.
- Éxito productivo confirmado: `nomina.netgogo.cl` fue desplegado y administrado desde el panel de producción.
- Nomina quedó operativa con Docker, PostgreSQL, migraciones, superusuario, login, Django Admin, estáticos, media y HTTPS.
- El patrón de despliegue quedó validado para repetirlo con otros proyectos Django.
- Próxima migración: detener el Docker antiguo de Condocdat, conservar su estructura/datos como respaldo, preparar `/home/max/projects/condocdat` y desplegarlo mediante el panel.

## Primera tarea al retomar

Auditar la estructura antigua de Condocdat y documentar exactamente su contenedor, Compose, volumen/base PostgreSQL y ubicación del código antes de detenerlo. No borrar datos ni volúmenes; primero preparar la nueva copia bajo `/home/max/projects/condocdat`.

## Próximo paso

Migrar Condocdat: detener el contenedor antiguo de forma controlada, conservar sus datos, subir solo el proyecto necesario a `/home/max/projects/condocdat`, adaptar su Compose/variables al modelo centralizado y desplegarlo mediante el panel.
