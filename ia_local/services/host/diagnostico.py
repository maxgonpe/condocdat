from __future__ import annotations

from typing import Any

from .router import (
    procesar_pregunta,
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

    diagnostico = {
        "pregunta":
            pregunta,

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
