from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from .inspector_urls import (
    construir_mapa_urls,
)


def _leer_archivo(
    ruta: str,
) -> str:
    if not ruta:
        return ""

    archivo = Path(
        ruta
    )

    if not archivo.is_file():
        return ""

    try:
        return archivo.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return ""


def _nombre_llamada(
    nodo: ast.Call,
) -> str:
    try:
        return ast.unparse(
            nodo.func
        )
    except Exception:
        return ""


def _codigo_nodo(
    contenido: str,
    nodo: ast.AST,
) -> str:
    try:
        return (
            ast.get_source_segment(
                contenido,
                nodo,
            )
            or ""
        )
    except Exception:
        return ""


def _buscar_simbolo_ast(
    contenido: str,
    simbolo: str,
) -> ast.AST | None:

    try:
        arbol = ast.parse(
            contenido
        )
    except SyntaxError:
        return None

    for nodo in arbol.body:

        if isinstance(
            nodo,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            if getattr(
                nodo,
                "name",
                "",
            ) == simbolo:
                return nodo

    return None


def _clasificar_simbolo(
    nodo: ast.AST | None,
) -> str:

    if isinstance(
        nodo,
        ast.FunctionDef,
    ):
        return "funcion"

    if isinstance(
        nodo,
        ast.AsyncFunctionDef,
    ):
        return "funcion_async"

    if isinstance(
        nodo,
        ast.ClassDef,
    ):
        return "clase"

    return "desconocido"


def _extraer_llamadas(
    nodo: ast.AST | None,
) -> list[dict[str, Any]]:

    if nodo is None:
        return []

    resultado = []

    for sub in ast.walk(
        nodo
    ):

        if not isinstance(
            sub,
            ast.Call,
        ):
            continue

        nombre = _nombre_llamada(
            sub
        )

        if not nombre:
            continue

        resultado.append(
            {
                "nombre":
                    nombre,

                "linea":
                    getattr(
                        sub,
                        "lineno",
                        None,
                    ),
            }
        )

    resultado.sort(
        key=lambda item: (
            item[
                "linea"
            ]
            or 0,
            item[
                "nombre"
            ],
        )
    )

    return resultado


def construir_perfil_view(
    url_item: dict[str, Any],
) -> dict[str, Any]:

    archivo = str(
        url_item.get(
            "archivo",
            ""
        )
        or ""
    )

    simbolo = str(
        url_item.get(
            "simbolo",
            ""
        )
        or ""
    )

    contenido = _leer_archivo(
        archivo
    )

    nodo = None

    if contenido and simbolo:
        nodo = _buscar_simbolo_ast(
            contenido,
            simbolo,
        )

    tipo_real = _clasificar_simbolo(
        nodo
    )

    linea_inicio = (
        getattr(
            nodo,
            "lineno",
            None,
        )
        if nodo
        else None
    )

    linea_fin = (
        getattr(
            nodo,
            "end_lineno",
            None,
        )
        if nodo
        else None
    )

    lineas_total = None

    if (
        linea_inicio is not None
        and linea_fin is not None
    ):
        lineas_total = (
            linea_fin
            - linea_inicio
            + 1
        )

    llamadas = _extraer_llamadas(
        nodo
    )

    codigo = ""

    if (
        contenido
        and nodo is not None
    ):
        codigo = _codigo_nodo(
            contenido,
            nodo,
        )

    return {
        "ruta":
            url_item.get(
                "ruta",
                ""
            ),

        "namespace":
            url_item.get(
                "namespace",
                ""
            ),

        "name":
            url_item.get(
                "name",
                ""
            ),

        "view":
            url_item.get(
                "view",
                ""
            ),

        "modulo":
            url_item.get(
                "modulo",
                ""
            ),

        "simbolo":
            simbolo,

        "archivo":
            archivo,

        "app":
            url_item.get(
                "app"
            ),

        "encontrada":
            nodo is not None,

        "tipo_real":
            tipo_real,

        "linea_inicio":
            linea_inicio,

        "linea_fin":
            linea_fin,

        "lineas_total":
            lineas_total,

        "llamadas":
            llamadas,

        "total_llamadas":
            len(
                llamadas
            ),

        "codigo":
            codigo,
    }


def construir_mapa_views() -> list[dict[str, Any]]:

    urls = construir_mapa_urls()

    resultado = []

    for item in urls:

        if not item.get(
            "view"
        ):
            continue

        perfil = construir_perfil_view(
            item
        )

        resultado.append(
            perfil
        )

    resultado.sort(
        key=lambda item: (
            item[
                "view"
            ],
            item[
                "ruta"
            ],
        )
    )

    return resultado


def construir_resumen_views() -> dict[str, Any]:

    mapa = construir_mapa_views()

    encontradas = [
        item
        for item in mapa
        if item[
            "encontrada"
        ]
    ]

    no_encontradas = [
        item
        for item in mapa
        if not item[
            "encontrada"
        ]
    ]

    ia_local = [
        item
        for item in mapa
        if (
            item.get(
                "app"
            )
            and item[
                "app"
            ][
                "tipo"
            ] == "ia_local"
        )
    ]

    proyecto = [
        item
        for item in mapa
        if (
            item.get(
                "app"
            )
            and item[
                "app"
            ][
                "tipo"
            ] == "proyecto"
        )
    ]

    return {
        "totales": {
            "views":
                len(
                    mapa
                ),

            "encontradas":
                len(
                    encontradas
                ),

            "no_encontradas":
                len(
                    no_encontradas
                ),

            "ia_local":
                len(
                    ia_local
                ),

            "proyecto":
                len(
                    proyecto
                ),
        },

        "views":
            mapa,

        "encontradas":
            encontradas,

        "no_encontradas":
            no_encontradas,

        "ia_local":
            ia_local,

        "proyecto":
            proyecto,
    }


def buscar_view(
    texto: str,
) -> list[dict[str, Any]]:

    objetivo = str(
        texto
        or ""
    ).strip().lower()

    if not objetivo:
        return []

    resultado = []

    for item in construir_mapa_views():

        campos = (
            item.get(
                "view",
                ""
            ),
            item.get(
                "simbolo",
                ""
            ),
            item.get(
                "name",
                ""
            ),
            item.get(
                "ruta",
                ""
            ),
        )

        if any(
            objetivo
            in str(
                campo
            ).lower()
            for campo
            in campos
        ):
            resultado.append(
                item
            )

    return resultado