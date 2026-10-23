"""
ARC002-C07-B01 — Auditoria conservadora de negaciones.

Contrasta evidencias textuales y AST diagnostico.
No infiere equivalencia semantica.
No invoca Qwen, BRIDGE, HOST ni ORM.
No autoriza ejecucion.
"""

from ia_local.services.llm.evidencia_negacion import (
    localizar_evidencias_negacion,
)
from ia_local.services.query.trazabilidad_not import (
    localizar_nodos_not,
)

VERSION = "IA-ARC002-C07-B01-v1"


def auditar_correspondencia_negativa(
    pregunta_original,
    expresion_logica=None,
):
    base = {
        "ok": False,
        "version": VERSION,
        "estado": "entrada_invalida",
        "pregunta_original": None,
        "expresion_logica": None,
        "evidencias_negativas": [],
        "nodos_not": [],
        "cantidad_evidencias": 0,
        "cantidad_nodos_not": 0,
        "discrepancias": [],
        "pendientes": [],
        "correspondencia_textual_demostrada": False,
        "alcance_certificado": False,
        "equivalencia_semantica_certificada": False,
        "cobertura_verificada": False,
        "integridad_completa": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }

    evidencias = localizar_evidencias_negacion(
        pregunta_original
    )

    if evidencias.get("ok") is not True:
        return base

    if (
        expresion_logica is not None
        and (
            not isinstance(expresion_logica, str)
            or not expresion_logica.strip()
        )
    ):
        return base

    pregunta = evidencias["pregunta_original"]

    salida = {
        **base,
        "ok": True,
        "estado": "auditoria_negativa_pendiente",
        "pregunta_original": pregunta,
        "expresion_logica": expresion_logica,
        "evidencias_negativas": evidencias["evidencias"],
        "cantidad_evidencias": evidencias["cantidad"],
    }

    discrepancias = []
    pendientes = ["certificacion_semantica_negacion"]

    if evidencias["cantidad"]:
        pendientes.append(
            "alcance_negaciones_lenguaje_natural"
        )

    if expresion_logica is None:
        if evidencias["cantidad"]:
            discrepancias.append(
                "negacion_original_sin_arbol_diagnostico"
            )

        pendientes.append("arbol_logico_no_aportado")

    else:
        diagnostico = localizar_nodos_not(
            expresion_logica
        )

        if diagnostico.get("ok") is not True:
            return {
                **salida,
                "ok": False,
                "estado": "ast_diagnostico_invalido",
                "discrepancias": [
                    "expresion_logica_no_validada"
                ],
                "pendientes": pendientes,
            }

        nodos = diagnostico["nodos_not"]

        salida["nodos_not"] = nodos
        salida["cantidad_nodos_not"] = len(nodos)

        if pregunta != expresion_logica.strip():
            # Son textos distintos: sus offsets no pueden
            # utilizarse como prueba de correspondencia.
            if evidencias["cantidad"] or nodos:
                discrepancias.append(
                    "correspondencia_entre_textos_no_demostrada"
                )

            pendientes.append(
                "vinculacion_pregunta_expresion_logica"
            )

        else:
            # La identidad del texto permite comparar
            # posiciones, pero NO certifica significado.
            if evidencias["cantidad"] and not nodos:
                discrepancias.append(
                    "marcadores_negativos_sin_not_ast"
                )

            if nodos and not evidencias["cantidad"]:
                pendientes.append(
                    "not_explicito_sin_evidencia_linguistica"
                )

            pendientes.append(
                "alcance_operadores_not_no_certificado"
            )

    salida["discrepancias"] = discrepancias
    salida["pendientes"] = list(dict.fromkeys(pendientes))

    return salida
