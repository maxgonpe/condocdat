from __future__ import annotations

import re
import unicodedata
from typing import Any


VERSION = "IA-LLM004-v1"


def _texto(
    valor: Any,
) -> str:

    return str(
        valor
        or ""
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
        for caracter
        in texto
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


def detectar_intencion_operacional(
    pregunta: str,
) -> dict[str, Any]:
    """
    Detecta únicamente intención operacional explícita.

    No resuelve:
    - modelo;
    - campos;
    - filtros;
    - relaciones;
    - ORM.

    Tampoco invoca LLM.
    """

    texto = _normalizar(
        pregunta
    )

    # --------------------------------------------------------
    # IA-LLM004-C02
    # EXISTENCIA NATURAL CON "HAY"
    # --------------------------------------------------------
    #
    # Ejemplos:
    #
    #   hay RDI abiertas
    #   hay documentos pendientes
    #   hay equipos activos
    #
    # Se exige que "hay" aparezca al inicio para evitar
    # falsos positivos cuando la palabra aparece dentro
    # de otra construcción.
    # --------------------------------------------------------

    if (
        texto == "hay"
        or texto.startswith(
            "hay "
        )
    ):

        return {
            "ok":
                True,

            "version":
                VERSION,

            "pregunta":
                pregunta,

            "intencion":
                "existencia",

            "accion_host":
                "contar",

            "detectada":
                True,

            "llm_invocado":
                False,

            "estado":
                "intencion_operacional_detectada",
        }

    base = {
        "ok": True,
        "version": VERSION,
        "pregunta": pregunta,
        "intencion": None,
        "accion_host": None,
        "detectada": False,
        "llm_invocado": False,
    }

    if not texto:

        return {
            **base,
            "estado": "pregunta_vacia",
        }

    # --------------------------------------------------------
    # EXISTENCIA
    # --------------------------------------------------------
    #
    # Estas expresiones preguntan por existencia, no solicitan
    # necesariamente una lista de registros.
    # --------------------------------------------------------

    patrones_existencia = (
        r"\bhay\s+(?:algun|alguna|algunos|algunas)\b",
        r"\bexiste\s+(?:algun|alguna|alguno)\b",
        r"\bexisten\s+(?:algunos|algunas)\b",
        r"\bexiste\b",
        r"\bexisten\b",
    )

    for patron in patrones_existencia:

        if re.search(
            patron,
            texto,
        ):

            return {
                **base,
                "estado":
                    "intencion_operacional_detectada",

                "intencion":
                    "existencia",

                # HOST no necesita una operación nueva.
                # Un conteo permite responder existencia
                # conservando toda la validación actual.
                "accion_host":
                    "contar",

                "detectada":
                    True,
            }

    # --------------------------------------------------------
    # CONTEO
    # --------------------------------------------------------

    if re.search(
        (
            r"\b("
            r"cuantos|cuantas|cantidad|"
            r"numero de|nro de|total de"
            r")\b"
        ),
        texto,
    ):

        return {
            **base,
            "estado":
                "intencion_operacional_detectada",

            "intencion":
                "conteo",

            "accion_host":
                "contar",

            "detectada":
                True,
        }

    # --------------------------------------------------------
    # LISTADO
    # --------------------------------------------------------

    if re.search(
        (
            r"\b("
            r"listar|lista|mostrar|muestra|"
            r"muestrame|dame|ver"
            r")\b"
        ),
        texto,
    ):

        return {
            **base,
            "estado":
                "intencion_operacional_detectada",

            "intencion":
                "listado",

            "accion_host":
                "listar",

            "detectada":
                True,
        }

    return {
        **base,
        "estado":
            "intencion_operacional_no_detectada",
    }
