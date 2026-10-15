from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from django.apps import apps

from .inspector_proyecto import (
    obtener_urls_proyecto,
)


# ============================================================
# UTILIDADES
# ============================================================

def _separar_view(
    view: str,
) -> tuple[str, str]:
    """
    Convierte:

        rdi.views.planos_actualizados_view

    en:

        modulo = rdi.views
        simbolo = planos_actualizados_view
    """

    valor = str(
        view
        or ""
    ).strip()

    if not valor:
        return "", ""

    partes = valor.split(".")

    if len(partes) < 2:
        return "", valor

    modulo = ".".join(
        partes[:-1]
    )

    simbolo = partes[-1]

    return (
        modulo,
        simbolo,
    )


def _resolver_app_por_modulo(
    modulo: str,
) -> dict[str, Any] | None:
    """
    Intenta determinar a qué app Django pertenece un módulo.

    No depende de nombres hardcodeados.
    """

    modulo = str(
        modulo
        or ""
    ).strip()

    if not modulo:
        return None

    candidatos = []

    for config in apps.get_app_configs():

        app_name = str(
            config.name
        )

        if (
            modulo == app_name
            or modulo.startswith(
                f"{app_name}."
            )
        ):
            candidatos.append(
                config
            )

    if not candidatos:
        return None

    candidatos.sort(
        key=lambda config: len(
            str(
                config.name
            )
        ),
        reverse=True,
    )

    config = candidatos[0]

    if str(
        config.name
    ).startswith(
        "django.contrib."
    ):
        tipo = "django"

    elif config.label == "ia_local":
        tipo = "ia_local"

    else:
        tipo = "proyecto"

    return {
        "label":
            config.label,

        "name":
            str(
                config.name
            ),

        "path":
            str(
                Path(
                    config.path
                ).resolve()
            ),

        "tipo":
            tipo,
    }


def _resolver_archivo_modulo(
    modulo: str,
) -> str:
    """
    Intenta localizar físicamente el archivo Python
    correspondiente al módulo.

    No importa ni ejecuta el módulo.
    """

    if not modulo:
        return ""

    try:
        spec = importlib.util.find_spec(
            modulo
        )

    except Exception:
        return ""

    if spec is None:
        return ""

    origen = getattr(
        spec,
        "origin",
        None,
    )

    if not origen:
        return ""

    if origen in {
        "built-in",
        "frozen",
    }:
        return ""

    try:
        return str(
            Path(
                origen
            ).resolve()
        )
    except Exception:
        return str(
            origen
        )


def _tipo_view_probable(
    simbolo: str,
) -> str:
    """
    Clasificación heurística muy conservadora.

    No intenta ejecutar la view.
    """

    valor = str(
        simbolo
        or ""
    ).strip()

    if not valor:
        return "desconocido"

    if valor.endswith(
        "_view"
    ):
        return "funcion"

    if valor.endswith(
        "View"
    ):
        return "clase"

    return "desconocido"


# ============================================================
# PERFIL DE UNA URL
# ============================================================

def construir_perfil_url(
    item: dict[str, Any],
) -> dict[str, Any]:

    ruta = str(
        item.get(
            "ruta",
            ""
        )
        or ""
    )

    namespace = str(
        item.get(
            "namespace",
            ""
        )
        or ""
    )

    nombre = str(
        item.get(
            "name",
            ""
        )
        or ""
    )

    view = str(
        item.get(
            "view",
            ""
        )
        or ""
    )

    modulo, simbolo = (
        _separar_view(
            view
        )
    )

    app = _resolver_app_por_modulo(
        modulo
    )

    archivo = (
        _resolver_archivo_modulo(
            modulo
        )
    )

    tipo_probable = (
        _tipo_view_probable(
            simbolo
        )
    )

    return {
        "ruta":
            ruta,

        "namespace":
            namespace,

        "name":
            nombre,

        "view":
            view,

        "modulo":
            modulo,

        "simbolo":
            simbolo,

        "archivo":
            archivo,

        "tipo_probable":
            tipo_probable,

        "app":
            app,
    }


# ============================================================
# MAPA URL -> VIEW
# ============================================================

def construir_mapa_urls() -> list[dict[str, Any]]:
    urls = (
        obtener_urls_proyecto()
    )

    resultado = []

    for item in urls:

        if item.get(
            "error"
        ):
            continue

        perfil = construir_perfil_url(
            item
        )

        resultado.append(
            perfil
        )

    resultado.sort(
        key=lambda item: (
            item[
                "ruta"
            ],
            item[
                "namespace"
            ],
            item[
                "name"
            ],
            item[
                "view"
            ],
        )
    )

    return resultado


# ============================================================
# RESUMEN
# ============================================================

def construir_resumen_urls() -> dict[str, Any]:
    mapa = construir_mapa_urls()

    con_view = [
        item
        for item in mapa
        if item[
            "view"
        ]
    ]

    con_app = [
        item
        for item in mapa
        if item[
            "app"
        ]
    ]

    proyecto = [
        item
        for item in mapa
        if (
            item[
                "app"
            ]
            and item[
                "app"
            ][
                "tipo"
            ] == "proyecto"
        )
    ]

    ia_local = [
        item
        for item in mapa
        if (
            item[
                "app"
            ]
            and item[
                "app"
            ][
                "tipo"
            ] == "ia_local"
        )
    ]

    django = [
        item
        for item in mapa
        if (
            item[
                "app"
            ]
            and item[
                "app"
            ][
                "tipo"
            ] == "django"
        )
    ]

    sin_app = [
        item
        for item in mapa
        if not item[
            "app"
        ]
    ]

    return {
        "totales": {
            "urls":
                len(
                    mapa
                ),

            "con_view":
                len(
                    con_view
                ),

            "con_app":
                len(
                    con_app
                ),

            "proyecto":
                len(
                    proyecto
                ),

            "ia_local":
                len(
                    ia_local
                ),

            "django":
                len(
                    django
                ),

            "sin_app":
                len(
                    sin_app
                ),
        },

        "urls":
            mapa,

        "proyecto":
            proyecto,

        "ia_local":
            ia_local,

        "django":
            django,

        "sin_app":
            sin_app,
    }