from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from django.apps import apps

from .inspector_llamadas import (
    construir_grafo_llamadas,
    construir_indice_simbolos,
)


# ============================================================
# OPERACIONES ORM CONOCIDAS
# ============================================================

OPERACIONES_LECTURA = {
    "all",
    "filter",
    "exclude",
    "get",
    "first",
    "last",
    "count",
    "exists",
    "values",
    "values_list",
    "order_by",
    "select_related",
    "prefetch_related",
    "aggregate",
    "annotate",
    "latest",
    "earliest",
    "in_bulk",
}

OPERACIONES_ESCRITURA = {
    "create",
    "get_or_create",
    "update_or_create",
    "bulk_create",
    "bulk_update",
    "update",
}

OPERACIONES_ORM = (
    OPERACIONES_LECTURA
    | OPERACIONES_ESCRITURA
)


# ============================================================
# MODELOS DJANGO REALES
# ============================================================

def construir_catalogo_modelos() -> dict[str, Any]:
    modelos = []

    por_label = {}
    por_nombre = {}

    for modelo in apps.get_models():

        label = modelo._meta.label
        nombre = modelo._meta.object_name

        item = {
            "label":
                label,

            "app_label":
                modelo._meta.app_label,

            "modelo":
                nombre,

            "tabla":
                modelo._meta.db_table,

            "modulo":
                modelo.__module__,
        }

        modelos.append(
            item
        )

        por_label[
            label.lower()
        ] = item

        por_nombre.setdefault(
            nombre.lower(),
            [],
        ).append(
            item
        )

    modelos.sort(
        key=lambda item: item[
            "label"
        ].lower()
    )

    return {
        "modelos":
            modelos,

        "por_label":
            por_label,

        "por_nombre":
            por_nombre,
    }


# ============================================================
# LECTURA / AST
# ============================================================

def _leer_archivo(
    ruta: str,
) -> str:

    archivo = Path(
        ruta
    )

    if not archivo.is_file():
        return ""

    try:
        return archivo.read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception:
        return ""


def _parsear(
    contenido: str,
    ruta: str = "",
) -> ast.Module | None:

    try:
        return ast.parse(
            contenido,
            filename=ruta or "<codigo>",
        )

    except SyntaxError:
        return None


def _texto_ast(
    nodo: ast.AST,
) -> str:

    try:
        return ast.unparse(
            nodo
        )

    except Exception:
        return ""


# ============================================================
# IMPORTS DE MODELOS
# ============================================================

def _catalogar_imports_modelos(
    arbol: ast.Module,
    catalogo: dict[str, Any],
    *,
    modulo_actual: str = "",
) -> dict[str, dict[str, Any]]:
    """
    Detecta modelos Django importados en un archivo.

    Soporta imports absolutos:

        from documents.models import Document

    e imports relativos:

        from .models import IAReglaSemantica
        from ..models import Modelo

    El enlace se realiza contra el catálogo real de modelos
    registrado por Django, no mediante nombres hardcodeados.
    """

    resultado = {}

    for nodo in arbol.body:

        if not isinstance(
            nodo,
            ast.ImportFrom,
        ):
            continue

        modulo_importado = str(
            nodo.module
            or ""
        )

        nivel_relativo = int(
            nodo.level
            or 0
        )

        # ----------------------------------------------------
        # Resolver módulo absoluto real del import
        # ----------------------------------------------------

        modulo_resuelto = modulo_importado

        if nivel_relativo > 0:

            partes_actual = (
                modulo_actual.split(".")
                if modulo_actual
                else []
            )

            # El módulo actual normalmente es algo como:
            #
            # ia_local.views
            #
            # Su paquete base es:
            #
            # ia_local
            #
            if partes_actual:
                paquete = partes_actual[:-1]
            else:
                paquete = []

            subir = (
                nivel_relativo
                - 1
            )

            if subir > 0:
                paquete = paquete[
                    :max(
                        0,
                        len(paquete)
                        - subir
                    )
                ]

            if modulo_importado:

                modulo_resuelto = ".".join(
                    paquete
                    + modulo_importado.split(".")
                )

            else:

                modulo_resuelto = ".".join(
                    paquete
                )

        if not (
            modulo_resuelto.endswith(
                ".models"
            )
            or modulo_resuelto == "models"
        ):
            continue

        # ----------------------------------------------------
        # Resolver cada símbolo contra modelos Django reales
        # ----------------------------------------------------

        for alias in nodo.names:

            nombre_real = str(
                alias.name
            )

            nombre_visible = (
                alias.asname
                or nombre_real
            )

            candidatos = []

            for modelo in catalogo[
                "modelos"
            ]:

                if (
                    modelo[
                        "modelo"
                    ] != nombre_real
                ):
                    continue

                if (
                    modelo[
                        "modulo"
                    ] == modulo_resuelto
                ):
                    candidatos.append(
                        modelo
                    )

            if len(
                candidatos
            ) == 1:

                resultado[
                    nombre_visible
                ] = candidatos[
                    0
                ]

    return resultado

# ============================================================
# apps.get_model(...)
# ============================================================

def _resolver_get_model(
    nodo: ast.Call,
    catalogo: dict[str, Any],
) -> dict[str, Any] | None:

    funcion = _texto_ast(
        nodo.func
    )

    if not (
        funcion == "apps.get_model"
        or funcion.endswith(
            ".apps.get_model"
        )
        or funcion.endswith(
            ".get_model"
        )
    ):
        return None

    args = nodo.args

    if not args:
        return None

    label = ""

    # apps.get_model("rdi", "PlanosRecord")
    if len(
        args
    ) >= 2:

        if (
            isinstance(
                args[0],
                ast.Constant,
            )
            and isinstance(
                args[0].value,
                str,
            )
            and isinstance(
                args[1],
                ast.Constant,
            )
            and isinstance(
                args[1].value,
                str,
            )
        ):

            label = (
                f"{args[0].value}."
                f"{args[1].value}"
            )

    # apps.get_model("rdi.PlanosRecord")
    elif len(
        args
    ) == 1:

        if (
            isinstance(
                args[0],
                ast.Constant,
            )
            and isinstance(
                args[0].value,
                str,
            )
        ):

            label = str(
                args[0].value
            )

    if not label:
        return None

    return catalogo[
        "por_label"
    ].get(
        label.lower()
    )


# ============================================================
# DETECCIÓN ORM
# ============================================================

def _descomponer_atributos(
    nodo: ast.AST,
) -> list[str]:

    partes = []

    actual = nodo

    while isinstance(
        actual,
        ast.Attribute,
    ):

        partes.append(
            actual.attr
        )

        actual = actual.value

    if isinstance(
        actual,
        ast.Name,
    ):
        partes.append(
            actual.id
        )

    partes.reverse()

    return partes


def _detectar_operacion_orm(
    nodo: ast.Call,
    aliases_modelos: dict[
        str,
        dict[str, Any],
    ],
) -> dict[str, Any] | None:
    """
    Detecta principalmente:

        Modelo.objects.filter(...)
        Modelo.objects.create(...)
        Modelo.objects.all().filter(...)
    """

    texto = _texto_ast(
        nodo.func
    )

    if not texto:
        return None

    # Encontrar qué modelo importado aparece al inicio.
    modelo = None
    alias_modelo = ""

    for alias, modelo_item in (
        aliases_modelos.items()
    ):

        if (
            texto == alias
            or texto.startswith(
                f"{alias}."
            )
        ):

            modelo = modelo_item
            alias_modelo = alias
            break

    if modelo is None:
        return None

    # Para considerarlo ORM debe existir acceso a objects.
    if (
        f"{alias_modelo}.objects"
        not in texto
    ):
        return None

    partes = texto.split(
        "."
    )

    operacion = ""

    for parte in reversed(
        partes
    ):

        if parte in OPERACIONES_ORM:
            operacion = parte
            break

    if not operacion:

        return None

    if operacion in OPERACIONES_ESCRITURA:
        modo = "escritura"

    else:
        modo = "lectura"

    return {
        "modelo":
            modelo,

        "alias":
            alias_modelo,

        "operacion":
            operacion,

        "modo":
            modo,

        "expresion":
            texto,

        "linea":
            getattr(
                nodo,
                "lineno",
                None,
            ),
    }


# ============================================================
# LOCALIZACIÓN DEL SÍMBOLO AST
# ============================================================

def _buscar_nodo_simbolo(
    arbol: ast.Module,
    nombre: str,
    linea_inicio: int | None,
) -> ast.AST | None:

    for nodo in arbol.body:

        if not isinstance(
            nodo,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            continue

        if getattr(
            nodo,
            "name",
            "",
        ) != nombre:
            continue

        if (
            linea_inicio is not None
            and getattr(
                nodo,
                "lineno",
                None,
            )
            != linea_inicio
        ):
            continue

        return nodo

    return None


# ============================================================
# MODELOS UTILIZADOS POR UN SÍMBOLO
# ============================================================

def analizar_modelos_simbolo(
    simbolo: dict[str, Any],
    *,
    catalogo: dict[str, Any] | None = None,
) -> dict[str, Any]:

    if catalogo is None:

        catalogo = (
            construir_catalogo_modelos()
        )

    ruta = str(
        simbolo.get(
            "ruta",
            ""
        )
        or ""
    )

    contenido = _leer_archivo(
        ruta
    )

    if not contenido:

        return {
            "modelos":
                [],

            "operaciones":
                [],

            "get_model":
                [],
        }

    arbol = _parsear(
        contenido,
        ruta,
    )

    if arbol is None:

        return {
            "modelos":
                [],

            "operaciones":
                [],

            "get_model":
                [],
        }

    aliases_modelos = (
        _catalogar_imports_modelos(
            arbol,
            catalogo,
            modulo_actual=str(
                simbolo.get(
                    "modulo",
                    ""
                )
                or ""
            ),
        )
    )

    nodo_simbolo = (
        _buscar_nodo_simbolo(
            arbol,
            simbolo.get(
                "nombre",
                ""
            ),
            simbolo.get(
                "linea_inicio"
            ),
        )
    )

    if nodo_simbolo is None:

        return {
            "modelos":
                [],

            "operaciones":
                [],

            "get_model":
                [],
        }

    operaciones = []
    modelos_encontrados = {}
    get_model_encontrados = []

    for nodo in ast.walk(
        nodo_simbolo
    ):

        if not isinstance(
            nodo,
            ast.Call,
        ):
            continue

        # ----------------------------------------------
        # ORM directo mediante Modelo.objects...
        # ----------------------------------------------

        operacion = (
            _detectar_operacion_orm(
                nodo,
                aliases_modelos,
            )
        )

        if operacion:

            operaciones.append(
                operacion
            )

            modelo = operacion[
                "modelo"
            ]

            modelos_encontrados[
                modelo[
                    "label"
                ]
            ] = modelo

        # ----------------------------------------------
        # apps.get_model(...)
        # ----------------------------------------------

        modelo_dinamico = (
            _resolver_get_model(
                nodo,
                catalogo,
            )
        )

        if modelo_dinamico:

            get_model_encontrados.append(
                {
                    "modelo":
                        modelo_dinamico,

                    "linea":
                        getattr(
                            nodo,
                            "lineno",
                            None,
                        ),

                    "expresion":
                        _texto_ast(
                            nodo
                        ),
                }
            )

            modelos_encontrados[
                modelo_dinamico[
                    "label"
                ]
            ] = modelo_dinamico

    operaciones.sort(
        key=lambda item: (
            item[
                "linea"
            ]
            or 0,
            item[
                "modelo"
            ][
                "label"
            ],
            item[
                "operacion"
            ],
        )
    )

    modelos = list(
        modelos_encontrados.values()
    )

    modelos.sort(
        key=lambda item: item[
            "label"
        ].lower()
    )

    return {
        "modelos":
            modelos,

        "operaciones":
            operaciones,

        "get_model":
            get_model_encontrados,

        "aliases_modelos":
            {
                alias:
                    modelo[
                        "label"
                    ]
                for alias, modelo
                in aliases_modelos.items()
            },
    }


# ============================================================
# BÚSQUEDA POR QUALNAME
# ============================================================

def analizar_simbolo_por_qualname(
    qualname: str,
) -> dict[str, Any]:

    indice = (
        construir_indice_simbolos()
    )

    simbolo = indice[
        "por_qualname"
    ].get(
        qualname
    )

    if not simbolo:

        return {
            "encontrado":
                False,

            "qualname":
                qualname,

            "modelos":
                [],

            "operaciones":
                [],
        }

    analisis = (
        analizar_modelos_simbolo(
            simbolo
        )
    )

    return {
        "encontrado":
            True,

        "simbolo":
            simbolo,

        **analisis,
    }


# ============================================================
# RECORRIDO DEL GRAFO DE LLAMADAS + MODELOS
# ============================================================

def _recoger_nodos_grafo(
    nodo: dict[str, Any],
    salida: list[dict[str, Any]],
    vistos: set[str],
) -> None:

    qualname = str(
        nodo.get(
            "qualname",
            ""
        )
        or ""
    )

    if (
        not qualname
        or qualname in vistos
    ):
        return

    vistos.add(
        qualname
    )

    salida.append(
        nodo
    )

    for llamada in nodo.get(
        "llamadas",
        [],
    ):

        for destino in llamada.get(
            "destinos",
            [],
        ):

            subnodo = destino.get(
                "nodo"
            )

            if subnodo:

                _recoger_nodos_grafo(
                    subnodo,
                    salida,
                    vistos,
                )


def construir_grafo_modelos(
    simbolo_raiz: str,
    *,
    profundidad: int = 3,
) -> dict[str, Any]:

    grafo_llamadas = (
        construir_grafo_llamadas(
            simbolo_raiz,
            profundidad=profundidad,
        )
    )

    indice = (
        construir_indice_simbolos()
    )

    catalogo = (
        construir_catalogo_modelos()
    )

    nodos = []
    vistos = set()

    for candidato in grafo_llamadas[
        "candidatos"
    ]:

        _recoger_nodos_grafo(
            candidato,
            nodos,
            vistos,
        )

    resultado_nodos = []

    modelos_globales = {}
    operaciones_globales = []

    for nodo in nodos:

        simbolo = indice[
            "por_qualname"
        ].get(
            nodo[
                "qualname"
            ]
        )

        if not simbolo:
            continue

        analisis = (
            analizar_modelos_simbolo(
                simbolo,
                catalogo=catalogo,
            )
        )

        for modelo in analisis[
            "modelos"
        ]:

            modelos_globales[
                modelo[
                    "label"
                ]
            ] = modelo

        for operacion in analisis[
            "operaciones"
        ]:

            operaciones_globales.append(
                {
                    "simbolo":
                        nodo[
                            "qualname"
                        ],

                    **operacion,
                }
            )

        resultado_nodos.append(
            {
                "qualname":
                    nodo[
                        "qualname"
                    ],

                "archivo":
                    nodo[
                        "archivo"
                    ],

                "linea_inicio":
                    nodo[
                        "linea_inicio"
                    ],

                "linea_fin":
                    nodo[
                        "linea_fin"
                    ],

                "modelos":
                    analisis[
                        "modelos"
                    ],

                "operaciones":
                    analisis[
                        "operaciones"
                    ],

                "get_model":
                    analisis[
                        "get_model"
                    ],
            }
        )

    modelos = list(
        modelos_globales.values()
    )

    modelos.sort(
        key=lambda item: item[
            "label"
        ].lower()
    )

    return {
        "simbolo_raiz":
            simbolo_raiz,

        "profundidad":
            profundidad,

        "total_nodos_codigo":
            len(
                resultado_nodos
            ),

        "total_modelos":
            len(
                modelos
            ),

        "modelos":
            modelos,

        "operaciones":
            operaciones_globales,

        "nodos":
            resultado_nodos,

        "grafo_llamadas":
            grafo_llamadas,
    }