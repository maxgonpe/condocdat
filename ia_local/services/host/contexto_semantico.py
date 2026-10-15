from __future__ import annotations

import re
import unicodedata
from typing import Any

from .consultor_grafo import (
    buscar_templates_de_view,
    buscar_urls_de_view,
)
from .indice_estructural import (
    construir_indice_estructural,
    obtener_campos_relaciones_modelo,
    obtener_funciones_que_usan_modelo,
    obtener_llamadas_simbolo,
    obtener_llamadores_simbolo,
    obtener_modelos_alcanzados_por_simbolo,
    obtener_views_que_usan_modelo,
    resolver_modelo_exacto,
    resolver_simbolo_exacto,
)
from .inspector_modelos_codigo import (
    construir_catalogo_modelos,
)
from .inspector_urls import (
    construir_mapa_urls,
)


# ============================================================
# IA-HOST021
# CONTEXTO ESTRUCTURAL BASADO EN EVIDENCIA
# ============================================================
#
# Principio:
#
#   HECHOS
#       HOST / Django / AST / índice estructural
#
#   EXPLICACIÓN
#       Qwen opcional, únicamente sobre esos hechos
#
# Este módulo conserva la interfaz pública anterior:
#
#   construir_contexto_semantico()
#   contexto_semantico_a_texto()
#   construir_contexto_llm()
#
# De ese modo no es necesario modificar intencion.py,
# respuesta_llm.py ni router.py.
#
# HOST021 elimina del contexto semántico el recorrido caro:
#
#   modelo -> todas las views -> construir un grafo por view
#
# y utiliza HOST020:
#
#   modelo -> índice inverso -> símbolos/views
#
# ============================================================


MAX_VIEWS_CONTEXTO = 30
MAX_FUNCIONES_CONTEXTO = 40
MAX_LLAMADAS_CONTEXTO = 40
MAX_RELACIONES_CONTEXTO = 50
MAX_CAMPOS_CONTEXTO = 80


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


def _contiene_literal_aislado(
    texto: str,
    literal: str,
) -> bool:
    """
    Busca un literal completo evitando coincidencias parciales.
    """

    texto = _normalizar(
        texto
    )

    literal = _normalizar(
        literal
    )

    if (
        not texto
        or not literal
    ):
        return False

    patron = (
        r"(?<![\w])"
        + re.escape(
            literal
        )
        + r"(?![\w])"
    )

    return bool(
        re.search(
            patron,
            texto,
        )
    )


def _deduplicar_textos(
    valores: list[str],
) -> list[str]:

    resultado = []
    vistos = set()

    for valor in valores:

        valor = _texto(
            valor
        )

        if (
            not valor
            or valor in vistos
        ):
            continue

        vistos.add(
            valor
        )

        resultado.append(
            valor
        )

    return resultado


def _limitar(
    items: list[Any],
    limite: int,
) -> tuple[
    list[Any],
    bool,
]:

    if len(
        items
    ) <= limite:

        return (
            items,
            False,
        )

    return (
        items[
            :limite
        ],
        True,
    )


# ============================================================
# DETECCIÓN DE SÍMBOLOS
# ============================================================

def detectar_simbolos_mencionados(
    pregunta: str,
) -> list[dict[str, Any]]:
    """
    Detecta símbolos reales del host.

    Prioridad:
        1. qualname exacto;
        2. nombre simple exacto y no ambiguo.

    La resolución final siempre se valida contra HOST020.
    """

    pregunta_normalizada = _normalizar(
        pregunta
    )

    if not pregunta_normalizada:
        return []

    indice = (
        construir_indice_estructural()
    )

    encontrados = []
    vistos = set()

    # --------------------------------------------------------
    # QUALNAME COMPLETO
    # --------------------------------------------------------

    simbolos = (
        indice.get(
            "simbolos_host",
            [],
        )
    )

    for simbolo in simbolos:

        qualname = _texto(
            simbolo.get(
                "qualname"
            )
        )

        if not qualname:
            continue

        if not _contiene_literal_aislado(
            pregunta_normalizada,
            qualname,
        ):
            continue

        if qualname in vistos:
            continue

        vistos.add(
            qualname
        )

        encontrados.append(
            simbolo
        )

    if encontrados:

        encontrados.sort(
            key=lambda item: (
                _normalizar(
                    item.get(
                        "qualname"
                    )
                )
            )
        )

        return encontrados

    # --------------------------------------------------------
    # NOMBRE SIMPLE ÚNICO
    # --------------------------------------------------------

    for simbolo in simbolos:

        nombre = _texto(
            simbolo.get(
                "nombre"
            )
        )

        if len(
            nombre
        ) < 4:
            continue

        if not _contiene_literal_aislado(
            pregunta_normalizada,
            nombre,
        ):
            continue

        resuelto = (
            resolver_simbolo_exacto(
                nombre,
                indice_simbolos=indice[
                    "indice_simbolos"
                ],
            )
        )

        if not resuelto:
            continue

        qualname = _texto(
            resuelto.get(
                "qualname"
            )
        )

        if (
            not qualname
            or qualname in vistos
        ):
            continue

        vistos.add(
            qualname
        )

        encontrados.append(
            resuelto
        )

    encontrados.sort(
        key=lambda item: (
            _normalizar(
                item.get(
                    "qualname"
                )
            )
        )
    )

    return encontrados


# ============================================================
# DETECCIÓN DE MODELOS
# ============================================================

def detectar_modelos_mencionados(
    pregunta: str,
) -> list[dict[str, Any]]:
    """
    Detecta modelos Django reales evitando que partes de un
    qualname de función se interpreten como modelos.

    Ejemplo protegido:

        transmital.views.transmital_create

    no debe detectar automáticamente:

        transmital.Transmital
    """

    pregunta_normalizada = _normalizar(
        pregunta
    )

    if not pregunta_normalizada:
        return []

    catalogo = (
        construir_catalogo_modelos()
    )

    encontrados = []
    vistos = set()

    # --------------------------------------------------------
    # 1. LABELS COMPLETOS EXACTOS
    # --------------------------------------------------------

    for modelo in catalogo.get(
        "modelos",
        [],
    ):

        label = _texto(
            modelo.get(
                "label"
            )
        )

        if not label:
            continue

        resuelto = (
            resolver_modelo_exacto(
                label,
                catalogo=catalogo,
            )
        )

        if not resuelto:
            continue

        if not _contiene_literal_aislado(
            pregunta_normalizada,
            label,
        ):
            continue

        label_real = _texto(
            resuelto.get(
                "label"
            )
        )

        if label_real in vistos:
            continue

        vistos.add(
            label_real
        )

        encontrados.append(
            resuelto
        )

    if encontrados:

        encontrados.sort(
            key=lambda item: (
                _normalizar(
                    item.get(
                        "label"
                    )
                )
            )
        )

        return encontrados

    # --------------------------------------------------------
    # 2. ENMASCARAR QUALNAMES DE SÍMBOLOS
    # --------------------------------------------------------

    texto_modelos = pregunta_normalizada

    for simbolo in detectar_simbolos_mencionados(
        pregunta
    ):

        qualname = _normalizar(
            simbolo.get(
                "qualname"
            )
        )

        if qualname:

            texto_modelos = (
                texto_modelos.replace(
                    qualname,
                    " ",
                )
            )

    texto_modelos = re.sub(
        r"\s+",
        " ",
        texto_modelos,
    ).strip()

    # --------------------------------------------------------
    # 3. NOMBRES CORTOS / TABLAS EXACTAS
    # --------------------------------------------------------

    for modelo in catalogo.get(
        "modelos",
        [],
    ):

        candidatos = (
            _texto(
                modelo.get(
                    "modelo"
                )
            ),
            _texto(
                modelo.get(
                    "tabla"
                )
            ),
        )

        detectado = False

        for candidato in candidatos:

            if len(
                candidato
            ) < 3:
                continue

            if _contiene_literal_aislado(
                texto_modelos,
                candidato,
            ):

                detectado = True
                break

        if not detectado:
            continue

        referencia = _texto(
            modelo.get(
                "modelo"
            )
        )

        resuelto = (
            resolver_modelo_exacto(
                referencia,
                catalogo=catalogo,
            )
        )

        if not resuelto:
            continue

        label = _texto(
            resuelto.get(
                "label"
            )
        )

        if label in vistos:
            continue

        vistos.add(
            label
        )

        encontrados.append(
            resuelto
        )

    encontrados.sort(
        key=lambda item: (
            _normalizar(
                item.get(
                    "label"
                )
            )
        )
    )

    return encontrados


# ============================================================
# DETECCIÓN DE URLS
# ============================================================

def detectar_urls_mencionadas(
    pregunta: str,
) -> list[dict[str, Any]]:
    """
    Detecta:
        - ruta exacta;
        - namespace:name exacto.

    No utiliza el name simple como señal primaria.
    """

    pregunta_normalizada = _normalizar(
        pregunta
    )

    if not pregunta_normalizada:
        return []

    mapa_urls = (
        construir_mapa_urls()
    )

    resultado = []
    vistos = set()

    # --------------------------------------------------------
    # RUTAS
    # --------------------------------------------------------

    for item in mapa_urls:

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

        ruta = _texto(
            item.get(
                "ruta"
            )
        )

        if not ruta:
            continue

        if not _contiene_literal_aislado(
            pregunta_normalizada,
            ruta,
        ):
            continue

        clave = (
            ruta,
            _texto(
                item.get(
                    "view"
                )
            ),
        )

        if clave in vistos:
            continue

        vistos.add(
            clave
        )

        resultado.append(
            item
        )

    if resultado:

        resultado.sort(
            key=lambda item: len(
                _texto(
                    item.get(
                        "ruta"
                    )
                )
            ),
            reverse=True,
        )

        return resultado

    # --------------------------------------------------------
    # NAMESPACE:NAME
    # --------------------------------------------------------

    for item in mapa_urls:

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

        nombre = _texto(
            item.get(
                "name"
            )
        )

        namespace = _texto(
            item.get(
                "namespace"
            )
        )

        if not (
            nombre
            and namespace
        ):
            continue

        completo = (
            f"{namespace}:{nombre}"
        )

        if not _contiene_literal_aislado(
            pregunta_normalizada,
            completo,
        ):
            continue

        clave = (
            _texto(
                item.get(
                    "ruta"
                )
            ),
            _texto(
                item.get(
                    "view"
                )
            ),
        )

        if clave in vistos:
            continue

        vistos.add(
            clave
        )

        resultado.append(
            item
        )

    return resultado


# ============================================================
# FILTRO MODELO / CLASE CANÓNICA
# ============================================================

def _filtrar_simbolos_modelos_canonicos(
    simbolos: list[dict[str, Any]],
    modelos: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Si un modelo fue detectado explícitamente, su definición
    Python no se duplica como símbolo independiente.
    """

    if (
        not simbolos
        or not modelos
    ):
        return simbolos

    canonicos = {
        _normalizar(
            (
                f"{modelo.get('modulo')}."
                f"{modelo.get('modelo')}"
            )
        )
        for modelo
        in modelos
        if (
            modelo.get(
                "modulo"
            )
            and modelo.get(
                "modelo"
            )
        )
    }

    resultado = []

    for simbolo in simbolos:

        qualname = _normalizar(
            simbolo.get(
                "qualname"
            )
        )

        if qualname in canonicos:
            continue

        resultado.append(
            simbolo
        )

    return resultado


# ============================================================
# CONTEXTO DE MODELO
# ============================================================

def _usos_demostrados_modelo(
    label: str,
) -> list[dict[str, Any]]:

    indice = (
        construir_indice_estructural()
    )

    usos = []

    simbolos = (
        indice.get(
            "por_modelo_simbolos",
            {},
        ).get(
            label.lower(),
            [],
        )
    )

    for simbolo in simbolos:

        qualname = _texto(
            simbolo.get(
                "qualname"
            )
        )

        for operacion in indice.get(
            "por_simbolo_operaciones",
            {},
        ).get(
            qualname,
            [],
        ):

            modelo_op = (
                operacion.get(
                    "modelo"
                )
                or {}
            )

            if _normalizar(
                modelo_op.get(
                    "label"
                )
            ) != _normalizar(
                label
            ):
                continue

            usos.append(
                {
                    "modelo":
                        label,

                    "simbolo":
                        qualname,

                    "archivo":
                        simbolo.get(
                            "archivo"
                        ),

                    "linea":
                        operacion.get(
                            "linea"
                        ),

                    "modo":
                        operacion.get(
                            "modo"
                        ),

                    "operacion":
                        operacion.get(
                            "operacion"
                        ),

                    "expresion":
                        operacion.get(
                            "expresion"
                        ),
                }
            )

    usos.sort(
        key=lambda item: (
            _normalizar(
                item.get(
                    "simbolo"
                )
            ),
            item.get(
                "linea"
            )
            or 0,
            _normalizar(
                item.get(
                    "operacion"
                )
            ),
        )
    )

    return usos


def _contexto_modelo(
    modelo: dict[str, Any],
    *,
    profundidad: int,
) -> dict[str, Any]:

    label = _texto(
        modelo.get(
            "label"
        )
    )

    funciones = (
        obtener_funciones_que_usan_modelo(
            label
        )
    )

    views = (
        obtener_views_que_usan_modelo(
            label,
            profundidad=profundidad,
        )
    )

    estructura = (
        obtener_campos_relaciones_modelo(
            label
        )
    )

    funciones_lista = (
        funciones.get(
            "resultados",
            [],
        )
        if funciones.get(
            "ok"
        )
        else []
    )

    views_lista = (
        views.get(
            "resultados",
            [],
        )
        if views.get(
            "ok"
        )
        else []
    )

    campos = (
        estructura.get(
            "campos",
            [],
        )
        if estructura.get(
            "ok"
        )
        else []
    )

    relaciones = (
        estructura.get(
            "relaciones",
            [],
        )
        if estructura.get(
            "ok"
        )
        else []
    )

    (
        funciones_contexto,
        funciones_truncadas,
    ) = _limitar(
        funciones_lista,
        MAX_FUNCIONES_CONTEXTO,
    )

    (
        views_contexto,
        views_truncadas,
    ) = _limitar(
        views_lista,
        MAX_VIEWS_CONTEXTO,
    )

    (
        campos_contexto,
        campos_truncados,
    ) = _limitar(
        campos,
        MAX_CAMPOS_CONTEXTO,
    )

    (
        relaciones_contexto,
        relaciones_truncadas,
    ) = _limitar(
        relaciones,
        MAX_RELACIONES_CONTEXTO,
    )

    resultado_views = []

    for item in views_contexto:

        resultado_views.append(
            {
                "view":
                    item.get(
                        "view"
                    ),

                "archivo":
                    item.get(
                        "archivo"
                    ),

                "urls":
                    _deduplicar_textos(
                        [
                            _texto(
                                url.get(
                                    "ruta"
                                )
                            )
                            for url
                            in item.get(
                                "urls",
                                [],
                            )
                        ]
                    ),

                "evidencias":
                    item.get(
                        "evidencias",
                        [],
                    ),
            }
        )

    return {
        "label":
            label,

        "modelo":
            modelo.get(
                "modelo"
            ),

        "app_label":
            modelo.get(
                "app_label"
            ),

        "tabla":
            modelo.get(
                "tabla"
            ),

        "modulo":
            modelo.get(
                "modulo"
            ),

        "funciones":
            funciones_contexto,

        "total_funciones":
            len(
                funciones_lista
            ),

        "funciones_truncadas":
            funciones_truncadas,

        "views":
            resultado_views,

        "total_views":
            len(
                views_lista
            ),

        "views_truncadas":
            views_truncadas,

        "campos":
            campos_contexto,

        "total_campos":
            len(
                campos
            ),

        "campos_truncados":
            campos_truncados,

        "relaciones":
            relaciones_contexto,

        "total_relaciones":
            len(
                relaciones
            ),

        "relaciones_truncadas":
            relaciones_truncadas,

        "usos_demostrados":
            _usos_demostrados_modelo(
                label
            ),

        "evidencia":
            "verificada_host020",
    }


# ============================================================
# CONTEXTO DE SÍMBOLO
# ============================================================

def _contexto_simbolo(
    simbolo: dict[str, Any],
    *,
    profundidad: int,
) -> dict[str, Any]:

    qualname = _texto(
        simbolo.get(
            "qualname"
        )
    )

    llamadas = (
        obtener_llamadas_simbolo(
            qualname
        )
    )

    llamadores = (
        obtener_llamadores_simbolo(
            qualname
        )
    )

    modelos = (
        obtener_modelos_alcanzados_por_simbolo(
            qualname,
            profundidad=profundidad,
        )
    )

    urls = (
        buscar_urls_de_view(
            qualname
        )
    )

    # IMPORTANTE:
    # estos templates APUNTAN a la view mediante URL/enlace.
    # No se afirma que la view los renderice.
    templates_que_apuntan = (
        buscar_templates_de_view(
            qualname
        )
    )

    llamadas_lista = (
        llamadas.get(
            "resultados",
            [],
        )
        if llamadas.get(
            "ok"
        )
        else []
    )

    llamadores_lista = (
        llamadores.get(
            "resultados",
            [],
        )
        if llamadores.get(
            "ok"
        )
        else []
    )

    modelos_lista = (
        modelos.get(
            "modelos",
            [],
        )
        if modelos.get(
            "ok"
        )
        else []
    )

    (
        llamadas_contexto,
        llamadas_truncadas,
    ) = _limitar(
        llamadas_lista,
        MAX_LLAMADAS_CONTEXTO,
    )

    (
        llamadores_contexto,
        llamadores_truncados,
    ) = _limitar(
        llamadores_lista,
        MAX_LLAMADAS_CONTEXTO,
    )

    indice = (
        construir_indice_estructural()
    )

    operaciones_directas = [
        {
            "modelo":
                (
                    operacion.get(
                        "modelo"
                    )
                    or {}
                ).get(
                    "label"
                ),

            "operacion":
                operacion.get(
                    "operacion"
                ),

            "modo":
                operacion.get(
                    "modo"
                ),

            "linea":
                operacion.get(
                    "linea"
                ),

            "expresion":
                operacion.get(
                    "expresion"
                ),
        }
        for operacion
        in indice.get(
            "por_simbolo_operaciones",
            {},
        ).get(
            qualname,
            [],
        )
    ]

    return {
        "nombre":
            simbolo.get(
                "nombre"
            ),

        "qualname":
            qualname,

        "tipo":
            simbolo.get(
                "tipo"
            ),

        "archivo":
            simbolo.get(
                "archivo"
            ),

        "linea_inicio":
            simbolo.get(
                "linea_inicio"
            ),

        "linea_fin":
            simbolo.get(
                "linea_fin"
            ),

        "llamadas":
            llamadas_contexto,

        "total_llamadas":
            len(
                llamadas_lista
            ),

        "llamadas_truncadas":
            llamadas_truncadas,

        "llamadores":
            llamadores_contexto,

        "total_llamadores":
            len(
                llamadores_lista
            ),

        "llamadores_truncados":
            llamadores_truncados,

        "modelos_alcanzables":
            [
                item.get(
                    "label"
                )
                for item
                in modelos_lista
            ],

        "evidencias_modelos":
            modelos.get(
                "evidencias",
                {},
            )
            if modelos.get(
                "ok"
            )
            else {},

        "operaciones_orm_directas":
            operaciones_directas,

        "urls":
            [
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
                }
                for item
                in urls
            ],

        "templates_que_apuntan":
            [
                {
                    "template":
                        item.get(
                            "template"
                        ),

                    "referencias":
                        item.get(
                            "referencias",
                            [],
                        ),
                }
                for item
                in templates_que_apuntan
            ],

        "evidencia":
            "verificada_host020",
    }


# ============================================================
# CONTEXTO DE URL
# ============================================================

def _contexto_url(
    item: dict[str, Any],
    *,
    profundidad: int,
) -> dict[str, Any]:

    view = _texto(
        item.get(
            "view"
        )
    )

    templates = (
        buscar_templates_de_view(
            view
        )
        if view
        else []
    )

    view_evidencia = None

    if view:

        simbolo = (
            resolver_simbolo_exacto(
                view
            )
        )

        if simbolo:

            view_evidencia = (
                _contexto_simbolo(
                    simbolo,
                    profundidad=profundidad,
                )
            )

    return {
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
            view,

        "templates_que_apuntan":
            [
                template.get(
                    "template"
                )
                for template
                in templates
            ],

        "view_evidencia":
            view_evidencia,

        "evidencia":
            "verificada_host020",
    }


# ============================================================
# CONTEXTO SEMÁNTICO ESTRUCTURADO
# ============================================================

def construir_contexto_semantico(
    pregunta: str,
    *,
    profundidad: int = 3,
) -> dict[str, Any]:
    """
    Construye un subgrafo relevante para la pregunta.

    No ejecuta LLM.

    Toda relación incluida debe provenir de:
        - catálogo Django;
        - _meta;
        - AST;
        - índice HOST020;
        - mapa real de URLs/templates.
    """

    modelos = (
        detectar_modelos_mencionados(
            pregunta
        )
    )

    simbolos = (
        detectar_simbolos_mencionados(
            pregunta
        )
    )

    urls = (
        detectar_urls_mencionadas(
            pregunta
        )
    )

    simbolos = (
        _filtrar_simbolos_modelos_canonicos(
            simbolos,
            modelos,
        )
    )

    contexto_modelos = [
        _contexto_modelo(
            modelo,
            profundidad=profundidad,
        )
        for modelo
        in modelos
    ]

    contexto_simbolos = [
        _contexto_simbolo(
            simbolo,
            profundidad=profundidad,
        )
        for simbolo
        in simbolos
    ]

    contexto_urls = [
        _contexto_url(
            item,
            profundidad=profundidad,
        )
        for item
        in urls
    ]

    hay_evidencia = bool(
        contexto_modelos
        or contexto_simbolos
        or contexto_urls
    )

    return {
        "pregunta":
            pregunta,

        "profundidad":
            profundidad,

        "version_contexto":
            "IA-HOST021",

        "politica_evidencia": {
            "hechos":
                "host_django_ast_indice",

            "llm":
                "solo_explicacion",

            "inferencias_no_demostradas":
                False,

            "template_view": (
                "templates_que_apuntan indica template -> URL/view; "
                "no implica view -> template renderizado."
            ),
        },

        "deteccion": {
            "modelos":
                len(
                    contexto_modelos
                ),

            "simbolos":
                len(
                    contexto_simbolos
                ),

            "urls":
                len(
                    contexto_urls
                ),
        },

        "modelos":
            contexto_modelos,

        "simbolos":
            contexto_simbolos,

        "urls":
            contexto_urls,

        "hay_evidencia":
            hay_evidencia,
    }


# ============================================================
# CONTEXTO TEXTUAL COMPACTO PARA LLM
# ============================================================

def contexto_semantico_a_texto(
    contexto: dict[str, Any],
) -> str:

    lineas = []

    lineas.append(
        "EVIDENCIA ESTRUCTURAL VERIFICADA DEL PROYECTO DJANGO"
    )

    lineas.append(
        "=" * 68
    )

    lineas.append(
        f"PREGUNTA: "
        f"{contexto.get('pregunta', '')}"
    )

    lineas.append(
        "FUENTE DE HECHOS: HOST / Django / AST / índice estructural."
    )

    lineas.append(
        "ROL DEL LLM: explicar únicamente los hechos incluidos aquí."
    )

    lineas.append("")

    if not contexto.get(
        "hay_evidencia"
    ):

        lineas.append(
            "No se encontró evidencia estructural suficiente."
        )

        lineas.append(
            "No inferir nombres, relaciones ni comportamientos."
        )

        return "\n".join(
            lineas
        )

    # ========================================================
    # MODELOS
    # ========================================================

    for modelo in contexto.get(
        "modelos",
        [],
    ):

        lineas.append(
            "HECHO VERIFICADO - MODELO"
        )

        lineas.append(
            f"- label: {modelo['label']}"
        )

        lineas.append(
            f"- tabla: {modelo['tabla']}"
        )

        lineas.append(
            f"- módulo: {modelo['modulo']}"
        )

        lineas.append(
            f"- funciones con uso directo demostrado: "
            f"{modelo['total_funciones']}"
        )

        for funcion in modelo.get(
            "funciones",
            [],
        ):

            lineas.append(
                f"  * {funcion.get('qualname')} "
                f"[{funcion.get('archivo')}:"
                f"{funcion.get('linea_inicio')}]"
            )

        if modelo.get(
            "funciones_truncadas"
        ):

            lineas.append(
                "  * lista truncada para mantener contexto compacto"
            )

        lineas.append(
            f"- views que alcanzan el modelo: "
            f"{modelo['total_views']}"
        )

        for view in modelo.get(
            "views",
            [],
        ):

            lineas.append(
                f"  * {view.get('view')}"
            )

            for url in view.get(
                "urls",
                [],
            ):

                lineas.append(
                    f"      URL: {url}"
                )

        if modelo.get(
            "views_truncadas"
        ):

            lineas.append(
                "  * lista de views truncada para contexto compacto"
            )

        lineas.append(
            f"- campos concretos: {modelo['total_campos']}"
        )

        for campo in modelo.get(
            "campos",
            [],
        ):

            detalle = (
                f"  * {campo.get('nombre')} "
                f"({campo.get('tipo')})"
            )

            if campo.get(
                "modelo_relacionado"
            ):

                detalle += (
                    f" -> {campo.get('modelo_relacionado')}"
                )

            lineas.append(
                detalle
            )

        lineas.append(
            f"- relaciones Django: {modelo['total_relaciones']}"
        )

        for relacion in modelo.get(
            "relaciones",
            [],
        ):

            lineas.append(
                f"  * {relacion.get('nombre')} "
                f"({relacion.get('tipo')}) "
                f"-> {relacion.get('modelo_relacionado')}"
            )

        usos = modelo.get(
            "usos_demostrados",
            [],
        )

        if usos:

            lineas.append(
                "- operaciones ORM demostradas:"
            )

        for uso in usos:

            lineas.append(
                f"  * {uso.get('simbolo')} "
                f"línea {uso.get('linea')}: "
                f"{uso.get('modo')} "
                f"{uso.get('operacion')} "
                f"sobre {uso.get('modelo')}"
            )

        lineas.append("")

    # ========================================================
    # SÍMBOLOS
    # ========================================================

    for simbolo in contexto.get(
        "simbolos",
        [],
    ):

        lineas.append(
            "HECHO VERIFICADO - SÍMBOLO"
        )

        lineas.append(
            f"- qualname: {simbolo['qualname']}"
        )

        lineas.append(
            f"- tipo: {simbolo['tipo']}"
        )

        lineas.append(
            f"- archivo: {simbolo['archivo']}"
        )

        lineas.append(
            f"- líneas: "
            f"{simbolo['linea_inicio']}-"
            f"{simbolo['linea_fin']}"
        )

        llamadas = simbolo.get(
            "llamadas",
            [],
        )

        if llamadas:

            lineas.append(
                "- llamadas internas demostradas:"
            )

            for destino in llamadas:

                lineas.append(
                    f"  * {destino}"
                )

        llamadores = simbolo.get(
            "llamadores",
            [],
        )

        if llamadores:

            lineas.append(
                "- llamadores demostrados:"
            )

            for origen in llamadores:

                lineas.append(
                    f"  * {origen}"
                )

        modelos = simbolo.get(
            "modelos_alcanzables",
            [],
        )

        if modelos:

            lineas.append(
                "- modelos alcanzables por el grafo:"
            )

            for modelo in modelos:

                lineas.append(
                    f"  * {modelo}"
                )

        operaciones = simbolo.get(
            "operaciones_orm_directas",
            [],
        )

        if operaciones:

            lineas.append(
                "- ORM directo del símbolo:"
            )

            for operacion in operaciones:

                lineas.append(
                    f"  * línea {operacion.get('linea')}: "
                    f"{operacion.get('modo')} "
                    f"{operacion.get('operacion')} "
                    f"sobre {operacion.get('modelo')}"
                )

        for url in simbolo.get(
            "urls",
            [],
        ):

            lineas.append(
                f"- URL registrada: "
                f"{url.get('ruta')}"
            )

        templates = simbolo.get(
            "templates_que_apuntan",
            [],
        )

        if templates:

            lineas.append(
                "- templates que APUNTAN a esta view "
                "(no implica renderizado por la view):"
            )

            for template in templates:

                lineas.append(
                    f"  * {template.get('template')}"
                )

        lineas.append("")

    # ========================================================
    # URLS
    # ========================================================

    for url in contexto.get(
        "urls",
        [],
    ):

        lineas.append(
            "HECHO VERIFICADO - URL"
        )

        lineas.append(
            f"- ruta: {url.get('ruta')}"
        )

        lineas.append(
            f"- nombre: "
            f"{url.get('namespace')}:"
            f"{url.get('name')}"
        )

        lineas.append(
            f"- view: {url.get('view')}"
        )

        for template in url.get(
            "templates_que_apuntan",
            [],
        ):

            lineas.append(
                f"- template que apunta a esta URL/view: "
                f"{template}"
            )

        lineas.append("")

    lineas.append(
        "REGLA DE RESPUESTA"
    )

    lineas.append(
        "1. Los elementos anteriores son hechos verificados por HOST."
    )

    lineas.append(
        "2. Puedes explicar cómo se relacionan esos hechos, "
        "pero no agregar relaciones ausentes."
    )

    lineas.append(
        "3. No confundir template que apunta a una view con "
        "template renderizado por esa view."
    )

    lineas.append(
        "4. Si la evidencia no alcanza para explicar un comportamiento, "
        "indicar exactamente qué parte no está demostrada."
    )

    return "\n".join(
        lineas
    )


# ============================================================
# CONTEXTO PARA LLM
# ============================================================

def construir_contexto_llm(
    pregunta: str,
    *,
    profundidad: int = 3,
) -> dict[str, Any]:

    estructurado = (
        construir_contexto_semantico(
            pregunta,
            profundidad=profundidad,
        )
    )

    texto = (
        contexto_semantico_a_texto(
            estructurado
        )
    )

    return {
        "pregunta":
            pregunta,

        "version_contexto":
            "IA-HOST021",

        "hay_evidencia":
            estructurado[
                "hay_evidencia"
            ],

        "deteccion":
            estructurado[
                "deteccion"
            ],

        "estructurado":
            estructurado,

        "contexto_texto":
            texto,

        "caracteres":
            len(
                texto
            ),
    }
