from __future__ import annotations

from typing import Any

from .router import (
    procesar_pregunta,
)

from ia_local.services.final.orquestador_consultas import (
    resolver_consulta,
)


# ============================================================
# UTILIDADES
# ============================================================


def _dict(
    valor: Any,
) -> dict[str, Any]:

    return (
        valor
        if isinstance(
            valor,
            dict,
        )
        else {}
    )


def _fase_actual(
    resultado: dict[str, Any],
) -> str:

    respuesta_estructurada = _dict(
        resultado.get(
            "respuesta_estructurada"
        )
    )

    fase = respuesta_estructurada.get(
        "fase"
    )

    if fase:
        return str(
            fase
        )

    if resultado.get(
        "ejecucion_datos"
    ):
        return "ejecucion"

    if resultado.get(
        "validacion_datos"
    ):
        return "validacion"

    if resultado.get(
        "interpretacion_datos"
    ):
        return "interpretacion"

    if resultado.get(
        "resultado_host"
    ):
        return "estructura"

    destino = resultado.get(
        "destino"
    )

    if destino == "ninguno":
        return "intencion"

    return "routing"


# ============================================================
# DIAGNÓSTICO
# ============================================================


def diagnosticar_pregunta(
    pregunta: str,
    *,
    profundidad: int = 3,
) -> dict[str, Any]:
    """
    HOST016-A.

    Ejecuta el pipeline público real de ia_local y organiza
    su resultado en un contrato de diagnóstico estable.

    No interpreta de nuevo.
    No ejecuta ORM adicional.
    No llama directamente a Qwen.
    No altera decisiones del router.
    """

    # --------------------------------------------------------
    # IA-LLM000
    # PREFLIGHT FINAL DETERMINISTA
    #
    # Sólo observa si FINAL001 puede interpretar la pregunta.
    # NO ejecuta ORM.
    # NO llama LLM.
    # --------------------------------------------------------

    final_previo = resolver_consulta(
        pregunta
    )

    resultado = procesar_pregunta(
        pregunta,
        profundidad=profundidad,
    )

    intencion = _dict(
        resultado.get(
            "intencion"
        )
    )

    resolucion_entidad = _dict(
        resultado.get(
            "resolucion_entidad_datos"
        )
    )

    

    if not resolucion_entidad:

        resolucion_entidad = _dict(
            intencion.get(
                "resolucion_entidad_datos"
            )
        )


    interpretacion = _dict(
        resultado.get(
            "interpretacion_datos"
        )
    )

    validacion = _dict(
        resultado.get(
            "validacion_datos"
        )
    )

    ejecucion = _dict(
        resultado.get(
            "ejecucion_datos"
        )
    )

    resultado_host = _dict(
        resultado.get(
            "resultado_host"
        )
    )

    respuesta_estructurada = _dict(
        resultado.get(
            "respuesta_estructurada"
        )
    )

    entidad_inicial = None

    determinista_previo = _dict(
        intencion.get(
            "determinista_previo"
        )
    )

    if determinista_previo:
        entidad_inicial = (
            determinista_previo.get(
                "entidad"
            )
        )

    if entidad_inicial is None:
        propuesta_llm = _dict(
            intencion.get(
                "propuesta_llm"
            )
        )

        entidad_inicial = (
            propuesta_llm.get(
                "entidad"
            )
        )

    entidad_final = intencion.get(
        "entidad"
    )

    estado = {
        "ok":
            bool(
                resultado.get(
                    "ok"
                )
            ),

        "fase":
            _fase_actual(
                resultado
            ),

        "bloqueado":
            not bool(
                resultado.get(
                    "ok"
                )
            ),

        "llm_invocado":
            bool(
                resultado.get(
                    "llm_invocado"
                )
                or intencion.get(
                    "llm_invocado"
                )
            ),
    }

    # --------------------------------------------------------
    # IA-LLM000
    # RESUMEN DE CANALIZACIÓN
    # --------------------------------------------------------

    intentos_final = final_previo.get(
        "intentos"
    )

    if not isinstance(
        intentos_final,
        list,
    ):
        intentos_final = []

    final_resuelto = bool(
        final_previo.get(
            "resuelto"
        )
    )

    llm_invocado = bool(
        estado.get(
            "llm_invocado"
        )
    )

    host_ok = bool(
        resultado.get(
            "ok"
        )
    )

    if final_resuelto:

        ruta_observada = (
            "final_determinista_resuelve"
        )

    elif (
        llm_invocado
        and host_ok
    ):

        ruta_observada = (
            "final_no_resuelve_host_llm_resuelve"
        )

    elif llm_invocado:

        ruta_observada = (
            "final_no_resuelve_host_llm_bloqueado"
        )

    elif host_ok:

        ruta_observada = (
            "final_no_resuelve_host_resuelve_sin_llm"
        )

    else:

        ruta_observada = (
            "final_no_resuelve_host_bloqueado"
        )

    diagnostico = {
        "pregunta":
            pregunta,

        "canalizacion": {
            "ruta_observada":
                ruta_observada,

            "final_resuelto":
                final_resuelto,

            "fallback_necesario":
                not final_resuelto,

            "llm_invocado":
                llm_invocado,

            "host_ok":
                host_ok,

            "fase_host":
                estado.get(
                    "fase"
                ),

            "ejecucion_realizada":
                bool(
                    ejecucion.get(
                        "ejecutado"
                    )
                ),
        },

        "final_determinista": {
            "ok":
                final_previo.get(
                    "ok"
                ),

            "version":
                final_previo.get(
                    "version"
                ),

            "estado":
                final_previo.get(
                    "estado"
                ),

            "resuelto":
                final_previo.get(
                    "resuelto"
                ),

            "intencion":
                final_previo.get(
                    "intencion"
                ),

            "componente":
                final_previo.get(
                    "componente"
                ),

            "componente_version":
                final_previo.get(
                    "componente_version"
                ),

            "ejecutable":
                final_previo.get(
                    "ejecutable"
                ),

            "tipo_plan":
                final_previo.get(
                    "tipo_plan"
                ),

            "razon":
                final_previo.get(
                    "razon"
                ),

            "intentos":
                intentos_final,

            "llm_invocado":
                bool(
                    final_previo.get(
                        "llm_invocado"
                    )
                ),
        },

        "llm": {
            "invocado":
                llm_invocado,

            "modelo":
                (
                    interpretacion.get(
                        "modelo_llm"
                    )
                    or intencion.get(
                        "modelo_llm"
                    )
                ),

            "metricas":
                (
                    interpretacion.get(
                        "metricas_llm"
                    )
                    or intencion.get(
                        "metricas_llm"
                    )
                ),

            "propuesta_cruda":
                interpretacion.get(
                    "propuesta_cruda"
                ),

            "propuesta":
                interpretacion.get(
                    "propuesta"
                ),
        },

        "host_resumen": {
            "destino":
                resultado.get(
                    "destino"
                ),

            "ok":
                host_ok,

            "fase":
                estado.get(
                    "fase"
                ),

            "entidad":
                entidad_final,

            "plan_validado":
                bool(
                    validacion.get(
                        "plan_validado"
                    )
                    or validacion.get(
                        "ok"
                    )
                ),

            "errores_validacion":
                validacion.get(
                    "errores",
                    [],
                ),

            "advertencias":
                validacion.get(
                    "advertencias",
                    [],
                ),

            "ejecutado":
                bool(
                    ejecucion.get(
                        "ejecutado"
                    )
                ),

            "total_devuelto":
                ejecucion.get(
                    "total_devuelto"
                ),

            "modelo_ejecutado":
                ejecucion.get(
                    "modelo"
                ),
        },

        "estado":
            estado,

        "routing": {
            "destino":
                resultado.get(
                    "destino"
                ),
        },

        "intencion": {
            "tipo":
                intencion.get(
                    "tipo"
                ),

            "subtipo":
                intencion.get(
                    "subtipo"
                ),

            "accion":
                intencion.get(
                    "accion"
                ),

            "origen":
                intencion.get(
                    "origen"
                ),

            "confianza":
                intencion.get(
                    "confianza"
                ),

            "validado":
                intencion.get(
                    "validado"
                ),

            "razon":
                intencion.get(
                    "razon"
                ),

            "terminos":
                intencion.get(
                    "terminos"
                )
                or [],

            "llm_invocado":
                bool(
                    intencion.get(
                        "llm_invocado"
                    )
                ),

            "propuesta_llm":
                intencion.get(
                    "propuesta_llm"
                ),

            "determinista_previo":
                intencion.get(
                    "determinista_previo"
                ),
        },

        "entidad": {
            "inicial":
                entidad_inicial,

            "final":
                entidad_final,

            "validada":
                bool(
                    intencion.get(
                        "validado"
                    )
                ),

            "resolucion_dinamica":
                resolucion_entidad
                or None,
        },

        "interpretacion":
            interpretacion
            or None,

        "validacion":
            validacion
            or None,

        "ejecucion":
            ejecucion
            or None,

        "estructura":
            resultado_host
            or None,

        "respuesta": {
            "texto":
                resultado.get(
                    "respuesta"
                ),

            "estructurada":
                respuesta_estructurada
                or None,

            "error":
                resultado.get(
                    "error"
                ),
        },

        # Se conserva el resultado bruto únicamente para
        # diagnóstico técnico. La UI podrá ocultarlo por defecto.
        "resultado_bruto":
            resultado,
    }

    return diagnostico
