"""
IA-ARC001-B02

Preparacion de consultas de datos sin ejecucion funcional ORM.

Este componente reutiliza los servicios HOST existentes.
La validacion estructural NO representa certificacion semantica.
"""

from ia_local.services.host.resolvedor_entidad_datos import (
    resolver_entidad_datos,
)
from ia_local.services.host.interprete_datos import (
    interpretar_consulta_datos,
)
from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)


VERSION = "IA-ARC001-B02-v1"


def _rechazo(pregunta, estado, *, diagnostico=None):
    return {
        "ok": False,
        "version": VERSION,
        "estado": estado,
        "pregunta_original": pregunta,
        "modelo": None,
        "plan": None,
        "interpretacion": None,
        "validacion": None,
        "diagnostico": diagnostico or {},
        "certificacion_semantica": False,
        "ejecutable": False,
        "ejecutado": False,
    }


def preparar_consulta_datos(pregunta):
    if not isinstance(pregunta, str) or not pregunta.strip():
        return _rechazo(pregunta, "pregunta_invalida")

    resolucion = resolver_entidad_datos(pregunta)

    if (
        not isinstance(resolucion, dict)
        or resolucion.get("resuelto") is not True
    ):
        return _rechazo(
            pregunta,
            "entidad_no_resuelta",
            diagnostico={"resolucion_entidad": resolucion},
        )

    modelo = resolucion.get("entidad")

    if not isinstance(modelo, str) or not modelo:
        return _rechazo(
            pregunta,
            "modelo_invalido",
            diagnostico={"resolucion_entidad": resolucion},
        )

    interpretacion = interpretar_consulta_datos(
        pregunta,
        modelo=modelo,
        evidencia_entidad=resolucion,
    )

    if (
        not isinstance(interpretacion, dict)
        or interpretacion.get("ok") is not True
    ):
        return _rechazo(
            pregunta,
            "interpretacion_no_resuelta",
            diagnostico={"interpretacion": interpretacion},
        )

    propuesta = interpretacion.get("propuesta")

    if not isinstance(propuesta, dict):
        return _rechazo(
            pregunta,
            "propuesta_invalida",
            diagnostico={"interpretacion": interpretacion},
        )

    # La resolucion HOST determina la entidad autorizada
    # para este proceso de preparacion. Qwen no puede
    # sustituirla por otro modelo.
    if propuesta.get("modelo") != modelo:
        return _rechazo(
            pregunta,
            "modelo_inconsistente",
            diagnostico={
                "modelo_host": modelo,
                "modelo_propuesto": propuesta.get("modelo"),
            },
        )

    validacion = validar_plan_datos(propuesta)

    if (
        not isinstance(validacion, dict)
        or validacion.get("ok") is not True
    ):
        return _rechazo(
            pregunta,
            "plan_rechazado_host",
            diagnostico={"validacion": validacion},
        )

    plan = validacion.get("plan")

    if (
        not isinstance(plan, dict)
        or plan.get("modelo") != modelo
    ):
        return _rechazo(
            pregunta,
            "plan_inconsistente",
        )

    return {
        "ok": True,
        "version": VERSION,
        "estado": "plan_host_preparado",
        "pregunta_original": pregunta,
        "modelo": modelo,
        "resolucion_entidad": resolucion,
        "interpretacion": interpretacion,
        "validacion": validacion,
        "plan": plan,
        "certificacion_semantica": False,
        "ejecutable": False,
        "ejecutado": False,
    }
