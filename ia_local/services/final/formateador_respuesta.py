from __future__ import annotations

from typing import Any

from ia_local.services.final.ejecutor_consultas import (
    ejecutar_consulta,
)


# ============================================================
# IA-FINAL004
# FORMATEADOR DE RESPUESTA PÚBLICA
# ============================================================
#
# Responsabilidad:
#
#   convertir la salida técnica de FINAL003/HOST en una
#   respuesta simple y estable para:
#
#   - views_bridge.py
#   - JsonResponse
#   - index.html
#   - futuras interfaces
#
# FINAL004:
#
#   - NO ejecuta ORM;
#   - NO interpreta nuevamente la consulta;
#   - NO usa LLM;
#   - NO modifica contratos HOST;
#   - sólo presenta resultados ya ejecutados/certificados.
#
# ============================================================


VERSION = "IA-FINAL004-v1"


def _texto(
    valor: Any,
) -> str:

    return str(
        valor or ""
    ).strip()


def _nombre_modelo(
    label: str | None,
) -> str:

    label = _texto(
        label
    )

    if not label:

        return "registros"

    if "." in label:

        label = label.split(
            "."
        )[-1]

    return label


def _respuesta_lista(
    resultado_host: dict[str, Any],
    *,
    modelo: str | None,
) -> dict[str, Any]:

    total = resultado_host.get(
        "total_devuelto",
        0,
    )

    registros = resultado_host.get(
        "resultados",
        [],
    )

    campos = resultado_host.get(
        "campos",
        [],
    )

    if not isinstance(
        total,
        int,
    ):

        total = 0

    if not isinstance(
        registros,
        list,
    ):

        registros = []

    if not isinstance(
        campos,
        list,
    ):

        campos = []

    nombre = _nombre_modelo(
        modelo
    )

    if total == 0:

        mensaje = (
            f"No se encontraron registros "
            f"de {nombre} para la consulta."
        )

    elif total == 1:

        mensaje = (
            f"Se encontró 1 registro "
            f"de {nombre}."
        )

    else:

        mensaje = (
            f"Se encontraron {total} registros "
            f"de {nombre}."
        )

    return {
        "tipo":
            "lista",

        "respuesta":
            mensaje,

        "total":
            total,

        "registros":
            registros,

        "campos":
            campos,
    }


def _respuesta_conteo_relacional(
    resultado_host: dict[str, Any],
) -> dict[str, Any]:

    resultado_interno = resultado_host.get(
        "resultado"
    )

    if not isinstance(
        resultado_interno,
        dict,
    ):

        return {
            "tipo":
                "conteo",

            "respuesta":
                "No fue posible obtener el conteo.",

            "total":
                None,

            "registros":
                [],

            "campos":
                [],
        }

    total = resultado_interno.get(
        "total"
    )

    registros_origen = (
        resultado_interno.get(
            "registros_origen"
        )
    )

    modelo_destino = _nombre_modelo(
        resultado_interno.get(
            "modelo_destino"
        )
    )

    if isinstance(
        total,
        int,
    ):

        if total == 0:

            mensaje = (
                f"No se encontraron "
                f"{modelo_destino} relacionados."
            )

        elif total == 1:

            mensaje = (
                f"Se encontró 1 "
                f"{modelo_destino} relacionado."
            )

        else:

            mensaje = (
                f"Se encontraron {total} "
                f"{modelo_destino} relacionados."
            )

    else:

        mensaje = (
            "El conteo fue ejecutado, "
            "pero no devolvió un total válido."
        )

    return {
        "tipo":
            "conteo",

        "respuesta":
            mensaje,

        "total":
            total,

        "registros_origen":
            registros_origen,

        "registros":
            [],

        "campos":
            [],
    }


def _respuesta_no_ejecutable(
    ejecucion: dict[str, Any],
) -> dict[str, Any]:

    tipo_contrato = _texto(
        ejecucion.get(
            "tipo_contrato"
        )
    )

    return {
        "tipo":
            "no_ejecutable",

        "respuesta": (
            "La consulta fue entendida, "
            "pero esta capacidad todavía no "
            "dispone de ejecución habilitada."
        ),

        "total":
            None,

        "registros":
            [],

        "campos":
            [],

        "tipo_contrato":
            tipo_contrato or None,
    }


def _respuesta_error(
    ejecucion: dict[str, Any],
) -> dict[str, Any]:

    mensaje = _texto(
        ejecucion.get(
            "mensaje"
        )
    )

    if not mensaje:

        mensaje = (
            "No fue posible completar la consulta."
        )

    return {
        "tipo":
            "error",

        "respuesta":
            mensaje,

        "total":
            None,

        "registros":
            [],

        "campos":
            [],
    }


def responder_consulta(
    pregunta: str,
) -> dict[str, Any]:

    pregunta = _texto(
        pregunta
    )

    ejecucion = ejecutar_consulta(
        pregunta
    )

    # --------------------------------------------------------
    # CONSULTA ENTENDIDA PERO TODAVÍA NO EJECUTABLE
    # --------------------------------------------------------

    if (
        ejecucion.get(
            "estado"
        )
        == "contrato_no_ejecutable"
    ):

        publico = _respuesta_no_ejecutable(
            ejecucion
        )

        return {
            "ok": False,
            "version": VERSION,

            "estado":
                "respuesta_no_ejecutable",

            "pregunta":
                pregunta,

            "tipo":
                publico[
                    "tipo"
                ],

            "respuesta":
                publico[
                    "respuesta"
                ],

            "total":
                publico[
                    "total"
                ],

            "registros":
                publico[
                    "registros"
                ],

            "campos":
                publico[
                    "campos"
                ],

            "intencion":
                ejecucion.get(
                    "intencion"
                ),

            "modelo":
                ejecucion.get(
                    "modelo"
                ),

            "ejecutado":
                False,

            "llm_invocado":
                False,

            "diagnostico": {
                "final003":
                    ejecucion,
            },
        }

    # --------------------------------------------------------
    # ERROR / RECHAZO
    # --------------------------------------------------------

    if not ejecucion.get(
        "ok"
    ):

        publico = _respuesta_error(
            ejecucion
        )

        return {
            "ok": False,
            "version": VERSION,

            "estado":
                "respuesta_error",

            "pregunta":
                pregunta,

            "tipo":
                publico[
                    "tipo"
                ],

            "respuesta":
                publico[
                    "respuesta"
                ],

            "total":
                publico[
                    "total"
                ],

            "registros":
                publico[
                    "registros"
                ],

            "campos":
                publico[
                    "campos"
                ],

            "intencion":
                ejecucion.get(
                    "intencion"
                ),

            "modelo":
                ejecucion.get(
                    "modelo"
                ),

            "ejecutado":
                ejecucion.get(
                    "ejecutado",
                    False,
                ),

            "llm_invocado":
                False,

            "diagnostico": {
                "final003":
                    ejecucion,
            },
        }

    resultado_host = ejecucion.get(
        "resultado"
    )

    if not isinstance(
        resultado_host,
        dict,
    ):

        publico = _respuesta_error(
            {
                "mensaje":
                    "La ejecución no devolvió "
                    "un resultado HOST válido."
            }
        )

    # --------------------------------------------------------
    # PLAN HOST / LISTADO
    # --------------------------------------------------------

    elif (
        ejecucion.get(
            "tipo_contrato"
        )
        == "plan_host"
    ):

        publico = _respuesta_lista(
            resultado_host,
            modelo=ejecucion.get(
                "modelo"
            ),
        )

    # --------------------------------------------------------
    # PLAN UNIFICADO / RELACIÓN
    # --------------------------------------------------------

    elif (
        ejecucion.get(
            "tipo_contrato"
        )
        == "plan_unificado"
        and resultado_host.get(
            "estrategia"
        )
        == "relacion_orm"
    ):

        publico = (
            _respuesta_conteo_relacional(
                resultado_host
            )
        )

    else:

        publico = {
            "tipo":
                "resultado",

            "respuesta":
                "La consulta fue ejecutada correctamente.",

            "total":
                None,

            "registros":
                [],

            "campos":
                [],
        }

    return {
        "ok": True,
        "version": VERSION,

        "estado":
            "respuesta_formateada",

        "pregunta":
            pregunta,

        "tipo":
            publico.get(
                "tipo"
            ),

        "respuesta":
            publico.get(
                "respuesta"
            ),

        "total":
            publico.get(
                "total"
            ),

        "registros":
            publico.get(
                "registros",
                [],
            ),

        "campos":
            publico.get(
                "campos",
                [],
            ),

        "registros_origen":
            publico.get(
                "registros_origen"
            ),

        "intencion":
            ejecucion.get(
                "intencion"
            ),

        "modelo":
            ejecucion.get(
                "modelo"
            ),

        "componente":
            ejecucion.get(
                "componente"
            ),

        "tipo_contrato":
            ejecucion.get(
                "tipo_contrato"
            ),

        "ejecutor":
            ejecucion.get(
                "ejecutor"
            ),

        "ejecutado":
            ejecucion.get(
                "ejecutado",
                False,
            ),

        "llm_invocado":
            False,

        # ----------------------------------------------------
        # El frontend normal no necesita leer diagnóstico.
        # Se conserva para pruebas y pantalla de diagnóstico.
        # ----------------------------------------------------

        "diagnostico": {
            "final003":
                ejecucion,
        },
    }