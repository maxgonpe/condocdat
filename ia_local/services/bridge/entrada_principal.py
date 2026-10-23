from __future__ import annotations

from ia_local.config.cardinalidad import (
    LIMITE_MUESTRA_PREDETERMINADO,
)


from typing import Any

from .respuesta_compacta import (
    consultar_respuesta_compacta,
)


VERSION = "IA-BRIDGE008-v1"



def consultar(
    pregunta: str,
    *,
    limite: int | None = LIMITE_MUESTRA_PREDETERMINADO,
    diagnostico: bool = False,
) -> dict[str, Any]:
    """
    Punto público oficial del nuevo pipeline IA.

    Flujo:

        lenguaje natural
        → SEM
        → BRIDGE
        → HOST
        → ORM
        → respuesta compacta

    Este módulo oculta a consumidores externos
    la estructura interna de BRIDGE001-007.

    Las vistas, APIs y futuras integraciones deberían
    utilizar esta función en lugar de importar
    directamente componentes internos del pipeline.
    """

    if pregunta is None:

        return {
            "ok":
                False,

            "version":
                VERSION,

            "ejecutado":
                False,

            "estado":
                "pregunta_vacia",

            "mensaje":
                "La pregunta está vacía.",
        }

    pregunta = str(
        pregunta
    ).strip()

    if not pregunta:

        return {
            "ok":
                False,

            "version":
                VERSION,

            "ejecutado":
                False,

            "estado":
                "pregunta_vacia",

            "mensaje":
                "La pregunta está vacía.",
        }

    resultado = (
        consultar_respuesta_compacta(
            pregunta,
            limite=limite,
            incluir_diagnostico=diagnostico,
        )
    )

    if not isinstance(
        resultado,
        dict,
    ):

        return {
            "ok":
                False,

            "version":
                VERSION,

            "pregunta":
                pregunta,

            "ejecutado":
                False,

            "estado":
                "resultado_invalido",

            "mensaje":
                (
                    "El pipeline no devolvió "
                    "una respuesta estructurada."
                ),
        }

    # --------------------------------------------------------
    # Conservamos el contrato público BRIDGE005,
    # pero identificamos que la entrada oficial ya es
    # BRIDGE008.
    # --------------------------------------------------------

    return {
        **resultado,

        "entrada_version":
            VERSION,
    }