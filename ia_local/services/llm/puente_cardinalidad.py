"""Cruza la consolidación semántica con cardinalidad transversal."""
from typing import Any

from ia_local.services.llm.consolidacion_semantica import (
    consolidar_interpretacion_semantica,
)
from ia_local.services.llm.cardinalidad_natural import (
    detectar_cardinalidad_natural,
)

VERSION = "IA-LLM008-F5-03-v1"


def _base(pregunta, estado):
    return {
        "ok": False,
        "version": VERSION,
        "estado": estado,
        "pregunta": pregunta,
        "cardinalidad": None,
        "restricciones_pendientes_host": [],
        "cobertura_verificada": False,
        "certificada_host": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }


def integrar_cardinalidad_semantica(
    pregunta: str,
) -> dict[str, Any]:
    texto = pregunta.strip() if isinstance(pregunta, str) else ""

    if not texto or len(texto) > 1000:
        return _base(texto, "pregunta_invalida")

    try:
        consolidado = consolidar_interpretacion_semantica(texto)
        cardinalidad = detectar_cardinalidad_natural(texto)
    except Exception:
        return _base(texto, "dependencia_no_disponible")

    if (
        not isinstance(consolidado, dict)
        or consolidado.get("ok") is not True
        or consolidado.get("ejecutado") is not False
        or consolidado.get("ejecutable") is not False
        or not isinstance(cardinalidad, dict)
        or cardinalidad.get("ok") is not True
    ):
        return _base(texto, "contrato_previo_invalido")

    restricciones = consolidado.get("restricciones")
    if not isinstance(restricciones, list):
        return _base(texto, "restricciones_invalidas")

    limites = [
        r for r in restricciones
        if isinstance(r, dict) and r.get("tipo") == "limite"
    ]

    pendientes = list(
        consolidado.get("restricciones_pendientes_host") or []
    )

    salida = {
        **_base(texto, "integracion_diagnostica"),
        "ok": True,
        "operacion": consolidado.get("operacion"),
        "cardinalidad": cardinalidad,
        "restricciones": restricciones,
        "restricciones_pendientes_host": pendientes,
        "omisiones_conocidas": consolidado.get(
            "omisiones_conocidas", []
        ),
        "llm_invocado": bool(consolidado.get("llm_invocado")),
    }

    if cardinalidad.get("totalidad_solicitada") is True:
        # Totalidad expresa una intención, no autorización
        # para entregar un conjunto sin límites de ejecución.
        if limites:
            return {
                **salida,
                "ok": False,
                "estado": "cardinalidad_contradictoria",
            }
        return {
            **salida,
            "estado": "totalidad_detectada",
        }

    if not limites:
        if cardinalidad.get("detectada") is True:
            # El detector encontró un límite que Qwen omitió.
            return {
                **salida,
                "estado": "limite_omitido_en_extraccion",
                "restricciones_pendientes_host": sorted(
                    set(pendientes) | {"limite"}
                ),
            }
        return {
            **salida,
            "estado": "sin_limite_explicito",
        }

    if len(limites) != 1:
        return {
            **salida,
            "ok": False,
            "estado": "multiples_limites_no_resueltos",
        }

    limite = limites[0]
    propuesta = limite.get("valor_propuesto")
    cantidad_original = cardinalidad.get("cantidad_original")
    cantidad_autorizada = cardinalidad.get("cantidad_solicitada")

    if (
        cardinalidad.get("detectada") is not True
        or cardinalidad.get("totalidad_solicitada") is not False
        or type(propuesta) is not int
        or type(cantidad_original) is not int
        or type(cantidad_autorizada) is not int
    ):
        return {
            **salida,
            "estado": "limite_pendiente_verificacion",
        }

    if propuesta != cantidad_original:
        return {
            **salida,
            "ok": False,
            "estado": "cantidad_propuesta_inconsistente",
        }

    if cantidad_autorizada < 1:
        return {
            **salida,
            "ok": False,
            "estado": "cantidad_autorizada_invalida",
        }

    return {
        **salida,
        "estado": "cardinalidad_conciliada",
        "cantidad_original": cantidad_original,
        "cantidad_autorizada": cantidad_autorizada,
        "limitada_por_politica": (
            cardinalidad.get("limitada_por_politica") is True
        ),
        # La conciliación es local; no equivale a certificación HOST.
        "cardinalidad_validada_localmente": True,
    }
