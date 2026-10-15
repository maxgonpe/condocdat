from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from django.conf import settings

from .inspector_proyecto import (
    obtener_archivos_python,
)

from .inspector_imports import (
    analizar_imports_simbolo,
)


# ============================================================
# UTILIDADES
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


def _nombre_llamada(
    nodo: ast.Call,
) -> str:
    try:
        return ast.unparse(
            nodo.func
        )
    except Exception:
        return ""


def _codigo_nodo(
    contenido: str,
    nodo: ast.AST,
) -> str:
    try:
        return (
            ast.get_source_segment(
                contenido,
                nodo,
            )
            or ""
        )
    except Exception:
        return ""


def _tipo_simbolo(
    nodo: ast.AST,
) -> str:

    if isinstance(
        nodo,
        ast.FunctionDef,
    ):
        return "funcion"

    if isinstance(
        nodo,
        ast.AsyncFunctionDef,
    ):
        return "funcion_async"

    if isinstance(
        nodo,
        ast.ClassDef,
    ):
        return "clase"

    return "desconocido"


def _modulo_desde_archivo(
    archivo: str,
) -> str:
    """
    Convierte:

        ia_local/services/foo.py

    en:

        ia_local.services.foo
    """

    ruta = Path(
        archivo
    )

    if ruta.suffix != ".py":
        return ""

    partes = list(
        ruta.with_suffix(
            ""
        ).parts
    )

    if partes and partes[-1] == "__init__":
        partes = partes[:-1]

    return ".".join(
        partes
    )


# ============================================================
# EXTRACCIÓN DE SÍMBOLOS
# ============================================================

def _extraer_simbolos_archivo(
    archivo_item: dict[str, Any],
) -> list[dict[str, Any]]:

    archivo_relativo = str(
        archivo_item.get(
            "archivo",
            ""
        )
        or ""
    )

    ruta_absoluta = str(
        archivo_item.get(
            "ruta",
            ""
        )
        or ""
    )

    contenido = _leer_archivo(
        ruta_absoluta
    )

    if not contenido:
        return []

    try:
        arbol = ast.parse(
            contenido,
            filename=ruta_absoluta,
        )
    except SyntaxError:
        return []

    modulo = _modulo_desde_archivo(
        archivo_relativo
    )

    resultado = []

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

        nombre = getattr(
            nodo,
            "name",
            "",
        )

        if not nombre:
            continue

        linea_inicio = getattr(
            nodo,
            "lineno",
            None,
        )

        linea_fin = getattr(
            nodo,
            "end_lineno",
            None,
        )

        lineas_total = None

        if (
            linea_inicio is not None
            and linea_fin is not None
        ):
            lineas_total = (
                linea_fin
                - linea_inicio
                + 1
            )

        llamadas = []

        for sub in ast.walk(
            nodo
        ):

            if not isinstance(
                sub,
                ast.Call,
            ):
                continue

            nombre_llamada = (
                _nombre_llamada(
                    sub
                )
            )

            if not nombre_llamada:
                continue

            llamadas.append(
                {
                    "nombre":
                        nombre_llamada,

                    "linea":
                        getattr(
                            sub,
                            "lineno",
                            None,
                        ),
                }
            )

        llamadas.sort(
            key=lambda item: (
                item[
                    "linea"
                ]
                or 0,
                item[
                    "nombre"
                ],
            )
        )

        qualname = (
            f"{modulo}.{nombre}"
            if modulo
            else nombre
        )

        resultado.append(
            {
                "nombre":
                    nombre,

                "qualname":
                    qualname,

                "modulo":
                    modulo,

                "archivo":
                    archivo_relativo,

                "ruta":
                    ruta_absoluta,

                "tipo":
                    _tipo_simbolo(
                        nodo
                    ),

                "linea_inicio":
                    linea_inicio,

                "linea_fin":
                    linea_fin,

                "lineas_total":
                    lineas_total,

                "llamadas":
                    llamadas,

                "codigo":
                    _codigo_nodo(
                        contenido,
                        nodo,
                    ),
            }
        )

    return resultado


# ============================================================
# ÍNDICE GLOBAL
# ============================================================

def construir_indice_simbolos() -> dict[str, Any]:

    archivos = (
        obtener_archivos_python()
    )

    simbolos = []

    por_nombre: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    por_qualname: dict[
        str,
        dict[str, Any],
    ] = {}

    errores = []

    for archivo in archivos:

        try:
            encontrados = (
                _extraer_simbolos_archivo(
                    archivo
                )
            )

        except Exception as exc:

            errores.append(
                {
                    "archivo":
                        archivo.get(
                            "archivo",
                            ""
                        ),

                    "error":
                        f"{type(exc).__name__}: {exc}",
                }
            )

            continue

        for simbolo in encontrados:

            simbolos.append(
                simbolo
            )

            por_nombre.setdefault(
                simbolo[
                    "nombre"
                ],
                [],
            ).append(
                simbolo
            )

            por_qualname[
                simbolo[
                    "qualname"
                ]
            ] = simbolo

    simbolos.sort(
        key=lambda item: (
            item[
                "archivo"
            ],
            item[
                "linea_inicio"
            ]
            or 0,
        )
    )

    return {
        "simbolos":
            simbolos,

        "por_nombre":
            por_nombre,

        "por_qualname":
            por_qualname,

        "errores":
            errores,
    }


# ============================================================
# RESOLUCIÓN DE UNA LLAMADA
# ============================================================

def _nombre_simple(
    llamada: str,
) -> str:

    valor = str(
        llamada
        or ""
    ).strip()

    if not valor:
        return ""

    return (
        valor
        .split(".")[-1]
        .strip()
    )


def resolver_llamada_interna(
    llamada: str,
    *,
    simbolo_origen: dict[str, Any] | None = None,
    indice: dict[str, Any] | None = None,
) -> dict[str, Any]:

    if indice is None:

        indice = (
            construir_indice_simbolos()
        )

    llamada = str(
        llamada
        or ""
    ).strip()

    nombre_simple = (
        _nombre_simple(
            llamada
        )
    )

    respuesta_base = {
        "llamada":
            llamada,

        "nombre_simple":
            nombre_simple,

        "resuelta":
            False,

        "ambigua":
            False,

        "destinos":
            [],

        "metodo_resolucion":
            None,
    }

    if not nombre_simple:
        return respuesta_base

    # ========================================================
    # 1. RESOLUCIÓN MEDIANTE IMPORTS REALES
    # ========================================================

    if simbolo_origen:

        imports = (
            analizar_imports_simbolo(
                simbolo_origen
            )
        )

        simbolos_importados = (
            imports.get(
                "simbolos",
                {}
            )
        )

        modulos_importados = (
            imports.get(
                "modulos",
                {}
            )
        )

        destino_import = None

        # ----------------------------------------------------
        # Caso:
        #
        # from .orm_generico import ejecutar_consulta
        #
        # ejecutar_consulta(...)
        # ----------------------------------------------------

        if "." not in llamada:

            destino_import = (
                simbolos_importados.get(
                    llamada
                )
            )

        # ----------------------------------------------------
        # Casos:
        #
        # import modulo as alias
        # alias.funcion(...)
        #
        # from paquete import modulo
        # modulo.funcion(...)
        # ----------------------------------------------------

        else:

            partes = llamada.split(
                "."
            )

            primero = partes[
                0
            ]

            resto = ".".join(
                partes[
                    1:
                ]
            )

            prefijo = (
                modulos_importados.get(
                    primero
                )
            )

            if prefijo and resto:

                destino_import = (
                    f"{prefijo}.{resto}"
                )

            else:

                prefijo = (
                    simbolos_importados.get(
                        primero
                    )
                )

                if prefijo and resto:

                    destino_import = (
                        f"{prefijo}.{resto}"
                    )

        if destino_import:

            destino = indice[
                "por_qualname"
            ].get(
                destino_import
            )

            if destino:

                return {
                    **respuesta_base,

                    "resuelta":
                        True,

                    "destinos":
                        [
                            destino
                        ],

                    "metodo_resolucion":
                        "import",
                }

    # ========================================================
    # 2. MISMO MÓDULO
    # ========================================================

    if simbolo_origen:

        modulo_origen = str(
            simbolo_origen.get(
                "modulo",
                ""
            )
            or ""
        )

        if modulo_origen:

            qualname_local = (
                f"{modulo_origen}."
                f"{nombre_simple}"
            )

            destino_local = indice[
                "por_qualname"
            ].get(
                qualname_local
            )

            if destino_local:

                return {
                    **respuesta_base,

                    "resuelta":
                        True,

                    "destinos":
                        [
                            destino_local
                        ],

                    "metodo_resolucion":
                        "mismo_modulo",
                }

    # ========================================================
    # 3. BÚSQUEDA GENERAL POR NOMBRE
    # ========================================================

    candidatos = list(
        indice[
            "por_nombre"
        ].get(
            nombre_simple,
            [],
        )
    )

    if not candidatos:
        return respuesta_base

    # ========================================================
    # 4. PRIORIZACIÓN POR MISMA APP
    # ========================================================

    if (
        simbolo_origen
        and len(
            candidatos
        ) > 1
    ):

        modulo_origen = str(
            simbolo_origen.get(
                "modulo",
                ""
            )
            or ""
        )

        app_origen = (
            modulo_origen.split(
                "."
            )[0]
            if modulo_origen
            else ""
        )

        if app_origen:

            misma_app = [
                item
                for item
                in candidatos
                if (
                    item[
                        "modulo"
                    ].split(
                        "."
                    )[0]
                    == app_origen
                )
            ]

            if misma_app:
                candidatos = misma_app

    return {
        **respuesta_base,

        "resuelta":
            len(
                candidatos
            ) == 1,

        "ambigua":
            len(
                candidatos
            ) > 1,

        "destinos":
            candidatos,

        "metodo_resolucion":
            (
                "nombre"
                if len(
                    candidatos
                ) == 1
                else "ambiguo"
            ),
    }

# ============================================================
# RESOLUCIÓN DE LLAMADAS DE UN SÍMBOLO
# ============================================================

def resolver_llamadas_simbolo(
    simbolo: dict[str, Any],
    *,
    indice: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:

    if indice is None:
        indice = (
            construir_indice_simbolos()
        )

    resultado = []

    for llamada in simbolo.get(
        "llamadas",
        [],
    ):

        resolucion = (
            resolver_llamada_interna(
                llamada.get(
                    "nombre",
                    ""
                ),
                simbolo_origen=simbolo,
                indice=indice,
            )
        )

        resultado.append(
            {
                "linea":
                    llamada.get(
                        "linea"
                    ),

                **resolucion,
            }
        )

    return resultado


# ============================================================
# BÚSQUEDA DE SÍMBOLOS
# ============================================================

def buscar_simbolo(
    texto: str,
) -> list[dict[str, Any]]:

    objetivo = str(
        texto
        or ""
    ).strip().lower()

    if not objetivo:
        return []

    indice = construir_indice_simbolos()

    resultado = []

    for simbolo in indice[
        "simbolos"
    ]:

        if (
            objetivo
            in simbolo[
                "nombre"
            ].lower()
            or objetivo
            in simbolo[
                "qualname"
            ].lower()
        ):
            resultado.append(
                simbolo
            )

    return resultado


# ============================================================
# GRAFO DE LLAMADAS
# ============================================================

def construir_grafo_llamadas(
    simbolo_raiz: str,
    *,
    profundidad: int = 2,
) -> dict[str, Any]:

    indice = construir_indice_simbolos()

    candidatos = []

    # Intento por qualname exacto.
    exacto = indice[
        "por_qualname"
    ].get(
        simbolo_raiz
    )

    if exacto:
        candidatos = [
            exacto
        ]

    else:
        nombre_simple = (
            _nombre_simple(
                simbolo_raiz
            )
        )

        candidatos = list(
            indice[
                "por_nombre"
            ].get(
                nombre_simple,
                [],
            )
        )

    visitados = set()

    def recorrer(
        simbolo: dict[str, Any],
        nivel: int,
    ) -> dict[str, Any]:

        clave = simbolo[
            "qualname"
        ]

        nodo = {
            "nombre":
                simbolo[
                    "nombre"
                ],

            "qualname":
                simbolo[
                    "qualname"
                ],

            "modulo":
                simbolo[
                    "modulo"
                ],

            "archivo":
                simbolo[
                    "archivo"
                ],

            "ruta":
                simbolo[
                    "ruta"
                ],

            "tipo":
                simbolo[
                    "tipo"
                ],

            "linea_inicio":
                simbolo[
                    "linea_inicio"
                ],

            "linea_fin":
                simbolo[
                    "linea_fin"
                ],

            "lineas_total":
                simbolo[
                    "lineas_total"
                ],

            "llamadas":
                [],
        }

        if nivel >= profundidad:
            return nodo

        if clave in visitados:
            return nodo

        visitados.add(
            clave
        )

        resoluciones = (
            resolver_llamadas_simbolo(
                simbolo,
                indice=indice,
            )
        )

        for resolucion in resoluciones:

            item = {
                "linea":
                    resolucion[
                        "linea"
                    ],

                "llamada":
                    resolucion[
                        "llamada"
                    ],

                "nombre_simple":
                    resolucion[
                        "nombre_simple"
                    ],

                "resuelta":
                    resolucion[
                        "resuelta"
                    ],

                "ambigua":
                    resolucion[
                        "ambigua"
                    ],

                "destinos":
                    [],
            }

            for destino in resolucion[
                "destinos"
            ]:

                destino_item = {
                    "nombre":
                        destino[
                            "nombre"
                        ],

                    "qualname":
                        destino[
                            "qualname"
                        ],

                    "archivo":
                        destino[
                            "archivo"
                        ],

                    "linea_inicio":
                        destino[
                            "linea_inicio"
                        ],

                    "linea_fin":
                        destino[
                            "linea_fin"
                        ],
                }

                if (
                    resolucion[
                        "resuelta"
                    ]
                    and nivel + 1
                    <= profundidad
                ):

                    destino_item[
                        "nodo"
                    ] = recorrer(
                        destino,
                        nivel + 1,
                    )

                item[
                    "destinos"
                ].append(
                    destino_item
                )

            nodo[
                "llamadas"
            ].append(
                item
            )

        return nodo

    return {
        "simbolo_raiz":
            simbolo_raiz,

        "profundidad":
            profundidad,

        "candidatos":
            [
                recorrer(
                    simbolo,
                    0,
                )
                for simbolo
                in candidatos
            ],

        "errores":
            indice[
                "errores"
            ],
    }


# ============================================================
# RESUMEN DEL ÍNDICE
# ============================================================

def construir_resumen_llamadas() -> dict[str, Any]:

    indice = construir_indice_simbolos()

    funciones = [
        item
        for item
        in indice[
            "simbolos"
        ]
        if item[
            "tipo"
        ] in {
            "funcion",
            "funcion_async",
        }
    ]

    clases = [
        item
        for item
        in indice[
            "simbolos"
        ]
        if item[
            "tipo"
        ] == "clase"
    ]

    return {
        "totales": {
            "simbolos":
                len(
                    indice[
                        "simbolos"
                    ]
                ),

            "funciones":
                len(
                    funciones
                ),

            "clases":
                len(
                    clases
                ),

            "errores":
                len(
                    indice[
                        "errores"
                    ]
                ),
        },

        "errores":
            indice[
                "errores"
            ],
    }