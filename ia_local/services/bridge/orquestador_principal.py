from __future__ import annotations

from ia_local.config.cardinalidad import LIMITE_MUESTRA_PREDETERMINADO

from typing import Any

from .entrada_principal import (
    consultar,
)


VERSION = "IA-BRIDGE009-v1"


# ============================================================
# ESTADOS QUE NUNCA PERMITEN FALLBACK
# ============================================================

ESTADOS_BLOQUEO_SEGURIDAD = {
    "rechazado_por_host",
    "plan_no_certificado",
    "plan_inconsistente",
    "validacion_host_ausente",
    "plan_host_ausente",
    "plan_validacion_ausente",
    "ejecucion_rechazada",
    "ejecucion_no_confirmada",
    "resultado_ejecucion_invalido",
    "limite_invalido",
    "pregunta_vacia",
    "error_interno",
}


# ============================================================
# ESTADOS SEMÁNTICOS POTENCIALMENTE RECUPERABLES
# ============================================================

ESTADOS_FALLBACK_ELEGIBLE = {
    "sem_no_resuelto",
    "sem_resuelto_sin_plan_completo",
    "entidad_no_resuelta",
    "entidad_no_resuelto",
    "campo_no_resuelto",
    "operador_no_resuelto",
    "operacion_no_resuelta",
    "operacion_no_resuelto",
}


# ============================================================
# ESTADOS QUE DELIBERADAMENTE NO SON RECUPERABLES
# ============================================================

ESTADOS_NO_FALLBACK = {
    "sem_ambiguo",
    "ambiguo",
    "valor_libre_vacio",
    "campo_sin_valor",
    "no_ejecutado",
}


def _estado_bridge(
    resultado: dict[str, Any],
) -> str | None:

    estado_bridge = resultado.get(
        "estado_bridge"
    )

    if estado_bridge:
        return str(
            estado_bridge
        )

    diagnostico = resultado.get(
        "diagnostico"
    )

    if isinstance(
        diagnostico,
        dict,
    ):

        bridge = diagnostico.get(
            "bridge"
        )

        if isinstance(
            bridge,
            dict,
        ):

            estado = bridge.get(
                "estado"
            )

            if estado:
                return str(
                    estado
                )

    return None


def clasificar_fallo_bridge(
    resultado: dict[str, Any],
) -> dict[str, Any]:
    """
    Clasifica una salida fallida del nuevo pipeline.

    La clasificación es fail-closed:

    un estado desconocido NO habilita fallback.
    """

    if not isinstance(
        resultado,
        dict,
    ):

        return {
            "fallback_elegible":
                False,

            "clasificacion":
                "resultado_invalido",

            "estado_bridge":
                None,

            "razon":
                (
                    "No existe una salida BRIDGE "
                    "estructurada."
                ),
        }

    estado = _estado_bridge(
        resultado
    )

    estado_general = resultado.get(
        "estado"
    )

    # --------------------------------------------------------
    # BLOQUEO DE SEGURIDAD
    # --------------------------------------------------------

    if (
        estado
        in ESTADOS_BLOQUEO_SEGURIDAD
        or
        estado_general
        in ESTADOS_BLOQUEO_SEGURIDAD
    ):

        return {
            "fallback_elegible":
                False,

            "clasificacion":
                "rechazo_seguridad",

            "estado_bridge":
                estado,

            "razon":
                (
                    "El nuevo pipeline rechazó la consulta "
                    "por una condición de seguridad o "
                    "validación HOST. El fallback está "
                    "prohibido."
                ),
        }

    # --------------------------------------------------------
    # CAPACIDAD SEMÁNTICA INSUFICIENTE
    # --------------------------------------------------------

    if estado in ESTADOS_FALLBACK_ELEGIBLE:

        return {
            "fallback_elegible":
                True,

            "clasificacion":
                "capacidad_semantica_insuficiente",

            "estado_bridge":
                estado,

            "razon":
                (
                    "El nuevo pipeline no pudo resolver "
                    "semánticamente la consulta, pero no "
                    "existió un rechazo HOST."
                ),
        }

    # --------------------------------------------------------
    # AMBIGÜEDAD / CONSULTA INCOMPLETA
    # --------------------------------------------------------

    if (
        estado
        in ESTADOS_NO_FALLBACK
    ):

        return {
            "fallback_elegible":
                False,

            "clasificacion":
                "consulta_ambigua_o_incompleta",

            "estado_bridge":
                estado,

            "razon":
                (
                    "La consulta es ambigua o incompleta. "
                    "No se permite intentar otro motor "
                    "para adivinar la intención."
                ),
        }

    # --------------------------------------------------------
    # DESCONOCIDO = FAIL CLOSED
    # --------------------------------------------------------

    return {
        "fallback_elegible":
            False,

        "clasificacion":
            "estado_no_clasificado",

        "estado_bridge":
            estado,

        "razon":
            (
                "El estado de fallo no está autorizado "
                "explícitamente para fallback."
            ),
    }


def consultar_orquestado(
    pregunta: str,
    *,
    limite: int = LIMITE_MUESTRA_PREDETERMINADO,
    diagnostico: bool = False,
    permitir_fallback_legado: bool = False,
) -> dict[str, Any]:
    """
    IA-BRIDGE009.

    Punto superior de consulta.

    Política:

        BRIDGE resuelve
            → devolver BRIDGE.

        BRIDGE rechaza por seguridad
            → detener.

        BRIDGE no comprende semánticamente
            → fallback sólo si fue habilitado
              explícitamente.

    El fallback legado está DESACTIVADO por defecto.
    """

    resultado_bridge = consultar(
        pregunta,
        limite=limite,
        diagnostico=diagnostico,
    )

    # ========================================================
    # BRIDGE RESOLVIÓ
    # ========================================================

    if (
        isinstance(
            resultado_bridge,
            dict,
        )
        and resultado_bridge.get(
            "ok",
            False,
        )
    ):

        return {
            **resultado_bridge,

            "orquestador_version":
                VERSION,

            "motor_usado":
                "bridge",

            "fallback_elegible":
                False,

            "fallback_habilitado":
                permitir_fallback_legado,

            "fallback_usado":
                False,

            "motivo_fallback":
                None,
        }

    # ========================================================
    # CLASIFICAR EL FALLO
    # ========================================================

    clasificacion = clasificar_fallo_bridge(
        resultado_bridge
    )

    fallback_elegible = bool(
        clasificacion.get(
            "fallback_elegible",
            False,
        )
    )

    # ========================================================
    # FALLBACK PROHIBIDO
    # ========================================================

    if not fallback_elegible:

        return {
            **resultado_bridge,

            "orquestador_version":
                VERSION,

            "motor_usado":
                "bridge",

            "fallback_elegible":
                False,

            "fallback_habilitado":
                permitir_fallback_legado,

            "fallback_usado":
                False,

            "motivo_fallback":
                clasificacion.get(
                    "clasificacion"
                ),

            "clasificacion_fallo":
                clasificacion,
        }

    # ========================================================
    # FALLBACK ELEGIBLE PERO DESACTIVADO
    # ========================================================

    if not permitir_fallback_legado:

        return {
            **resultado_bridge,

            "orquestador_version":
                VERSION,

            "motor_usado":
                "bridge",

            "fallback_elegible":
                True,

            "fallback_habilitado":
                False,

            "fallback_usado":
                False,

            "motivo_fallback":
                clasificacion.get(
                    "clasificacion"
                ),

            "clasificacion_fallo":
                clasificacion,

            "mensaje_fallback":
                (
                    "La consulta es elegible para fallback "
                    "legado, pero el fallback está "
                    "desactivado."
                ),
        }



    # ========================================================
    # FALLBACK EXPLÍCITAMENTE HABILITADO
    # ========================================================

    try:

        from .fallback_legado import (
            ejecutar_fallback_legado,
        )

        resultado_legado = (
            ejecutar_fallback_legado(
                pregunta,
                limite=limite,
            )
        )

    except Exception as exc:

        return {
            **resultado_bridge,

            "orquestador_version":
                VERSION,

            "motor_usado":
                "bridge",

            "fallback_elegible":
                True,

            "fallback_habilitado":
                True,

            "fallback_intentado":
                True,

            "fallback_usado":
                False,

            "fallback_ok":
                False,

            "motivo_fallback":
                clasificacion.get(
                    "clasificacion"
                ),

            "clasificacion_fallo":
                clasificacion,

            "error_fallback":
                str(
                    exc
                ),

            "mensaje_fallback":
                (
                    "El fallback fue autorizado, "
                    "pero ocurrió un error al intentar "
                    "resolver su proveedor."
                ),
        }


    if not isinstance(
        resultado_legado,
        dict,
    ):

        return {
            **resultado_bridge,

            "orquestador_version":
                VERSION,

            "motor_usado":
                "bridge",

            "fallback_elegible":
                True,

            "fallback_habilitado":
                True,

            "fallback_intentado":
                True,

            "fallback_usado":
                False,

            "fallback_ok":
                False,

            "motivo_fallback":
                clasificacion.get(
                    "clasificacion"
                ),

            "clasificacion_fallo":
                clasificacion,

            "mensaje_fallback":
                (
                    "El proveedor de fallback devolvió "
                    "un resultado inválido."
                ),
        }


    if not resultado_legado.get(
        "ok",
        False,
    ):

        return {
            **resultado_bridge,

            "orquestador_version":
                VERSION,

            "motor_usado":
                "bridge",

            "fallback_elegible":
                True,

            "fallback_habilitado":
                True,

            "fallback_intentado":
                True,

            "fallback_usado":
                False,

            "fallback_ok":
                False,

            "motivo_fallback":
                clasificacion.get(
                    "clasificacion"
                ),

            "clasificacion_fallo":
                clasificacion,

            "estado_fallback":
                resultado_legado.get(
                    "estado"
                ),

            "mensaje_fallback":
                resultado_legado.get(
                    "mensaje"
                ),

            "fallback":
                (
                    resultado_legado
                    if diagnostico
                    else None
                ),
        }


    # ========================================================
    # FALLBACK REALMENTE EJECUTADO CON ÉXITO
    # ========================================================

    return {
        **resultado_legado,

        "orquestador_version":
            VERSION,

        "entrada_version":
            resultado_bridge.get(
                "entrada_version"
            ),

        "motor_usado":
            "legado",

        "fallback_elegible":
            True,

        "fallback_habilitado":
            True,

        "fallback_intentado":
            True,

        "fallback_usado":
            True,

        "fallback_ok":
            True,

        "motivo_fallback":
            clasificacion.get(
                "clasificacion"
            ),

        "clasificacion_fallo":
            clasificacion,

        "bridge_original":
            (
                resultado_bridge
                if diagnostico
                else None
            ),
    }