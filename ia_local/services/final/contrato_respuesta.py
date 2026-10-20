from __future__ import annotations

from typing import Any

from ia_local.services.final.orquestador_consultas import (
    resolver_consulta,
)


# ============================================================
# IA-FINAL002
# CONTRATO ÚNICO DE RESPUESTA
# ============================================================
#
# Responsabilidad:
#
#   normalizar la salida heterogénea de BRIDGE / QUERY
#   en un único contrato consumible por:
#
#   - FINAL003;
#   - vistas Django;
#   - API JSON;
#   - templates;
#   - diagnóstico.
#
# FINAL002:
#
#   - NO ejecuta ORM;
#   - NO ejecuta SQL;
#   - NO usa LLM;
#   - NO modifica datos;
#   - NO reinterpreta la pregunta;
#   - NO reemplaza HOST.
#
# ============================================================


VERSION = "IA-FINAL002-v1"


def _texto(
    valor: Any,
) -> str:

    return str(
        valor or ""
    ).strip()


def _modelo_desde_resultado(
    resultado: dict[str, Any],
) -> str | None:

    modelo = resultado.get(
        "modelo"
    )

    if isinstance(
        modelo,
        str,
    ) and modelo:

        return modelo

    modelo_origen = resultado.get(
        "modelo_origen"
    )

    if isinstance(
        modelo_origen,
        str,
    ) and modelo_origen:

        return modelo_origen

    plan = resultado.get(
        "plan"
    )

    if isinstance(
        plan,
        dict,
    ):

        modelo = plan.get(
            "modelo"
        )

        if isinstance(
            modelo,
            str,
        ) and modelo:

            return modelo

    plan_host = resultado.get(
        "plan_host"
    )

    if isinstance(
        plan_host,
        dict,
    ):

        modelo = plan_host.get(
            "modelo"
        )

        if isinstance(
            modelo,
            str,
        ) and modelo:

            return modelo

    contrato = resultado.get(
        "contrato_logico"
    )

    if isinstance(
        contrato,
        dict,
    ):

        modelo = contrato.get(
            "modelo"
        )

        if isinstance(
            modelo,
            str,
        ) and modelo:

            return modelo

    plan_unificado = resultado.get(
        "plan_unificado"
    )

    if isinstance(
        plan_unificado,
        dict,
    ):

        modelo_base = plan_unificado.get(
            "modelo_base"
        )

        if isinstance(
            modelo_base,
            dict,
        ):

            label = modelo_base.get(
                "label"
            )

            if isinstance(
                label,
                str,
            ) and label:

                return label

    return None


def _clasificar_contrato(
    *,
    intencion: str,
    resultado: dict[str, Any],
    final001: dict[str, Any],
) -> tuple[
    str,
    dict[str, Any] | None,
]:

    # --------------------------------------------------------
    # PLAN HOST ORDINARIO
    # --------------------------------------------------------

    if final001.get(
        "tipo_plan"
    ) in {
        "plan",
        "plan_host",
        "validacion_host.plan",
    }:

        plan = final001.get(
            "plan_ejecutable"
        )

        if isinstance(
            plan,
            dict,
        ):

            return (
                "plan_host",
                plan,
            )

    # --------------------------------------------------------
    # PLAN UNIFICADO HOST033
    # --------------------------------------------------------

    if (
        final001.get(
            "tipo_plan"
        )
        == "plan_unificado"
    ):

        plan = final001.get(
            "plan_ejecutable"
        )

        if isinstance(
            plan,
            dict,
        ):

            return (
                "plan_unificado",
                plan,
            )

    # --------------------------------------------------------
    # QUERY002 / QUERY003
    # --------------------------------------------------------

    contrato_logico = resultado.get(
        "contrato_logico"
    )

    if isinstance(
        contrato_logico,
        dict,
    ):

        if intencion == "condiciones_or":

            return (
                "contrato_logico_or",
                contrato_logico,
            )

        if intencion == "grupo_logico":

            return (
                "arbol_logico",
                contrato_logico,
            )

    # --------------------------------------------------------
    # QUERY007
    # --------------------------------------------------------

    if intencion == "relacion":

        return (
            "ruta_relacional",
            {
                "modelo_origen":
                    resultado.get(
                        "modelo_origen"
                    ),

                "modelo_destino":
                    resultado.get(
                        "modelo_destino"
                    ),

                "ruta_orm":
                    resultado.get(
                        "ruta_orm"
                    ),

                "profundidad":
                    resultado.get(
                        "profundidad"
                    ),

                "contiene_relacion_multiple":
                    resultado.get(
                        "contiene_relacion_multiple"
                    ),
            },
        )

    # --------------------------------------------------------
    # QUERY008
    #
    # Conservamos la evidencia completa porque QUERY008
    # puede describir distintas representaciones:
    # relación multivaluada, serializada o estructura repetida.
    # --------------------------------------------------------

    if intencion == "coleccion":

        return (
            "coleccion",
            resultado,
        )

    # --------------------------------------------------------
    # QUERY009
    # --------------------------------------------------------

    if intencion == "agregacion":

        return (
            "agregacion",
            {
                "modelo":
                    resultado.get(
                        "modelo"
                    ),

                "operacion_semantica":
                    resultado.get(
                        "operacion_semantica"
                    ),

                "accion_plan":
                    resultado.get(
                        "accion_plan"
                    ),

                "objetivo_solicitado":
                    resultado.get(
                        "objetivo_solicitado"
                    ),

                "objetivo_host":
                    resultado.get(
                        "objetivo_host"
                    ),

                "operacion_host":
                    resultado.get(
                        "operacion_host"
                    ),
            },
        )

    # --------------------------------------------------------
    # QUERY010
    # --------------------------------------------------------

    if intencion == "agrupamiento":

        return (
            "agrupamiento",
            {
                "modelo":
                    resultado.get(
                        "modelo"
                    ),

                "grupo_solicitado":
                    resultado.get(
                        "grupo_solicitado"
                    ),

                "campo_agrupacion":
                    resultado.get(
                        "campo_agrupacion"
                    ),

                "objetivo_solicitado":
                    resultado.get(
                        "objetivo_solicitado"
                    ),

                "objetivo_agregado":
                    resultado.get(
                        "objetivo_agregado"
                    ),

                "operacion_semantica":
                    resultado.get(
                        "operacion_semantica"
                    ),

                "accion_plan":
                    resultado.get(
                        "accion_plan"
                    ),

                "agrupamiento_host":
                    resultado.get(
                        "agrupamiento_host"
                    ),
            },
        )

    return (
        "interpretacion",
        resultado,
    )


def _ejecutor_sugerido(
    *,
    tipo_contrato: str,
    contrato: dict[str, Any] | None,
) -> str | None:

    if tipo_contrato == "plan_host":

        return "ejecutor_datos"

    if tipo_contrato == "plan_unificado":

        return "orquestador_plan_unificado"

    if tipo_contrato == "ruta_relacional":

        return None

    if tipo_contrato == "coleccion":

        return None

    if tipo_contrato == "agregacion":

        # HOST certifica actualmente la operación,
        # pero todavía no existe un ejecutor general
        # de agregaciones en la capa HOST.
        return None

    if tipo_contrato == "agrupamiento":

        if isinstance(
            contrato,
            dict,
        ):

            agrupamiento_host = contrato.get(
                "agrupamiento_host"
            )

            if isinstance(
                agrupamiento_host,
                dict,
            ):

                sugerido = (
                    agrupamiento_host.get(
                        "ejecutor_sugerido"
                    )
                )

                if isinstance(
                    sugerido,
                    str,
                ) and sugerido:

                    return sugerido

        return None

    # OR y árboles lógicos todavía no tienen
    # ejecutor HOST específico.
    return None


def construir_contrato_respuesta(
    pregunta: str,
) -> dict[str, Any]:

    pregunta = _texto(
        pregunta
    )

    final001 = resolver_consulta(
        pregunta
    )

    if not final001.get(
        "ok"
    ):

        return {
            "ok": False,
            "version": VERSION,

            "estado":
                "consulta_no_normalizada",

            "pregunta":
                pregunta,

            "resuelto":
                False,

            "intencion":
                final001.get(
                    "intencion"
                ),

            "componente":
                final001.get(
                    "componente"
                ),

            "modelo":
                None,

            "tipo_contrato":
                None,

            "contrato":
                None,

            "ejecutable":
                False,

            "ejecutor_sugerido":
                None,

            "resultado":
                None,

            "respuesta":
                None,

            "diagnostico": {
                "final001":
                    final001,
            },

            "ejecutado":
                False,

            "llm_invocado":
                False,
        }

    resultado = final001.get(
        "resultado_interpretacion"
    )

    if not isinstance(
        resultado,
        dict,
    ):

        resultado = {}

    intencion = _texto(
        final001.get(
            "intencion"
        )
    )

    (
        tipo_contrato,
        contrato,
    ) = _clasificar_contrato(
        intencion=intencion,
        resultado=resultado,
        final001=final001,
    )

    modelo = _modelo_desde_resultado(
        resultado
    )

    ejecutor = _ejecutor_sugerido(
        tipo_contrato=tipo_contrato,
        contrato=contrato,
    )

    # --------------------------------------------------------
    # IMPORTANTE
    #
    # "ejecutable" significa:
    # existe hoy un ejecutor HOST real que FINAL003
    # podrá invocar de forma controlada.
    #
    # No basta con que una QUERY esté semánticamente validada.
    # --------------------------------------------------------

    ejecutable = (
        ejecutor
        in {
            "ejecutor_datos",
            "orquestador_plan_unificado",
        }
    )

    return {
        "ok": True,
        "version": VERSION,

        "estado":
            "contrato_normalizado",

        "pregunta":
            pregunta,

        "resuelto":
            True,

        "intencion":
            intencion,

        "componente":
            final001.get(
                "componente"
            ),

        "componente_version":
            final001.get(
                "componente_version"
            ),

        "modelo":
            modelo,

        "tipo_contrato":
            tipo_contrato,

        "contrato":
            contrato,

        "ejecutable":
            ejecutable,

        "ejecutor_sugerido":
            ejecutor,

        "resultado":
            None,

        "respuesta":
            None,

        "diagnostico": {
            "final001_version":
                final001.get(
                    "version"
                ),

            "final001_estado":
                final001.get(
                    "estado"
                ),

            "intentos":
                final001.get(
                    "intentos",
                    [],
                ),

            "interpretacion":
                resultado,
        },

        "ejecutado":
            False,

        "llm_invocado":
            False,

        "razon": (
            "FINAL002 normalizó la interpretación "
            "sin ejecutar ORM."
        ),
    }