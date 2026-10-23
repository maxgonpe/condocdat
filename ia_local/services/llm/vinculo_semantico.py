"""
ARC003-B02-B — Identidad determinista del contexto semantico.

Vincula pregunta, coleccion normalizada y plan HOST.
No certifica semantica, permisos ni autoriza ejecucion.
"""

import hashlib
import json

from ia_local.services.llm.trazabilidad_compuesta import (
    _verificar_coleccion_identificada,
)


VERSION = "IA-ARC003-B02-B-v1"


def _huella(datos):
    serializado = json.dumps(
        datos,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(
        serializado.encode("utf-8")
    ).hexdigest()


def vincular_contexto_semantico(
    pregunta,
    coleccion,
    plan_host,
):
    base = {
        "ok": False,
        "version": VERSION,
        "estado": "entrada_invalida",
        "huella_pregunta": None,
        "huella_coleccion": None,
        "huella_plan": None,
        "identificador_vinculo": None,
        "certificacion_semantica": False,
        "cobertura_verificada": False,
        "integridad_completa": False,
        "ejecutable": False,
        "ejecutado": False,
    }

    if (
        not isinstance(pregunta, str)
        or not pregunta.strip()
        or not isinstance(coleccion, dict)
        or not isinstance(plan_host, dict)
    ):
        return base

    if (
        coleccion.get("pregunta_original") != pregunta
        or not _verificar_coleccion_identificada(coleccion)
        or plan_host.get("ejecutable") is True
        or plan_host.get("ejecutado") is True
        or plan_host.get("certificacion_semantica") is True
    ):
        return base

    try:
        huella_pregunta = _huella({
            "tipo": "pregunta",
            "valor": pregunta,
        })

        huella_coleccion = _huella({
            "tipo": "coleccion",
            "valor": coleccion,
        })

        huella_plan = _huella({
            "tipo": "plan_host",
            "valor": plan_host,
        })

        identificador = _huella({
            "version": VERSION,
            "pregunta": huella_pregunta,
            "coleccion": huella_coleccion,
            "plan": huella_plan,
        })

    except (TypeError, ValueError, OverflowError, RecursionError):
        return {
            **base,
            "estado": "datos_no_canonizables",
        }

    return {
        **base,
        "ok": True,
        "estado": "contexto_vinculado_pendiente",
        "huella_pregunta": huella_pregunta,
        "huella_coleccion": huella_coleccion,
        "huella_plan": huella_plan,
        "identificador_vinculo": identificador,
    }


def verificar_vinculo_semantico(
    pregunta,
    coleccion,
    plan_host,
    vinculo,
):
    """
    Verifica correspondencia exacta con un vinculo previo.

    No acredita procedencia ni certifica semantica.
    No habilita ejecucion.
    """
    base = {
        "ok": False,
        "version": VERSION,
        "estado": "vinculo_invalido",
        "coincidencia_verificada": False,
        "certificacion_semantica": False,
        "cobertura_verificada": False,
        "integridad_completa": False,
        "ejecutable": False,
        "ejecutado": False,
    }

    if not isinstance(vinculo, dict):
        return base

    if (
        vinculo.get("ok") is not True
        or vinculo.get("version") != VERSION
        or vinculo.get("estado")
            != "contexto_vinculado_pendiente"
        or vinculo.get("ejecutable") is not False
        or vinculo.get("ejecutado") is not False
        or vinculo.get("certificacion_semantica") is not False
        or vinculo.get("cobertura_verificada") is not False
        or vinculo.get("integridad_completa") is not False
    ):
        return base

    esperado = vincular_contexto_semantico(
        pregunta,
        coleccion,
        plan_host,
    )

    if esperado.get("ok") is not True:
        return {
            **base,
            "estado": "contexto_actual_invalido",
        }

    campos = (
        "huella_pregunta",
        "huella_coleccion",
        "huella_plan",
        "identificador_vinculo",
    )

    if any(
        not isinstance(vinculo.get(campo), str)
        or vinculo[campo] != esperado[campo]
        for campo in campos
    ):
        return {
            **base,
            "estado": "contexto_modificado",
        }

    return {
        **base,
        "ok": True,
        "estado": "vinculo_coincidente_no_certificado",
        "coincidencia_verificada": True,
    }
