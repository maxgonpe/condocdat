from __future__ import annotations

import re
import unicodedata
from typing import Any

from ia_local.config.cardinalidad import (
    LIMITE_MAXIMO_SOLICITABLE,
)


# ============================================================
# IA-LLM004-D1
# CARDINALIDAD NATURAL
# ============================================================
#
# Responsabilidad:
#
#   detectar cardinalidad EXPLÍCITA en lenguaje natural.
#
# No:
#
#   - resuelve modelos;
#   - interpreta campos;
#   - ejecuta ORM;
#   - decide orden;
#   - invoca LLM;
#   - conoce reglas de negocio.
#
# ============================================================


VERSION = "IA-LLM004-D1-v1"


EXPRESIONES_TOTALIDAD = (
    "todos",
    "todas",
    "todo",
    "toda",
    "sin limite",
    "completo",
    "completa",
    "completos",
    "completas",
    "la totalidad",
)


def _texto(
    valor: Any,
) -> str:

    return str(
        valor or ""
    ).strip()


def _normalizar(
    valor: Any,
) -> str:

    texto = _texto(
        valor
    )

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(
            caracter
        )
    )

    texto = texto.lower()

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()


def _resultado_base(
    pregunta: str,
) -> dict[str, Any]:

    return {
        "ok":
            True,

        "version":
            VERSION,

        "pregunta":
            pregunta,

        "detectada":
            False,

        "cantidad_solicitada":
            None,

        "totalidad_solicitada":
            False,

        "origen":
            None,

        "limitada_por_politica":
            False,

        "llm_invocado":
            False,
    }


def _normalizar_cantidad(
    cantidad: int,
) -> tuple[int | None, bool]:

    if cantidad <= 0:

        return (
            None,
            False,
        )

    if cantidad > LIMITE_MAXIMO_SOLICITABLE:

        return (
            LIMITE_MAXIMO_SOLICITABLE,
            True,
        )

    return (
        cantidad,
        False,
    )


def detectar_cardinalidad_natural(
    pregunta: str,
) -> dict[str, Any]:

    """
    Detecta únicamente cardinalidad explícita.

    Ejemplos soportados:

        dame 5 registros
        muestra 10 documentos
        los primeros 3
        las últimas 8
        solo 4
        una muestra de 25
        todas las RDI

    Si no existe evidencia inequívoca de cardinalidad,
    no inventa una cantidad.
    """

    texto = _normalizar(
        pregunta
    )

    base = _resultado_base(
        pregunta
    )

    if not texto:

        return {
            **base,
            "estado":
                "pregunta_vacia",
        }

    # --------------------------------------------------------
    # TOTALIDAD EXPLÍCITA
    # --------------------------------------------------------

    if any(
        expresion in texto
        for expresion
        in EXPRESIONES_TOTALIDAD
    ):

        return {
            **base,

            "estado":
                "totalidad_detectada",

            "detectada":
                True,

            "cantidad_solicitada":
                None,

            "totalidad_solicitada":
                True,

            "origen":
                "totalidad_explicita",
        }

    # --------------------------------------------------------
    # CANTIDAD EXPLÍCITA
    # --------------------------------------------------------
    #
    # Los patrones son deliberadamente contextuales.
    #
    # No interpretamos cualquier número presente en la
    # pregunta como un límite.
    #
    # Esto evita errores con:
    #
    #   año 2026
    #   RDI 123
    #   documento 456
    #
    # --------------------------------------------------------

    patrones = (
        (
            "solo_n",
            r"\b(?:solo|solamente|unicamente)\s+(\d{1,6})\b",
        ),

        (
            "orden_n",
            (
                r"\b(?:primeros?|primeras?|"
                r"ultimos?|ultimas?)\s+"
                r"(\d{1,6})\b"
            ),
        ),

        (
            "muestra_de_n",
            (
                r"\b(?:una\s+)?muestra\s+de\s+"
                r"(\d{1,6})\b"
            ),
        ),

        (
            "verbo_n",
            (
                r"\b(?:dame|mostrar|muestra|muestrame|"
                r"lista|listar)\s+"
                r"(?:los\s+|las\s+|unos\s+|unas\s+)?"
                r"(\d{1,6})\b"
            ),
        ),
    )

    for origen, patron in patrones:

        coincidencia = re.search(
            patron,
            texto,
        )

        if not coincidencia:

            continue

        try:

            cantidad_cruda = int(
                coincidencia.group(
                    1
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            continue

        (
            cantidad,
            limitada,
        ) = _normalizar_cantidad(
            cantidad_cruda
        )

        if cantidad is None:

            return {
                **base,

                "estado":
                    "cantidad_invalida",

                "origen":
                    origen,
            }

        return {
            **base,

            "estado":
                "cantidad_detectada",

            "detectada":
                True,

            "cantidad_solicitada":
                cantidad,

            "totalidad_solicitada":
                False,

            "origen":
                origen,

            "cantidad_original":
                cantidad_cruda,

            "limitada_por_politica":
                limitada,
        }


    # IA-LLM008-F5-02-R1: CANTIDADES EN PALABRAS
    # La cantidad solo se detecta en contextos explícitos.
    # Conservamos la política transversal original.

    numeros_palabras = {
        "uno": 1, "una": 1,
        "dos": 2, "tres": 3, "cuatro": 4,
        "cinco": 5, "seis": 6, "siete": 7,
        "ocho": 8, "nueve": 9, "diez": 10,
        "once": 11, "doce": 12, "trece": 13,
        "catorce": 14, "quince": 15,
        "dieciseis": 16, "diecisiete": 17,
        "dieciocho": 18, "diecinueve": 19,
        "veinte": 20,
    }

    alternativas = "|".join(
        sorted(numeros_palabras, key=len, reverse=True)
    )

    patrones_palabras = (
        (
            "solo_palabra",
            rf"\b(?:solo|solamente|unicamente)\s+"
            rf"({alternativas})\b",
        ),
        (
            "orden_palabra",
            rf"\b(?:primeros?|primeras?|ultimos?|ultimas?)"
            rf"\s+({alternativas})\b",
        ),
        (
            "muestra_palabra",
            rf"\b(?:una\s+)?muestra\s+de\s+"
            rf"({alternativas})\b",
        ),
        (
            "verbo_palabra",
            rf"\b(?:dame|mostrar|muestra|muestrame|"
            rf"lista|listar)\s+"
            rf"(?:los\s+|las\s+|unos\s+|unas\s+)?"
            rf"({alternativas})\b",
        ),
    )

    for origen, patron in patrones_palabras:
        coincidencia = re.search(patron, texto)

        if not coincidencia:
            continue

        cantidad_cruda = numeros_palabras.get(
            coincidencia.group(1)
        )

        if cantidad_cruda is None:
            continue

        cantidad, limitada = _normalizar_cantidad(
            cantidad_cruda
        )

        if cantidad is None:
            return {
                **base,
                "estado": "cantidad_invalida",
                "origen": origen,
            }

        return {
            **base,
            "estado": "cantidad_detectada",
            "detectada": True,
            "cantidad_solicitada": cantidad,
            "totalidad_solicitada": False,
            "origen": origen,
            "cantidad_original": cantidad_cruda,
            "limitada_por_politica": limitada,
        }

    return {
        **base,

        "estado":
            "cardinalidad_no_detectada",
    }
