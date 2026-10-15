from __future__ import annotations

from pathlib import Path
from typing import Any

from django.apps import apps

from .inspector_proyecto import (
    obtener_apps_instaladas,
    obtener_archivos_python,
    obtener_templates,
    obtener_urls_proyecto,
)


def _normalizar_ruta(valor: str) -> str:
    return str(
        Path(valor).resolve()
    )


def _archivos_python_por_app(
    app_path: str,
    archivos_python: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    raiz_app = Path(
        app_path
    ).resolve()

    resultado = []

    for item in archivos_python:
        ruta = Path(
            item["ruta"]
        ).resolve()

        try:
            ruta.relative_to(
                raiz_app
            )
        except ValueError:
            continue

        resultado.append(
            item
        )

    return resultado


def _templates_por_app(
    app_path: str,
    templates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    raiz_app = Path(
        app_path
    ).resolve()

    resultado = []

    for item in templates:
        ruta = Path(
            item["ruta"]
        ).resolve()

        try:
            ruta.relative_to(
                raiz_app
            )
        except ValueError:
            continue

        resultado.append(
            item
        )

    return resultado


def _urls_por_app(
    app_name: str,
    app_label: str,
    urls: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    resultado = []

    prefijos = {
        app_name,
        app_label,
    }

    for item in urls:
        view = str(
            item.get(
                "view",
                ""
            )
            or ""
        )

        if not view:
            continue

        modulo_raiz = (
            view
            .split(".")[0]
            .strip()
        )

        if modulo_raiz in prefijos:
            resultado.append(
                item
            )

    return resultado


def _detectar_archivo(
    archivos: list[dict[str, Any]],
    nombre: str,
) -> bool:
    objetivo = nombre.lower()

    for item in archivos:
        ruta = Path(
            item["ruta"]
        )

        if ruta.name.lower() == objetivo:
            return True

    return False


def _detectar_directorio(
    app_path: str,
    nombre: str,
) -> bool:
    ruta = (
        Path(app_path)
        / nombre
    )

    return (
        ruta.exists()
        and ruta.is_dir()
    )


def _contar_management_commands(
    app_path: str,
) -> int:
    ruta = (
        Path(app_path)
        / "management"
        / "commands"
    )

    if not ruta.exists():
        return 0

    total = 0

    for archivo in ruta.glob(
        "*.py"
    ):
        if archivo.name == "__init__.py":
            continue

        total += 1

    return total


def _obtener_modelos_app(
    app_label: str,
) -> list[str]:
    try:
        config = apps.get_app_config(
            app_label
        )
    except LookupError:
        return []

    resultado = []

    for modelo in config.get_models():
        resultado.append(
            modelo._meta.label
        )

    resultado.sort(
        key=str.lower
    )

    return resultado


def construir_perfil_app(
    app: dict[str, Any],
    *,
    archivos_python: list[dict[str, Any]],
    templates: list[dict[str, Any]],
    urls: list[dict[str, Any]],
) -> dict[str, Any]:

    app_path = _normalizar_ruta(
        app["path"]
    )

    archivos_app = (
        _archivos_python_por_app(
            app_path,
            archivos_python,
        )
    )

    templates_app = (
        _templates_por_app(
            app_path,
            templates,
        )
    )

    urls_app = (
        _urls_por_app(
            app["name"],
            app["label"],
            urls,
        )
    )

    modelos = _obtener_modelos_app(
        app["label"]
    )

    tiene_views = _detectar_archivo(
        archivos_app,
        "views.py",
    )

    tiene_forms = _detectar_archivo(
        archivos_app,
        "forms.py",
    )

    tiene_signals = _detectar_archivo(
        archivos_app,
        "signals.py",
    )

    tiene_urls = _detectar_archivo(
        archivos_app,
        "urls.py",
    )

    tiene_admin = _detectar_archivo(
        archivos_app,
        "admin.py",
    )

    tiene_services = _detectar_directorio(
        app_path,
        "services",
    )

    management_commands = (
        _contar_management_commands(
            app_path
        )
    )

    if app["tipo"] == "django":
        rol = "infraestructura"

    elif app["tipo"] == "ia_local":
        rol = "ia_local"

    else:
        rol = "dominio"

    return {
        "label":
            app["label"],

        "name":
            app["name"],

        "verbose_name":
            app["verbose_name"],

        "path":
            app_path,

        "tipo":
            app["tipo"],

        "rol":
            rol,

        "modelos":
            modelos,

        "total_modelos":
            len(
                modelos
            ),

        "urls":
            urls_app,

        "total_urls":
            len(
                urls_app
            ),

        "archivos_python":
            archivos_app,

        "total_archivos_python":
            len(
                archivos_app
            ),

        "templates":
            templates_app,

        "total_templates":
            len(
                templates_app
            ),

        "tiene_views":
            tiene_views,

        "tiene_forms":
            tiene_forms,

        "tiene_signals":
            tiene_signals,

        "tiene_urls":
            tiene_urls,

        "tiene_admin":
            tiene_admin,

        "tiene_services":
            tiene_services,

        "management_commands":
            management_commands,
    }


def construir_perfiles_apps() -> list[dict[str, Any]]:
    apps_instaladas = (
        obtener_apps_instaladas()
    )

    archivos_python = (
        obtener_archivos_python()
    )

    templates = (
        obtener_templates()
    )

    urls = (
        obtener_urls_proyecto()
    )

    resultado = []

    for app in apps_instaladas:
        perfil = construir_perfil_app(
            app,
            archivos_python=archivos_python,
            templates=templates,
            urls=urls,
        )

        resultado.append(
            perfil
        )

    resultado.sort(
        key=lambda item: (
            item["rol"],
            item["label"],
        )
    )

    return resultado


def construir_resumen_apps() -> dict[str, Any]:
    perfiles = (
        construir_perfiles_apps()
    )

    dominio = [
        item
        for item in perfiles
        if item[
            "rol"
        ] == "dominio"
    ]

    infraestructura = [
        item
        for item in perfiles
        if item[
            "rol"
        ] == "infraestructura"
    ]

    propias_ia = [
        item
        for item in perfiles
        if item[
            "rol"
        ] == "ia_local"
    ]

    return {
        "totales": {
            "apps":
                len(
                    perfiles
                ),

            "dominio":
                len(
                    dominio
                ),

            "infraestructura":
                len(
                    infraestructura
                ),

            "ia_local":
                len(
                    propias_ia
                ),
        },

        "dominio":
            dominio,

        "infraestructura":
            infraestructura,

        "ia_local":
            propias_ia,

        "apps":
            perfiles,
    }