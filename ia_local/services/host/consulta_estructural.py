from __future__ import annotations

import re
import unicodedata
from typing import Any

from .indice_estructural import (
    obtener_campos_relaciones_modelo,
    obtener_funciones_que_usan_modelo,
    obtener_llamadas_simbolo,
    obtener_llamadores_simbolo,
    obtener_modelos_alcanzados_por_simbolo,
    obtener_views_que_usan_modelo,
    resolver_modelo_exacto,
    resolver_simbolo_exacto,
)
from .inspector_urls import (
    construir_mapa_urls,
)


# ============================================================
# IA-HOST020 - CONSULTA DEL GRAFO ESTRUCTURAL
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

    texto = unicodedata.normalize(
        "NFKD",
        _texto(
            valor
        ),
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


def _contiene_alguno(
    texto: str,
    valores: tuple[str, ...],
) -> bool:

    texto = _normalizar(
        texto
    )

    return any(
        valor in texto
        for valor
        in valores
    )


# ============================================================
# EXTRACCIÓN DE REFERENCIAS
# ============================================================

PATRON_QUALNAME = re.compile(
    r"(?<![\w])"
    r"([A-Za-z_][A-Za-z0-9_]*"
    r"(?:\.[A-Za-z_][A-Za-z0-9_]*){1,})"
    r"(?![\w])"
)

PATRON_PALABRA = re.compile(
    r"(?<![\w])"
    r"([A-Za-z_][A-Za-z0-9_]*)"
    r"(?![\w])"
)


def _referencias_calificadas(
    pregunta: str,
) -> list[str]:

    resultado = []

    for coincidencia in (
        PATRON_QUALNAME.findall(
            pregunta
        )
    ):

        if coincidencia not in resultado:
            resultado.append(
                coincidencia
            )

    return resultado


def _resolver_modelo_pregunta(
    pregunta: str,
) -> dict[str, Any] | None:

    # --------------------------------------------------------
    # 1. LABEL CALIFICADO
    # --------------------------------------------------------

    for referencia in (
        _referencias_calificadas(
            pregunta
        )
    ):

        modelo = (
            resolver_modelo_exacto(
                referencia
            )
        )

        if modelo:
            return modelo

    # --------------------------------------------------------
    # 2. NOMBRE SIMPLE ÚNICO
    # --------------------------------------------------------

    for palabra in (
        PATRON_PALABRA.findall(
            pregunta
        )
    ):

        modelo = (
            resolver_modelo_exacto(
                palabra
            )
        )

        if modelo:
            return modelo

    return None


def _resolver_simbolo_pregunta(
    pregunta: str,
) -> dict[str, Any] | None:

    # HOST020 exige referencia estructural demostrable.
    # Se priorizan qualnames completos para evitar ambigüedad.

    for referencia in (
        _referencias_calificadas(
            pregunta
        )
    ):

        simbolo = (
            resolver_simbolo_exacto(
                referencia
            )
        )

        if simbolo:
            return simbolo

    return None


# ============================================================
# DETECCIÓN
# ============================================================

def detectar_consulta_grafo(
    pregunta: str,
) -> dict[str, Any] | None:
    """
    Detecta consultas estructurales relacionales HOST020.

    IA-HOST020-C01:
    - los qualnames se consideran OBJETIVOS estructurales;
    - sus componentes no participan en la detección semántica;
    - se prioriza símbolo/modelo según el recurso explícito pedido.

    No utiliza LLM.
    """

    texto = _normalizar(
        pregunta
    )

    if not texto:
        return None

    # --------------------------------------------------------
    # Separar OBJETIVOS de la INTENCIÓN.
    #
    # Ejemplo:
    #
    #   ¿Qué modelos utiliza transmital.views.transmital_create?
    #
    # "transmital.views.transmital_create" es el objetivo.
    # Las palabras "views" y "transmital" dentro del qualname
    # NO deben interpretarse como recurso o modelo solicitado.
    # --------------------------------------------------------

    referencias = (
        _referencias_calificadas(
            pregunta
        )
    )

    texto_intencion = texto

    for referencia in referencias:

        texto_intencion = (
            texto_intencion.replace(
                _normalizar(
                    referencia
                ),
                " ",
            )
        )

    texto_intencion = re.sub(
        r"\s+",
        " ",
        texto_intencion,
    ).strip()

    # Resolver candidatos estructurales una sola vez.
    simbolo = (
        _resolver_simbolo_pregunta(
            pregunta
        )
    )

    modelo = (
        _resolver_modelo_pregunta(
            pregunta
        )
    )

    # ========================================================
    # 1. CAMPOS DE MODELO
    # ========================================================

    if _contiene_alguno(
        texto_intencion,
        (
            "campo ",
            "campos ",
            "campos tiene",
            "campos de",
        ),
    ):

        if modelo:

            return {
                "tipo":
                    "estructura",

                "subtipo":
                    "grafo",

                "accion":
                    "campos_modelo",

                "objetivo":
                    modelo[
                        "label"
                    ],

                "validado":
                    True,

                "origen":
                    "determinista",

                "confianza":
                    "alta",
            }

    # ========================================================
    # 2. RELACIONES DE MODELO
    # ========================================================

    if _contiene_alguno(
        texto_intencion,
        (
            "relacion ",
            "relaciones ",
            "relaciones tiene",
            "relaciones de",
        ),
    ):

        if modelo:

            return {
                "tipo":
                    "estructura",

                "subtipo":
                    "grafo",

                "accion":
                    "relaciones_modelo",

                "objetivo":
                    modelo[
                        "label"
                    ],

                "validado":
                    True,

                "origen":
                    "determinista",

                "confianza":
                    "alta",
            }

    # ========================================================
    # 3. MODELOS UTILIZADOS POR UN SÍMBOLO
    #
    # Debe evaluarse ANTES que "views utilizan modelo".
    # ========================================================

    if (
        _contiene_alguno(
            texto_intencion,
            (
                "modelo",
                "modelos",
            ),
        )
        and _contiene_alguno(
            texto_intencion,
            (
                "utiliza",
                "utilizan",
                "usa ",
                "usan ",
                "ocupa",
                "ocupan",
            ),
        )
        and simbolo
    ):

        return {
            "tipo":
                "estructura",

            "subtipo":
                "grafo",

            "accion":
                "modelos_simbolo",

            "objetivo":
                simbolo[
                    "qualname"
                ],

            "profundidad":
                2,

            "validado":
                True,

            "origen":
                "determinista",

            "confianza":
                "alta",
        }

    # ========================================================
    # 4. FUNCIONES QUE UTILIZAN UN MODELO
    # ========================================================

    if (
        _contiene_alguno(
            texto_intencion,
            (
                "funcion",
                "funciones",
            ),
        )
        and _contiene_alguno(
            texto_intencion,
            (
                "utiliza",
                "utilizan",
                "usa ",
                "usan ",
                "ocupa",
                "ocupan",
            ),
        )
        and modelo
    ):

        return {
            "tipo":
                "estructura",

            "subtipo":
                "grafo",

            "accion":
                "funciones_modelo",

            "objetivo":
                modelo[
                    "label"
                ],

            "validado":
                True,

            "origen":
                "determinista",

            "confianza":
                "alta",
        }

    # ========================================================
    # 5. VIEWS QUE UTILIZAN UN MODELO
    # ========================================================

    if (
        _contiene_alguno(
            texto_intencion,
            (
                "view",
                "views",
                "vista",
                "vistas",
            ),
        )
        and _contiene_alguno(
            texto_intencion,
            (
                "utiliza",
                "utilizan",
                "usa ",
                "usan ",
                "ocupa",
                "ocupan",
            ),
        )
        and modelo
    ):

        return {
            "tipo":
                "estructura",

            "subtipo":
                "grafo",

            "accion":
                "views_modelo",

            "objetivo":
                modelo[
                    "label"
                ],

            "profundidad":
                2,

            "validado":
                True,

            "origen":
                "determinista",

            "confianza":
                "alta",
        }

    # ========================================================
    # 6. QUIÉN LLAMA A UNA FUNCIÓN
    # ========================================================

    if (
        _contiene_alguno(
            texto_intencion,
            (
                "quien llama",
                "quienes llaman",
                "funciones llaman a",
                "funcion llama a",
                "llama a la funcion",
                "llaman a la funcion",
            ),
        )
        and simbolo
    ):

        return {
            "tipo":
                "estructura",

            "subtipo":
                "grafo",

            "accion":
                "llamadores_simbolo",

            "objetivo":
                simbolo[
                    "qualname"
                ],

            "validado":
                True,

            "origen":
                "determinista",

            "confianza":
                "alta",
        }

    # ========================================================
    # 7. QUÉ FUNCIONES LLAMA UN SÍMBOLO
    # ========================================================

    if (
        _contiene_alguno(
            texto_intencion,
            (
                "funcion",
                "funciones",
            ),
        )
        and _contiene_alguno(
            texto_intencion,
            (
                " llama ",
                " llamadas ",
                "invoca",
                "invocadas",
            ),
        )
        and simbolo
    ):

        return {
            "tipo":
                "estructura",

            "subtipo":
                "grafo",

            "accion":
                "llamadas_simbolo",

            "objetivo":
                simbolo[
                    "qualname"
                ],

            "validado":
                True,

            "origen":
                "determinista",

            "confianza":
                "alta",
        }

    # ========================================================
    # 8. URLS DE UNA VIEW/SÍMBOLO
    # ========================================================

    if (
        _contiene_alguno(
            texto_intencion,
            (
                "url ",
                "urls ",
                "ruta ",
                "rutas ",
            ),
        )
        and simbolo
    ):

        return {
            "tipo":
                "estructura",

            "subtipo":
                "grafo",

            "accion":
                "urls_view",

            "objetivo":
                simbolo[
                    "qualname"
                ],

            "validado":
                True,

            "origen":
                "determinista",

            "confianza":
                "alta",
        }

    return None


# ============================================================
# CONSULTAS DIRECTAS
# ============================================================

def _urls_de_view(
    view: str,
) -> list[dict[str, Any]]:

    objetivo = _normalizar(
        view
    )

    if not objetivo:
        return []

    resultado = []

    for item in construir_mapa_urls():

        if _normalizar(
            item.get(
                "view"
            )
        ) != objetivo:
            continue

        app = (
            item.get(
                "app"
            )
            or {}
        )

        if app.get(
            "tipo"
        ) != "proyecto":
            continue

        resultado.append(
            {
                "ruta":
                    item.get(
                        "ruta"
                    ),

                "name":
                    item.get(
                        "name"
                    ),

                "namespace":
                    item.get(
                        "namespace"
                    ),

                "view":
                    item.get(
                        "view"
                    ),
            }
        )

    resultado.sort(
        key=lambda item: (
            _texto(
                item.get(
                    "ruta"
                )
            )
        )
    )

    return resultado


# ============================================================
# RESPUESTAS
# ============================================================

def _respuesta_lista(
    cabecera: str,
    elementos: list[str],
) -> str:

    lineas = [
        cabecera
    ]

    for elemento in elementos:
        lineas.append(
            f"- {elemento}"
        )

    return "\n".join(
        lineas
    )


def ejecutar_consulta_grafo(
    pregunta: str,
    plan: dict[str, Any],
) -> dict[str, Any]:
    """
    Ejecuta una consulta relacional HOST020 sin LLM.
    """

    accion = _texto(
        plan.get(
            "accion"
        )
    )

    objetivo = _texto(
        plan.get(
            "objetivo"
        )
    )

    profundidad = int(
        plan.get(
            "profundidad",
            2,
        )
        or 2
    )

    datos: Any = None
    respuesta = ""
    total = 0

    # --------------------------------------------------------
    # URLS DE VIEW
    # --------------------------------------------------------

    if accion == "urls_view":

        resultados = (
            _urls_de_view(
                objetivo
            )
        )

        total = len(
            resultados
        )

        respuesta = _respuesta_lista(
            (
                f"Se encontraron {total} URLs registradas "
                f"para {objetivo}:"
            ),
            [
                (
                    f"{item.get('ruta')} "
                    f"→ {item.get('view')}"
                )
                for item
                in resultados
            ],
        )

        datos = resultados

    # --------------------------------------------------------
    # LLAMADAS DE SÍMBOLO
    # --------------------------------------------------------

    elif accion == "llamadas_simbolo":

        resultado = (
            obtener_llamadas_simbolo(
                objetivo
            )
        )

        if not resultado.get(
            "ok"
        ):
            return _error(
                pregunta,
                plan,
                resultado.get(
                    "error"
                ),
            )

        resultados = (
            resultado.get(
                "resultados",
                [],
            )
        )

        total = len(
            resultados
        )

        respuesta = _respuesta_lista(
            (
                f"Se encontraron {total} funciones internas "
                f"llamadas por {objetivo}:"
            ),
            resultados,
        )

        datos = resultado

    # --------------------------------------------------------
    # LLAMADORES
    # --------------------------------------------------------

    elif accion == "llamadores_simbolo":

        resultado = (
            obtener_llamadores_simbolo(
                objetivo
            )
        )

        if not resultado.get(
            "ok"
        ):
            return _error(
                pregunta,
                plan,
                resultado.get(
                    "error"
                ),
            )

        resultados = (
            resultado.get(
                "resultados",
                [],
            )
        )

        total = len(
            resultados
        )

        respuesta = _respuesta_lista(
            (
                f"Se encontraron {total} funciones internas "
                f"que llaman a {objetivo}:"
            ),
            resultados,
        )

        datos = resultado

    # --------------------------------------------------------
    # MODELOS DE SÍMBOLO
    # --------------------------------------------------------

    elif accion == "modelos_simbolo":

        resultado = (
            obtener_modelos_alcanzados_por_simbolo(
                objetivo,
                profundidad=profundidad,
            )
        )

        if not resultado.get(
            "ok"
        ):
            return _error(
                pregunta,
                plan,
                resultado.get(
                    "error"
                ),
            )

        modelos = (
            resultado.get(
                "modelos",
                [],
            )
        )

        total = len(
            modelos
        )

        respuesta = _respuesta_lista(
            (
                f"Se encontraron {total} modelos Django "
                f"alcanzables desde {objetivo} "
                f"hasta profundidad {profundidad}:"
            ),
            [
                _texto(
                    item.get(
                        "label"
                    )
                )
                for item
                in modelos
            ],
        )

        datos = resultado

    # --------------------------------------------------------
    # FUNCIONES DE MODELO
    # --------------------------------------------------------

    elif accion == "funciones_modelo":

        resultado = (
            obtener_funciones_que_usan_modelo(
                objetivo
            )
        )

        if not resultado.get(
            "ok"
        ):
            return _error(
                pregunta,
                plan,
                resultado.get(
                    "error"
                ),
            )

        resultados = (
            resultado.get(
                "resultados",
                [],
            )
        )

        total = len(
            resultados
        )

        respuesta = _respuesta_lista(
            (
                f"Se encontraron {total} funciones que usan "
                f"directamente el modelo {objetivo}:"
            ),
            [
                (
                    f"{item.get('qualname')} "
                    f"[{item.get('archivo')}:"
                    f"{item.get('linea_inicio')}]"
                )
                for item
                in resultados
            ],
        )

        datos = resultado

    # --------------------------------------------------------
    # VIEWS DE MODELO
    # --------------------------------------------------------

    elif accion == "views_modelo":

        resultado = (
            obtener_views_que_usan_modelo(
                objetivo,
                profundidad=profundidad,
            )
        )

        if not resultado.get(
            "ok"
        ):
            return _error(
                pregunta,
                plan,
                resultado.get(
                    "error"
                ),
            )

        resultados = (
            resultado.get(
                "resultados",
                [],
            )
        )

        total = len(
            resultados
        )

        respuesta = _respuesta_lista(
            (
                f"Se encontraron {total} views registradas "
                f"que alcanzan el modelo {objetivo} "
                f"hasta profundidad {profundidad}:"
            ),
            [
                item.get(
                    "view"
                )
                for item
                in resultados
            ],
        )

        datos = resultado

    # --------------------------------------------------------
    # CAMPOS
    # --------------------------------------------------------

    elif accion == "campos_modelo":

        resultado = (
            obtener_campos_relaciones_modelo(
                objetivo
            )
        )

        if not resultado.get(
            "ok"
        ):
            return _error(
                pregunta,
                plan,
                resultado.get(
                    "error"
                ),
            )

        campos = (
            resultado.get(
                "campos",
                [],
            )
        )

        total = len(
            campos
        )

        respuesta = _respuesta_lista(
            (
                f"Se encontraron {total} campos concretos "
                f"en {objetivo}:"
            ),
            [
                (
                    f"{item.get('nombre')} "
                    f"({item.get('tipo')})"
                    + (
                        f" → {item.get('modelo_relacionado')}"
                        if item.get(
                            "modelo_relacionado"
                        )
                        else ""
                    )
                )
                for item
                in campos
            ],
        )

        datos = resultado

    # --------------------------------------------------------
    # RELACIONES
    # --------------------------------------------------------

    elif accion == "relaciones_modelo":

        resultado = (
            obtener_campos_relaciones_modelo(
                objetivo
            )
        )

        if not resultado.get(
            "ok"
        ):
            return _error(
                pregunta,
                plan,
                resultado.get(
                    "error"
                ),
            )

        relaciones = (
            resultado.get(
                "relaciones",
                [],
            )
        )

        total = len(
            relaciones
        )

        respuesta = _respuesta_lista(
            (
                f"Se encontraron {total} relaciones Django "
                f"en {objetivo}:"
            ),
            [
                (
                    f"{item.get('nombre')} "
                    f"({item.get('tipo')}) "
                    f"→ {item.get('modelo_relacionado')}"
                )
                for item
                in relaciones
            ],
        )

        datos = resultado

    else:

        return _error(
            pregunta,
            plan,
            (
                "La operación estructural solicitada "
                "no está soportada por HOST020."
            ),
        )

    return {
        "ok":
            True,

        "pregunta":
            pregunta,

        "respondido_por":
            "host",

        "llm_invocado":
            False,

        "hay_evidencia":
            True,

        "tipo":
            "grafo_estructural",

        "accion":
            accion,

        "objetivo":
            objetivo,

        "profundidad":
            profundidad,

        "total":
            total,

        "plan":
            plan,

        "resultados":
            datos,

        "contexto": (
            "Relación estructural obtenida directamente "
            "desde índices e inspectores del proyecto Django "
            "anfitrión. No se utilizó LLM para determinar "
            "los hechos."
        ),

        "respuesta":
            respuesta,
    }


def _error(
    pregunta: str,
    plan: dict[str, Any],
    mensaje: Any,
) -> dict[str, Any]:

    return {
        "ok":
            False,

        "pregunta":
            pregunta,

        "respondido_por":
            "host",

        "llm_invocado":
            False,

        "plan":
            plan,

        "error":
            _texto(
                mensaje
            )
            or (
                "No fue posible resolver "
                "la consulta estructural."
            ),
    }
