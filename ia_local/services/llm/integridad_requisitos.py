"""
ARC002-B02 — Diagnóstico de integridad de requisitos.

No interpreta preguntas.
No certifica cobertura semántica.
No autoriza ni ejecuta consultas.
"""

from typing import Any


VERSION = "IA-ARC002-B02-v1"


def diagnosticar_integridad_requisitos(
    coleccion: dict[str, Any],
) -> dict[str, Any]:
    base = {
        "version": VERSION,
        "ok": False,
        "estado": "coleccion_invalida",
        "pregunta_original": None,
        "identificador_coleccion": None,
        "requisitos_identificados": [],
        "requisitos_pendientes": [],
        "integridad_demostrada": False,
        "cobertura_verificada": False,
        "ejecutable": False,
        "ejecutado": False,
    }

    if not isinstance(coleccion, dict):
        return base

    if (
        coleccion.get("ok") is not True
        or coleccion.get("estado")
            != "coleccion_normalizada_pendiente"
        or coleccion.get("ejecutable") is not False
        or coleccion.get("ejecutado") is not False
    ):
        return base

    pregunta = coleccion.get("pregunta_original")
    identificador = coleccion.get("identificador_coleccion")
    restricciones = coleccion.get("restricciones")
    pendientes = coleccion.get("pendientes")

    if (
        not isinstance(pregunta, str)
        or not pregunta.strip()
        or not isinstance(identificador, str)
        or not identificador
        or not isinstance(restricciones, list)
        or not isinstance(pendientes, list)
    ):
        return base

    ids = []

    for restriccion in restricciones:
        if not isinstance(restriccion, dict):
            return base

        identificador_requisito = restriccion.get("id")

        if (
            not isinstance(identificador_requisito, str)
            or not identificador_requisito
            or restriccion.get("estado_certificacion")
                != "pendiente"
            or restriccion.get("certificada_host") is not False
            or restriccion.get("certificada_plan_completo")
                is not False
        ):
            return base

        ids.append(identificador_requisito)

    if len(ids) != len(set(ids)):
        return base

    if (
        set(pendientes) != set(ids)
        or len(pendientes) != len(ids)
    ):
        return base

    return {
        **base,
        "ok": True,
        "estado": "integridad_pendiente",
        "pregunta_original": pregunta,
        "identificador_coleccion": identificador,
        "requisitos_identificados": ids,
        "requisitos_pendientes": list(pendientes),
    }
