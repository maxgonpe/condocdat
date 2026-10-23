"""Extracción declarativa de restricciones con Qwen.

No ejecuta ORM, no certifica campos y no autoriza planes.
"""
import json
import unicodedata
from typing import Any

from ia_local.services.host.respuesta_llm import consultar_ollama
from ia_local.services.host.interprete_datos import _extraer_json
from ia_local.services.llm.cobertura_preliminar import (
    analizar_cobertura_semantica,
)

VERSION = "IA-LLM008-F4-05-R3-01-v1"

TIPOS = {
    "filtro",
    "ordenamiento",
    "limite",
    "negacion_relacional",
    "fecha",
    "agrupamiento",
    "agregacion",
}

EQUIVALENCIAS = {
    "filtro_explicito": "filtro",
    "ordenamiento": "ordenamiento",
    "limite": "limite",
    "negacion_relacional": "negacion_relacional",
    "conteo": "conteo",
}

PROMPT = """
Eres un analizador semántico de consultas empresariales.

Tu responsabilidad es extraer todas las restricciones explícitas
de la pregunta, sin resolverlas ni ejecutarlas.

Devuelve exclusivamente un objeto JSON con esta estructura:

{
  "operacion": "listar",
  "restricciones": [
    {
      "tipo": "ordenamiento",
      "evidencia_textual": "últimos"
    },
    {
      "tipo": "limite",
      "evidencia_textual": "cinco",
      "valor_propuesto": 5
    }
  ]
}

Reglas:
- operacion solo puede ser "listar", "contar" o "no_resuelta".
- restricciones debe ser una lista.
- Tipos permitidos: filtro, ordenamiento, limite,
  negacion_relacional, fecha, agrupamiento, agregacion.
- Extrae todas las condiciones solicitadas, no solamente una.
- evidencia_textual debe ser una cita literal de la pregunta.
- No inventes condiciones ni valores.
- No inventes nombres de modelos, campos ni relaciones.
- No devuelvas SQL, rutas ORM ni código Python.
- No introduzcas una condición de filtro solo porque
  la pregunta mencione una entidad.
- Si no hay restricciones explícitas, devuelve lista vacía.
- Si desconoces la operación, utiliza "no_resuelta".
- Un conteo se representa en "operacion", no como filtro.
- Devuelve JSON válido, sin explicación adicional.
"""

def _normalizar(valor: str) -> str:
    valor = unicodedata.normalize("NFKD", valor.casefold())
    return "".join(
        c for c in valor if not unicodedata.combining(c)
    )

def _base(pregunta: str, estado: str, invocado=False):
    return {
        "ok": False,
        "version": VERSION,
        "estado": estado,
        "pregunta": pregunta,
        "operacion": None,
        "restricciones": [],
        "capacidades_detectadas": [],
        "capacidades_omitidas": [],
        "cobertura_verificada": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": invocado,
    }

def extraer_restricciones_semanticas(pregunta: str) -> dict[str, Any]:
    texto = pregunta.strip() if isinstance(pregunta, str) else ""

    if not texto or len(texto) > 1000:
        return _base(texto, "pregunta_invalida")

    cobertura = analizar_cobertura_semantica(texto)

    if not isinstance(cobertura, dict) or cobertura.get("ok") is not True:
        return _base(texto, "cobertura_preliminar_no_disponible")

    accion = cobertura.get("accion_host")

    if accion not in {"listar", "contar"}:
        return _base(texto, "operacion_no_soportada")

    contexto = (
        "Analiza la pregunta de forma completa. "
        "No tienes autorización para ejecutar consultas, "
        "inventar campos ni decidir que una restricción "
        "está certificada."
    )

    try:
        respuesta = consultar_ollama(
            pregunta=texto,
            contexto=contexto,
            prompt_sistema=PROMPT,
        )
    except Exception:
        return _base(texto, "error_llm", True)

    if not isinstance(respuesta, dict) or respuesta.get("ok") is not True:
        return _base(texto, "respuesta_llm_fallida", True)

    propuesta = _extraer_json(respuesta.get("respuesta"))

    if not isinstance(propuesta, dict):
        return _base(texto, "json_no_resuelto", True)

    if set(propuesta) != {"operacion", "restricciones"}:
        return _base(texto, "contrato_invalido", True)

    if propuesta["operacion"] != accion:
        return _base(texto, "operacion_inconsistente", True)

    restricciones = propuesta["restricciones"]

    if not isinstance(restricciones, list) or len(restricciones) > 20:
        return _base(texto, "restricciones_invalidas", True)

    verificadas = []

    for elemento in restricciones:
        if not isinstance(elemento, dict):
            return _base(texto, "restriccion_invalida", True)

        if not {"tipo", "evidencia_textual"}.issubset(elemento):
            return _base(texto, "restriccion_incompleta", True)

        if set(elemento) - {
            "tipo", "evidencia_textual", "valor_propuesto"
        }:
            return _base(texto, "atributos_no_permitidos", True)

        tipo = elemento["tipo"]
        evidencia = elemento["evidencia_textual"]

        if tipo not in TIPOS:
            return _base(texto, "tipo_no_permitido", True)

        if (
            not isinstance(evidencia, str)
            or not evidencia.strip()
            or len(evidencia) > 200
            or _normalizar(evidencia.strip()) not in _normalizar(texto)
        ):
            return _base(texto, "evidencia_no_verificable", True)

        nuevo = {
            "tipo": tipo,
            "evidencia_textual": evidencia.strip(),
        }

        if "valor_propuesto" in elemento:
            valor = elemento["valor_propuesto"]

            if not (
                valor is None
                or isinstance(valor, str) and len(valor) <= 100
                or type(valor) is int and 0 <= valor <= 1000000
                or type(valor) is float and 0 <= valor <= 1000000
                or type(valor) is bool
            ):
                return _base(texto, "valor_propuesto_invalido", True)

            nuevo["valor_propuesto"] = valor

        verificadas.append(nuevo)

    tipos_encontrados = {r["tipo"] for r in verificadas}

    pendientes = cobertura.get("capacidades_pendientes", [])

    requeridas = {
        EQUIVALENCIAS[tipo]
        for tipo in pendientes
        if tipo in EQUIVALENCIAS and tipo != "conteo"
    }

    omitidas = sorted(requeridas - tipos_encontrados)

    resultado = {
        **_base(texto, "extraccion_validada", True),
        "ok": True,
        "operacion": accion,
        "restricciones": verificadas,
        "capacidades_detectadas": sorted(tipos_encontrados),
        "capacidades_omitidas": omitidas,
        "estado": (
            "omisiones_detectadas"
            if omitidas
            else "extraccion_validada"
        ),
        # Una evidencia literal no demuestra comprensión completa
        # ni certificación de la restricción contra HOST.
        "cobertura_verificada": False,
    }

    return resultado
