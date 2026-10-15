from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from django.conf import settings

from .contexto_semantico import (
    construir_contexto_llm,
)


# ============================================================
# CONFIGURACIÓN
# ============================================================


MODELO_DEFAULT = (
    "qwen3:4b-instruct-2507-q4_K_M"
)

OLLAMA_URL_DEFAULT = (
    "http://127.0.0.1:11434"
)


def _obtener_configuracion() -> dict[str, Any]:
    """
    Prioridad:

    1. settings.py
    2. variables de entorno
    3. valores por defecto

    Esto mantiene HOST012 portable.
    """

    url = getattr(
        settings,
        "IA_LOCAL_OLLAMA_URL",
        None,
    )

    if not url:
        url = os.getenv(
            "IA_LOCAL_OLLAMA_URL"
        )

    if not url:
        url = os.getenv(
            "OLLAMA_HOST"
        )

    if not url:
        url = OLLAMA_URL_DEFAULT

    modelo = getattr(
        settings,
        "IA_LOCAL_OLLAMA_MODEL",
        None,
    )

    if not modelo:
        modelo = os.getenv(
            "IA_LOCAL_OLLAMA_MODEL"
        )

    if not modelo:
        modelo = os.getenv(
            "OLLAMA_MODEL"
        )

    if not modelo:
        modelo = MODELO_DEFAULT

    timeout = getattr(
        settings,
        "IA_LOCAL_OLLAMA_TIMEOUT",
        120,
    )

    return {
        "url":
            str(
                url
            ).rstrip(
                "/"
            ),

        "modelo":
            str(
                modelo
            ),

        "timeout":
            int(
                timeout
            ),
    }


# ============================================================
# PROMPT DEL SISTEMA
# ============================================================

def _construir_prompt_sistema() -> str:
    return (
        "Eres un analizador técnico de un proyecto Django. "
        "Responde exclusivamente a partir de la evidencia "
        "estructural proporcionada.\n\n"

        "CONTRATO DE EVIDENCIA:\n"

        "1. Las relaciones marcadas como "
        "'USOS DE MODELO DEMOSTRADOS' son hechos "
        "estructurales confirmados por el analizador.\n"

        "2. Si una relación dice que una función usa un modelo "
        "mediante determinadas operaciones ORM, puedes afirmarlo "
        "directamente como hecho.\n"

        "3. Una relación URL -> view demuestra únicamente que "
        "esa ruta resuelve a esa view.\n"

        "4. Una relación con un template demuestra únicamente "
        "que existe esa asociación estructural. No demuestra que "
        "la view lo renderice directamente.\n"

        "5. No deduzcas comportamiento a partir de nombres. "
        "Palabras como 'ia', 'json', 'consulta', 'pdf', 'excel' "
        "o similares dentro de identificadores no demuestran "
        "qué hace una función.\n"

        "6. No inventes archivos, funciones, modelos, tablas, "
        "URLs, templates, llamadas, datos ni comportamiento.\n"

        "7. No uses conocimiento general de Django para completar "
        "información ausente de la evidencia.\n"

        "8. Si la evidencia demuestra una relación, no la niegues "
        "por exigir información adicional que el analizador ya "
        "ha certificado.\n"

        "9. Si la evidencia no demuestra el comportamiento interno "
        "de una función o view, dilo expresamente.\n"

        "10. Conserva exactamente los identificadores técnicos. "
        "No los abrevies, corrijas, reformules ni reescribas.\n"

        "11. Distingue correctamente modelo, función, view, URL, "
        "template, tabla y operación ORM.\n"

        "12. Responde en español, de forma concreta y técnica.\n\n"

        "REGLA FINAL:\n"
        "Afirma los hechos explícitamente demostrados por la "
        "evidencia y no agregues ninguna conclusión que exceda "
        "esa evidencia."
    )


# ============================================================
# OLLAMA
# ============================================================


def consultar_ollama(
    *,
    pregunta: str,
    contexto: str,
    prompt_sistema: str | None = None,
) -> dict[str, Any]:

    config = (
        _obtener_configuracion()
    )

    endpoint = (
        f"{config['url']}"
        f"/api/chat"
    )

    payload = {
        "model":
            config[
                "modelo"
            ],

        "stream":
            False,

        "options": {
            "temperature":
                0,
        },

        "messages": [
            {
                "role":
                    "system",

                "content":
                    (
                        prompt_sistema
                        or _construir_prompt_sistema()
                    ),
            },
            {
                "role":
                    "user",

                "content": (
                    f"{contexto}"
                    "\n\n"
                    "PREGUNTA A RESPONDER:\n"
                    f"{pregunta}"
                ),
            },
        ],
    }

    datos = json.dumps(
        payload
    ).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        endpoint,
        data=datos,
        headers={
            "Content-Type":
                "application/json",
        },
        method="POST",
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=config[
                "timeout"
            ],
        ) as response:

            cuerpo = response.read()

    except urllib.error.HTTPError as exc:

        detalle = ""

        try:
            detalle = (
                exc.read()
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )
        except Exception:
            pass

        return {
            "ok":
                False,

            "tipo_error":
                "http",

            "error":
                f"HTTP {exc.code}",

            "detalle":
                detalle,

            "modelo":
                config[
                    "modelo"
                ],

            "endpoint":
                endpoint,
        }

    except urllib.error.URLError as exc:

        return {
            "ok":
                False,

            "tipo_error":
                "conexion",

            "error":
                str(
                    exc.reason
                ),

            "modelo":
                config[
                    "modelo"
                ],

            "endpoint":
                endpoint,
        }

    except Exception as exc:

        return {
            "ok":
                False,

            "tipo_error":
                "general",

            "error":
                str(
                    exc
                ),

            "modelo":
                config[
                    "modelo"
                ],

            "endpoint":
                endpoint,
        }

    try:

        respuesta = json.loads(
            cuerpo.decode(
                "utf-8"
            )
        )

    except Exception as exc:

        return {
            "ok":
                False,

            "tipo_error":
                "json",

            "error":
                str(
                    exc
                ),

            "respuesta_cruda":
                cuerpo.decode(
                    "utf-8",
                    errors="replace",
                ),

            "modelo":
                config[
                    "modelo"
                ],

            "endpoint":
                endpoint,
        }

    mensaje = (
        respuesta.get(
            "message",
            {}
        )
    )

    contenido = str(
        mensaje.get(
            "content",
            ""
        )
        or ""
    ).strip()

    if not contenido:

        return {
            "ok":
                False,

            "tipo_error":
                "respuesta_vacia",

            "error":
                "Ollama no devolvió contenido.",

            "respuesta":
                respuesta,

            "modelo":
                config[
                    "modelo"
                ],

            "endpoint":
                endpoint,
        }

    return {
        "ok":
            True,

        "respuesta":
            contenido,

        "modelo":
            config[
                "modelo"
            ],

        "endpoint":
            endpoint,

        "eval_count":
            respuesta.get(
                "eval_count"
            ),

        "prompt_eval_count":
            respuesta.get(
                "prompt_eval_count"
            ),

        "total_duration":
            respuesta.get(
                "total_duration"
            ),
    }


# ============================================================
# CONSULTA HOST COMPLETA
# ============================================================


def responder_pregunta_host(
    pregunta: str,
    *,
    profundidad: int = 3,
) -> dict[str, Any]:
    """
    Circuito HOST011 -> Qwen.

    Si HOST011 no encuentra evidencia, Qwen NO se invoca.
    """

    contexto = (
        construir_contexto_llm(
            pregunta,
            profundidad=profundidad,
        )
    )

    if not contexto[
        "hay_evidencia"
    ]:

        return {
            "ok":
                True,

            "respondido_por":
                "host",

            "llm_invocado":
                False,

            "pregunta":
                pregunta,

            "hay_evidencia":
                False,

            "deteccion":
                contexto[
                    "deteccion"
                ],

            "respuesta": (
                "No se encontró evidencia estructural "
                "suficiente en el proyecto para responder "
                "esta pregunta."
            ),

            "contexto":
                contexto[
                    "contexto_texto"
                ],
        }

    resultado_llm = (
        consultar_ollama(
            pregunta=pregunta,
            contexto=contexto[
                "contexto_texto"
            ],
        )
    )

    if not resultado_llm[
        "ok"
    ]:

        return {
            "ok":
                False,

            "respondido_por":
                "llm",

            "llm_invocado":
                True,

            "pregunta":
                pregunta,

            "hay_evidencia":
                True,

            "deteccion":
                contexto[
                    "deteccion"
                ],

            "contexto":
                contexto[
                    "contexto_texto"
                ],

            "error":
                resultado_llm,
        }

    return {
        "ok":
            True,

        "respondido_por":
            "llm",

        "llm_invocado":
            True,

        "pregunta":
            pregunta,

        "hay_evidencia":
            True,

        "deteccion":
            contexto[
                "deteccion"
            ],

        "modelo":
            resultado_llm[
                "modelo"
            ],

        "respuesta":
            resultado_llm[
                "respuesta"
            ],

        "metricas": {
            "prompt_eval_count":
                resultado_llm.get(
                    "prompt_eval_count"
                ),

            "eval_count":
                resultado_llm.get(
                    "eval_count"
                ),

            "total_duration":
                resultado_llm.get(
                    "total_duration"
                ),
        },

        "contexto":
            contexto[
                "contexto_texto"
            ],
    }