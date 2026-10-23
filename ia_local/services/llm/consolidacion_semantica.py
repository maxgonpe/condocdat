"""Consolidación semántica, sin certificación ni ejecución."""
import unicodedata
from typing import Any

from ia_local.services.llm.auditoria_semantica import (
    auditar_restricciones_semanticas,
)

VERSION = "IA-LLM008-F4-05-R3-03-v1"


def _normalizar(valor):
    texto = unicodedata.normalize("NFKD", valor.casefold())
    return "".join(
        c for c in texto if not unicodedata.combining(c)
    )


def _base(pregunta, estado, auditoria=None):
    return {
        "ok": False,
        "version": VERSION,
        "estado": estado,
        "pregunta": pregunta,
        "operacion": None,
        "restricciones": [],
        "cantidad_restricciones": 0,
        "restricciones_pendientes_host": [],
        "omisiones_conocidas": [],
        "cobertura_verificada": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": bool(
            isinstance(auditoria, dict)
            and auditoria.get("llm_invocado")
        ),
    }


def consolidar_interpretacion_semantica(
    pregunta: str,
) -> dict[str, Any]:
    texto = pregunta.strip() if isinstance(pregunta, str) else ""

    if not texto or len(texto) > 1000:
        return _base(texto, "pregunta_invalida")

    try:
        auditoria = auditar_restricciones_semanticas(texto)
    except Exception:
        return _base(texto, "auditoria_no_disponible")

    if (
        not isinstance(auditoria, dict)
        or auditoria.get("ok") is not True
        or auditoria.get("ejecutado") is not False
    ):
        return _base(
            texto, "auditoria_no_validada", auditoria
        )

    inicial = auditoria.get("extraccion_inicial")

    if (
        not isinstance(inicial, dict)
        or inicial.get("ok") is not True
        or inicial.get("ejecutado") is not False
        or inicial.get("operacion") not in {"listar", "contar"}
    ):
        return _base(
            texto, "extraccion_inicial_invalida", auditoria
        )

    consolidadas = []
    vistas = set()

    fuentes = (
        ("extraccion_inicial", inicial.get("restricciones")),
        ("auditoria", auditoria.get("omisiones_auditoria")),
    )

    for origen, elementos in fuentes:
        if not isinstance(elementos, list):
            return _base(
                texto, "contrato_restricciones_invalido", auditoria
            )

        for elemento in elementos:
            if not isinstance(elemento, dict):
                return _base(
                    texto, "restriccion_invalida", auditoria
                )

            tipo = elemento.get("tipo")
            evidencia = elemento.get("evidencia_textual")

            if (
                not isinstance(tipo, str)
                or not isinstance(evidencia, str)
                or not evidencia.strip()
                or len(evidencia) > 200
                or _normalizar(evidencia.strip())
                    not in _normalizar(texto)
            ):
                return _base(
                    texto, "evidencia_invalida", auditoria
                )

            clave = (tipo, _normalizar(evidencia.strip()))

            if clave in vistas:
                continue

            vistas.add(clave)

            restriccion = {
                "tipo": tipo,
                "evidencia_textual": evidencia.strip(),
                "origen": origen,
                "certificada_host": False,
            }

            if "valor_propuesto" in elemento:
                restriccion["valor_propuesto"] = (
                    elemento["valor_propuesto"]
                )

            consolidadas.append(restriccion)

    omisiones = inicial.get("capacidades_omitidas", [])

    if not isinstance(omisiones, list):
        return _base(
            texto, "omisiones_iniciales_invalidas", auditoria
        )

    # Las omisiones detectadas por el auditor se recuperan,
    # pero aún no se consideran restricciones certificadas.
    tipos = {r["tipo"] for r in consolidadas}

    equivalencias = {
        "filtro_explicito": "filtro",
    }

    no_representadas = sorted({
        equivalencias.get(c, c)
        for c in omisiones
        if isinstance(c, str)
        and equivalencias.get(c, c) not in tipos
    })

    return {
        **_base(texto, "consolidacion_diagnostica", auditoria),
        "ok": True,
        "operacion": inicial["operacion"],
        "restricciones": consolidadas,
        "cantidad_restricciones": len(consolidadas),
        "restricciones_pendientes_host": sorted(tipos),
        "omisiones_conocidas": no_representadas,
        # ARC002-B01:
        # Una lista vacia de restricciones no demuestra
        # que la pregunta original carezca de filtros.
        #
        # Este indicador es diagnostico. No certifica
        # extracciones no vacias ni autoriza ejecucion.
        "restricciones_vacias_pendientes": not bool(
            consolidadas
        ),
        "requiere_revision": bool(
            consolidadas
            or no_representadas
            or not consolidadas
        ),
        "llm_invocado": True,
    }
