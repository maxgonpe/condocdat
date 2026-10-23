"""
ARC002-C07-B04 — Diagnostico conjunto de negaciones.

Compone las auditorias C07-B01, B02 y B03.
No interpreta, certifica ni ejecuta consultas.
"""

from ia_local.services.llm.auditoria_negacion import (
    auditar_correspondencia_negativa,
)
from ia_local.services.llm.integridad_negacion_compuesta import (
    auditar_integridad_negativa_compuesta,
)
from ia_local.services.llm.auditoria_sustituciones import (
    auditar_sustituciones_semanticas,
)

VERSION = "IA-ARC002-C07-B04-v1"


def diagnosticar_negacion_integral(
    pregunta,
    coleccion,
    plan,
    expresion_logica=None,
):
    base = {
        "ok": False,
        "version": VERSION,
        "estado": "entrada_invalida",
        "pregunta_original": pregunta,
        "diagnosticos": {},
        "discrepancias": [],
        "pendientes": [],
        "equivalencia_semantica_certificada": False,
        "cobertura_verificada": False,
        "integridad_completa": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }

    if (
        not isinstance(pregunta, str)
        or not pregunta.strip()
        or not isinstance(coleccion, dict)
        or not isinstance(plan, dict)
        or coleccion.get("pregunta_original") != pregunta
        or coleccion.get("ejecutable") is not False
        or coleccion.get("ejecutado") is not False
        or plan.get("ejecutable") is True
        or plan.get("ejecutado") is True
    ):
        return base

    # Las tres auditorias se recalculan con los contratos
    # originales. No se aceptan resultados precertificados.
    diagnosticos = {
        "correspondencia": auditar_correspondencia_negativa(
            pregunta,
            expresion_logica,
        ),
        "integridad": auditar_integridad_negativa_compuesta(
            coleccion,
        ),
        "sustituciones": auditar_sustituciones_semanticas(
            pregunta,
            plan,
        ),
    }

    for nombre, resultado in diagnosticos.items():
        if (
            not isinstance(resultado, dict)
            or resultado.get("ok") is not True
            or resultado.get("pregunta_original") != pregunta
            or resultado.get("ejecutable") is not False
            or resultado.get("ejecutado") is not False
        ):
            return {
                **base,
                "estado": "diagnostico_invalido",
                "diagnosticos": diagnosticos,
                "discrepancias": [{
                    "origen": nombre,
                    "motivo": "diagnostico_no_valido",
                }],
            }

    discrepancias = []
    pendientes = []

    for nombre, resultado in diagnosticos.items():
        for item in resultado.get("discrepancias", []):
            discrepancias.append({
                "origen": nombre,
                "detalle": item,
            })

        for item in resultado.get("pendientes", []):
            pendientes.append({
                "origen": nombre,
                "detalle": item,
            })

    return {
        **base,
        "ok": True,
        "estado": (
            "revision_con_discrepancias"
            if discrepancias
            else "revision_semantica_pendiente"
        ),
        "diagnosticos": diagnosticos,
        "discrepancias": discrepancias,
        "pendientes": pendientes,
    }
