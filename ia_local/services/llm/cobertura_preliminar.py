"""Contrato preliminar de cobertura semántica.

Detecta capacidades explícitas. No valida filtros, no invoca
Qwen y no ejecuta ORM.
"""
import re
import unicodedata
from typing import Any

from ia_local.services.llm.intencion_operacional import (
    detectar_intencion_operacional,
)

VERSION = "IA-LLM008-F4-05-R2-v1"

def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(
        caracter for caracter in texto
        if not unicodedata.combining(caracter)
    )

def analizar_cobertura_semantica(pregunta: str) -> dict[str, Any]:
    texto = pregunta.strip() if isinstance(pregunta, str) else ""

    base = {
        "ok": False,
        "version": VERSION,
        "pregunta": texto,
        "estado": "pregunta_invalida",
        "accion_host": None,
        "capacidades": [],
        "capacidades_pendientes": [],
        "cobertura_completa": False,
        "ejecutado": False,
        "llm_invocado": False,
    }

    if not texto or len(texto) > 1000:
        return base

    try:
        operacional = detectar_intencion_operacional(texto)
    except Exception:
        return {**base, "estado": "detector_no_disponible"}

    if (
        not isinstance(operacional, dict)
        or operacional.get("ok") is not True
        or operacional.get("detectada") is not True
    ):
        return {**base, "estado": "intencion_no_resuelta"}

    accion = operacional.get("accion_host")
    if accion not in {"listar", "contar"}:
        return {**base, "estado": "operacion_no_soportada"}

    normalizada = _normalizar(texto)
    capacidades = []

    if accion == "contar":
        capacidades.append("conteo")
    else:
        capacidades.append("listado")

    patrones = {
        "ordenamiento": (
            r"\b(?:ultim\w*|primer\w*|recient\w*|"
            r"ordenad\w*|ordenar|ascendente|descendente|"
            r"mas\s+nuev\w*|mas\s+antigu\w*)\b"
        ),
        "negacion_relacional": (
            r"\b(?:sin|ningun\w*|"
            r"no\s+(?:tien\w*|pose\w*|contien\w*|"
            r"estan?\s+asociad\w*))\b"
        ),
        "limite": (
            r"\b(?:mostrar|muestrame|listar|ver|dame|"
            r"muestreme|quiero|necesito)\s+"
            r"(?:los|las|unos|unas)?\s*\d+\s+\w+"
        ),
        "filtro_explicito": (
            r"\b(?:con\s+estado|en\s+estado|"
            r"cuyo\s+estado|cuyos\s+estados|"
            r"donde|que\s+esten|que\s+sean)\b"
        ),
    }

    for capacidad, patron in patrones.items():
        if re.search(patron, normalizada):
            capacidades.append(capacidad)

    # La interpretación relacional actual admite únicamente
    # el listado simple. Las demás capacidades quedan pendientes.
    pendientes = [
        capacidad for capacidad in capacidades
        if capacidad != "listado"
    ]

    return {
        **base,
        "ok": True,
        "estado": (
            "capacidades_pendientes"
            if pendientes else "listado_simple_candidato"
        ),
        "accion_host": accion,
        "capacidades": capacidades,
        "capacidades_pendientes": pendientes,
        # No equivale a fidelidad semántica total:
        # solo acredita ausencia de señales reconocidas.
        "cobertura_completa": False,
    }
