from __future__ import annotations

from ia_local.config.cardinalidad import (
    LIMITE_MUESTRA_PREDETERMINADO,
)


from typing import Any

from ia_local.services.host.ejecutor_datos import (
    ejecutar_plan_datos,
)

from .campo_operador_valor import (
    componer_campo_operador_valor,
)


VERSION = "IA-BRIDGE004-v1"



# ============================================================
# VERIFICACIÓN DEL CONTRATO PREVIO
# ============================================================


def _verificar_plan_certificado(
    resultado_bridge: dict[str, Any],
) -> dict[str, Any]:
    """
    Comprueba que BRIDGE003 realmente haya terminado con
    un plan HOST validado.

    Esta función NO valida estructura Django.
    Esa responsabilidad sigue perteneciendo a HOST.

    Solamente impide que BRIDGE004 ejecute una salida
    incompleta, fallida o no certificada.
    """

    if not isinstance(
        resultado_bridge,
        dict,
    ):

        return {
            "ok":
                False,

            "estado":
                "resultado_bridge_invalido",

            "razon":
                (
                    "BRIDGE003 no entregó un "
                    "resultado estructurado."
                ),
        }

    if not resultado_bridge.get(
        "ok",
        False,
    ):

        return {
            "ok":
                False,

            "estado":
                "bridge_no_resuelto",

            "razon":
                (
                    "BRIDGE003 no pudo construir "
                    "un plan ejecutable."
                ),
        }

    if (
        resultado_bridge.get(
            "estado"
        )
        != "plan_host_validado"
    ):

        return {
            "ok":
                False,

            "estado":
                "estado_bridge_no_ejecutable",

            "estado_bridge":
                resultado_bridge.get(
                    "estado"
                ),

            "razon":
                (
                    "La salida BRIDGE no está marcada "
                    "como plan HOST validado."
                ),
        }

    validacion_host = resultado_bridge.get(
        "validacion_host"
    )

    if not isinstance(
        validacion_host,
        dict,
    ):

        return {
            "ok":
                False,

            "estado":
                "validacion_host_ausente",

            "razon":
                (
                    "No existe evidencia estructurada "
                    "de validación HOST."
                ),
        }

    if not validacion_host.get(
        "plan_validado",
        False,
    ):

        return {
            "ok":
                False,

            "estado":
                "plan_no_certificado",

            "razon":
                (
                    "HOST no certificó el plan."
                ),
        }

    plan_host = resultado_bridge.get(
        "plan_host"
    )

    if not isinstance(
        plan_host,
        dict,
    ):

        return {
            "ok":
                False,

            "estado":
                "plan_host_ausente",

            "razon":
                (
                    "BRIDGE003 indicó éxito pero "
                    "no entregó un plan_host."
                ),
        }

    # --------------------------------------------------------
    # CONSISTENCIA BÁSICA
    # --------------------------------------------------------

    plan_validacion = validacion_host.get(
        "plan"
    )

    if not isinstance(
        plan_validacion,
        dict,
    ):

        return {
            "ok":
                False,

            "estado":
                "plan_validacion_ausente",

            "razon":
                (
                    "La validación HOST no contiene "
                    "el plan certificado."
                ),
        }

    # No exigimos igualdad completa mediante == como regla
    # arquitectónica futura, pero sí comprobamos las piezas
    # críticas que identifican la consulta.

    for clave in (
        "modelo",
        "operacion",
        "filtros",
        "orden",
        "limite",
    ):

        if (
            plan_host.get(
                clave
            )
            != plan_validacion.get(
                clave
            )
        ):

            return {
                "ok":
                    False,

                "estado":
                    "plan_inconsistente",

                "clave":
                    clave,

                "razon":
                    (
                        "El plan_host y el plan certificado "
                        "por HOST no coinciden."
                    ),
            }

    return {
        "ok":
            True,

        "estado":
            "plan_certificado",

        "plan":
            plan_host,
    }


# ============================================================
# EJECUCIÓN CONTROLADA
# ============================================================


def ejecutar_consulta_bridge(
    expresion: str,
    *,
    limite: int | None = LIMITE_MUESTRA_PREDETERMINADO,
) -> dict[str, Any]:
    """
    IA-BRIDGE004.

    Flujo:

        lenguaje natural
        → BRIDGE003
        → plan HOST validado
        → verificación BRIDGE004
        → ejecutar_plan_datos()
        → segunda validación HOST
        → ORM

    BRIDGE004 nunca ejecuta una propuesta cruda.
    """

    base = {
        "ok":
            False,

        "version":
            VERSION,

        "expresion":
            expresion,

        "llm_invocado":
            False,

        "ejecutado":
            False,

        "bridge":
            None,

        "certificacion":
            None,

        "ejecucion":
            None,
    }

    # ========================================================
    # 1. CONSTRUIR Y VALIDAR MEDIANTE BRIDGE003
    # ========================================================

    resultado_bridge = (
        componer_campo_operador_valor(
            expresion,
            limite=limite,
        )
    )

    base[
        "bridge"
    ] = resultado_bridge

    # ========================================================
    # 2. VERIFICAR QUE EL PLAN ESTÁ CERTIFICADO
    # ========================================================

    certificacion = (
        _verificar_plan_certificado(
            resultado_bridge
        )
    )

    base[
        "certificacion"
    ] = certificacion

    if not certificacion.get(
        "ok",
        False,
    ):

        return {
            **base,

            "estado":
                "no_ejecutado",

            "razon":
                certificacion.get(
                    "razon",
                    (
                        "El plan no superó la "
                        "certificación previa."
                    ),
                ),
        }

    plan_certificado = certificacion[
        "plan"
    ]

    # ========================================================
    # 3. EJECUTOR HOST
    # ========================================================
    #
    # ejecutar_plan_datos() vuelve a ejecutar
    # validar_plan_datos() internamente.
    #
    # Por tanto:
    #
    #   BRIDGE003 valida
    #       +
    #   BRIDGE004 verifica
    #       +
    #   HOST revalida
    #       =
    #   ORM
    #
    # ========================================================

    ejecucion = ejecutar_plan_datos(
        plan_certificado
    )

    base[
        "ejecucion"
    ] = ejecucion

    if not isinstance(
        ejecucion,
        dict,
    ):

        return {
            **base,

            "estado":
                "resultado_ejecucion_invalido",

            "razon":
                (
                    "HOST no devolvió un resultado "
                    "estructurado de ejecución."
                ),
        }

    if not ejecucion.get(
        "ok",
        False,
    ):

        return {
            **base,

            "estado":
                "ejecucion_rechazada",

            "razon":
                (
                    "El ejecutor HOST rechazó o no pudo "
                    "completar el plan."
                ),
        }

    if not ejecucion.get(
        "ejecutado",
        False,
    ):

        return {
            **base,

            "estado":
                "ejecucion_no_confirmada",

            "razon":
                (
                    "HOST respondió sin confirmar "
                    "ejecución ORM."
                ),
        }

    # ========================================================
    # 4. RESULTADO
    # ========================================================

    return {
        **base,

        "ok":
            True,

        "ejecutado":
            True,

        "estado":
            "ejecutado_controlado",

        "operacion":
            ejecucion.get(
                "operacion"
            ),

        "modelo":
            ejecucion.get(
                "modelo"
            ),

        "razon":
            (
                "El plan certificado fue revalidado "
                "y ejecutado por HOST mediante ORM."
            ),
    }