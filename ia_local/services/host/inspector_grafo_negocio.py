from __future__ import annotations

from typing import Any

from .inspector_modelos_codigo import (
    construir_grafo_modelos,
)
from .inspector_templates import (
    construir_mapa_templates,
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


def _normalizar_ruta(
    valor: str,
) -> str:
    ruta = _texto(
        valor
    )

    if not ruta:
        return ""

    ruta = ruta.split(
        "?",
        1,
    )[0]

    ruta = ruta.split(
        "#",
        1,
    )[0]

    ruta = ruta.strip()

    if ruta.startswith("/"):
        ruta = ruta[1:]

    return ruta


# ============================================================
# RESOLUCIÓN DE RAÍZ
# ============================================================


def resolver_raices_negocio(
    entrada: str,
) -> list[dict[str, Any]]:
    """
    Intenta resolver una entrada como:

        view completa:
            ia_local.views.consulta_ia_json

        ruta:
            ia/consultar/
            /ia/consultar/

        nombre URL:
            consultar

        namespace:name:
            ia_local:consultar

    Si no encuentra ninguna URL coincidente, considera la
    entrada como un posible qualname de símbolo.
    """

    entrada = _texto(
        entrada
    )

    if not entrada:
        return []

    entrada_ruta = _normalizar_ruta(
        entrada
    )

    mapa_urls = (
        construir_mapa_urls()
    )

    encontrados: dict[
        str,
        dict[str, Any],
    ] = {}

    for item in mapa_urls:

        view = _texto(
            item.get(
                "view"
            )
        )

        ruta = _normalizar_ruta(
            item.get(
                "ruta",
                ""
            )
        )

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

        nombre_completo = (
            f"{namespace}:{nombre}"
            if namespace and nombre
            else nombre
        )

        coincide = any(
            (
                view == entrada,
                ruta == entrada_ruta,
                nombre == entrada,
                nombre_completo == entrada,
            )
        )

        if not coincide:
            continue

        if not view:
            continue

        raiz = encontrados.setdefault(
            view,
            {
                "view":
                    view,

                "urls":
                    [],
            },
        )

        raiz[
            "urls"
        ].append(
            item
        )

    if encontrados:
        return list(
            encontrados.values()
        )

    # Puede ser una función interna que no tenga URL.
    return [
        {
            "view":
                entrada,

            "urls":
                [],
        }
    ]


# ============================================================
# TEMPLATE -> URL -> VIEW
# ============================================================


def _buscar_templates_entrada(
    view: str,
) -> list[dict[str, Any]]:

    resultado = []

    for template in construir_mapa_templates():

        for referencia in template.get(
            "referencias",
            [],
        ):

            for destino in referencia.get(
                "destinos",
                [],
            ):

                if _texto(
                    destino.get(
                        "view"
                    )
                ) != view:
                    continue

                app = template.get(
                    "app"
                )

                resultado.append(
                    {
                        "template":
                            template.get(
                                "archivo"
                            ),

                        "ruta_template":
                            template.get(
                                "ruta"
                            ),

                        "app":
                            (
                                app.get(
                                    "label"
                                )
                                if app
                                else None
                            ),

                        "tipo_app":
                            (
                                app.get(
                                    "tipo"
                                )
                                if app
                                else None
                            ),

                        "linea":
                            referencia.get(
                                "linea"
                            ),

                        "tipo_referencia":
                            referencia.get(
                                "tipo"
                            ),

                        "valor":
                            referencia.get(
                                "valor"
                            ),

                        "url": {
                            "ruta":
                                destino.get(
                                    "ruta"
                                ),

                            "name":
                                destino.get(
                                    "name"
                                ),

                            "namespace":
                                destino.get(
                                    "namespace"
                                ),

                            "view":
                                destino.get(
                                    "view"
                                ),
                        },
                    }
                )

    resultado.sort(
        key=lambda item: (
            _texto(
                item.get(
                    "template"
                )
            ),
            item.get(
                "linea"
            )
            or 0,
        )
    )

    return resultado


# ============================================================
# APLANAR GRAFO DE LLAMADAS
# ============================================================


def _aplanar_grafo_llamadas(
    grafo_llamadas: dict[str, Any],
) -> dict[str, Any]:

    nodos: dict[
        str,
        dict[str, Any],
    ] = {}

    aristas = []

    llamadas_externas = []
    llamadas_ambiguas = []

    procesados = set()

    def recorrer(
        nodo: dict[str, Any],
    ) -> None:

        qualname = _texto(
            nodo.get(
                "qualname"
            )
        )

        if not qualname:
            return

        if qualname not in nodos:

            nodos[
                qualname
            ] = {
                "qualname":
                    qualname,

                "nombre":
                    nodo.get(
                        "nombre"
                    ),

                "modulo":
                    nodo.get(
                        "modulo"
                    ),

                "archivo":
                    nodo.get(
                        "archivo"
                    ),

                "ruta":
                    nodo.get(
                        "ruta"
                    ),

                "tipo":
                    nodo.get(
                        "tipo"
                    ),

                "linea_inicio":
                    nodo.get(
                        "linea_inicio"
                    ),

                "linea_fin":
                    nodo.get(
                        "linea_fin"
                    ),

                "lineas_total":
                    nodo.get(
                        "lineas_total"
                    ),
            }

        if qualname in procesados:
            return

        procesados.add(
            qualname
        )

        for llamada in nodo.get(
            "llamadas",
            [],
        ):

            nombre_llamada = _texto(
                llamada.get(
                    "llamada"
                )
            )

            linea = llamada.get(
                "linea"
            )

            resuelta = bool(
                llamada.get(
                    "resuelta"
                )
            )

            ambigua = bool(
                llamada.get(
                    "ambigua"
                )
            )

            destinos = llamada.get(
                "destinos",
                [],
            )

            if resuelta:

                estado = "interna"

            elif ambigua:

                estado = "ambigua"

            else:

                estado = "externa"

            if not destinos:

                item = {
                    "origen":
                        qualname,

                    "destino":
                        None,

                    "llamada":
                        nombre_llamada,

                    "linea":
                        linea,

                    "estado":
                        estado,
                }

                aristas.append(
                    item
                )

                if estado == "externa":

                    llamadas_externas.append(
                        item
                    )

                continue

            for destino in destinos:

                destino_qualname = _texto(
                    destino.get(
                        "qualname"
                    )
                )

                item = {
                    "origen":
                        qualname,

                    "destino":
                        destino_qualname
                        or None,

                    "llamada":
                        nombre_llamada,

                    "linea":
                        linea,

                    "estado":
                        estado,
                }

                aristas.append(
                    item
                )

                if estado == "ambigua":

                    llamadas_ambiguas.append(
                        item
                    )

                subnodo = destino.get(
                    "nodo"
                )

                if subnodo:

                    recorrer(
                        subnodo
                    )

    for candidato in grafo_llamadas.get(
        "candidatos",
        [],
    ):

        recorrer(
            candidato
        )

    lista_nodos = list(
        nodos.values()
    )

    lista_nodos.sort(
        key=lambda item: item[
            "qualname"
        ]
    )

    return {
        "nodos":
            lista_nodos,

        "aristas":
            aristas,

        "llamadas_externas":
            llamadas_externas,

        "llamadas_ambiguas":
            llamadas_ambiguas,
    }


# ============================================================
# CONSTRUIR UNA RAÍZ
# ============================================================


def _construir_raiz_negocio(
    raiz: dict[str, Any],
    *,
    profundidad: int,
) -> dict[str, Any]:

    view = _texto(
        raiz.get(
            "view"
        )
    )

    grafo_modelos = (
        construir_grafo_modelos(
            view,
            profundidad=profundidad,
        )
    )

    grafo_codigo = (
        _aplanar_grafo_llamadas(
            grafo_modelos.get(
                "grafo_llamadas",
                {},
            )
        )
    )

    templates = (
        _buscar_templates_entrada(
            view
        )
    )

    modelos = grafo_modelos.get(
        "modelos",
        [],
    )

    operaciones = grafo_modelos.get(
        "operaciones",
        [],
    )

    tablas = []

    tablas_vistas = set()

    for modelo in modelos:

        tabla = _texto(
            modelo.get(
                "tabla"
            )
        )

        if (
            tabla
            and tabla not in tablas_vistas
        ):

            tablas_vistas.add(
                tabla
            )

            tablas.append(
                {
                    "tabla":
                        tabla,

                    "modelo":
                        modelo.get(
                            "label"
                        ),
                }
            )

    urls = []

    for item in raiz.get(
        "urls",
        [],
    ):

        urls.append(
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

                "app":
                    item.get(
                        "app"
                    ),

                "tipo_app":
                    item.get(
                        "tipo_app"
                    ),
            }
        )

    return {
        "raiz":
            view,

        "profundidad":
            profundidad,

        "templates":
            templates,

        "urls":
            urls,

        "codigo": {
            "nodos":
                grafo_codigo[
                    "nodos"
                ],

            "aristas":
                grafo_codigo[
                    "aristas"
                ],

            "llamadas_externas":
                grafo_codigo[
                    "llamadas_externas"
                ],

            "llamadas_ambiguas":
                grafo_codigo[
                    "llamadas_ambiguas"
                ],
        },

        "modelos":
            modelos,

        "operaciones_orm":
            operaciones,

        "tablas":
            tablas,

        "estadisticas": {
            "templates":
                len(
                    templates
                ),

            "urls":
                len(
                    urls
                ),

            "nodos_codigo":
                len(
                    grafo_codigo[
                        "nodos"
                    ]
                ),

            "aristas_codigo":
                len(
                    grafo_codigo[
                        "aristas"
                    ]
                ),

            "llamadas_externas":
                len(
                    grafo_codigo[
                        "llamadas_externas"
                    ]
                ),

            "llamadas_ambiguas":
                len(
                    grafo_codigo[
                        "llamadas_ambiguas"
                    ]
                ),

            "modelos":
                len(
                    modelos
                ),

            "operaciones_orm":
                len(
                    operaciones
                ),

            "tablas":
                len(
                    tablas
                ),
        },
    }


# ============================================================
# GRAFO NEGOCIO
# ============================================================


def construir_grafo_negocio(
    entrada: str,
    *,
    profundidad: int = 3,
) -> dict[str, Any]:

    raices = resolver_raices_negocio(
        entrada
    )

    resultado = []

    for raiz in raices:

        resultado.append(
            _construir_raiz_negocio(
                raiz,
                profundidad=profundidad,
            )
        )

    return {
        "entrada":
            entrada,

        "profundidad":
            profundidad,

        "total_raices":
            len(
                resultado
            ),

        "raices":
            resultado,
    }


# ============================================================
# RESUMEN COMPACTO
# ============================================================


def resumir_grafo_negocio(
    entrada: str,
    *,
    profundidad: int = 3,
) -> dict[str, Any]:

    grafo = construir_grafo_negocio(
        entrada,
        profundidad=profundidad,
    )

    raices = []

    for raiz in grafo[
        "raices"
    ]:

        raices.append(
            {
                "raiz":
                    raiz[
                        "raiz"
                    ],

                **raiz[
                    "estadisticas"
                ],
            }
        )

    return {
        "entrada":
            entrada,

        "profundidad":
            profundidad,

        "total_raices":
            grafo[
                "total_raices"
            ],

        "raices":
            raices,
    }