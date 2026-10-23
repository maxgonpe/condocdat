"""Diagnóstico de integridad de una consulta compuesta.

Recibe contratos existentes. No ejecuta ni autoriza ORM.
"""
from typing import Any

VERSION = "IA-LLM008-F5-06-02-v1"


def evaluar_integridad_plan_compuesto(
    pregunta: str,
    *,
    relacion: dict,
    cardinalidad: dict,
    ordenamiento: dict,
    filtro: dict | None = None,
) -> dict[str, Any]:

    resultado = {
        "ok": False,
        "version": VERSION,
        "estado": "contrato_invalido",
        "pregunta": pregunta,
        "componentes": {},
        "pendientes": [],
        "requiere_aclaracion": False,
        "integridad_completa": False,
        "cobertura_verificada": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }

    if (
        not isinstance(pregunta, str)
        or not pregunta.strip()
        or not isinstance(relacion, dict)
        or not isinstance(cardinalidad, dict)
        or not isinstance(ordenamiento, dict)
        or (filtro is not None and not isinstance(filtro, dict))
    ):
        return resultado

    pendientes = []
    componentes = {}

    # La certificación relacional debe provenir de QUERY007/HOST.
    vr = relacion.get("validacion_ruta")
    relacion_certificada = (
        relacion.get("ok") is True
        and relacion.get("estado") == "relacion_certificada"
        and relacion.get("componente_certificador") == "QUERY007/HOST"
        and relacion.get("ejecutado") is False
        and relacion.get("ejecutable") is False
        and isinstance(vr, dict)
        and vr.get("ok") is True
        and vr.get("valida") is True
        and vr.get("origen") == "django_meta"
        and vr.get("modelo_origen") == relacion.get("modelo_origen")
        and vr.get("modelo_destino") == relacion.get("modelo_destino")
        and vr.get("ruta_orm") == relacion.get("ruta_orm")
        and vr.get("profundidad") == relacion.get("profundidad")
    )

    misma_pregunta_relacional = (
        relacion.get("pregunta") == pregunta
    )

    componentes["relacion"] = {
        "certificada_aisladamente": relacion_certificada,
        "corresponde_pregunta_original": misma_pregunta_relacional,
        "modelo_origen": relacion.get("modelo_origen"),
        "modelo_destino": relacion.get("modelo_destino"),
        "ruta_orm": relacion.get("ruta_orm"),
    }

    if not relacion_certificada:
        pendientes.append("relacion_no_certificada")
    elif not misma_pregunta_relacional:
        pendientes.append("relacion_pregunta_distinta")

    # F5-03: cardinalidad conciliada con la política transversal.
    cardinalidad_ok = (
        cardinalidad.get("ok") is True
        and cardinalidad.get("estado") == "cardinalidad_conciliada"
        and cardinalidad.get("pregunta") == pregunta
        and cardinalidad.get("cardinalidad_validada_localmente") is True
        and cardinalidad.get("ejecutado") is False
        and cardinalidad.get("ejecutable") is False
        and type(cardinalidad.get("cantidad_autorizada")) is int
        and cardinalidad["cantidad_autorizada"] > 0
    )

    componentes["cardinalidad"] = {
        "validada_localmente": cardinalidad_ok,
        "cantidad_autorizada": (
            cardinalidad.get("cantidad_autorizada")
            if cardinalidad_ok else None
        ),
    }

    if not cardinalidad_ok:
        pendientes.append("cardinalidad_pendiente")

    # F5-04: QUERY004 debe certificar el orden explícito.
    orden_query = ordenamiento.get("ordenamiento_query")
    orden_ok = (
        ordenamiento.get("ok") is True
        and ordenamiento.get("estado") == "ordenamiento_resuelto_query004"
        and ordenamiento.get("certificada_host") is True
        and ordenamiento.get("ejecutado") is False
        and ordenamiento.get("ejecutable") is False
        and isinstance(orden_query, dict)
        and orden_query.get("ok") is True
        and orden_query.get("estado") == "plan_orden_validado"
        and orden_query.get("ejecutado") is False
        and orden_query.get("llm_invocado") is False
    )

    componentes["ordenamiento"] = {
        "certificado_aisladamente": orden_ok,
        "estado": ordenamiento.get("estado"),
    }

    if not orden_ok:
        pendientes.append("ordenamiento_pendiente")

    # F5-05: una elección validada aislada no certifica el plan.
    filtro_seleccionado = (
        isinstance(filtro, dict)
        and filtro.get("ok") is True
        and filtro.get("estado") in {
            "eleccion_filtro_certificada",
            "filtro_seleccionado_pendiente_plan",
        }
        and filtro.get("ejecutado") is False
        and filtro.get("ejecutable") is False
        and isinstance(filtro.get("seleccion"), dict)
    )

    componentes["filtro"] = {
        "seleccion_certificada_aisladamente": bool(
            filtro_seleccionado
        ),
        "estado": filtro.get("estado") if filtro else "sin_seleccion",
    }

    if not filtro_seleccionado:
        pendientes.append("filtro_sin_seleccion_certificada")
    elif filtro.get("modelo") != relacion.get("modelo_destino"):
        pendientes.append("filtro_modelo_no_coincidente")

    # La cobertura completa aún no está demostrada.
    pendientes.append("integracion_semantica_total_pendiente")
    pendientes.append("certificacion_conjunta_host_pendiente")

    resultado.update({
        "ok": True,
        "estado": "plan_compuesto_bloqueado",
        "componentes": componentes,
        "pendientes": pendientes,
        "requiere_aclaracion": (
            "ordenamiento_pendiente" in pendientes
            or "filtro_sin_seleccion_certificada" in pendientes
        ),
    })

    return resultado
