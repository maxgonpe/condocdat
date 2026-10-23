"""Auditoría diagnóstica de restricciones omitidas.

No ejecuta ORM ni certifica planes.
"""
import json
import unicodedata
from typing import Any

from ia_local.services.host.respuesta_llm import consultar_ollama
from ia_local.services.host.interprete_datos import _extraer_json
from ia_local.services.llm.extraccion_semantica import (
    extraer_restricciones_semanticas,
    TIPOS,
)

VERSION = "IA-LLM008-F4-05-R3-02-v1"

PROMPT = """
Eres un auditor de fidelidad semántica.

Recibirás una PREGUNTA ORIGINAL y una EXTRACCIÓN PREVIA.

Tu tarea NO es repetir la extracción. Debes detectar las
restricciones explícitas de la pregunta que no estén
representadas en la extracción previa.

Presta especial atención a:
- Adjetivos o expresiones que restringen resultados.
- Estados de registros.
- Fechas y períodos.
- Cantidades y límites.
- Ordenamientos.
- Negaciones.
- Agrupaciones y cálculos.
- Valores vinculados a condiciones.

Devuelve exclusivamente JSON:

{
  "omisiones": [
    {
      "tipo": "filtro",
      "evidencia_textual": "pendientes"
    }
  ]
}

Tipos permitidos:
filtro, ordenamiento, limite, negacion_relacional,
fecha, agrupamiento, agregacion.

Reglas:
- No inventes restricciones.
- Toda evidencia debe aparecer literalmente en la pregunta.
- No repitas una restricción ya cubierta en la extracción previa.
- Si no encuentras omisiones, devuelve {"omisiones": []}.
- No construyas SQL ni ORM.
- No certifiques campos, modelos ni valores.
"""

def _normalizar(texto):
    valor = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(
        c for c in valor if not unicodedata.combining(c)
    )

def _salida(pregunta, estado, *, base=None, invocado=False):
    return {
        "ok": False,
        "version": VERSION,
        "estado": estado,
        "pregunta": pregunta,
        "extraccion_inicial": base,
        "omisiones_auditoria": [],
        "requiere_revision": True,
        "cobertura_verificada": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": invocado,
    }

def auditar_restricciones_semanticas(
    pregunta: str,
) -> dict[str, Any]:

    texto = pregunta.strip() if isinstance(pregunta, str) else ""

    if not texto or len(texto) > 1000:
        return _salida(texto, "pregunta_invalida")

    inicial = extraer_restricciones_semanticas(texto)

    if not isinstance(inicial, dict) or inicial.get("ok") is not True:
        return _salida(
            texto, "extraccion_inicial_no_valida",
            base=inicial,
            invocado=bool(
                isinstance(inicial, dict)
                and inicial.get("llm_invocado")
            ),
        )

    contexto = json.dumps(
        {
            "pregunta_original": texto,
            "extraccion_previa": {
                "operacion": inicial.get("operacion"),
                "restricciones": inicial.get("restricciones", []),
            },
        },
        ensure_ascii=False,
    )

    try:
        respuesta = consultar_ollama(
            pregunta=texto,
            contexto=contexto,
            prompt_sistema=PROMPT,
        )
    except Exception:
        return _salida(
            texto, "error_auditoria_llm",
            base=inicial, invocado=True,
        )

    if not isinstance(respuesta, dict) or respuesta.get("ok") is not True:
        return _salida(
            texto, "respuesta_auditoria_fallida",
            base=inicial, invocado=True,
        )

    propuesta = _extraer_json(respuesta.get("respuesta"))

    if (
        not isinstance(propuesta, dict)
        or set(propuesta) != {"omisiones"}
        or not isinstance(propuesta["omisiones"], list)
        or len(propuesta["omisiones"]) > 20
    ):
        return _salida(
            texto, "contrato_auditoria_invalido",
            base=inicial, invocado=True,
        )

    originales = inicial.get("restricciones", [])
    omisiones = []
    vistos = set()

    for elemento in propuesta["omisiones"]:
        if (
            not isinstance(elemento, dict)
            or set(elemento) != {"tipo", "evidencia_textual"}
        ):
            return _salida(
                texto, "omision_invalida",
                base=inicial, invocado=True,
            )

        tipo = elemento["tipo"]
        evidencia = elemento["evidencia_textual"]

        if (
            not isinstance(tipo, str)
            or tipo not in TIPOS
            or not isinstance(evidencia, str)
            or not evidencia.strip()
            or len(evidencia) > 200
            or _normalizar(evidencia.strip()) not in _normalizar(texto)
        ):
            return _salida(
                texto, "evidencia_auditoria_invalida",
                base=inicial, invocado=True,
            )

        clave = (tipo, _normalizar(evidencia.strip()))

        # El auditor debe comunicar diferencias, no duplicados
        # textuales ya presentes.
        if any(
            isinstance(r, dict)
            and r.get("tipo") == tipo
            and _normalizar(str(r.get("evidencia_textual", "")).strip())
                == clave[1]
            for r in originales
        ):
            continue

        if clave not in vistos:
            vistos.add(clave)
            omisiones.append({
                "tipo": tipo,
                "evidencia_textual": evidencia.strip(),
            })

    return {
        **_salida(
            texto,
            "omisiones_detectadas"
            if omisiones else "sin_omisiones_adicionales_detectadas",
            base=inicial,
            invocado=True,
        ),
        "ok": True,
        "omisiones_auditoria": omisiones,
        "requiere_revision": bool(
            omisiones or inicial.get("capacidades_omitidas")
        ),
    }
