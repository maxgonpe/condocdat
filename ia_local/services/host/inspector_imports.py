from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


# ============================================================
# UTILIDADES
# ============================================================


def _leer_archivo(
    ruta: str,
) -> str:

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


def _paquete_modulo(
    modulo_actual: str,
) -> list[str]:

    partes = [
        parte
        for parte
        in str(
            modulo_actual
            or ""
        ).split(".")
        if parte
    ]

    if partes:
        return partes[:-1]

    return []


def _resolver_modulo_relativo(
    modulo_actual: str,
    modulo_importado: str,
    nivel: int,
) -> str:
    """
    Ejemplo:

        modulo_actual:
            ia_local.services.host.respuesta_llm

        from .contexto_semantico import construir_contexto_semantico

    produce:

        ia_local.services.host.contexto_semantico
    """

    modulo_importado = str(
        modulo_importado
        or ""
    )

    nivel = int(
        nivel
        or 0
    )

    if nivel <= 0:
        return modulo_importado

    paquete = _paquete_modulo(
        modulo_actual
    )

    subir = (
        nivel
        - 1
    )

    if subir > 0:

        paquete = paquete[
            :max(
                0,
                len(
                    paquete
                )
                - subir
            )
        ]

    if modulo_importado:

        return ".".join(
            paquete
            + modulo_importado.split(".")
        )

    return ".".join(
        paquete
    )


# ============================================================
# ANÁLISIS DE IMPORTS
# ============================================================


def analizar_imports_archivo(
    ruta: str,
    modulo_actual: str,
) -> dict[str, Any]:

    contenido = _leer_archivo(
        ruta
    )

    if not contenido:

        return {
            "simbolos":
                {},

            "modulos":
                {},

            "imports":
                [],

            "error":
                None,
        }

    try:

        arbol = ast.parse(
            contenido,
            filename=ruta,
        )

    except SyntaxError as exc:

        return {
            "simbolos":
                {},

            "modulos":
                {},

            "imports":
                [],

            "error":
                f"SyntaxError: {exc}",
        }

    simbolos = {}
    modulos = {}
    imports = []

    for nodo in arbol.body:

        # ====================================================
        # import modulo
        # import modulo as alias
        # ====================================================

        if isinstance(
            nodo,
            ast.Import,
        ):

            for alias in nodo.names:

                destino = str(
                    alias.name
                    or ""
                ).strip()

                if not destino:
                    continue

                if alias.asname:

                    visible = alias.asname

                else:

                    # Python enlaza el primer componente:
                    #
                    # import paquete.modulo
                    # -> nombre visible "paquete"
                    visible = destino.split(
                        "."
                    )[0]

                    destino = visible

                modulos[
                    visible
                ] = destino

                imports.append(
                    {
                        "tipo":
                            "import",

                        "visible":
                            visible,

                        "destino":
                            destino,

                        "linea":
                            getattr(
                                nodo,
                                "lineno",
                                None,
                            ),
                    }
                )

            continue

        # ====================================================
        # from modulo import simbolo
        # from .modulo import simbolo
        # ====================================================

        if not isinstance(
            nodo,
            ast.ImportFrom,
        ):
            continue

        modulo_resuelto = (
            _resolver_modulo_relativo(
                modulo_actual,
                nodo.module
                or "",
                nodo.level
                or 0,
            )
        )

        for alias in nodo.names:

            nombre_real = str(
                alias.name
                or ""
            ).strip()

            if (
                not nombre_real
                or nombre_real == "*"
            ):
                continue

            nombre_visible = (
                alias.asname
                or nombre_real
            )

            if modulo_resuelto:

                destino = (
                    f"{modulo_resuelto}."
                    f"{nombre_real}"
                )

            else:

                destino = nombre_real

            simbolos[
                nombre_visible
            ] = destino

            imports.append(
                {
                    "tipo":
                        "from",

                    "visible":
                        nombre_visible,

                    "destino":
                        destino,

                    "modulo":
                        modulo_resuelto,

                    "linea":
                        getattr(
                            nodo,
                            "lineno",
                            None,
                        ),
                }
            )

    return {
        "simbolos":
            simbolos,

        "modulos":
            modulos,

        "imports":
            imports,

        "error":
            None,
    }


def analizar_imports_simbolo(
    simbolo: dict[str, Any],
) -> dict[str, Any]:

    return analizar_imports_archivo(
        str(
            simbolo.get(
                "ruta",
                ""
            )
            or ""
        ),
        str(
            simbolo.get(
                "modulo",
                ""
            )
            or ""
        ),
    )