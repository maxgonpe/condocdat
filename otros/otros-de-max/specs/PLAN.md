# Plan de trabajo: Netgogo principal

## Objetivo

Simplificar la estructura heredada de producción y administrar cada proyecto Django como una aplicación independiente. El primer objetivo operativo es publicar `nomina.netgogo.cl` mediante el panel; después se detendrá el `condocdat` antiguo y se migrará Condocdat al mismo modelo desde `/home/max/projects/condocdat`.

En desarrollo, los proyectos vivirán bajo `/home/maxgonpe/max/projects/`. En producción, cada proyecto tendrá su propia carpeta bajo `/home/max/projects/`, su código, Dockerfile, Compose y variables, mientras PostgreSQL central y Traefik serán infraestructura compartida.

La estructura antigua, sus ambientes virtuales y contenedores solo se eliminarán después de validar cada migración.

## Alcance inicial

- Identificar la copia real del proyecto principal.
- Mantener una sola estructura activa para `myproject_netgogo`.
- Validar Docker Compose, Django, PostgreSQL, variables de entorno y Traefik.
- Mantener PostgreSQL como servicio persistente del proyecto principal.
- Usar una base de datos propia para Netgogo.
- Conectar la aplicación web a la red externa `traefik_default`.
- Mantener los proyectos secundarios fuera del despliegue inicial.
- Validar un patrón repetible para sumar nuevos subdominios.
- Documentar una plantilla de aplicación con Compose, PostgreSQL, red y router Traefik.
- Diseñar posteriormente un panel o comando automatizado para crear servicios a partir de esa plantilla.

## Fuera de alcance

- Eliminar la estructura antigua antes de validar las migraciones.
- Separación de bases de datos existentes.
- Optimización profunda del código Django.
- Configuración de Git o sincronización automática.
- Limpieza irreversible de bases de datos o archivos.
- Backups nuevos durante esta fase, por indicación del usuario.

## Fases

### Fase 0: Inventario operativo

- Determinar qué carpeta, Compose, contenedores y volúmenes corresponden a producción.
- Determinar el nombre real de la base de datos principal.
- Revisar variables de entorno efectivamente usadas.
- Revisar red y routers activos de Traefik.
- No mover archivos funcionales en esta fase.

### Fase 1: Estructura mínima

- Seleccionar una única carpeta fuente para Netgogo.
- Separar código activo de históricos, pruebas y duplicados.
- Crear una estructura clara de aplicación, configuración, Docker y recursos.
- Mover únicamente archivos confirmados como obsoletos a `old`.

### Fase 2: Docker y PostgreSQL

- Dejar un Compose principal con `db`, `web` y, si corresponde, `static`.
- Configurar persistencia mediante volúmenes.
- Configurar la conexión Django con variables de entorno.
- Ejecutar comprobaciones de salud y migraciones.

### Fase 3: Traefik y publicación

- Conectar solo los servicios HTTP necesarios a `traefik_default`.
- Configurar `netgogo.cl` y `www.netgogo.cl`.
- Verificar HTTPS, certificado y puerto interno de Gunicorn.
- Verificar estáticos y media.

### Fase 4: Comprobación funcional

- Login y administración.
- Tienda y catálogo.
- Carrito y creación de órdenes.
- Pasarela de pagos y webhook.
- Persistencia después de reiniciar contenedores.

### Fase 5: Método para sumar aplicaciones

- Definir plantilla de Compose para cada proyecto secundario.
- Cada proyecto tendrá su propio código, Dockerfile, variables y base de datos.
- Solo el servicio web se conectará a Traefik.
- Las bases de datos permanecerán en redes internas, salvo necesidad concreta.
- Cada alta deberá validar nombre de servicio, subdominio, red Traefik, puerto interno, variables y persistencia.
- El modelo elegido será un PostgreSQL central con una base y usuario independientes por clon; no se creará un contenedor PostgreSQL por clon.

### Fase 6: Panel de despliegue

- Crear un panel protegido o comando administrativo para registrar una aplicación.
- Empezar con un panel local en modo vista previa, sin ejecutar Docker ni conectarse a producción.
- Generar Compose, variables, base PostgreSQL, router Traefik y certificado mediante una plantilla.
- Mostrar estado, logs y operaciones limitadas de iniciar, detener y actualizar.
- Mantener confirmación explícita antes de acciones destructivas.
- Probar las operaciones reales primero con un clon descartable local.

### Fase 7: Migración de aplicaciones reales

- Preparar y publicar Nomina desde `/home/max/projects/nomina`.
- Administrar Nomina mediante el panel y validar su operación productiva.
- Detener el contenedor antiguo de Condocdat sin borrar sus datos.
- Publicar Condocdat desde `/home/max/projects/condocdat` usando el mismo patrón.
- Repetir la migración para los demás proyectos Django.
- Tras validar cada aplicación, retirar ambientes virtuales, contenedores y carpetas heredadas que ya no estén en uso.

## Regla de avance

No se pasa de fase si la fase anterior no cumple sus criterios de aceptación definidos en `CHECKLIST.md`.
