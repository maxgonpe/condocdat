from __future__ import annotations

import json
import re
from typing import Any

from .catalogo_datos import (
    buscar_modelo_datos,
)
from .respuesta_llm import (
    consultar_ollama,
)
from .perfilador_datos import (
    perfilar_modelo,
)


# ============================================================
# CONTRATO
# ============================================================


OPERACIONES_PROPUESTAS = {
    "listar",
    "contar",
}


OPERADORES_PROPUESTOS = {
    "exact",
    "iexact",
    "contains",
    "icontains",
    "gt",
    "gte",
    "lt",
    "lte",
    "isnull",
    "year",
    "month",
    "day",
}


LIMITE_PREDETERMINADO = 20
LIMITE_MAXIMO_PROPUESTO = 100


EXPRESIONES_SIN_LIMITE = (
    "todos",
    "todas",
    "todo",
    "toda",
    "sin limite",
    "sin límite",
    "completo",
    "completa",
    "completos",
    "completas",
    "la totalidad",
)


def _solicita_sin_limite(
    pregunta: str,
) -> bool:
    """Detecta si el usuario pide explícitamente todos los registros."""
    texto = re.sub(
        r"\s+",
        " ",
        str(pregunta or "").strip().lower(),
    )
    if not texto:
        return False
    return any(
        expresion in texto
        for expresion in EXPRESIONES_SIN_LIMITE
    )


# ============================================================
# UTILIDADES
# ============================================================


def _texto(
    valor: Any,
) -> str:

    return str(
        valor
        or ""
    ).strip()


def _extraer_json(
    contenido: Any,
) -> dict[str, Any] | None:

    texto = _texto(
        contenido
    )

    if not texto:
        return None

    try:

        valor = json.loads(
            texto
        )

        if isinstance(
            valor,
            dict,
        ):
            return valor

    except Exception:
        pass

    texto = re.sub(
        r"^```(?:json)?\s*",
        "",
        texto,
        flags=re.IGNORECASE,
    )

    texto = re.sub(
        r"\s*```$",
        "",
        texto,
    )

    try:

        valor = json.loads(
            texto
        )

        if isinstance(
            valor,
            dict,
        ):
            return valor

    except Exception:
        pass

    inicio = texto.find(
        "{"
    )

    fin = texto.rfind(
        "}"
    )

    if (
        inicio >= 0
        and fin > inicio
    ):

        fragmento = texto[
            inicio:fin + 1
        ]

        try:

            valor = json.loads(
                fragmento
            )

            if isinstance(
                valor,
                dict,
            ):
                return valor

        except Exception:
            pass

    return None


# ============================================================
# MODELO
# ============================================================


def obtener_descripcion_modelo(
    referencia: str,
) -> dict[str, Any] | None:
    """
    Obtiene únicamente un modelo inequívoco del catálogo.
    """

    candidatos = buscar_modelo_datos(
        referencia
    )

    if len(
        candidatos
    ) != 1:
        return None

    return candidatos[
        0
    ]


# ============================================================
# CONTEXTO PARA QWEN
# ============================================================


def _campos_para_prompt(
    modelo: dict[str, Any],
) -> list[dict[str, Any]]:

    resultado = []

    for campo in modelo.get(
        "campos",
        [],
    ):

        if not campo.get(
            "consultable"
        ):
            continue

        resultado.append(
            {
                "nombre":
                    campo.get(
                        "nombre"
                    ),

                "tipo":
                    campo.get(
                        "tipo"
                    ),
            }
        )

    return resultado


def _perfiles_para_prompt(
    modelo: dict[str, Any],
) -> list[dict[str, Any]]:

    resultado = perfilar_modelo(
        modelo[
            "label"
        ],
        max_valores=15,
    )

    if not resultado.get(
        "ok"
    ):
        return []

    perfiles_crudos = [
        perfil
        for perfil
        in resultado.get(
            "perfiles",
            [],
        )
        if perfil.get(
            "ok"
        )
    ]

    perfiles_crudos.sort(
        key=lambda perfil: (
            int(
                perfil.get(
                    "total_distintos",
                    999999,
                )
            ),
            str(
                perfil.get(
                    "campo",
                    "",
                )
            ),
        )
    )

    perfiles = []

    for perfil in perfiles_crudos[:10]:

        valores = [
            item.get(
                "valor"
            )
            for item
            in perfil.get(
                "valores",
                [],
            )
            if item.get(
                "valor"
            )
            not in {
                None,
                "",
            }
        ]

        valores = valores[:15]

        if not valores:
            continue

        perfiles.append(
            {
                "campo":
                    perfil.get(
                        "campo"
                    ),

                "valores":
                    valores,
            }
        )

    return perfiles


def _construir_contexto(
    modelo: dict[str, Any],
    evidencia_entidad: dict[str, Any] | None = None,
) -> str:

    campos = _campos_para_prompt(
        modelo
    )

    perfiles = _perfiles_para_prompt(
        modelo
    )

    evidencia_host = (
        evidencia_entidad
        if isinstance(
            evidencia_entidad,
            dict,
        )
        else {}
    )

    bloque_evidencia = ""

    if evidencia_host:

        bloque_evidencia = (
            "\n\nEVIDENCIA REAL VALIDADA POR EL HOST:\n"
            + json.dumps(
                evidencia_host,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\n"
        )

    return (
        "MODELO DJANGO VALIDADO POR EL HOST:\n"
        f"{modelo['label']}\n\n"

        "TABLA:\n"
        f"{modelo['tabla']}\n\n"

        "CAMPOS CONSULTABLES REALES:\n"
        f"{json.dumps(campos, ensure_ascii=False, separators=(',', ':'))}\n\n"

        "VALORES REALES OBSERVADOS EN CAMPOS CATEGORICOS:\n"
        f"{json.dumps(perfiles, ensure_ascii=False, separators=(',', ':'))}\n\n"

        "OPERACIONES PERMITIDAS EN ESTA FASE:\n"
        "- listar\n"
        "- contar\n\n"

        "OPERADORES QUE PUEDES PROPONER:\n"
        + "\n".join(
            f"- {operador}"
            for operador
            in sorted(
                OPERADORES_PROPUESTOS
            )
        )
        + bloque_evidencia
    )


# ============================================================
# PROMPT
# ============================================================


def _prompt_sistema() -> str:

    return (
        "Eres un intérprete declarativo de consultas "
        "para Django.\n\n"

        "NO debes responder la pregunta del usuario.\n"
        "NO debes ejecutar nada.\n"
        "NO debes generar SQL.\n"
        "NO debes generar código Python.\n"
        "NO debes generar expresiones ORM.\n\n"

        "Tu tarea es transformar la pregunta en un plan "
        "de consulta declarativo.\n\n"

        "REGLAS OBLIGATORIAS:\n"
        "1. Usa solamente el modelo indicado por el host.\n"
        "2. Usa solamente campos incluidos explícitamente "
        "en CAMPOS CONSULTABLES REALES.\n"
        "3. No inventes campos.\n"
        "4. No inventes relaciones.\n"
        "5. No inventes otros modelos.\n"
        "6. Si una condición del usuario no puede asociarse "
        "con seguridad a un campo real, no inventes el campo; "
        "agrégala a condiciones_no_resueltas.\n"
        "7. Solo puedes proponer operaciones listar o contar.\n"
        "8. Los filtros deben ser declarativos.\n"
        "9. El campo de orden debe existir entre los campos "
        "consultables reales.\n"
        "10. Si el usuario no especifica un límite, usa 20.\n"
        "11. Nunca excedas un límite de 100.\n"
        "12. No asumas que un valor propuesto existe realmente "
        "en la base de datos. Solo interpreta el lenguaje.\n"
        "13. Si un campo tiene VALORES REALES OBSERVADOS, no "
        "propongas para ese campo un valor categórico que no "
        "aparezca entre esos valores.\n"
        "14. Si una expresión del usuario no puede relacionarse "
        "con seguridad con uno de los valores observados, agrégala "
        "a condiciones_no_resueltas.\n"
        "15. No inventes equivalencias semánticas entre valores "
        "observados y palabras del usuario.\n"
        "16. Si una expresión importante queda en "
        "condiciones_no_resueltas, NO agregues filtros intentando "
        "suponer posibles significados de esa expresión.\n"
        "17. No combines varios valores observados para aproximar "
        "una categoría desconocida.\n"
        "18. Si no existe evidencia suficiente para un filtro, "
        "omítelo.\n"
        "19. Si existe EVIDENCIA REAL VALIDADA POR EL HOST, "
        "puedes utilizarla como hecho comprobado.\n"
        "20. Una coincidencia textual validada por el HOST indica "
        "que la expresión indicada aparece realmente en el campo "
        "real indicado.\n"
        "21. Para una evidencia textual validada, puedes proponer "
        "un filtro icontains usando exclusivamente el campo y la "
        "frase demostrados por el HOST.\n"
        "22. No cambies el campo, el valor ni el modelo indicado "
        "por la evidencia HOST.\n"
        "23. Si la evidencia HOST es ambigua o no está resuelta, "
        "no la conviertas en filtro.\n\n"

        "Devuelve EXCLUSIVAMENTE JSON válido con esta forma:\n"
        "{\n"
        '  "modelo": "app.Model",\n'
        '  "operacion": "listar|contar",\n'
        '  "filtros": [\n'
        "    {\n"
        '      "campo": "nombre_campo",\n'
        '      "operador": "operador",\n'
        '      "valor": "valor"\n'
        "    }\n"
        "  ],\n"
        '  "orden": [\n'
        "    {\n"
        '      "campo": "nombre_campo",\n'
        '      "direccion": "asc|desc"\n'
        "    }\n"
        "  ],\n"
        '  "limite": 20,\n'
        "\n"
        "REGLA DE LÍMITE:\n"
        "- Si el usuario pide explícitamente todos/todas, la totalidad "
        "o sin límite, devuelve null en limite.\n"
        "- Si no pide totalidad y tampoco indica una cantidad, usa 20.\n"
        "- Si indica una cantidad concreta, úsala respetando el máximo permitido.\n"
        '  "condiciones_no_resueltas": []\n'
        "}\n\n"

        "No uses Markdown.\n"
        "No agregues explicaciones fuera del JSON."
    )


# ============================================================
# NORMALIZACIÓN DE PROPUESTA
# ============================================================


def _normalizar_propuesta(
    propuesta: dict[str, Any],
    *,
    modelo: dict[str, Any],
) -> dict[str, Any]:

    operacion = _texto(
        propuesta.get(
            "operacion"
        )
    ).lower()

    if operacion not in OPERACIONES_PROPUESTAS:
        operacion = "listar"

    filtros_crudos = propuesta.get(
        "filtros"
    )

    if not isinstance(
        filtros_crudos,
        list,
    ):
        filtros_crudos = []

    filtros = []

    for item in filtros_crudos:

        if not isinstance(
            item,
            dict,
        ):
            continue

        filtros.append(
            {
                "campo":
                    _texto(
                        item.get(
                            "campo"
                        )
                    ),

                "operador":
                    _texto(
                        item.get(
                            "operador"
                        )
                    ).lower(),

                "valor":
                    item.get(
                        "valor"
                    ),
            }
        )

    orden_crudo = propuesta.get(
        "orden"
    )

    if not isinstance(
        orden_crudo,
        list,
    ):
        orden_crudo = []

    orden = []

    for item in orden_crudo:

        if isinstance(
            item,
            str,
        ):

            campo = _texto(
                item
            )

            if campo:

                orden.append(
                    {
                        "campo":
                            campo,

                        "direccion":
                            "asc",
                    }
                )

            continue

        if not isinstance(
            item,
            dict,
        ):
            continue

        campo = _texto(
            item.get(
                "campo"
            )
        )

        direccion = _texto(
            item.get(
                "direccion",
                item.get(
                    "operador",
                    "asc",
                ),
            )
        ).lower()

        if direccion not in {
            "asc",
            "desc",
        }:
            direccion = "asc"

        if not campo:
            continue

        orden.append(
            {
                "campo":
                    campo,

                "direccion":
                    direccion,
            }
        )

    limite_crudo = propuesta.get(
        "limite",
        LIMITE_PREDETERMINADO,
    )

    if limite_crudo is None:
        limite = None
    else:
        try:
            limite = int(limite_crudo)
        except (TypeError, ValueError):
            limite = LIMITE_PREDETERMINADO

        limite = max(
            1,
            min(
                limite,
                LIMITE_MAXIMO_PROPUESTO,
            ),
        )

    condiciones = propuesta.get(
        "condiciones_no_resueltas"
    )

    if not isinstance(
        condiciones,
        list,
    ):
        condiciones = []

    condiciones = [
        _texto(
            item
        )
        for item
        in condiciones
        if _texto(
            item
        )
    ]

    # --------------------------------------------------------
    # POLITICA CONSERVADORA E2B
    # --------------------------------------------------------
    #
    # Si el LLM reconoce que una condición importante no pudo
    # resolverse, no conservamos filtros especulativos.
    #
    # El validador rechazará posteriormente el plan completo,
    # pero además mantenemos limpio el contrato declarativo.
    #

    if condiciones:
        filtros = []


    return {
        "modelo":
            modelo[
                "label"
            ],

        "operacion":
            operacion,

        "filtros":
            filtros,

        "orden":
            orden,

        "limite":
            limite,

        "condiciones_no_resueltas":
            condiciones,
    }


# ============================================================
# INTERPRETACIÓN
# ============================================================


def interpretar_consulta_datos(
    pregunta: str,
    *,
    modelo: str,
    evidencia_entidad: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Construye una PROPUESTA declarativa.

    Esta función NO valida filtros para ejecución
    y NO ejecuta ORM.
    """

    descripcion = obtener_descripcion_modelo(
        modelo
    )

    if descripcion is None:

        return {
            "ok":
                False,

            "pregunta":
                pregunta,

            "modelo":
                modelo,

            "llm_invocado":
                False,

            "error": {
                "tipo":
                    "modelo_no_resuelto",

                "mensaje":
                    (
                        "El modelo no pudo resolverse "
                        "de forma inequívoca en el catálogo."
                    ),
            },
        }

    contexto = _construir_contexto(
        descripcion,
        evidencia_entidad=evidencia_entidad,
    )

    resultado_llm = consultar_ollama(
        pregunta=pregunta,
        contexto=contexto,
        prompt_sistema=_prompt_sistema(),
    )

    if not resultado_llm.get(
        "ok"
    ):

        return {
            "ok":
                False,

            "pregunta":
                pregunta,

            "modelo":
                descripcion[
                    "label"
                ],

            "llm_invocado":
                True,

            "error":
                resultado_llm,
        }

    propuesta_cruda = _extraer_json(
        resultado_llm.get(
            "respuesta"
        )
    )

    if propuesta_cruda is None:

        return {
            "ok":
                False,

            "pregunta":
                pregunta,

            "modelo":
                descripcion[
                    "label"
                ],

            "llm_invocado":
                True,

            "error": {
                "tipo":
                    "json_invalido",

                "mensaje":
                    (
                        "Qwen no devolvió un plan "
                        "de datos JSON válido."
                    ),

                "respuesta_cruda":
                    resultado_llm.get(
                        "respuesta"
                    ),
            },
        }

    propuesta = _normalizar_propuesta(
        propuesta_cruda,
        modelo=descripcion,
    )

    if (
        propuesta.get("operacion") == "listar"
        and _solicita_sin_limite(pregunta)
    ):
        propuesta["limite"] = None

    return {
        "ok":
            True,

        "pregunta":
            pregunta,

        "modelo":
            descripcion[
                "label"
            ],

        "llm_invocado":
            True,

        "propuesta":
            propuesta,

        "propuesta_cruda":
            propuesta_cruda,

        "modelo_llm":
            resultado_llm.get(
                "modelo"
            ),

        "metricas_llm": {
            "eval_count":
                resultado_llm.get(
                    "eval_count"
                ),

            "prompt_eval_count":
                resultado_llm.get(
                    "prompt_eval_count"
                ),

            "total_duration":
                resultado_llm.get(
                    "total_duration"
                ),
        },

        "evidencia_entidad":
            evidencia_entidad,

        "catalogo": {
            "tabla":
                descripcion[
                    "tabla"
                ],

            "campos_consultables":
                descripcion[
                    "campos_consultables"
                ],
        },
    }
