from __future__ import annotations

from typing import Any

from .inspector_grafo_negocio import (
    construir_grafo_negocio,
)
from .inspector_modelos_codigo import (
    construir_catalogo_modelos,
)
from .inspector_templates import (
    construir_mapa_templates,
)
from .inspector_urls import (
    construir_mapa_urls,
)
from .inspector_llamadas import (
    construir_indice_simbolos,
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


def _coincide(
    objetivo: str,
    *valores: Any,
) -> bool:

    objetivo = _normalizar(
        objetivo
    )

    if not objetivo:
        return False

    for valor in valores:

        if objetivo in _normalizar(
            valor
        ):
            return True

    return False


# ============================================================
# CONSULTA DE URLS
# ============================================================


def buscar_urls(
    texto: str,
) -> list[dict[str, Any]]:

    resultado = []

    for item in construir_mapa_urls():

        if not _coincide(
            texto,
            item.get(
                "ruta"
            ),
            item.get(
                "name"
            ),
            item.get(
                "namespace"
            ),
            item.get(
                "view"
            ),
        ):
            continue

        resultado.append(
            item
        )

    return resultado


# ============================================================
# CONSULTA DE TEMPLATES
# ============================================================


def buscar_templates(
    texto: str,
) -> list[dict[str, Any]]:

    resultado = []

    for template in construir_mapa_templates():

        coincide_template = _coincide(
            texto,
            template.get(
                "archivo"
            ),
            template.get(
                "ruta"
            ),
        )

        referencias = []

        for ref in template.get(
            "referencias",
            [],
        ):

            coincide_ref = _coincide(
                texto,
                ref.get(
                    "valor"
                ),
                ref.get(
                    "ruta_normalizada"
                ),
            )

            destinos = []

            for destino in ref.get(
                "destinos",
                [],
            ):

                if _coincide(
                    texto,
                    destino.get(
                        "ruta"
                    ),
                    destino.get(
                        "name"
                    ),
                    destino.get(
                        "namespace"
                    ),
                    destino.get(
                        "view"
                    ),
                ):

                    coincide_ref = True

                destinos.append(
                    destino
                )

            if coincide_ref:

                referencias.append(
                    {
                        **ref,
                        "destinos":
                            destinos,
                    }
                )

        if (
            coincide_template
            or referencias
        ):

            resultado.append(
                {
                    **template,

                    "referencias_coincidentes":
                        referencias,
                }
            )

    return resultado


# ============================================================
# CONSULTA DE SÍMBOLOS
# ============================================================


def buscar_simbolos(
    texto: str,
) -> list[dict[str, Any]]:

    indice = (
        construir_indice_simbolos()
    )

    resultado = []

    for simbolo in indice[
        "simbolos"
    ]:

        if not _coincide(
            texto,
            simbolo.get(
                "nombre"
            ),
            simbolo.get(
                "qualname"
            ),
            simbolo.get(
                "modulo"
            ),
            simbolo.get(
                "archivo"
            ),
        ):
            continue

        resultado.append(
            simbolo
        )

    return resultado


# ============================================================
# CONSULTA DE MODELOS
# ============================================================


def buscar_modelos(
    texto: str,
) -> list[dict[str, Any]]:

    catalogo = (
        construir_catalogo_modelos()
    )

    resultado = []

    for modelo in catalogo[
        "modelos"
    ]:

        if not _coincide(
            texto,
            modelo.get(
                "label"
            ),
            modelo.get(
                "app_label"
            ),
            modelo.get(
                "modelo"
            ),
            modelo.get(
                "tabla"
            ),
            modelo.get(
                "modulo"
            ),
        ):
            continue

        resultado.append(
            modelo
        )

    return resultado


# ============================================================
# URLS DE UNA VIEW
# ============================================================


def buscar_urls_de_view(
    view: str,
) -> list[dict[str, Any]]:

    objetivo = _normalizar(
        view
    )

    if not objetivo:
        return []

    return [
        item
        for item
        in construir_mapa_urls()
        if _normalizar(
            item.get(
                "view"
            )
        ) == objetivo
    ]


# ============================================================
# TEMPLATES QUE APUNTAN A UNA VIEW
# ============================================================


def buscar_templates_de_view(
    view: str,
) -> list[dict[str, Any]]:

    objetivo = _normalizar(
        view
    )

    resultado = []

    if not objetivo:
        return resultado

    for template in construir_mapa_templates():

        coincidencias = []

        for ref in template.get(
            "referencias",
            [],
        ):

            for destino in ref.get(
                "destinos",
                [],
            ):

                if _normalizar(
                    destino.get(
                        "view"
                    )
                ) != objetivo:
                    continue

                coincidencias.append(
                    {
                        "linea":
                            ref.get(
                                "linea"
                            ),

                        "tipo":
                            ref.get(
                                "tipo"
                            ),

                        "valor":
                            ref.get(
                                "valor"
                            ),

                        "destino":
                            destino,
                    }
                )

        if coincidencias:

            resultado.append(
                {
                    "template":
                        template.get(
                            "archivo"
                        ),

                    "ruta":
                        template.get(
                            "ruta"
                        ),

                    "app":
                        template.get(
                            "app"
                        ),

                    "referencias":
                        coincidencias,
                }
            )

    return resultado


# ============================================================
# FUNCIONES QUE LLAMAN A OTRA FUNCIÓN
# ============================================================


def buscar_llamadores(
    simbolo_destino: str,
) -> list[dict[str, Any]]:

    indice = (
        construir_indice_simbolos()
    )

    objetivo = _normalizar(
        simbolo_destino
    )

    nombre_objetivo = (
        simbolo_destino
        .split(
            "."
        )[-1]
        .strip()
        .lower()
    )

    resultado = []

    for simbolo in indice[
        "simbolos"
    ]:

        coincidencias = []

        for llamada in simbolo.get(
            "llamadas",
            [],
        ):

            nombre = _normalizar(
                llamada.get(
                    "nombre"
                )
            )

            nombre_simple = (
                nombre
                .split(
                    "."
                )[-1]
            )

            if (
                nombre == objetivo
                or nombre_simple
                == nombre_objetivo
            ):

                coincidencias.append(
                    llamada
                )

        if coincidencias:

            resultado.append(
                {
                    "simbolo":
                        simbolo,

                    "llamadas":
                        coincidencias,
                }
            )

    return resultado


# ============================================================
# GRAFO DE UNA ENTRADA
# ============================================================


def consultar_entrada(
    entrada: str,
    *,
    profundidad: int = 3,
) -> dict[str, Any]:

    return construir_grafo_negocio(
        entrada,
        profundidad=profundidad,
    )


# ============================================================
# BUSCAR MODELO DENTRO DE GRAFOS DE VIEWS
# ============================================================


def buscar_views_por_modelo(
    modelo: str,
    *,
    profundidad: int = 3,
) -> list[dict[str, Any]]:
    """
    Recorre las views registradas en URLs y determina qué
    grafos alcanzan el modelo solicitado.
    """

    objetivo = _normalizar(
        modelo
    )

    if not objetivo:
        return []

    views = []

    vistas = set()

    for url in construir_mapa_urls():

        view = _texto(
            url.get(
                "view"
            )
        )

        if (
            not view
            or view in vistas
        ):
            continue

        vistas.add(
            view
        )

        grafo = construir_grafo_negocio(
            view,
            profundidad=profundidad,
        )

        for raiz in grafo.get(
            "raices",
            [],
        ):

            modelos = raiz.get(
                "modelos",
                [],
            )

            coincidencias = [
                item
                for item
                in modelos
                if _coincide(
                    objetivo,
                    item.get(
                        "label"
                    ),
                    item.get(
                        "modelo"
                    ),
                    item.get(
                        "tabla"
                    ),
                )
            ]

            if not coincidencias:
                continue

            views.append(
                {
                    "view":
                        view,

                    "modelos":
                        coincidencias,

                    "urls":
                        raiz.get(
                            "urls",
                            [],
                        ),

                    "templates":
                        raiz.get(
                            "templates",
                            [],
                        ),

                    "operaciones_orm":
                        [
                            op
                            for op
                            in raiz.get(
                                "operaciones_orm",
                                [],
                            )
                            if _coincide(
                                objetivo,
                                op.get(
                                    "modelo",
                                    {}
                                ).get(
                                    "label"
                                ),
                                op.get(
                                    "modelo",
                                    {}
                                ).get(
                                    "modelo"
                                ),
                                op.get(
                                    "modelo",
                                    {}
                                ).get(
                                    "tabla"
                                ),
                            )
                        ],
                }
            )

    return views


# ============================================================
# CONSULTA GENERAL
# ============================================================


def consultar_grafo(
    texto: str,
    *,
    profundidad: int = 3,
) -> dict[str, Any]:

    return {
        "consulta":
            texto,

        "urls":
            buscar_urls(
                texto
            ),

        "templates":
            buscar_templates(
                texto
            ),

        "simbolos":
            buscar_simbolos(
                texto
            ),

        "modelos":
            buscar_modelos(
                texto
            ),

        "llamadores":
            buscar_llamadores(
                texto
            ),

        "profundidad":
            profundidad,
    }