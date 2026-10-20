from __future__ import annotations

from typing import Any


VERSION = "IA-FINAL009-v1"


def _texto(
    valor: Any,
) -> str:

    return str(
        valor
        or ""
    ).strip()


def aplicar_politica_respuesta(
    *,
    pregunta: str,
    respuesta: dict[str, Any],
) -> dict[str, Any]:
    """
    IA-FINAL009

    Clasifica la respuesta FINAL004 sin reinterpretar
    la consulta.

    NO:
    - ejecuta ORM;
    - llama LLM;
    - modifica contratos;
    - inventa intención;
    - crea propuestas SEM;
    - convierte ambigüedad en conocimiento.
    """

    pregunta = _texto(
        pregunta
    )

    if not isinstance(
        respuesta,
        dict,
    ):

        return {
            "ok": False,
            "version": VERSION,
            "estado": "respuesta_invalida",
            "clasificacion": "error_interno",
            "respuesta":
                "No fue posible obtener una respuesta válida.",
            "requiere_aclaracion": False,
            "revision_semantica": False,
            "ejecutado": False,
            "llm_invocado": False,
        }

    salida = dict(
        respuesta
    )

    salida[
        "version_politica"
    ] = VERSION

    diagnostico = respuesta.get(
        "diagnostico"
    )

    if not isinstance(
        diagnostico,
        dict,
    ):

        diagnostico = {}

    final003 = diagnostico.get(
        "final003"
    )

    if not isinstance(
        final003,
        dict,
    ):

        final003 = {}

    estado_final003 = _texto(
        final003.get(
            "estado"
        )
    )

    # --------------------------------------------------------
    # CONSULTA VACÍA / INCOMPLETA
    # --------------------------------------------------------

    if (
        not pregunta
        or estado_final003 == "pregunta_vacia"
    ):

        salida[
            "clasificacion"
        ] = "consulta_incompleta"

        salida[
            "respuesta"
        ] = (
            "La consulta está incompleta. "
            "Indica qué información deseas consultar."
        )

        salida[
            "requiere_aclaracion"
        ] = True

        salida[
            "revision_semantica"
        ] = False

        return salida

    # --------------------------------------------------------
    # CAPACIDAD CONOCIDA PERO NO EJECUTABLE
    # --------------------------------------------------------

    if (
        estado_final003
        == "contrato_no_ejecutable"
        or respuesta.get(
            "estado"
        )
        == "respuesta_no_ejecutable"
    ):

        salida[
            "clasificacion"
        ] = "capacidad_no_ejecutable"

        salida[
            "requiere_aclaracion"
        ] = False

        salida[
            "revision_semantica"
        ] = False

        return salida

    # --------------------------------------------------------
    # CONSULTA NO RESUELTA
    # --------------------------------------------------------

    if (
        estado_final003
        == "contrato_no_disponible"
    ):

        salida[
            "clasificacion"
        ] = "consulta_no_resuelta"

        salida[
            "respuesta"
        ] = (
            "No pude determinar con suficiente seguridad "
            "qué deseas consultar. Reformula la consulta "
            "indicando la entidad, operación o condición."
        )

        salida[
            "requiere_aclaracion"
        ] = True

        # Una consulta no resuelta NO implica por sí sola
        # una carencia semántica.
        salida[
            "revision_semantica"
        ] = False

        return salida

    # --------------------------------------------------------
    # EJECUCIÓN CORRECTA
    # --------------------------------------------------------

    if (
        respuesta.get(
            "ok"
        )
        is True
        and respuesta.get(
            "ejecutado"
        )
        is True
    ):

        salida[
            "clasificacion"
        ] = "resuelta_ejecutada"

        salida[
            "requiere_aclaracion"
        ] = False

        salida[
            "revision_semantica"
        ] = False

        return salida

    # --------------------------------------------------------
    # OTRO ERROR CONTROLADO
    # --------------------------------------------------------

    salida[
        "clasificacion"
    ] = "error_controlado"

    salida[
        "requiere_aclaracion"
    ] = False

    salida[
        "revision_semantica"
    ] = False

    return salida