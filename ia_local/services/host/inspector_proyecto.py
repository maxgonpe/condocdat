from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterator

from django.apps import apps
from django.conf import settings
from django.urls import URLPattern, URLResolver, get_resolver


# ============================================================
# EXCLUSIONES DE INVENTARIO FÍSICO
# ============================================================

DIRECTORIOS_EXCLUIDOS = {
    ".git",
    ".env",
    ".venv",
    "env",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    "node_modules",
    "site-packages",
    "dist-packages",
    "staticfiles",
    "media",
}

PREFIJOS_ENTORNO_VIRTUAL = (
    ".venv_",
    ".venv-",
    "venv_",
    "venv-",
    ".env_",
    ".env-",
    "env_",
    "env-",
    "virtualenv",
    ".virtualenv",
)

SUFIJOS_BACKUP = (
    "_bak.py",
    "_backup.py",
    "_old.py",
    "_copy.py",
)


def _directorios_excluidos_configurados() -> set[str]:
    """
    Devuelve exclusiones adicionales configuradas
    opcionalmente por el proyecto anfitrión.

    Ejemplo en settings.py:

        IA_LOCAL_EXCLUDE_DIRS = [
            "directorio_temporal",
            "codigo_archivado",
        ]

    Esta configuración es completamente genérica y no
    contiene conocimiento del negocio del host.
    """

    configurados = getattr(
        settings,
        "IA_LOCAL_EXCLUDE_DIRS",
        [],
    )

    if isinstance(
        configurados,
        str,
    ):
        configurados = [
            configurados
        ]

    try:
        resultado = {
            str(item)
            .strip()
            .lower()
            for item
            in configurados
            if str(item).strip()
        }

    except TypeError:
        resultado = set()

    return resultado


def _nombre_directorio_excluido(
    nombre: str,
) -> bool:
    """
    Determina si un directorio debe quedar fuera
    del inventario físico de IA Local.

    Además de nombres exactos reconoce variantes
    habituales de entornos virtuales como:

        .venv_qr
        .venv-test
        venv_local
        env_dev
        virtualenv_python
    """

    nombre_normalizado = (
        str(
            nombre
            or ""
        )
        .strip()
        .lower()
    )

    if not nombre_normalizado:
        return False

    excluidos = (
        DIRECTORIOS_EXCLUIDOS
        | _directorios_excluidos_configurados()
    )

    if nombre_normalizado in excluidos:
        return True

    if nombre_normalizado.startswith(
        PREFIJOS_ENTORNO_VIRTUAL
    ):
        return True

    return False


# ============================================================
# IDENTIDAD DEL PROYECTO
# ============================================================

def obtener_identidad_proyecto() -> dict[str, Any]:
    """
    Obtiene identidad estructural del proyecto Django anfitrión.

    No contiene conocimiento específico del proyecto.
    """

    base_dir = Path(
        settings.BASE_DIR
    ).resolve()

    root_urlconf = str(
        getattr(
            settings,
            "ROOT_URLCONF",
            "",
        )
        or ""
    )

    settings_module = (
        os.environ.get(
            "DJANGO_SETTINGS_MODULE",
            "",
        )
        or ""
    )

    nombre_proyecto = ""

    if root_urlconf:
        nombre_proyecto = (
            root_urlconf
            .split(".")[0]
            .strip()
        )

    if (
        not nombre_proyecto
        and settings_module
    ):
        nombre_proyecto = (
            settings_module
            .split(".")[0]
            .strip()
        )

    if not nombre_proyecto:
        nombre_proyecto = (
            base_dir.name
            or "django"
        )

    return {
        "nombre":
            nombre_proyecto,

        "base_dir":
            str(
                base_dir
            ),

        "root_urlconf":
            root_urlconf,

        "settings_module":
            settings_module,
    }


# ============================================================
# APPS
# ============================================================

def obtener_apps_instaladas() -> list[dict[str, Any]]:
    resultado = []

    for config in apps.get_app_configs():

        modelos = list(
            config.get_models()
        )

        nombre = str(
            config.name
        )

        if nombre.startswith(
            "django.contrib."
        ):
            tipo = "django"

        elif config.label == "ia_local":
            tipo = "ia_local"

        else:
            tipo = "proyecto"

        resultado.append(
            {
                "label":
                    config.label,

                "name":
                    nombre,

                "verbose_name":
                    str(
                        config.verbose_name
                    ),

                "path":
                    str(
                        Path(
                            config.path
                        ).resolve()
                    ),

                "tipo":
                    tipo,

                "modelos":
                    len(
                        modelos
                    ),
            }
        )

    resultado.sort(
        key=lambda item: (
            item["tipo"],
            item["label"],
        )
    )

    return resultado


# ============================================================
# MODELOS
# ============================================================

def obtener_modelos_proyecto() -> list[dict[str, Any]]:
    resultado = []

    for modelo in apps.get_models():

        meta = modelo._meta

        resultado.append(
            {
                "label":
                    meta.label,

                "app_label":
                    meta.app_label,

                "modelo":
                    meta.object_name,

                "tabla":
                    meta.db_table,

                "verbose_name":
                    str(
                        meta.verbose_name
                    ),

                "verbose_name_plural":
                    str(
                        meta.verbose_name_plural
                    ),

                "abstracto":
                    bool(
                        meta.abstract
                    ),

                "proxy":
                    bool(
                        meta.proxy
                    ),

                "campos":
                    len(
                        meta.get_fields()
                    ),
            }
        )

    resultado.sort(
        key=lambda item: (
            item[
                "label"
            ]
            .lower()
        )
    )

    return resultado


# ============================================================
# INVENTARIO FÍSICO
# ============================================================

def _ruta_excluida(
    ruta: Path,
    base_dir: Path,
) -> bool:
    """
    Determina si una ruta pertenece a un árbol
    que IA Local no debe inspeccionar.

    La decisión se basa únicamente en estructura física,
    nunca en conocimiento específico del proyecto anfitrión.
    """

    try:
        ruta_resuelta = (
            ruta.resolve()
        )

        relativa = (
            ruta_resuelta.relative_to(
                base_dir
            )
        )

    except (
        OSError,
        RuntimeError,
        ValueError,
    ):
        return True

    for parte in relativa.parts:

        if _nombre_directorio_excluido(
            parte
        ):
            return True

    return False


def _python_permitido(
    ruta: Path,
    base_dir: Path,
) -> bool:

    if _ruta_excluida(
        ruta,
        base_dir,
    ):
        return False

    nombre = (
        ruta.name
        .lower()
    )

    if nombre.endswith(
        SUFIJOS_BACKUP
    ):
        return False

    if ".bak" in nombre:
        return False

    return True


def _iterar_archivos(
    base_dir: Path,
    sufijo: str,
) -> Iterator[Path]:
    """
    Recorre físicamente el proyecto y poda los directorios
    excluidos ANTES de entrar en ellos.

    Esto evita recorrer:

        virtualenvs
        site-packages
        node_modules
        caches
        media
        staticfiles

    y reduce considerablemente el trabajo posterior
    de los inspectores AST.
    """

    for (
        raiz,
        directorios,
        archivos,
    ) in os.walk(
        base_dir,
        topdown=True,
        followlinks=False,
    ):

        # ----------------------------------------------------
        # PODA TEMPRANA
        # ----------------------------------------------------

        directorios[:] = [
            nombre
            for nombre
            in directorios
            if not _nombre_directorio_excluido(
                nombre
            )
        ]

        raiz_path = Path(
            raiz
        )

        # Defensa adicional por si la raíz actual
        # ya pertenece a un árbol excluido.

        if _ruta_excluida(
            raiz_path,
            base_dir,
        ):
            directorios[:] = []
            continue

        # ----------------------------------------------------
        # ARCHIVOS
        # ----------------------------------------------------

        for nombre_archivo in archivos:

            if not (
                nombre_archivo
                .lower()
                .endswith(
                    sufijo.lower()
                )
            ):
                continue

            ruta = (
                raiz_path
                / nombre_archivo
            )

            if _ruta_excluida(
                ruta,
                base_dir,
            ):
                continue

            yield ruta


def obtener_archivos_python() -> list[dict[str, Any]]:
    base_dir = Path(
        settings.BASE_DIR
    ).resolve()

    resultado = []

    for ruta in _iterar_archivos(
        base_dir,
        ".py",
    ):

        if not _python_permitido(
            ruta,
            base_dir,
        ):
            continue

        try:
            relativa = (
                ruta.relative_to(
                    base_dir
                )
            )

        except ValueError:
            continue

        try:
            bytes_archivo = (
                ruta.stat().st_size
            )

        except OSError:
            continue

        resultado.append(
            {
                "archivo":
                    str(
                        relativa
                    ),

                "ruta":
                    str(
                        ruta.resolve()
                    ),

                "bytes":
                    bytes_archivo,
            }
        )

    resultado.sort(
        key=lambda item: (
            item[
                "archivo"
            ]
            .lower()
        )
    )

    return resultado


# ============================================================
# TEMPLATES
# ============================================================

def obtener_templates() -> list[dict[str, Any]]:
    base_dir = Path(
        settings.BASE_DIR
    ).resolve()

    resultado = []

    for ruta in _iterar_archivos(
        base_dir,
        ".html",
    ):

        partes_lower = {
            parte.lower()
            for parte
            in ruta.parts
        }

        if "templates" not in partes_lower:
            continue

        try:
            relativa = (
                ruta.relative_to(
                    base_dir
                )
            )

        except ValueError:
            continue

        try:
            bytes_archivo = (
                ruta.stat().st_size
            )

        except OSError:
            continue

        resultado.append(
            {
                "archivo":
                    str(
                        relativa
                    ),

                "ruta":
                    str(
                        ruta.resolve()
                    ),

                "bytes":
                    bytes_archivo,
            }
        )

    resultado.sort(
        key=lambda item: (
            item[
                "archivo"
            ]
            .lower()
        )
    )

    return resultado


# ============================================================
# URLS
# ============================================================

def obtener_urls_proyecto() -> list[dict[str, Any]]:
    resultado = []

    try:
        resolver_raiz = (
            get_resolver()
        )

    except Exception as exc:

        return [
            {
                "error":
                    (
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    )
            }
        ]

    def recorrer(
        patrones,
        prefijo: str = "",
        namespace: str = "",
    ) -> None:

        for patron in patrones:

            # ------------------------------------------------
            # URL FINAL
            # ------------------------------------------------

            if isinstance(
                patron,
                URLPattern,
            ):

                ruta_local = str(
                    patron.pattern
                )

                ruta = (
                    f"{prefijo}"
                    f"{ruta_local}"
                )

                nombre = (
                    patron.name
                    or ""
                )

                lookup_str = ""

                try:
                    lookup_str = (
                        patron.lookup_str
                        or ""
                    )

                except Exception:
                    pass

                resultado.append(
                    {
                        "ruta":
                            ruta,

                        "name":
                            nombre,

                        "namespace":
                            namespace,

                        "view":
                            lookup_str,
                    }
                )

                continue

            # ------------------------------------------------
            # URL RESOLVER / INCLUDE
            # ------------------------------------------------

            if isinstance(
                patron,
                URLResolver,
            ):

                ruta_local = str(
                    patron.pattern
                )

                nuevo_prefijo = (
                    f"{prefijo}"
                    f"{ruta_local}"
                )

                namespace_local = (
                    patron.namespace
                    or ""
                )

                if (
                    namespace
                    and namespace_local
                ):
                    nuevo_namespace = (
                        f"{namespace}:"
                        f"{namespace_local}"
                    )

                elif namespace_local:
                    nuevo_namespace = (
                        namespace_local
                    )

                else:
                    nuevo_namespace = (
                        namespace
                    )

                try:
                    hijos = (
                        patron.url_patterns
                    )

                except Exception:
                    continue

                recorrer(
                    hijos,
                    prefijo=nuevo_prefijo,
                    namespace=nuevo_namespace,
                )

    try:
        recorrer(
            resolver_raiz.url_patterns
        )

    except Exception as exc:

        resultado.append(
            {
                "error":
                    (
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    )
            }
        )

    resultado.sort(
        key=lambda item: (
            str(
                item.get(
                    "ruta",
                    ""
                )
            ),
            str(
                item.get(
                    "name",
                    ""
                )
            ),
        )
    )

    return resultado


# ============================================================
# RESUMEN GENERAL
# ============================================================

def construir_resumen_proyecto() -> dict[str, Any]:

    identidad = (
        obtener_identidad_proyecto()
    )

    apps_instaladas = (
        obtener_apps_instaladas()
    )

    modelos = (
        obtener_modelos_proyecto()
    )

    urls = (
        obtener_urls_proyecto()
    )

    archivos_python = (
        obtener_archivos_python()
    )

    templates = (
        obtener_templates()
    )

    apps_proyecto = [
        item
        for item
        in apps_instaladas
        if item[
            "tipo"
        ] == "proyecto"
    ]

    apps_django = [
        item
        for item
        in apps_instaladas
        if item[
            "tipo"
        ] == "django"
    ]

    errores_urls = [
        item
        for item
        in urls
        if item.get(
            "error"
        )
    ]

    return {
        "identidad":
            identidad,

        "totales": {

            "apps":
                len(
                    apps_instaladas
                ),

            "apps_proyecto":
                len(
                    apps_proyecto
                ),

            "apps_django":
                len(
                    apps_django
                ),

            "modelos":
                len(
                    modelos
                ),

            "urls":
                len(
                    [
                        item
                        for item
                        in urls
                        if not item.get(
                            "error"
                        )
                    ]
                ),

            "archivos_python":
                len(
                    archivos_python
                ),

            "templates":
                len(
                    templates
                ),

            "errores_urls":
                len(
                    errores_urls
                ),
        },

        "apps":
            apps_instaladas,

        "modelos":
            modelos,

        "urls":
            urls,

        "archivos_python":
            archivos_python,

        "templates":
            templates,
    }