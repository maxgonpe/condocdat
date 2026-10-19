from __future__ import annotations

from typing import Any

from .ejecutor_controlado import (
    ejecutar_consulta_bridge,
)


VERSION = "IA-BRIDGE005-v1"

LIMITE_PREDETERMINADO = 20


# ============================================================
# UTILIDADES
# ============================================================


def _respuesta_error(
    *,
    pregunta: str,
    resultado: dict[str, Any],
    incluir_diagnostico: bool,
) -> dict[str, Any]:

    respuesta = {
        "ok":
            False,

        "version":
            VERSION,

        "pregunta":
            pregunta,

        "ejecutado":
            False,

        "estado":
            resultado.get(
                "estado",
                "error",
            ),

        "mensaje":
            resultado.get(
                "razon",
                (
                    "La consulta no pudo "
                    "ejecutarse de forma segura."
                ),
            ),
    }

    bridge = resultado.get(
        "bridge"
    )

    if isinstance(
        bridge,
        dict,
    ):

        respuesta[
            "estado_bridge"
        ] = bridge.get(
            "estado"
        )

        validacion_host = bridge.get(
            "validacion_host"
        )

        if isinstance(
            validacion_host,
            dict,
        ):

            errores = validacion_host.get(
                "errores",
                [],
            )

            if errores:

                respuesta[
                    "errores"
                ] = errores

    if incluir_diagnostico:

        respuesta[
            "diagnostico"
        ] = resultado

    return respuesta


def _respuesta_conteo(
    *,
    pregunta: str,
    resultado: dict[str, Any],
    ejecucion: dict[str, Any],
    incluir_diagnostico: bool,
) -> dict[str, Any]:

    respuesta = {
        "ok":
            True,

        "version":
            VERSION,

        "pregunta":
            pregunta,

        "ejecutado":
            True,

        "tipo":
            "conteo",

        "modelo":
            ejecucion.get(
                "modelo"
            ),

        "total":
            ejecucion.get(
                "total",
                0,
            ),

        "filtros":
            ejecucion.get(
                "filtros",
                [],
            ),

        "mensaje":
            (
                f"Se encontraron "
                f"{ejecucion.get('total', 0)} "
                f"registro(s)."
            ),
    }

    if incluir_diagnostico:

        respuesta[
            "diagnostico"
        ] = resultado

    return respuesta


def _respuesta_lista(
    *,
    pregunta: str,
    resultado: dict[str, Any],
    ejecucion: dict[str, Any],
    incluir_diagnostico: bool,
) -> dict[str, Any]:

    resultados = ejecucion.get(
        "resultados",
        [],
    )

    if not isinstance(
        resultados,
        list,
    ):

        resultados = []

    respuesta = {
        "ok":
            True,

        "version":
            VERSION,

        "pregunta":
            pregunta,

        "ejecutado":
            True,

        "tipo":
            "lista",

        "modelo":
            ejecucion.get(
                "modelo"
            ),

        "total_devuelto":
            ejecucion.get(
                "total_devuelto",
                len(
                    resultados
                ),
            ),

        "limite":
            ejecucion.get(
                "limite"
            ),

        "campos":
            ejecucion.get(
                "campos",
                [],
            ),

        "resultados":
            resultados,

        "filtros":
            ejecucion.get(
                "filtros",
                [],
            ),

        "mensaje":
            (
                f"Se devolvieron "
                f"{ejecucion.get('total_devuelto', len(resultados))} "
                f"registro(s)."
            ),
    }

    if incluir_diagnostico:

        respuesta[
            "diagnostico"
        ] = resultado

    return respuesta


# ============================================================
# RESPUESTA PRINCIPAL
# ============================================================


def consultar_respuesta_compacta(
    pregunta: str,
    *,
    limite: int | None = LIMITE_PREDETERMINADO,
    incluir_diagnostico: bool = False,
) -> dict[str, Any]:
    """
    IA-BRIDGE005.

    Ejecuta el pipeline BRIDGE004 y transforma la salida
    técnica en un contrato compacto para API/interfaz.

    No interpreta datos.
    No ejecuta ORM directamente.
    No invoca LLM.
    """

    resultado = ejecutar_consulta_bridge(
        pregunta,
        limite=limite,
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
                    "un resultado estructurado."
                ),
        }

    if not resultado.get(
        "ok",
        False,
    ):

        return _respuesta_error(
            pregunta=pregunta,
            resultado=resultado,
            incluir_diagnostico=(
                incluir_diagnostico
            ),
        )

    if not resultado.get(
        "ejecutado",
        False,
    ):

        return _respuesta_error(
            pregunta=pregunta,
            resultado=resultado,
            incluir_diagnostico=(
                incluir_diagnostico
            ),
        )

    ejecucion = resultado.get(
        "ejecucion"
    )

    if not isinstance(
        ejecucion,
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
                "ejecucion_ausente",

            "mensaje":
                (
                    "El pipeline confirmó ejecución "
                    "pero no entregó el bloque de resultados."
                ),
        }

    operacion = ejecucion.get(
        "operacion"
    )

    if operacion == "contar":

        return _respuesta_conteo(
            pregunta=pregunta,
            resultado=resultado,
            ejecucion=ejecucion,
            incluir_diagnostico=(
                incluir_diagnostico
            ),
        )

    if operacion == "listar":

        return _respuesta_lista(
            pregunta=pregunta,
            resultado=resultado,
            ejecucion=ejecucion,
            incluir_diagnostico=(
                incluir_diagnostico
            ),
        )

    return {
        "ok":
            False,

        "version":
            VERSION,

        "pregunta":
            pregunta,

        "ejecutado":
            True,

        "estado":
            "operacion_no_soportada",

        "operacion":
            operacion,

        "mensaje":
            (
                "La ejecución finalizó, pero "
                "BRIDGE005 no reconoce el tipo "
                "de operación recibido."
            ),
    }