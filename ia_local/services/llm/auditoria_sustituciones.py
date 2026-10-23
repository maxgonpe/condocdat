"""
ARC002-C07-B03 — Auditoria preventiva de sustituciones semanticas.

Identifica riesgos de negacion omitida o representada sin
certificacion. No infiere equivalencias entre valores o estados.
No invoca HOST, BRIDGE, Qwen ni ORM.
"""

import re

from ia_local.services.llm.evidencia_negacion import (
    localizar_evidencias_negacion,
)

VERSION = "IA-ARC002-C07-B03-v1"

# Complementa los marcadores ya reconocidos por B03.
# Son indicios linguisticos, no operadores ORM certificados.
PATRON_NEGACION_ADICIONAL = re.compile(
    r"\b(?:excepto|excluyendo|distinto\s+de|"
    r"diferente\s+de)\b",
    flags=re.IGNORECASE,
)

OPERADORES_NEGATIVOS = {
    "ne",
    "not",
    "not_exact",
    "exclude",
    "isnot",
}


def auditar_sustituciones_semanticas(pregunta, plan):
    base = {
        "ok": False,
        "version": VERSION,
        "estado": "entrada_invalida",
        "pregunta_original": pregunta,
        "negacion_original_detectada": False,
        "negacion_representada_en_plan": False,
        "evidencias_negativas": [],
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
        or len(pregunta) > 1000
        or not isinstance(plan, dict)
    ):
        return base

    filtros = plan.get("filtros")

    if (
        not isinstance(filtros, list)
        or not all(isinstance(f, dict) for f in filtros)
        or plan.get("ejecutable") is True
        or plan.get("ejecutado") is True
    ):
        return base

    evidencias = localizar_evidencias_negacion(pregunta)

    if evidencias.get("ok") is not True:
        return base

    hay_negacion = bool(
        evidencias["evidencias"]
        or PATRON_NEGACION_ADICIONAL.search(pregunta)
    )

    representada = any(
        filtro.get("negado") is True
        or (
            isinstance(filtro.get("operador"), str)
            and filtro["operador"].strip().lower()
            in OPERADORES_NEGATIVOS
        )
        for filtro in filtros
    )

    discrepancias = []
    pendientes = ["certificacion_semantica_integral"]

    if hay_negacion:
        pendientes.extend([
            "alcance_negacion_no_certificado",
            "equivalencia_negativa_no_demostrada",
        ])

        if not representada:
            discrepancias.append(
                "negacion_original_sin_representacion_explicita"
            )
        else:
            pendientes.append(
                "representacion_negativa_sin_certificacion"
            )

    if representada and not hay_negacion:
        discrepancias.append(
            "negacion_plan_sin_respaldo_textual_detectado"
        )
        pendientes.append(
            "procedencia_negacion_plan_pendiente"
        )

    return {
        **base,
        "ok": True,
        "estado": (
            "sustitucion_negativa_potencial"
            if discrepancias
            else "revision_semantica_pendiente"
        ),
        "pregunta_original": pregunta,
        "negacion_original_detectada": hay_negacion,
        "negacion_representada_en_plan": representada,
        "evidencias_negativas": evidencias["evidencias"],
        "discrepancias": discrepancias,
        "pendientes": list(dict.fromkeys(pendientes)),
    }
