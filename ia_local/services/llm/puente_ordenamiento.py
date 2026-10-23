"""Puente diagnóstico entre restricciones LLM y QUERY004.

No modifica la pregunta, no construye ORM y no ejecuta datos.
"""
from typing import Any

from ia_local.services.query.ordenamiento_natural import (
    componer_ordenamiento_natural,
)

VERSION = "IA-LLM008-F5-04-04-v1"


def evaluar_ordenamiento_semantico(
    pregunta: str,
    restricciones: list[dict],
) -> dict[str, Any]:

    base = {
        "ok": False,
        "version": VERSION,
        "estado": "ordenamiento_no_evaluado",
        "ordenamiento_query": None,
        "requiere_aclaracion": False,
        "certificada_host": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }

    if (
        not isinstance(pregunta, str)
        or not pregunta.strip()
        or not isinstance(restricciones, list)
        or any(not isinstance(r, dict) for r in restricciones)
    ):
        return {**base, "estado": "contrato_invalido"}

    ordenes = [
        r for r in restricciones
        if r.get("tipo") == "ordenamiento"
    ]

    if not ordenes:
        return {
            **base,
            "ok": True,
            "estado": "sin_ordenamiento_solicitado",
        }

    if len(ordenes) != 1:
        return {
            **base,
            "estado": "ordenamientos_multiples_no_resueltos",
            "requiere_aclaracion": True,
        }

    evidencia = ordenes[0].get("evidencia_textual")

    if (
        not isinstance(evidencia, str)
        or not evidencia.strip()
    ):
        return {
            **base,
            "estado": "evidencia_orden_invalida",
        }

    # QUERY004 es la autoridad para interpretar y certificar
    # el ordenamiento. No generamos expresiones alternativas.
    try:
        resultado = componer_ordenamiento_natural(
            pregunta.strip()
        )
    except Exception:
        return {
            **base,
            "estado": "query004_no_disponible",
        }

    if not isinstance(resultado, dict):
        return {
            **base,
            "estado": "contrato_query004_invalido",
        }

    if (
        resultado.get("ejecutado") is not False
        or resultado.get("llm_invocado") is not False
    ):
        return {
            **base,
            "estado": "contrato_seguridad_query004_invalido",
        }

    if resultado.get("ok") is not True:
        return {
            **base,
            "ok": True,
            "estado": "ordenamiento_pendiente_query004",
            "estado_query004": resultado.get("estado"),
            "razon_query004": resultado.get("razon"),
            "requiere_aclaracion": True,
            "ordenamiento_query": resultado,
        }

    # Conservamos la salida certificada por QUERY004, pero
    # aún no autorizamos el plan relacional completo.
    return {
        **base,
        "ok": True,
        "estado": "ordenamiento_resuelto_query004",
        "ordenamiento_query": resultado,
        "certificada_host": True,
    }
