from __future__ import annotations

import re
import unicodedata
from typing import Any


# ============================================================
# IA-SEM
# NORMALIZACIÓN SEMÁNTICA COMÚN
# ============================================================


def texto_limpio(
    valor: Any,
) -> str:
    """
    Convierte un valor a texto seguro y elimina espacios periféricos.
    """

    return str(
        valor
        or ""
    ).strip()


def separar_nombre_tecnico(
    valor: Any,
) -> str:
    """
    Convierte nombres técnicos frecuentes a una forma legible.

    Ejemplos:

        CorreoEnviado
            -> Correo Enviado

        DocumentAttachment
            -> Document Attachment

        RDIRecord
            -> RDI Record

        HTTPResponse
            -> HTTP Response

        fecha_inicio
            -> fecha inicio

        cliente-taller
            -> cliente taller

    No realiza inferencias lingüísticas ni genera sinónimos.
    """

    texto = texto_limpio(
        valor
    )

    if not texto:
        return ""

    texto = texto.replace(
        "_",
        " ",
    )

    texto = texto.replace(
        "-",
        " ",
    )

    # --------------------------------------------------------
    # SIGLA + PALABRA
    #
    # RDIRecord     -> RDI Record
    # HTTPResponse  -> HTTP Response
    # --------------------------------------------------------

    texto = re.sub(
        r"(?<=[A-ZÁÉÍÓÚÑ])(?=[A-ZÁÉÍÓÚÑ][a-záéíóúñ])",
        " ",
        texto,
    )

    # --------------------------------------------------------
    # minúscula/número + Mayúscula
    #
    # CorreoEnviado -> Correo Enviado
    # item2Codigo   -> item2 Codigo
    # --------------------------------------------------------

    texto = re.sub(
        r"(?<=[a-záéíóúñ0-9])(?=[A-ZÁÉÍÓÚÑ])",
        " ",
        texto,
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()


def normalizar_texto(
    valor: Any,
) -> str:
    """
    Forma canónica utilizada por la capa IA-SEM.

    - separa nombres técnicos;
    - elimina acentos;
    - convierte a minúsculas;
    - colapsa espacios.

    Deliberadamente NO singulariza, pluraliza ni genera sinónimos.
    """

    texto = separar_nombre_tecnico(
        valor
    )

    if not texto:
        return ""

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


def deduplicar_terminos(
    valores,
) -> list[dict[str, str]]:
    """
    Deduplica expresiones por su forma normalizada.

    Conserva la primera representación legible encontrada.
    """

    resultado = []
    vistos = set()

    for valor in valores:

        texto = texto_limpio(
            valor
        )

        normalizado = normalizar_texto(
            texto
        )

        if (
            not texto
            or not normalizado
            or normalizado in vistos
        ):
            continue

        vistos.add(
            normalizado
        )

        resultado.append(
            {
                "texto":
                    texto,

                "normalizado":
                    normalizado,
            }
        )

    return resultado