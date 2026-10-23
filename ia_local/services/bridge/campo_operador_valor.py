from __future__ import annotations

from ia_local.config.cardinalidad import (
    LIMITE_MUESTRA_PREDETERMINADO,
)


import re
from typing import Any

from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)

from ia_local.services.semantica.normalizacion import (
    normalizar_texto,
)

from ia_local.services.semantica.politica_prioridad import (
    resolver_con_politica,
)

from .compositor_sem_host import (
    componer_sem_a_host,
)


VERSION = "IA-BRIDGE003-v1"

MAX_FRAGMENTO = 6


# ============================================================
# OPERACIONES DE CONSULTA
# ============================================================


OPERACIONES = {
    "listar": "listar",
    "lista": "listar",
    "listame": "listar",
    "mostrar": "listar",
    "muestra": "listar",
    "muestrame": "listar",
    "dame": "listar",
    "ver": "listar",

    "contar": "contar",
    "cuenta": "contar",
    "cuantos": "contar",
    "cuantas": "contar",
    "cantidad": "contar",
    "total": "contar",
}


# ============================================================
# OPERADORES DE FILTRO
# ============================================================
#
# Se utilizan solamente expresiones explícitas.
#
# No intentamos deducir operadores mediante similitud.
#
# El valor final siempre vuelve a ser validado por HOST.
# ============================================================


OPERADORES = [
    # --------------------------------------------------------
    # TEXTO
    # --------------------------------------------------------

    (
        ("no", "contiene"),
        "NO_SOPORTADO",
    ),

    (
        ("no", "contenga"),
        "NO_SOPORTADO",
    ),

    (
        ("contiene",),
        "icontains",
    ),

    (
        ("contengan",),
        "icontains",
    ),

    (
        ("contenga",),
        "icontains",
    ),

    (
        ("incluye",),
        "icontains",
    ),

    (
        ("incluyan",),
        "icontains",
    ),

    (
        ("incluya",),
        "icontains",
    ),

    (
        ("igual", "a"),
        "iexact",
    ),

    (
        ("es", "igual", "a"),
        "iexact",
    ),

    (
        ("es",),
        "iexact",
    ),

    # --------------------------------------------------------
    # COMPARACIÓN
    # --------------------------------------------------------

    (
        ("mayor", "o", "igual", "que"),
        "gte",
    ),

    (
        ("mayor", "o", "igual", "a"),
        "gte",
    ),

    (
        ("menor", "o", "igual", "que"),
        "lte",
    ),

    (
        ("menor", "o", "igual", "a"),
        "lte",
    ),

    (
        ("mayor", "que"),
        "gt",
    ),

    (
        ("mayor", "a"),
        "gt",
    ),

    (
        ("menor", "que"),
        "lt",
    ),

    (
        ("menor", "a"),
        "lt",
    ),

    # --------------------------------------------------------
    # NULOS
    # --------------------------------------------------------

    (
        ("es", "nulo"),
        "isnull_true",
    ),

    (
        ("esta", "vacio"),
        "isnull_true",
    ),

    (
        ("esta", "vacia"),
        "isnull_true",
    ),

    (
        ("no", "es", "nulo"),
        "isnull_false",
    ),

    (
        ("no", "esta", "vacio"),
        "isnull_false",
    ),

    (
        ("no", "esta", "vacia"),
        "isnull_false",
    ),
]


# Ordenar siempre expresiones largas primero.
OPERADORES = sorted(
    OPERADORES,
    key=lambda item: len(
        item[0]
    ),
    reverse=True,
)


# ============================================================
# CONECTORES GRAMATICALES
# ============================================================


CONECTORES = {
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",

    "de",
    "del",
    "al",

    "que",
    "cuyo",
    "cuya",
    "cuyos",
    "cuyas",

    "con",
    "donde",

    "campo",
    "atributo",
    "propiedad",

    "todos",
    "todas",
    "todo",
    "toda",
}


# ============================================================
# TOKENIZACIÓN
# ============================================================


def _tokenizar(
    texto: str,
) -> list[dict[str, Any]]:
    """
    Mantiene simultáneamente:

        original
        normalizado

    para que la detección sea tolerante a acentos pero el
    valor libre conserve la escritura del usuario.
    """

    partes = re.findall(
        r'"[^"]*"|\'[^\']*\'|\S+',
        texto,
    )

    tokens = []

    for indice, parte in enumerate(
        partes
    ):

        original = parte.strip()

        sin_comillas = original

        if (
            len(
                sin_comillas
            )
            >= 2
            and (
                (
                    sin_comillas.startswith(
                        '"'
                    )
                    and sin_comillas.endswith(
                        '"'
                    )
                )
                or (
                    sin_comillas.startswith(
                        "'"
                    )
                    and sin_comillas.endswith(
                        "'"
                    )
                )
            )
        ):
            sin_comillas = (
                sin_comillas[
                    1:-1
                ]
            )

        normalizado = normalizar_texto(
            sin_comillas
        )

        tokens.append(
            {
                "indice":
                    indice,

                "original":
                    sin_comillas,

                "normalizado":
                    normalizado,

                "citado":
                    sin_comillas
                    != original,
            }
        )

    return tokens


def _palabras_normalizadas(
    tokens: list[dict[str, Any]],
) -> list[str]:

    return [
        token[
            "normalizado"
        ]
        for token
        in tokens
    ]


# ============================================================
# OPERACIÓN PRINCIPAL
# ============================================================


def _resolver_operacion(
    tokens: list[dict[str, Any]],
) -> dict[str, Any]:

    candidatos = []

    for token in tokens:

        palabra = token[
            "normalizado"
        ]

        operacion = OPERACIONES.get(
            palabra
        )

        if not operacion:
            continue

        candidatos.append(
            {
                "operacion":
                    operacion,

                "indice":
                    token[
                        "indice"
                    ],

                "texto":
                    token[
                        "original"
                    ],
            }
        )

    operaciones = {
        candidato[
            "operacion"
        ]
        for candidato
        in candidatos
    }

    if not operaciones:

        return {
            "ok":
                False,

            "estado":
                "operacion_no_resuelta",
        }

    if len(
        operaciones
    ) > 1:

        return {
            "ok":
                False,

            "estado":
                "operacion_ambigua",

            "candidatos":
                candidatos,
        }

    return {
        "ok":
            True,

        "estado":
            "operacion_resuelta",

        "operacion":
            next(
                iter(
                    operaciones
                )
            ),

        "indices":
            {
                candidato[
                    "indice"
                ]
                for candidato
                in candidatos
            },

        "candidatos":
            candidatos,
    }


# ============================================================
# OPERADOR CAMPO / VALOR
# ============================================================


def _buscar_operador(
    tokens: list[dict[str, Any]],
) -> dict[str, Any]:

    palabras = _palabras_normalizadas(
        tokens
    )

    coincidencias = []

    for expresion, operador in OPERADORES:

        largo = len(
            expresion
        )

        for inicio in range(
            0,
            len(
                palabras
            )
            - largo
            + 1,
        ):

            fin = (
                inicio
                + largo
            )

            if tuple(
                palabras[
                    inicio:fin
                ]
            ) != expresion:
                continue

            coincidencias.append(
                {
                    "expresion":
                        " ".join(
                            expresion
                        ),

                    "operador":
                        operador,

                    "inicio":
                        inicio,

                    "fin":
                        fin,
                }
            )

    if not coincidencias:

        return {
            "ok":
                False,

            "estado":
                "operador_no_resuelto",
        }

    # Las expresiones están ordenadas de mayor a menor,
    # pero nos aseguramos nuevamente.

    max_largo = max(
        coincidencia[
            "fin"
        ]
        - coincidencia[
            "inicio"
        ]
        for coincidencia
        in coincidencias
    )

    coincidencias = [
        coincidencia
        for coincidencia
        in coincidencias
        if (
            coincidencia[
                "fin"
            ]
            - coincidencia[
                "inicio"
            ]
            == max_largo
        )
    ]

    posiciones = {
        (
            coincidencia[
                "inicio"
            ],
            coincidencia[
                "fin"
            ],
        )
        for coincidencia
        in coincidencias
    }

    if len(
        posiciones
    ) > 1:

        return {
            "ok":
                False,

            "estado":
                "operador_ambiguo",

            "coincidencias":
                coincidencias,
        }

    coincidencia = coincidencias[
        0
    ]

    if (
        coincidencia[
            "operador"
        ]
        == "NO_SOPORTADO"
    ):

        return {
            "ok":
                False,

            "estado":
                "operador_no_soportado",

            "expresion":
                coincidencia[
                    "expresion"
                ],
        }

    return {
        "ok":
            True,

        "estado":
            "operador_resuelto",

        **coincidencia,
    }


# ============================================================
# FRAGMENTOS SEM
# ============================================================


def _fragmentos(
    tokens: list[dict[str, Any]],
    *,
    posiciones_permitidas: set[int],
) -> list[dict[str, Any]]:

    resultados = []

    indices = sorted(
        posiciones_permitidas
    )

    if not indices:
        return resultados

    for largo in range(
        min(
            MAX_FRAGMENTO,
            len(
                tokens
            ),
        ),
        0,
        -1,
    ):

        for inicio in range(
            0,
            len(
                tokens
            )
            - largo
            + 1,
        ):

            fin = inicio + largo

            rango = set(
                range(
                    inicio,
                    fin,
                )
            )

            if not rango.issubset(
                posiciones_permitidas
            ):
                continue

            # Fragmentos que comienzan o terminan únicamente
            # con conectores no aportan precisión.

            palabras = [
                tokens[
                    indice
                ][
                    "normalizado"
                ]
                for indice
                in range(
                    inicio,
                    fin,
                )
            ]

            while (
                palabras
                and palabras[0]
                in CONECTORES
            ):
                palabras.pop(
                    0
                )
                inicio += 1

            while (
                palabras
                and palabras[-1]
                in CONECTORES
            ):
                palabras.pop()

                fin -= 1

            if not palabras:
                continue

            texto = " ".join(
                palabras
            )

            resultados.append(
                {
                    "texto":
                        texto,

                    "inicio":
                        inicio,

                    "fin":
                        fin,

                    "largo":
                        len(
                            palabras
                        ),
                }
            )

    return resultados


# ============================================================
# ENTIDAD
# ============================================================


def _resolver_entidad(
    tokens: list[dict[str, Any]],
    *,
    indices_operacion: set[int],
    operador_inicio: int,
) -> dict[str, Any]:

    posiciones = {
        indice
        for indice
        in range(
            0,
            operador_inicio,
        )
        if indice
        not in indices_operacion
    }

    candidatos = []

    ocupados = set()

    for fragmento in _fragmentos(
        tokens,
        posiciones_permitidas=posiciones,
    ):

        rango = set(
            range(
                fragmento[
                    "inicio"
                ],
                fragmento[
                    "fin"
                ],
            )
        )

        if rango & ocupados:
            continue

        resolucion = resolver_con_politica(
            fragmento[
                "texto"
            ],
            incluir_reglas=False,
        )

        if (
            resolucion.get(
                "estado"
            )
            != "resuelto"
        ):
            continue

        resultado = resolucion.get(
            "resultado"
        )

        if not isinstance(
            resultado,
            dict,
        ):
            continue

        if (
            resultado.get(
                "tipo"
            )
            != "entidad"
        ):
            continue

        candidatos.append(
            {
                "fragmento":
                    fragmento,

                "resultado":
                    resultado,

                "resolucion":
                    resolucion,
            }
        )

        ocupados.update(
            rango
        )

    modelos = {
        candidato[
            "resultado"
        ].get(
            "modelo"
        )
        for candidato
        in candidatos
        if candidato[
            "resultado"
        ].get(
            "modelo"
        )
    }

    if not modelos:

        return {
            "ok":
                False,

            "estado":
                "entidad_no_resuelta",

            "candidatos":
                candidatos,
        }

    if len(
        modelos
    ) > 1:

        return {
            "ok":
                False,

            "estado":
                "entidad_ambigua",

            "modelos":
                sorted(
                    modelos
                ),

            "candidatos":
                candidatos,
        }

    modelo = next(
        iter(
            modelos
        )
    )

    candidatos_modelo = [
        candidato
        for candidato
        in candidatos
        if candidato[
            "resultado"
        ].get(
            "modelo"
        )
        == modelo
    ]

    elegido = max(
        candidatos_modelo,
        key=lambda candidato: (
            candidato[
                "fragmento"
            ][
                "largo"
            ]
        ),
    )

    return {
        "ok":
            True,

        "estado":
            "entidad_resuelta",

        "modelo":
            modelo,

        "fragmento":
            elegido[
                "fragmento"
            ],

        "resultado":
            elegido[
                "resultado"
            ],

        "resolucion":
            elegido[
                "resolucion"
            ],
    }


# ============================================================
# CAMPO
# ============================================================


def _resolver_campo(
    tokens: list[dict[str, Any]],
    *,
    modelo: str,
    indices_operacion: set[int],
    entidad_fragmento: dict[str, Any],
    operador_inicio: int,
) -> dict[str, Any]:

    posiciones_excluidas = set(
        indices_operacion
    )

    posiciones_excluidas.update(
        range(
            entidad_fragmento[
                "inicio"
            ],
            entidad_fragmento[
                "fin"
            ],
        )
    )

    posiciones = {
        indice
        for indice
        in range(
            0,
            operador_inicio,
        )
        if indice
        not in posiciones_excluidas
    }

    candidatos = []

    for fragmento in _fragmentos(
        tokens,
        posiciones_permitidas=posiciones,
    ):

        resolucion = resolver_con_politica(
            fragmento[
                "texto"
            ],
            modelo_contexto=modelo,
            incluir_reglas=False,
        )

        if (
            resolucion.get(
                "estado"
            )
            != "resuelto"
        ):
            continue

        resultado = resolucion.get(
            "resultado"
        )

        if not isinstance(
            resultado,
            dict,
        ):
            continue

        if (
            resultado.get(
                "tipo"
            )
            != "campo"
        ):
            continue

        if (
            resultado.get(
                "modelo"
            )
            != modelo
        ):
            continue

        candidatos.append(
            {
                "fragmento":
                    fragmento,

                "resultado":
                    resultado,

                "resolucion":
                    resolucion,
            }
        )

    campos = {
        candidato[
            "resultado"
        ].get(
            "campo"
        )
        for candidato
        in candidatos
        if candidato[
            "resultado"
        ].get(
            "campo"
        )
    }

    if not campos:

        return {
            "ok":
                False,

            "estado":
                "campo_no_resuelto",

            "modelo":
                modelo,

            "candidatos":
                candidatos,
        }

    if len(
        campos
    ) > 1:

        return {
            "ok":
                False,

            "estado":
                "campo_ambiguo",

            "modelo":
                modelo,

            "campos":
                sorted(
                    campos
                ),

            "candidatos":
                candidatos,
        }

    campo = next(
        iter(
            campos
        )
    )

    candidatos_campo = [
        candidato
        for candidato
        in candidatos
        if candidato[
            "resultado"
        ].get(
            "campo"
        )
        == campo
    ]

    elegido = max(
        candidatos_campo,
        key=lambda candidato: (
            candidato[
                "fragmento"
            ][
                "largo"
            ]
        ),
    )

    return {
        "ok":
            True,

        "estado":
            "campo_resuelto",

        "modelo":
            modelo,

        "campo":
            campo,

        "fragmento":
            elegido[
                "fragmento"
            ],

        "resultado":
            elegido[
                "resultado"
            ],

        "resolucion":
            elegido[
                "resolucion"
            ],
    }


# ============================================================
# TEXTO NO CONSUMIDO ANTES DEL OPERADOR
# ============================================================


def _validar_prefijo_consumido(
    tokens: list[dict[str, Any]],
    *,
    indices_operacion: set[int],
    entidad_fragmento: dict[str, Any],
    campo_fragmento: dict[str, Any],
    operador_inicio: int,
) -> dict[str, Any]:

    ocupados = set(
        indices_operacion
    )

    ocupados.update(
        range(
            entidad_fragmento[
                "inicio"
            ],
            entidad_fragmento[
                "fin"
            ],
        )
    )

    ocupados.update(
        range(
            campo_fragmento[
                "inicio"
            ],
            campo_fragmento[
                "fin"
            ],
        )
    )

    sobrantes = []

    for indice in range(
        0,
        operador_inicio,
    ):

        if indice in ocupados:
            continue

        palabra = tokens[
            indice
        ][
            "normalizado"
        ]

        if palabra in CONECTORES:
            continue

        sobrantes.append(
            tokens[
                indice
            ][
                "original"
            ]
        )

    if sobrantes:

        return {
            "ok":
                False,

            "estado":
                "prefijo_no_resuelto",

            "terminos":
                sobrantes,
        }

    return {
        "ok":
            True,

        "estado":
            "prefijo_consumido",
    }


# ============================================================
# VALOR LIBRE
# ============================================================


def _extraer_valor(
    tokens: list[dict[str, Any]],
    *,
    operador: dict[str, Any],
) -> dict[str, Any]:

    tipo_operador = operador[
        "operador"
    ]

    if tipo_operador == "isnull_true":

        return {
            "ok":
                True,

            "estado":
                "valor_resuelto",

            "operador":
                "isnull",

            "valor":
                False,
        }

    if type_operator := (
        tipo_operador
        == "isnull_false"
    ):

        return {
            "ok":
                True,

            "estado":
                "valor_resuelto",

            "operador":
                "isnull",

            "valor":
                False,
        }

    tokens_valor = tokens[
        operador[
            "fin"
        ]:
    ]

    if not tokens_valor:

        return {
            "ok":
                False,

            "estado":
                "valor_libre_vacio",
        }

    valor = " ".join(
        token[
            "original"
        ]
        for token
        in tokens_valor
    ).strip()

    if not valor:

        return {
            "ok":
                False,

            "estado":
                "valor_libre_vacio",
        }

    return {
        "ok":
            True,

        "estado":
            "valor_resuelto",

        "operador":
            tipo_operador,

        "valor":
            valor,
    }


# ============================================================
# BRIDGE003
# ============================================================


def componer_campo_operador_valor(
    expresion: str,
    *,
    limite: int | None = LIMITE_MUESTRA_PREDETERMINADO,
) -> dict[str, Any]:
    """
    IA-BRIDGE003.

    Orden de trabajo:

        1. Intenta BRIDGE002.
        2. Si BRIDGE002 ya resuelve la consulta, se conserva.
        3. Si no, busca patrón:

              operación
              + entidad
              + campo
              + operador
              + valor libre

        4. SEM resuelve entidad y campo.
        5. BRIDGE traduce operador.
        6. HOST valida el plan completo.

    Nunca ejecuta ORM.
    Nunca invoca LLM.
    """

    base = {
        "ok":
            False,

        "version":
            VERSION,

        "expresion":
            expresion,

        "llm_invocado":
            False,

        "ejecutado":
            False,

        "modo":
            None,

        "propuesta_host":
            None,

        "validacion_host":
            None,
    }

    # ========================================================
    # COMPATIBILIDAD BRIDGE002
    # ========================================================

    resultado_bridge002 = componer_sem_a_host(
        expresion,
        limite=limite,
    )

    if resultado_bridge002.get(
        "ok"
    ):

        return {
            **base,

            "ok":
                True,

            "estado":
                "plan_host_validado",

            "modo":
                "bridge002",

            "bridge002":
                resultado_bridge002,

            "propuesta_host":
                resultado_bridge002.get(
                    "propuesta_host"
                ),

            "validacion_host":
                resultado_bridge002.get(
                    "validacion_host"
                ),

            "plan_host":
                resultado_bridge002.get(
                    "plan_host"
                ),

            "razon":
                (
                    "La consulta ya pudo resolverse "
                    "mediante composición semántica BRIDGE002."
                ),
        }

    # ========================================================
    # TOKENIZAR
    # ========================================================

    tokens = _tokenizar(
        expresion
    )

    base[
        "tokens"
    ] = tokens

    if not tokens:

        return {
            **base,

            "estado":
                "expresion_vacia",
        }

    # ========================================================
    # OPERACIÓN
    # ========================================================

    operacion = _resolver_operacion(
        tokens
    )

    base[
        "operacion"
    ] = operacion

    if not operacion.get(
        "ok"
    ):

        return {
            **base,

            "estado":
                operacion.get(
                    "estado"
                ),
        }

    # ========================================================
    # OPERADOR DE FILTRO
    # ========================================================

    operador = _buscar_operador(
        tokens
    )

    base[
        "operador_filtro"
    ] = operador

    if not operador.get(
        "ok"
    ):

        return {
            **base,

            "estado":
                operador.get(
                    "estado"
                ),
        }

    # ========================================================
    # ENTIDAD
    # ========================================================

    entidad = _resolver_entidad(
        tokens,
        indices_operacion=(
            operacion[
                "indices"
            ]
        ),
        operador_inicio=(
            operador[
                "inicio"
            ]
        ),
    )

    base[
        "entidad"
    ] = entidad

    if not entidad.get(
        "ok"
    ):

        return {
            **base,

            "estado":
                entidad.get(
                    "estado"
                ),
        }

    # ========================================================
    # CAMPO, AHORA CON CONTEXTO DE MODELO
    # ========================================================

    campo = _resolver_campo(
        tokens,
        modelo=entidad[
            "modelo"
        ],
        indices_operacion=(
            operacion[
                "indices"
            ]
        ),
        entidad_fragmento=(
            entidad[
                "fragmento"
            ]
        ),
        operador_inicio=(
            operador[
                "inicio"
            ]
        ),
    )

    base[
        "campo"
    ] = campo

    if not campo.get(
        "ok"
    ):

        return {
            **base,

            "estado":
                campo.get(
                    "estado"
                ),
        }

    # ========================================================
    # TODO EL PREFIJO DEBE ESTAR EXPLICADO
    # ========================================================

    prefijo = _validar_prefijo_consumido(
        tokens,
        indices_operacion=(
            operacion[
                "indices"
            ]
        ),
        entidad_fragmento=(
            entidad[
                "fragmento"
            ]
        ),
        campo_fragmento=(
            campo[
                "fragmento"
            ]
        ),
        operador_inicio=(
            operador[
                "inicio"
            ]
        ),
    )

    base[
        "prefijo"
    ] = prefijo

    if not prefijo.get(
        "ok"
    ):

        return {
            **base,

            "estado":
                prefijo.get(
                    "estado"
                ),
        }

    # ========================================================
    # VALOR
    # ========================================================

    valor = _extraer_valor(
        tokens,
        operador=operador,
    )

    base[
        "valor_libre"
    ] = valor

    if not valor.get(
        "ok"
    ):

        return {
            **base,

            "estado":
                valor.get(
                    "estado"
                ),
        }

    # ========================================================
    # PROPUESTA HOST
    # ========================================================

    filtro = {
        "campo":
            campo[
                "campo"
            ],

        "operador":
            valor[
                "operador"
            ],

        "valor":
            valor[
                "valor"
            ],
    }

    propuesta_host = {
        "modelo":
            entidad[
                "modelo"
            ],

        "operacion":
            operacion[
                "operacion"
            ],

        "filtros": [
            filtro
        ],

        "orden":
            [],

        "limite":
            limite,

        "condiciones_no_resueltas":
            [],
    }

    base[
        "propuesta_host"
    ] = propuesta_host

    # ========================================================
    # VALIDACIÓN HOST
    # ========================================================

    validacion_host = validar_plan_datos(
        propuesta_host
    )

    base[
        "validacion_host"
    ] = validacion_host

    if not validacion_host.get(
        "plan_validado",
        False,
    ):

        return {
            **base,

            "estado":
                "rechazado_por_host",

            "modo":
                "campo_operador_valor",

            "razon":
                (
                    "BRIDGE003 construyó el filtro, "
                    "pero HOST rechazó el plan."
                ),
        }

    return {
        **base,

        "ok":
            True,

        "estado":
            "plan_host_validado",

        "modo":
            "campo_operador_valor",

        "plan_host":
            validacion_host.get(
                "plan"
            ),

        "razon":
            (
                "Campo, operador y valor libre fueron "
                "resueltos y HOST validó el plan sin "
                "ejecutar ORM."
            ),
    }