"""
IA-ARC001-C02-B

Auditoria preventiva de planes HOST preparados.

No certifica cobertura integral.
No modifica planes ni ejecuta ORM.
"""

import re

from ia_local.services.llm.auditoria_semantica import (
    auditar_restricciones_semanticas,
)
from ia_local.services.llm.consolidacion_semantica import (
    consolidar_interpretacion_semantica,
)
from ia_local.services.llm.cobertura_semantica import (
    evaluar_cobertura_semantica,
)

VERSION = "IA-ARC001-C02-B-v1"

NEGACION_EXPLICITA = re.compile(
    r"\b(?:no|sin|excepto|excluyendo|distinto\s+de|"
    r"diferente\s+de|que\s+no)\b",
    flags=re.IGNORECASE,
)


def _resultado(pregunta, estado, pendientes=None):
    return {
        "version": VERSION,
        "pregunta_original": pregunta,
        "estado": estado,
        "ok": False,
        "cobertura_certificada": False,
        "ejecutable": False,
        "ejecutado": False,
        "pendientes": pendientes or [],
    }


def auditar_plan_preparado(pregunta, plan):
    """
    Audita riesgos conocidos sin conceder autorizacion.

    La ausencia de riesgos detectados NO equivale a
    fidelidad semantica integral.
    """

    if not isinstance(pregunta, str) or not pregunta.strip():
        return _resultado(pregunta, "entrada_invalida")

    if not isinstance(plan, dict):
        return _resultado(pregunta, "plan_invalido")

    filtros = plan.get("filtros")

    if not isinstance(filtros, list):
        return _resultado(pregunta, "plan_invalido")

    if not all(isinstance(filtro, dict) for filtro in filtros):
        return _resultado(pregunta, "plan_invalido")

    pendientes = []

    # Primera barrera: señales explícitas de negación.
    # Este control es conservador y NO prueba equivalencia.
    hay_negacion_textual = bool(
        NEGACION_EXPLICITA.search(pregunta)
    )

    hay_negacion_plan = any(
        filtro.get("negado") is True
        or filtro.get("operador") in (
            "ne",
            "not",
            "not_exact",
            "exclude",
            "isnot",
        )
        for filtro in filtros
    )

    if hay_negacion_textual and not hay_negacion_plan:
        pendientes.append(
            "negacion_textual_sin_representacion_explica"
        )

    # Reutilizamos la infraestructura existente.
    try:
        auditoria = auditar_restricciones_semanticas(
            pregunta
        )

        consolidacion = consolidar_interpretacion_semantica(
            pregunta
        )

        if not isinstance(auditoria, dict):
            raise ValueError("auditoria_invalida")

        if not isinstance(consolidacion, dict):
            raise ValueError("consolidacion_invalida")

        cobertura = evaluar_cobertura_semantica(
            pregunta,
            consolidacion,
        )

        if not isinstance(cobertura, dict):
            raise ValueError("cobertura_invalida")

    except Exception:
        pendientes.append("auditoria_interna_no_disponible")

        return _resultado(
            pregunta,
            "revision_pendiente",
            pendientes,
        )

    if auditoria.get("omisiones_auditoria"):
        pendientes.append("omisiones_auditoria_detectadas")

    if auditoria.get("requiere_revision") is True:
        pendientes.append("revision_auditoria_requerida")

    if consolidacion.get("requiere_revision") is True:
        pendientes.append("revision_consolidacion_requerida")

    if consolidacion.get("omisiones_conocidas"):
        pendientes.append("omisiones_conocidas")

    if cobertura.get("componentes_pendientes"):
        pendientes.append("componentes_cobertura_pendientes")

    if pendientes:
        return _resultado(
            pregunta,
            "revision_pendiente",
            pendientes,
        )

    return _resultado(
        pregunta,
        "sin_omision_demostrada",
    )
