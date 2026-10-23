"""IA-LLM007-F2: contrato seguro de aclaración, independiente del host.

No ejecuta ORM ni planes. Las selecciones son propuestas verificadas, nunca autorización.
"""
from __future__ import annotations

from typing import Any
from django.apps import apps
from .resolvedor_entidad_datos import resolver_entidad_datos


def _puntaje(candidato: dict[str, Any]) -> int | float | None:
    for clave in ("puntaje_total", "puntaje", "puntaje_textual"):
        valor = candidato.get(clave)
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            return valor
    return None


def _opciones_certificadas(resultado: dict[str, Any], limite: int = 8) -> list[dict[str, str]]:
    candidatos = resultado.get("candidatos") or []
    if not isinstance(candidatos, list):
        return []
    candidatos = [c for c in candidatos if isinstance(c, dict)]
    if len(candidatos) < 2:
        return []

    # Si existe puntuación, solo las opciones empatadas con el primer candidato
    # constituyen una ambigüedad demostrada, no el resto del ranking.
    mejor = _puntaje(candidatos[0])
    if mejor is not None:
        candidatos = [c for c in candidatos if _puntaje(c) == mejor]

    opciones = []
    vistos = set()
    for candidato in candidatos:
        etiqueta = candidato.get("modelo") or candidato.get("entidad") or candidato.get("label")
        if not isinstance(etiqueta, str) or not etiqueta or etiqueta in vistos:
            continue
        try:
            modelo = apps.get_model(etiqueta, require_ready=True)
        except (LookupError, ValueError):
            continue
        if modelo is None or modelo._meta.label != etiqueta:
            continue
        if modelo._meta.app_label == "ia_local" or modelo._meta.proxy or modelo._meta.abstract:
            continue
        vistos.add(etiqueta)
        opciones.append({
            "id": etiqueta,
            "etiqueta": str(modelo._meta.verbose_name),
            "modelo": etiqueta,
        })
        if len(opciones) >= limite:
            break
    return opciones


def preparar_aclaracion(pregunta: str, *, limite: int = 8) -> dict[str, Any]:
    """Devuelve alternativas verificadas o un estado de no aclaración."""
    if not isinstance(pregunta, str) or not pregunta.strip():
        return {"ok": False, "estado": "pregunta_invalida", "ejecutado": False, "llm_invocado": False}
    if not isinstance(limite, int) or isinstance(limite, bool) or not (2 <= limite <= 25):
        return {"ok": False, "estado": "limite_invalido", "ejecutado": False, "llm_invocado": False}
    resolucion = resolver_entidad_datos(pregunta)
    estado = resolucion.get("estado_resolucion")
    if estado != "ambiguo":
        return {
            "ok": False, "estado": "aclaracion_no_necesaria" if estado == "resuelto" else "sin_alternativas_certificadas",
            "estado_resolucion": estado, "pregunta_original": pregunta,
            "ejecutado": False, "llm_invocado": False,
        }
    opciones = _opciones_certificadas(resolucion, limite)
    if len(opciones) < 2:
        return {
            "ok": False, "estado": "sin_alternativas_certificadas",
            "estado_resolucion": estado, "pregunta_original": pregunta,
            "ejecutado": False, "llm_invocado": False,
        }
    return {
        "ok": True, "estado": "requiere_aclaracion", "estado_resolucion": estado,
        "pregunta_original": pregunta,
        "pregunta_aclaracion": "¿A cuál de estas entidades te refieres?",
        "opciones": opciones, "ejecutado": False, "llm_invocado": False,
    }


def verificar_eleccion(pregunta_original: str, opcion_id: str) -> dict[str, Any]:
    """Recertifica la opción; no autoriza ejecución ni altera la pregunta."""
    aclaracion = preparar_aclaracion(pregunta_original)
    if not aclaracion.get("ok"):
        return {"ok": False, "estado": "aclaracion_no_disponible", "ejecutado": False, "llm_invocado": False}
    ids = {o["id"] for o in aclaracion["opciones"]}
    if not isinstance(opcion_id, str) or opcion_id not in ids:
        return {"ok": False, "estado": "eleccion_no_certificada", "ejecutado": False, "llm_invocado": False}
    return {
        "ok": True, "estado": "eleccion_certificada", "pregunta_original": pregunta_original,
        "entidad_seleccionada": opcion_id,
        "requiere_validacion_host": True,
        "ejecutado": False, "llm_invocado": False,
    }
