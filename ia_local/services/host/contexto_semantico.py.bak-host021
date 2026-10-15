from __future__ import annotations

import re
from typing import Any

from .consultor_grafo import (
    buscar_llamadores,
    buscar_templates_de_view,
    buscar_urls_de_view,
    buscar_views_por_modelo,
)
from .inspector_llamadas import (
    construir_indice_simbolos,
)
from .inspector_modelos_codigo import (
    construir_catalogo_modelos,
)
from .inspector_urls import (
    construir_mapa_urls,
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
    return _texto(
        valor
    ).lower()



def _contiene_literal_aislado(
    texto: str,
    literal: str,
) -> bool:
    """
    Busca un literal completo evitando coincidencias parciales.

    Ejemplos:
        consulta_ia
    no coincide dentro de:
        consulta_ia_json

    Y:
        ia/
    no coincide dentro de:
        ia/consultar/
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


# ============================================================
# DETECCIÓN DE MODELOS MENCIONADOS
# ============================================================


def detectar_modelos_mencionados(
    pregunta: str,
) -> list[dict[str, Any]]:

    pregunta_normalizada = _normalizar(
        pregunta
    )

    if not pregunta_normalizada:
        return []

    catalogo = (
        construir_catalogo_modelos()
    )

    encontrados = []

    for modelo in catalogo[
        "modelos"
    ]:

        candidatos = {
            _normalizar(
                modelo.get(
                    "label"
                )
            ),
            _normalizar(
                modelo.get(
                    "modelo"
                )
            ),
            _normalizar(
                modelo.get(
                    "tabla"
                )
            ),
        }

        candidatos = {
            item
            for item
            in candidatos
            if len(
                item
            ) >= 3
        }

        if any(
            item in pregunta_normalizada
            for item in candidatos
        ):

            encontrados.append(
                modelo
            )

    encontrados.sort(
        key=lambda item: item[
            "label"
        ].lower()
    )

    return encontrados


# ============================================================
# DETECCIÓN DE SÍMBOLOS MENCIONADOS
# ============================================================


def detectar_simbolos_mencionados(
    pregunta: str,
) -> list[dict[str, Any]]:
    """
    Detecta símbolos mencionados explícitamente.

    Prioridad:
    1. qualname exacto
    2. nombre de símbolo exacto

    No utiliza substring libre, para evitar casos como
    consulta_ia dentro de consulta_ia_json.
    """

    pregunta_normalizada = _normalizar(
        pregunta
    )

    if not pregunta_normalizada:
        return []

    indice = (
        construir_indice_simbolos()
    )

    exactos_qualname = []

    for simbolo in indice[
        "simbolos"
    ]:

        qualname = _normalizar(
            simbolo.get(
                "qualname"
            )
        )

        if not qualname:
            continue

        if _contiene_literal_aislado(
            pregunta_normalizada,
            qualname,
        ):
            exactos_qualname.append(
                simbolo
            )

    if exactos_qualname:
        exactos_qualname.sort(
            key=lambda item: item[
                "qualname"
            ]
        )
        return exactos_qualname

    exactos_nombre = []
    vistos = set()

    for simbolo in indice[
        "simbolos"
    ]:

        nombre = _normalizar(
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

        qualname = simbolo[
            "qualname"
        ]

        if qualname in vistos:
            continue

        vistos.add(
            qualname
        )

        exactos_nombre.append(
            simbolo
        )

    exactos_nombre.sort(
        key=lambda item: item[
            "qualname"
        ]
    )

    return exactos_nombre


# ============================================================
# DETECCIÓN DE URLS MENCIONADAS
# ============================================================


def detectar_urls_mencionadas(
    pregunta: str,
) -> list[dict[str, Any]]:
    """
    Detecta URLs mencionadas explícitamente.

    Prioridad:
    1. ruta exacta
    2. namespace:name exacto

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

    coincidencias_ruta = []
    vistos = set()

    for item in mapa_urls:

        ruta = _normalizar(
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
            item.get(
                "ruta"
            ),
            item.get(
                "view"
            ),
        )

        if clave in vistos:
            continue

        vistos.add(
            clave
        )

        coincidencias_ruta.append(
            item
        )

    if coincidencias_ruta:
        coincidencias_ruta.sort(
            key=lambda item: len(
                _texto(
                    item.get(
                        "ruta"
                    )
                )
            ),
            reverse=True,
        )
        return coincidencias_ruta

    resultado = []
    vistos = set()

    for item in mapa_urls:

        nombre = _normalizar(
            item.get(
                "name"
            )
        )

        namespace = _normalizar(
            item.get(
                "namespace"
            )
        )

        if not (
            nombre
            and namespace
        ):
            continue

        nombre_completo = (
            f"{namespace}:{nombre}"
        )

        if not _contiene_literal_aislado(
            pregunta_normalizada,
            nombre_completo,
        ):
            continue

        clave = (
            item.get(
                "ruta"
            ),
            item.get(
                "view"
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


def _filtrar_simbolos_modelos_canonicos(
    simbolos: list[dict[str, Any]],
    modelos: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Si un modelo Django fue detectado explícitamente, conserva
    como símbolo de esa clase únicamente su definición canónica
    registrada por Django.
    """

    if (
        not simbolos
        or not modelos
    ):
        return simbolos

    canonicos_por_nombre = {}

    for modelo in modelos:

        nombre = _normalizar(
            modelo.get(
                "modelo"
            )
        )

        modulo = _normalizar(
            modelo.get(
                "modulo"
            )
        )

        if not (
            nombre
            and modulo
        ):
            continue

        canonicos_por_nombre[
            nombre
        ] = (
            f"{modulo}.{nombre}"
        )

    resultado = []
    vistos = set()

    for simbolo in simbolos:

        nombre = _normalizar(
            simbolo.get(
                "nombre"
            )
        )

        qualname = _normalizar(
            simbolo.get(
                "qualname"
            )
        )

        canonico = (
            canonicos_por_nombre.get(
                nombre
            )
        )

        if (
            canonico
            and qualname != canonico
        ):
            continue

        clave = simbolo.get(
            "qualname"
        )

        if clave in vistos:
            continue

        vistos.add(
            clave
        )

        resultado.append(
            simbolo
        )

    return resultado


# ============================================================
# CONTEXTO DE UN MODELO
# ============================================================

def _contexto_modelo(
    modelo: dict[str, Any],
    *,
    profundidad: int,
) -> dict[str, Any]:

    label = modelo[
        "label"
    ]

    views = (
        buscar_views_por_modelo(
            label,
            profundidad=profundidad,
        )
    )

    resultado_views = []

    # --------------------------------------------------------
    # Esta estructura reúne relaciones MODELO -> FUNCIÓN ORM
    # demostradas por HOST007/HOST008, eliminando duplicados
    # producidos porque varias views pueden alcanzar la misma
    # función.
    # --------------------------------------------------------

    usos_por_clave = {}

    for item in views:

        urls = _deduplicar_textos(
            [
                _texto(
                    url.get(
                        "ruta"
                    )
                )
                for url in item.get(
                    "urls",
                    [],
                )
            ]
        )

        templates = _deduplicar_textos(
            [
                _texto(
                    template.get(
                        "template"
                    )
                )
                for template in item.get(
                    "templates",
                    [],
                )
            ]
        )

        operaciones = []

        for operacion in item.get(
            "operaciones_orm",
            [],
        ):

            dato_operacion = {
                "simbolo":
                    operacion.get(
                        "simbolo"
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
            }

            operaciones.append(
                dato_operacion
            )

            # =================================================
            # USO DE MODELO DEMOSTRADO
            # =================================================

            simbolo = _texto(
                operacion.get(
                    "simbolo"
                )
            )

            modo = _texto(
                operacion.get(
                    "modo"
                )
            )

            linea = operacion.get(
                "linea"
            )

            nombre_operacion = _texto(
                operacion.get(
                    "operacion"
                )
            )

            if not simbolo:
                continue

            clave = (
                simbolo,
                modo,
                linea,
            )

            if clave not in usos_por_clave:

                usos_por_clave[
                    clave
                ] = {
                    "modelo":
                        label,

                    "tabla":
                        modelo.get(
                            "tabla"
                        ),

                    "simbolo":
                        simbolo,

                    "modo":
                        modo,

                    "linea":
                        linea,

                    "operaciones":
                        [],
                }

            if (
                nombre_operacion
                and nombre_operacion
                not in usos_por_clave[
                    clave
                ][
                    "operaciones"
                ]
            ):

                usos_por_clave[
                    clave
                ][
                    "operaciones"
                ].append(
                    nombre_operacion
                )

        resultado_views.append(
            {
                "view":
                    item.get(
                        "view"
                    ),

                "urls":
                    urls,

                "templates":
                    templates,

                "operaciones_orm":
                    operaciones,
            }
        )

    usos_demostrados = list(
        usos_por_clave.values()
    )

    usos_demostrados.sort(
        key=lambda item: (
            item[
                "simbolo"
            ],
            item[
                "linea"
            ]
            if item[
                "linea"
            ] is not None
            else -1,
        )
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

        "views":
            resultado_views,

        # Relación directa y explícita para HOST012.
        "usos_demostrados":
            usos_demostrados,
    }



# ============================================================
# CONTEXTO DE UN SÍMBOLO
# ============================================================


def _contexto_simbolo(
    simbolo: dict[str, Any],
) -> dict[str, Any]:

    qualname = simbolo[
        "qualname"
    ]

    llamadores = (
        buscar_llamadores(
            qualname
        )
    )

    resultado_llamadores = []

    for item in llamadores:

        origen = item[
            "simbolo"
        ]

        resultado_llamadores.append(
            {
                "qualname":
                    origen.get(
                        "qualname"
                    ),

                "archivo":
                    origen.get(
                        "archivo"
                    ),

                "llamadas":
                    [
                        {
                            "nombre":
                                llamada.get(
                                    "nombre"
                                ),

                            "linea":
                                llamada.get(
                                    "linea"
                                ),
                        }
                        for llamada
                        in item.get(
                            "llamadas",
                            [],
                        )
                    ],
            }
        )

    urls = (
        buscar_urls_de_view(
            qualname
        )
    )

    templates = (
        buscar_templates_de_view(
            qualname
        )
    )

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

        "llamadores":
            resultado_llamadores,

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

        "templates":
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
                in templates
            ],
    }


# ============================================================
# CONTEXTO DE URL
# ============================================================


def _contexto_url(
    item: dict[str, Any],
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

        "templates":
            [
                template.get(
                    "template"
                )
                for template
                in templates
            ],
    }


# ============================================================
# CONTEXTO SEMÁNTICO ESTRUCTURADO
# ============================================================


def construir_contexto_semantico(
    pregunta: str,
    *,
    profundidad: int = 3,
) -> dict[str, Any]:

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
            simbolo
        )
        for simbolo
        in simbolos
    ]

    contexto_urls = [
        _contexto_url(
            item
        )
        for item
        in urls
    ]

    return {
        "pregunta":
            pregunta,

        "profundidad":
            profundidad,

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
            bool(
                contexto_modelos
                or contexto_simbolos
                or contexto_urls
            ),
    }


# ============================================================
# CONTEXTO TEXTUAL COMPACTO PARA LLM
# ============================================================


def contexto_semantico_a_texto(
    contexto: dict[str, Any],
) -> str:

    lineas = []

    lineas.append(
        "EVIDENCIA ESTRUCTURAL DEL PROYECTO DJANGO"
    )

    lineas.append(
        "=" * 60
    )

    lineas.append(
        f"PREGUNTA: "
        f"{contexto.get('pregunta', '')}"
    )

    lineas.append("")

    if not contexto.get(
        "hay_evidencia"
    ):

        lineas.append(
            "No se encontró evidencia estructural "
            "suficiente para la pregunta."
        )

        lineas.append(
            "No inferir nombres, relaciones ni "
            "comportamientos no demostrados."
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
            "MODELO"
        )

        lineas.append(
            f"- label: "
            f"{modelo['label']}"
        )

        lineas.append(
            f"- tabla: "
            f"{modelo['tabla']}"
        )

        lineas.append(
            f"- módulo: "
            f"{modelo['modulo']}"
        )

        if modelo[
            "views"
        ]:

            lineas.append(
                "- views relacionadas:"
            )

        for view in modelo[
            "views"
        ]:

            lineas.append(
                f"  * {view['view']}"
            )

            for url in view[
                "urls"
            ]:

                lineas.append(
                    f"      URL: {url}"
                )

            for template in view[
                "templates"
            ]:

                lineas.append(
                    f"      template: "
                    f"{template}"
                )

            for op in view[
                "operaciones_orm"
            ]:

                lineas.append(
                    f"      ORM: "
                    f"{op['modo']} "
                    f"{op['operacion']} "
                    f"en {op['simbolo']} "
                    f"línea {op['linea']}"
                )

        # ====================================================
        # RELACIONES MODELO -> FUNCIÓN DEMOSTRADAS
        # ====================================================

        if modelo.get(
            "usos_demostrados"
        ):

            lineas.append(
                "- USOS DE MODELO DEMOSTRADOS:"
            )

        for uso in modelo.get(
            "usos_demostrados",
            [],
        ):

            lineas.append(
                f"  * modelo: "
                f"{uso['modelo']}"
            )

            lineas.append(
                f"    función: "
                f"{uso['simbolo']}"
            )

            lineas.append(
                f"    tabla: "
                f"{uso['tabla']}"
            )

            lineas.append(
                f"    modo: "
                f"{uso['modo']}"
            )

            lineas.append(
                f"    operaciones ORM: "
                f"{', '.join(uso['operaciones'])}"
            )

            lineas.append(
                f"    línea: "
                f"{uso['linea']}"
            )

            lineas.append(
                "    hecho: esta función usa el modelo "
                "indicado mediante las operaciones ORM "
                "listadas."
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
            "SÍMBOLO"
        )

        lineas.append(
            f"- qualname: "
            f"{simbolo['qualname']}"
        )

        lineas.append(
            f"- tipo: "
            f"{simbolo['tipo']}"
        )

        lineas.append(
            f"- archivo: "
            f"{simbolo['archivo']}"
        )

        lineas.append(
            f"- líneas: "
            f"{simbolo['linea_inicio']}"
            f"-"
            f"{simbolo['linea_fin']}"
        )

        if simbolo[
            "llamadores"
        ]:

            lineas.append(
                "- llamado desde:"
            )

        for llamador in simbolo[
            "llamadores"
        ]:

            lineas.append(
                f"  * "
                f"{llamador['qualname']}"
            )

            for llamada in llamador[
                "llamadas"
            ]:

                lineas.append(
                    f"      línea "
                    f"{llamada['linea']}: "
                    f"{llamada['nombre']}"
                )

        for url in simbolo[
            "urls"
        ]:

            lineas.append(
                f"- URL: "
                f"{url['ruta']}"
            )

        for template in simbolo[
            "templates"
        ]:

            lineas.append(
                f"- template: "
                f"{template['template']}"
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
            "URL"
        )

        lineas.append(
            f"- ruta: "
            f"{url['ruta']}"
        )

        lineas.append(
            f"- nombre: "
            f"{url['namespace']}:"
            f"{url['name']}"
        )

        lineas.append(
            f"- view: "
            f"{url['view']}"
        )

        for template in url[
            "templates"
        ]:

            lineas.append(
                f"- template: "
                f"{template}"
            )

        lineas.append("")

    lineas.append(
        "REGLA DE RESPUESTA"
    )

    lineas.append(
        "Usar solamente la evidencia anterior. "
        "Si falta información para afirmar algo, "
        "indicarlo explícitamente."
    )

    return "\n".join(
        lineas
    )

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