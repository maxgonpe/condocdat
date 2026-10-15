from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from .contexto_semantico import (
    construir_contexto_semantico,
)
from .respuesta_llm import (
    consultar_ollama,
)


# ============================================================
# CONSTANTES
# ============================================================


TIPOS_VALIDOS = {
    "estructura",
    "datos",
    "desconocida",
}


# Verbos y expresiones genéricas que indican intención
# de consultar registros/datos.
#
# IMPORTANTE:
# No contienen conocimiento de ningún proyecto anfitrión.
PATRONES_DATOS = (
    r"\bmostrar\b",
    r"\bmuestrame\b",
    r"\blistar\b",
    r"\blista\b",
    r"\bdame\b",
    r"\bbuscar\b",
    r"\bbusca\b",
    r"\bencontrar\b",
    r"\bfiltrar\b",
    r"\bfiltra\b",
    r"\bcuantos\b",
    r"\bcuantas\b",
    r"\btotal\b",
    r"\bregistros\b",
    r"\bpendientes\b",
    r"\bactivos\b",
    r"\binactivos\b",
    r"\bdel mes\b",
    r"\bde este mes\b",
    r"\bde agosto\b",
    r"\bde septiembre\b",
)


# Palabras que apuntan explícitamente a estructura/código,
# incluso cuando HOST todavía no encuentra una entidad real.
PATRONES_ESTRUCTURA = (
    r"\bfuncion\b",
    r"\bfunciones\b",
    r"\bmetodo\b",
    r"\bmetodos\b",
    r"\bclase\b",
    r"\bclases\b",
    r"\bmodelo\b",
    r"\bmodelos\b",
    r"\burl\b",
    r"\burls\b",
    r"\bview\b",
    r"\bvista\b",
    r"\bvistas\b",
    r"\btemplate\b",
    r"\btemplates\b",
    r"\bimport\b",
    r"\bimports\b",
    r"\btabla\b",
    r"\btablas\b",
    r"\borm\b",
    r"\barchivo\b",
    r"\barchivos\b",
    r"\bllama\b",
    r"\bllaman\b",
    r"\bdefine\b",
    r"\bdefinida\b",
    r"\bdefinido\b",
    r"\busa\b",
    r"\busan\b",
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


def _normalizar(
    valor: Any,
) -> str:

    texto = _texto(
        valor
    )

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        caracter
        for caracter
        in texto
        if not unicodedata.combining(
            caracter
        )
    )

    texto = texto.lower()

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()


def _coincide_patron(
    texto: str,
    patrones: tuple[str, ...],
) -> bool:

    normalizado = _normalizar(
        texto
    )

    for patron in patrones:

        if re.search(
            patron,
            normalizado,
        ):
            return True

    return False


def _primer_valor(
    item: dict[str, Any],
    *claves: str,
) -> str | None:

    for clave in claves:

        valor = item.get(
            clave
        )

        if valor not in (
            None,
            "",
            [],
            {},
        ):
            return _texto(
                valor
            )

    return None


# ============================================================
# EXTRACCIÓN DE ENTIDADES DETECTADAS
# ============================================================


def _entidad_modelo(
    item: dict[str, Any],
) -> str | None:

    return _primer_valor(
        item,
        "label",
        "modelo",
        "model",
        "qualname",
        "nombre",
        "name",
        "tabla",
    )


def _entidad_simbolo(
    item: dict[str, Any],
) -> str | None:

    return _primer_valor(
        item,
        "qualname",
        "simbolo",
        "nombre",
        "name",
        "view",
        "funcion",
    )


def _entidad_url(
    item: dict[str, Any],
) -> str | None:

    return _primer_valor(
        item,
        "ruta",
        "route",
        "namespace_name",
        "name",
        "namespace",
        "view",
    )


# ============================================================
# ACCIÓN ESTRUCTURAL
# ============================================================


def _accion_estructura(
    pregunta: str,
) -> str:

    texto = _normalizar(
        pregunta
    )

    if re.search(
        r"\b(quien|que)\s+llama",
        texto,
    ):
        return "buscar_llamadores"

    if re.search(
        r"\b(us(a|an)|utiliza|utilizan)\b",
        texto,
    ):
        return "buscar_uso"

    if re.search(
        r"\bdonde\b.*\b(defin|esta)\b",
        texto,
    ):
        return "localizar"

    if re.search(
        r"\bque\s+hace\b",
        texto,
    ):
        return "explicar"

    return "consultar_estructura"


# ============================================================
# DETECCIÓN DETERMINISTA
# ============================================================


def detectar_intencion_determinista(
    pregunta: str,
    *,
    profundidad: int = 3,
) -> dict[str, Any]:
    """
    Clasifica la intención sin utilizar LLM.

    Prioridad:

        1. URL detectada por HOST
        2. símbolo detectado por HOST
        3. modelo detectado por HOST
        4. evidencia estructural HOST
        5. patrón genérico de estructura
        6. patrón genérico de datos
        7. desconocida

    Esta función NO ejecuta ORM.
    """

    pregunta = _texto(
        pregunta
    )

    resultado_base = {
        "ok":
            True,

        "pregunta":
            pregunta,

        "tipo":
            "desconocida",

        "subtipo":
            None,

        "accion":
            None,

        "entidad":
            None,

        "terminos":
            [],

        "confianza":
            "baja",

        "origen":
            "determinista",

        "validado":
            False,

        "razon":
            "",

        "candidatos":
            [],

        "errores":
            [],
    }

    if not pregunta:

        resultado_base[
            "errores"
        ].append(
            "La pregunta está vacía."
        )

        resultado_base[
            "razon"
        ] = (
            "No existe contenido suficiente "
            "para detectar una intención."
        )

        return resultado_base

    contexto = (
        construir_contexto_semantico(
            pregunta,
            profundidad=profundidad,
        )
    )

    modelos = contexto.get(
        "modelos",
        [],
    ) or []

    simbolos = contexto.get(
        "simbolos",
        [],
    ) or []

    urls = contexto.get(
        "urls",
        [],
    ) or []

    # --------------------------------------------------------
    # 1. URL
    # --------------------------------------------------------

    if urls:

        entidad = _entidad_url(
            urls[0]
        )

        return {
            **resultado_base,

            "tipo":
                "estructura",

            "subtipo":
                "url",

            "accion":
                _accion_estructura(
                    pregunta
                ),

            "entidad":
                entidad,

            "terminos":
                [
                    entidad
                ]
                if entidad
                else [],

            "confianza":
                "alta",

            "validado":
                True,

            "razon": (
                "HOST detectó una URL real "
                "del proyecto anfitrión."
            ),

            "candidatos":
                urls,

            "contexto_deteccion":
                contexto.get(
                    "deteccion"
                ),
        }

    # --------------------------------------------------------
    # INTENCIÓN EXPLÍCITA
    # --------------------------------------------------------

    es_estructura_explicita = (
        _coincide_patron(
            pregunta,
            PATRONES_ESTRUCTURA,
        )
    )

    es_datos_explicita = (
        _coincide_patron(
            pregunta,
            PATRONES_DATOS,
        )
    )

    # --------------------------------------------------------
    # 2. DATOS CON ENTIDAD REAL
    #
    # Si el lenguaje indica claramente consulta de registros,
    # la existencia de un modelo no convierte la pregunta
    # automáticamente en una consulta estructural.
    #
    # El modelo detectado puede utilizarse para validar la
    # entidad, pero HOST014 NO ejecuta ORM.
    # --------------------------------------------------------

    if (
        es_datos_explicita
        and not es_estructura_explicita
    ):

        entidad = None

        if modelos:

            entidad = _entidad_modelo(
                modelos[0]
            )

        return {
            **resultado_base,

            "tipo":
                "datos",

            "subtipo":
                "consulta",

            "accion":
                "consultar",

            "entidad":
                entidad,

            "terminos":
                [
                    entidad
                ]
                if entidad
                else [],

            "confianza":
                (
                    "alta"
                    if entidad
                    else "media"
                ),

            "validado":
                bool(
                    entidad
                ),

            "razon":
                (
                    "La pregunta expresa una consulta "
                    "de datos y HOST validó el modelo "
                    "mencionado."
                    if entidad
                    else
                    "La pregunta expresa una consulta "
                    "de datos, pero todavía no existe "
                    "una entidad validada."
                ),

            "candidatos":
                modelos,

            "contexto_deteccion":
                contexto.get(
                    "deteccion"
                ),
        }

    # --------------------------------------------------------
    # 3. MODELO
    #
    # Un modelo Django también es una clase Python. Cuando
    # HOST lo detecta simultáneamente como modelo y símbolo,
    # conservamos la clasificación más específica: modelo.
    # --------------------------------------------------------

    if modelos:

        entidad = _entidad_modelo(
            modelos[0]
        )

        return {
            **resultado_base,

            "tipo":
                "estructura",

            "subtipo":
                "modelo",

            "accion":
                _accion_estructura(
                    pregunta
                ),

            "entidad":
                entidad,

            "terminos":
                [
                    entidad
                ]
                if entidad
                else [],

            "confianza":
                "alta",

            "validado":
                True,

            "razon": (
                "HOST detectó un modelo Django "
                "real del proyecto anfitrión."
            ),

            "candidatos":
                modelos,

            "contexto_deteccion":
                contexto.get(
                    "deteccion"
                ),
        }

    # --------------------------------------------------------
    # 4. SÍMBOLO
    # --------------------------------------------------------

    if simbolos:

        entidad = _entidad_simbolo(
            simbolos[0]
        )

        return {
            **resultado_base,

            "tipo":
                "estructura",

            "subtipo":
                "simbolo",

            "accion":
                _accion_estructura(
                    pregunta
                ),

            "entidad":
                entidad,

            "terminos":
                [
                    entidad
                ]
                if entidad
                else [],

            "confianza":
                "alta",

            "validado":
                True,

            "razon": (
                "HOST detectó un símbolo real "
                "en el código del proyecto."
            ),

            "candidatos":
                simbolos,

            "contexto_deteccion":
                contexto.get(
                    "deteccion"
                ),
        }

    # --------------------------------------------------------
    # 4. EVIDENCIA ESTRUCTURAL HOST
    # --------------------------------------------------------

    if contexto.get(
        "hay_evidencia"
    ):

        return {
            **resultado_base,

            "tipo":
                "estructura",

            "subtipo":
                "general",

            "accion":
                _accion_estructura(
                    pregunta
                ),

            "confianza":
                "media",

            "validado":
                True,

            "razon": (
                "HOST encontró evidencia estructural "
                "en el proyecto."
            ),

            "contexto_deteccion":
                contexto.get(
                    "deteccion"
                ),
        }

    # --------------------------------------------------------
    # 5. LENGUAJE ESTRUCTURAL SIN ENTIDAD VALIDADA
    # --------------------------------------------------------

    if _coincide_patron(
        pregunta,
        PATRONES_ESTRUCTURA,
    ):

        return {
            **resultado_base,

            "tipo":
                "estructura",

            "subtipo":
                "no_resuelto",

            "accion":
                _accion_estructura(
                    pregunta
                ),

            "confianza":
                "media",

            "validado":
                False,

            "razon": (
                "La pregunta tiene forma estructural, "
                "pero HOST no encontró una entidad "
                "que confirme la referencia."
            ),

            "contexto_deteccion":
                contexto.get(
                    "deteccion"
                ),
        }

    # --------------------------------------------------------
    # 6. CONSULTA DE DATOS
    # --------------------------------------------------------

    if _coincide_patron(
        pregunta,
        PATRONES_DATOS,
    ):

        return {
            **resultado_base,

            "tipo":
                "datos",

            "subtipo":
                "consulta",

            "accion":
                "consultar",

            "confianza":
                "media",

            "validado":
                False,

            "razon": (
                "La pregunta contiene una intención "
                "genérica de consulta de registros. "
                "La entidad todavía no ha sido validada."
            ),

            "contexto_deteccion":
                contexto.get(
                    "deteccion"
                ),
        }

    # --------------------------------------------------------
    # 7. DESCONOCIDA
    # --------------------------------------------------------

    return {
        **resultado_base,

        "razon": (
            "No existe evidencia estructural ni una "
            "intención de datos suficientemente clara."
        ),

        "contexto_deteccion":
            contexto.get(
                "deteccion"
            ),
    }


# ============================================================
# HOST014-B - PROMPT DE INTENCIÓN
# ============================================================


def _prompt_sistema_intencion() -> str:

    return (
        "Eres un clasificador de intención para una "
        "aplicación Django portable.\n\n"

        "Tu única tarea es clasificar la intención de "
        "la pregunta. NO respondas la pregunta.\n\n"

        "TIPOS PERMITIDOS:\n"
        "- estructura\n"
        "- datos\n"
        "- desconocida\n\n"

        "REGLAS OBLIGATORIAS:\n"
        "1. No inventes modelos, campos, funciones, URLs "
        "ni tablas.\n"
        "2. No generes SQL.\n"
        "3. No generes ORM.\n"
        "4. No generes Python.\n"
        "5. No asumas que una entidad existe.\n"
        "6. Si no puedes identificar una entidad, usa null.\n"
        "7. Si la intención no es suficientemente clara, "
        "usa desconocida.\n"
        "8. Una pregunta sobre registros, listados, conteos, "
        "estados o información almacenada normalmente es datos.\n"
        "9. Una pregunta sobre código, modelos, funciones, "
        "URLs, views, templates, imports o relaciones del "
        "programa normalmente es estructura.\n\n"

        "Devuelve EXCLUSIVAMENTE JSON válido con esta forma:\n"
        "{\n"
        '  "tipo": "estructura|datos|desconocida",\n'
        '  "subtipo": "texto o null",\n'
        '  "accion": "texto o null",\n'
        '  "entidad": "texto o null",\n'
        '  "terminos": []\n'
        "}\n\n"

        "No escribas Markdown ni explicaciones fuera del JSON."
    )


# ============================================================
# PARSEO SEGURO DE JSON LLM
# ============================================================


def _extraer_json_llm(
    contenido: Any,
) -> dict[str, Any] | None:

    texto = _texto(
        contenido
    )

    if not texto:
        return None

    # Qwen normalmente obedecerá JSON puro.
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

    # Defensa contra fences accidentales.
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

    # Último intento: primer objeto JSON visible.
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
# INTERPRETACIÓN LLM
# ============================================================


def interpretar_intencion_llm(
    pregunta: str,
    *,
    resultado_determinista: dict[str, Any],
) -> dict[str, Any]:

    contexto_deteccion = (
        resultado_determinista.get(
            "contexto_deteccion"
        )
        or {}
    )

    contexto = (
        "CLASIFICACION DETERMINISTA PREVIA:\n"
        f"tipo={resultado_determinista.get('tipo')}\n"
        f"subtipo={resultado_determinista.get('subtipo')}\n"
        f"accion={resultado_determinista.get('accion')}\n"
        f"entidad={resultado_determinista.get('entidad')}\n"
        f"validado={resultado_determinista.get('validado')}\n"
        f"deteccion_host={json.dumps(contexto_deteccion, ensure_ascii=False)}\n\n"

        "La clasificación determinista es contexto auxiliar. "
        "No significa que una entidad no validada exista."
    )

    resultado = consultar_ollama(
        pregunta=pregunta,
        contexto=contexto,
        prompt_sistema=(
            _prompt_sistema_intencion()
        ),
    )

    if not resultado.get(
        "ok"
    ):

        return {
            "ok":
                False,

            "propuesta":
                None,

            "error":
                resultado,

            "modelo":
                resultado.get(
                    "modelo"
                ),
        }

    propuesta = _extraer_json_llm(
        resultado.get(
            "respuesta"
        )
    )

    if propuesta is None:

        return {
            "ok":
                False,

            "propuesta":
                None,

            "error": {
                "tipo_error":
                    "json_intencion",

                "error":
                    "Qwen no devolvió JSON de intención válido.",

                "respuesta":
                    resultado.get(
                        "respuesta"
                    ),
            },

            "modelo":
                resultado.get(
                    "modelo"
                ),
        }

    return {
        "ok":
            True,

        "propuesta":
            propuesta,

        "modelo":
            resultado.get(
                "modelo"
            ),

        "eval_count":
            resultado.get(
                "eval_count"
            ),

        "prompt_eval_count":
            resultado.get(
                "prompt_eval_count"
            ),

        "total_duration":
            resultado.get(
                "total_duration"
            ),
    }


# ============================================================
# VALIDACIÓN DE PROPUESTA LLM
# ============================================================


def validar_intencion_llm(
    pregunta: str,
    propuesta: dict[str, Any],
    *,
    profundidad: int = 3,
) -> dict[str, Any]:

    tipo = _normalizar(
        propuesta.get(
            "tipo"
        )
    )

    if tipo not in TIPOS_VALIDOS:

        tipo = "desconocida"

    entidad_propuesta = _texto(
        propuesta.get(
            "entidad"
        )
    ) or None

    terminos = propuesta.get(
        "terminos"
    )

    if not isinstance(
        terminos,
        list,
    ):
        terminos = []

    terminos = [
        _texto(
            item
        )
        for item
        in terminos
        if _texto(
            item
        )
    ]

    # --------------------------------------------------------
    # DESCONOCIDA
    # --------------------------------------------------------

    if tipo == "desconocida":

        return {
            "ok":
                True,

            "pregunta":
                pregunta,

            "tipo":
                "desconocida",

            "subtipo":
                None,

            "accion":
                None,

            "entidad":
                None,

            "terminos":
                terminos,

            "confianza":
                "baja",

            "origen":
                "llm",

            "validado":
                False,

            "razon": (
                "Qwen no pudo proponer una intención "
                "suficientemente precisa."
            ),

            "candidatos":
                [],

            "errores":
                [],
        }

    # --------------------------------------------------------
    # VALIDAR ENTIDAD CONTRA HOST
    # --------------------------------------------------------

    texto_validacion = pregunta

    if entidad_propuesta:

        texto_validacion = (
            f"{pregunta} "
            f"{entidad_propuesta}"
        )

    contexto = construir_contexto_semantico(
        texto_validacion,
        profundidad=profundidad,
    )

    modelos = contexto.get(
        "modelos",
        [],
    ) or []

    simbolos = contexto.get(
        "simbolos",
        [],
    ) or []

    urls = contexto.get(
        "urls",
        [],
    ) or []

    # --------------------------------------------------------
    # DATOS
    # --------------------------------------------------------

    if tipo == "datos":

        entidad = None
        candidatos = []

        if modelos:

            entidad = _entidad_modelo(
                modelos[0]
            )

            candidatos = modelos

        return {
            "ok":
                True,

            "pregunta":
                pregunta,

            "tipo":
                "datos",

            "subtipo":
                "consulta",

            "accion":
                "consultar",

            "entidad":
                entidad,

            "terminos":
                (
                    [entidad]
                    if entidad
                    else terminos
                ),

            "confianza":
                (
                    "alta"
                    if entidad
                    else "media"
                ),

            "origen":
                "llm",

            "validado":
                bool(
                    entidad
                ),

            "razon":
                (
                    "Qwen propuso una consulta de datos "
                    "y HOST validó el modelo."
                    if entidad
                    else
                    "Qwen propuso una consulta de datos, "
                    "pero HOST no validó una entidad."
                ),

            "candidatos":
                candidatos,

            "errores":
                [],

            "contexto_deteccion":
                contexto.get(
                    "deteccion"
                ),
        }

    # --------------------------------------------------------
    # ESTRUCTURA
    # Prioridad:
    # URL -> modelo -> símbolo
    # --------------------------------------------------------

    if urls:

        entidad = _entidad_url(
            urls[0]
        )

        return {
            "ok":
                True,

            "pregunta":
                pregunta,

            "tipo":
                "estructura",

            "subtipo":
                "url",

            "accion":
                _accion_estructura(
                    pregunta
                ),

            "entidad":
                entidad,

            "terminos":
                [entidad]
                if entidad
                else terminos,

            "confianza":
                "alta",

            "origen":
                "llm",

            "validado":
                True,

            "razon":
                "HOST validó la URL propuesta.",

            "candidatos":
                urls,

            "errores":
                [],

            "contexto_deteccion":
                contexto.get(
                    "deteccion"
                ),
        }

    if modelos:

        entidad = _entidad_modelo(
            modelos[0]
        )

        return {
            "ok":
                True,

            "pregunta":
                pregunta,

            "tipo":
                "estructura",

            "subtipo":
                "modelo",

            "accion":
                _accion_estructura(
                    pregunta
                ),

            "entidad":
                entidad,

            "terminos":
                [entidad]
                if entidad
                else terminos,

            "confianza":
                "alta",

            "origen":
                "llm",

            "validado":
                True,

            "razon":
                "HOST validó el modelo propuesto.",

            "candidatos":
                modelos,

            "errores":
                [],

            "contexto_deteccion":
                contexto.get(
                    "deteccion"
                ),
        }

    if simbolos:

        entidad = _entidad_simbolo(
            simbolos[0]
        )

        return {
            "ok":
                True,

            "pregunta":
                pregunta,

            "tipo":
                "estructura",

            "subtipo":
                "simbolo",

            "accion":
                _accion_estructura(
                    pregunta
                ),

            "entidad":
                entidad,

            "terminos":
                [entidad]
                if entidad
                else terminos,

            "confianza":
                "alta",

            "origen":
                "llm",

            "validado":
                True,

            "razon":
                "HOST validó el símbolo propuesto.",

            "candidatos":
                simbolos,

            "errores":
                [],

            "contexto_deteccion":
                contexto.get(
                    "deteccion"
                ),
        }

    # La intención puede ser estructural,
    # pero la entidad NO está demostrada.
    return {
        "ok":
            True,

        "pregunta":
            pregunta,

        "tipo":
            "estructura",

        "subtipo":
            "no_resuelto",

        "accion":
            _accion_estructura(
                pregunta
            ),

        "entidad":
            None,

        "terminos":
            terminos,

        "confianza":
            "media",

        "origen":
            "llm",

        "validado":
            False,

        "razon": (
            "Qwen propuso una intención estructural, "
            "pero HOST no encontró evidencia que valide "
            "la entidad."
        ),

        "candidatos":
            [],

        "errores":
            [],

        "contexto_deteccion":
            contexto.get(
                "deteccion"
            ),
    }


# ============================================================
# DECISIÓN DE FALLBACK
# ============================================================


def _requiere_fallback_llm(
    resultado: dict[str, Any],
) -> bool:

    tipo = resultado.get(
        "tipo"
    )

    if tipo == "desconocida":
        return True

    if not resultado.get(
        "validado"
    ):

        return True

    return False


# ============================================================
# API PÚBLICA HOST014
# ============================================================


def detectar_intencion(
    pregunta: str,
    *,
    profundidad: int = 3,
) -> dict[str, Any]:
    """
    Intención portable HOST014.

    1. Siempre intenta resolución determinista.
    2. Si existe evidencia suficiente, Qwen no participa.
    3. Si la intención queda incompleta, Qwen propone.
    4. Toda propuesta de Qwen vuelve a ser validada por HOST.
    """

    determinista = (
        detectar_intencion_determinista(
            pregunta,
            profundidad=profundidad,
        )
    )

    if not _requiere_fallback_llm(
        determinista
    ):

        return {
            **determinista,

            "llm_invocado":
                False,
        }

    resultado_llm = (
        interpretar_intencion_llm(
            pregunta,
            resultado_determinista=determinista,
        )
    )

    if not resultado_llm.get(
        "ok"
    ):

        return {
            **determinista,

            "llm_invocado":
                True,

            "llm_error":
                resultado_llm.get(
                    "error"
                ),
        }

    validada = validar_intencion_llm(
        pregunta,
        resultado_llm[
            "propuesta"
        ],
        profundidad=profundidad,
    )

    return {
        **validada,

        "llm_invocado":
            True,

        "propuesta_llm":
            resultado_llm.get(
                "propuesta"
            ),

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

        "determinista_previo":
            {
                "tipo":
                    determinista.get(
                        "tipo"
                    ),

                "subtipo":
                    determinista.get(
                        "subtipo"
                    ),

                "entidad":
                    determinista.get(
                        "entidad"
                    ),

                "validado":
                    determinista.get(
                        "validado"
                    ),
            },
    }
