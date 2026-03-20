# Configuración de correo (Enviar correo desde CONDOCDAT)

## Dónde se configura

- **Desarrollo local**: archivo **`.env`** en la raíz del proyecto (`/home/max/condocdat/.env`).
  - Ese archivo está en `.gitignore` y **no se sube** al repositorio.
  - Django carga sus variables al arrancar gracias a `python-dotenv` en `condocdat/settings.py`.

- **Producción**: las variables deben definirse **en el servidor**, no en un archivo dentro del repo.
  - Opción 1: archivo `.env` en la raíz del proyecto **solo en el servidor**, con el mismo contenido que en local (incluido `EMAIL_HOST_PASSWORD=...`). Asegurarse de que ese `.env` no esté en git.
  - **Docker:** el `.env` no está dentro del contenedor; las variables de correo deben estar en el `.env` **del host** y figurar en `docker-compose.prod.yml` (p. ej. `EMAIL_HOST_PASSWORD=${EMAIL_HOST_PASSWORD}`). Tras editar `.env`, recrear el contenedor.
  - Opción 2: exportar antes de arrancar la app, por ejemplo en systemd:
    ```ini
    [Service]
    Environment="EMAIL_HOST_PASSWORD=tu_contraseña_real"
    Environment="EMAIL_HOST_USER=max.gonzalez@propamat.cl"
    ```
  - Opción 3: si usas un panel de hosting (Heroku, Railway, etc.), añadir `EMAIL_HOST_PASSWORD` y el resto en la sección "Environment variables" / "Config vars".

## Variables que usa el proyecto

| Variable              | Ejemplo                         | Descripción                    |
|-----------------------|---------------------------------|--------------------------------|
| `EMAIL_HOST`          | `smtp.office365.com`           | Servidor SMTP (Outlook)        |
| `EMAIL_PORT`          | `587`                          | Puerto TLS                     |
| `EMAIL_USE_TLS`       | `True`                         | Usar TLS                       |
| `EMAIL_HOST_USER`     | `max.gonzalez@propamat.cl`     | Cuenta de envío                |
| `EMAIL_HOST_PASSWORD` | *(valor secreto)*             | Contraseña o contraseña de app  |
| `DEFAULT_FROM_EMAIL`  | Igual que `EMAIL_HOST_USER`   | Remitente visible              |

**Importante**: en producción no pongas la contraseña en código ni en un archivo que se suba a git. Solo en el entorno del servidor o en un `.env` que exista únicamente en el servidor.
