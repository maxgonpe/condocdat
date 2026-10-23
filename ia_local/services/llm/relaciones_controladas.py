"""Adaptador relacional reutilizable y sin ejecución ORM.

QUERY007 certifica la ruta mediante HOST. Este módulo no
construye consultas SQL ni acepta rutas ORM externas.
"""

from typing import Any

from ia_local.services.query.relaciones_orm import (
    componer_relacion_orm,
)

VERSION = "IA-LLM008-F3-02-v1"


def certificar_relacion(
    expresion: str,
) -> dict[str, Any]:
    """Certifica una expresión mediante QUERY007, sin ejecutar datos."""

    pregunta = (
        expresion.strip()
        if isinstance(expresion, str)
        else ""
    )

    base = {
        "ok": False,
        "version": VERSION,
        "estado": "relacion_no_certificada",
        "pregunta": pregunta,
        "ejecutado": False,
        "llm_invocado": False,
        "modelo_origen": None,
        "modelo_destino": None,
        "ruta_orm": None,
        "profundidad": None,
        "validacion_ruta": None,
    }

    if not pregunta:
        return {
            **base,
            "estado": "pregunta_vacia",
        }

    try:
        resultado = componer_relacion_orm(pregunta)
    except Exception:
        return {
            **base,
            "estado": "error_certificacion",
        }

    if not isinstance(resultado, dict):
        return {
            **base,
            "estado": "contrato_query_invalido",
        }

    if (
        resultado.get("ok") is not True
        or resultado.get("estado")
        != "ruta_relacional_validada"
        or resultado.get("ejecutado") is not False
    ):
        return {
            **base,
            "estado": "relacion_no_certificada",
            "estado_query": resultado.get("estado"),
        }

    origen = resultado.get("modelo_origen")
    destino = resultado.get("modelo_destino")
    ruta = resultado.get("ruta_orm")
    validacion = resultado.get("validacion_ruta")
    profundidad = resultado.get("profundidad")

    if (
        not isinstance(origen, str)
        or not origen.strip()
        or not isinstance(destino, str)
        or not destino.strip()
        or not isinstance(ruta, (str, list, tuple))
        or not ruta
        or not isinstance(validacion, dict)
        or not validacion
        or type(profundidad) is not int
        or profundidad < 1
    ):
        return {
            **base,
            "estado": "evidencia_relacional_incompleta",
        }

    # IA-LLM008-F3-05: evidencia HOST obligatoria.
    if (
        validacion.get("ok") is not True
        or validacion.get("valida") is not True
        or validacion.get("modelo_origen") != origen
        or validacion.get("modelo_destino") != destino
        or validacion.get("ruta_orm") != ruta
        or type(validacion.get("profundidad")) is not int
        or validacion["profundidad"] != profundidad
        or validacion.get("origen") != "django_meta"
        or validacion.get("llm_invocado") is not False
    ):
        return {
            **base,
            "estado": "evidencia_host_inconsistente",
        }

    pasos = validacion.get("pasos")

    if not isinstance(pasos, list) or len(pasos) != profundidad:
        return {
            **base,
            "estado": "pasos_relacionales_invalidos",
        }

    actual = origen
    segmentos = []

    for indice, paso in enumerate(pasos, start=1):
        if not isinstance(paso, dict):
            return {
                **base,
                "estado": "paso_relacional_invalido",
            }

        segmento = paso.get("segmento_orm")
        siguiente = paso.get("modelo_destino")

        if (
            type(paso.get("indice")) is not int
            or paso["indice"] != indice
            or paso.get("modelo_origen") != actual
            or not isinstance(siguiente, str)
            or not siguiente.strip()
            or not isinstance(segmento, str)
            or not segmento.strip()
            or "__" in segmento
        ):
            return {
                **base,
                "estado": "cadena_relacional_inconsistente",
            }

        segmentos.append(segmento)
        actual = siguiente

    if actual != destino or not isinstance(ruta, str):
        return {
            **base,
            "estado": "destino_relacional_inconsistente",
        }

    if "__".join(segmentos) != ruta:
        return {
            **base,
            "estado": "ruta_relacional_inconsistente",
        }

    return {
        **base,
        "ok": True,
        "estado": "relacion_certificada",
        "modelo_origen": origen,
        "modelo_destino": destino,
        "ruta_orm": ruta,
        "profundidad": profundidad,
        "contiene_relacion_multiple": resultado.get(
            "contiene_relacion_multiple"
        ),
        "validacion_ruta": validacion,
        "componente_certificador": "QUERY007",
    }
