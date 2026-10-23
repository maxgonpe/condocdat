from __future__ import annotations

from ia_local.config.cardinalidad import (
    LIMITE_MUESTRA_PREDETERMINADO,
)


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


VERSION = "IA-BRIDGE002-v1"

MAX_PALABRAS_COMPONENTE = 6


# ============================================================
# VOCABULARIO PORTABLE DE OPERACIÓN
# ============================================================


PALABRAS_LISTAR = {
    "lista",
    "listar",
    "listame",
    "muestra",
    "mostrar",
    "muestrame",
    "dame",
    "ver",
}


PALABRAS_CONTAR = {
    "cuantos",
    "cuantas",
    "cantidad",
    "total",
    "contar",
    "cuenta",
}


EXPRESIONES_CONTAR = {
    "numero de",
}


# ============================================================
# PALABRAS DE ENLACE
# ============================================================


PALABRAS_IGNORABLES = {
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
    "con",
    "en",
    "cuyo",
    "cuya",
    "cuyos",
    "cuyas",
    "todos",
    "todas",
    "todo",
    "toda",
    "por",
}


# ============================================================
# OPERACIÓN
# ============================================================


def _resolver_operacion(
    texto_normalizado: str,
) -> dict[str, Any]:

    palabras = texto_normalizado.split()

    encontrados = []

    posiciones = set()

    for indice, palabra in enumerate(
        palabras
    ):

        if palabra in PALABRAS_CONTAR:

            encontrados.append(
                "contar"
            )

            posiciones.add(
                indice
            )

        elif palabra in PALABRAS_LISTAR:

            encontrados.append(
                "listar"
            )

            posiciones.add(
                indice
            )

    # Expresiones compuestas como "numero de".

    for expresion in EXPRESIONES_CONTAR:

        partes = expresion.split()

        largo = len(
            partes
        )

        for inicio in range(
            0,
            len(
                palabras
            )
            - largo
            + 1,
        ):

            if (
                palabras[
                    inicio:
                    inicio + largo
                ]
                == partes
            ):

                encontrados.append(
                    "contar"
                )

                posiciones.update(
                    range(
                        inicio,
                        inicio + largo,
                    )
                )

    operaciones = set(
        encontrados
    )

    if not operaciones:

        return {
            "resuelto":
                False,

            "estado":
                "operacion_no_resuelta",

            "operacion":
                None,

            "posiciones":
                posiciones,
        }

    if len(
        operaciones
    ) > 1:

        return {
            "resuelto":
                False,

            "estado":
                "operacion_ambigua",

            "operacion":
                None,

            "operaciones":
                sorted(
                    operaciones
                ),

            "posiciones":
                posiciones,
        }

    return {
        "resuelto":
            True,

        "estado":
            "resuelto",

        "operacion":
            next(
                iter(
                    operaciones
                )
            ),

        "posiciones":
            posiciones,
    }


# ============================================================
# FRAGMENTOS
# ============================================================


def _generar_fragmentos(
    palabras: list[str],
    *,
    posiciones_excluidas: set[int],
) -> list[dict[str, Any]]:
    """
    Genera fragmentos contiguos de mayor a menor longitud.

    Nunca atraviesa una palabra utilizada explícitamente
    como operador.
    """

    fragmentos = []

    max_largo = min(
        MAX_PALABRAS_COMPONENTE,
        len(
            palabras
        ),
    )

    for largo in range(
        max_largo,
        0,
        -1,
    ):

        for inicio in range(
            0,
            len(
                palabras
            )
            - largo
            + 1,
        ):

            fin = inicio + largo

            posiciones = set(
                range(
                    inicio,
                    fin,
                )
            )

            if (
                posiciones
                & posiciones_excluidas
            ):
                continue

            texto = " ".join(
                palabras[
                    inicio:
                    fin
                ]
            )

            fragmentos.append(
                {
                    "texto":
                        texto,

                    "inicio":
                        inicio,

                    "fin":
                        fin,

                    "posiciones":
                        posiciones,

                    "largo":
                        largo,
                }
            )

    return fragmentos


# ============================================================
# RESOLUCIÓN DE COMPONENTES
# ============================================================


def _resolver_fragmento(
    texto: str,
) -> dict[str, Any]:

    return resolver_con_politica(
        texto,
        incluir_reglas=False,
    )


def _extraer_componentes(
    texto_normalizado: str,
    *,
    posiciones_operacion: set[int],
) -> dict[str, Any]:

    palabras = texto_normalizado.split()

    fragmentos = _generar_fragmentos(
        palabras,
        posiciones_excluidas=(
            posiciones_operacion
        ),
    )

    posiciones_ocupadas = set(
        posiciones_operacion
    )

    componentes = []

    ambiguos = []

    for fragmento in fragmentos:

        posiciones = fragmento[
            "posiciones"
        ]

        # Preferimos coincidencias más largas.
        # Una coincidencia ya aceptada no puede solaparse.

        if (
            posiciones
            & posiciones_ocupadas
        ):
            continue

        resolucion = _resolver_fragmento(
            fragmento[
                "texto"
            ]
        )

        estado = resolucion.get(
            "estado"
        )

        if estado == "ambiguo":

            ambiguos.append(
                {
                    "fragmento":
                        fragmento[
                            "texto"
                        ],

                    "inicio":
                        fragmento[
                            "inicio"
                        ],

                    "fin":
                        fragmento[
                            "fin"
                        ],

                    "resolucion":
                        resolucion,
                }
            )

            continue

        if estado != "resuelto":
            continue

        resultado = resolucion.get(
            "resultado"
        )

        if not isinstance(
            resultado,
            dict,
        ):
            continue

        tipo = resultado.get(
            "tipo"
        )

        if tipo not in {
            "entidad",
            "campo",
            "valor",
        }:
            continue

        componentes.append(
            {
                "fragmento":
                    fragmento[
                        "texto"
                    ],

                "inicio":
                    fragmento[
                        "inicio"
                    ],

                "fin":
                    fragmento[
                        "fin"
                    ],

                "tipo":
                    tipo,

                "resultado":
                    resultado,

                "resolucion":
                    resolucion,
            }
        )

        posiciones_ocupadas.update(
            posiciones
        )

    posiciones_no_resueltas = []

    palabras_no_resueltas = []

    for indice, palabra in enumerate(
        palabras
    ):

        if indice in posiciones_ocupadas:
            continue

        if palabra in PALABRAS_IGNORABLES:
            continue

        posiciones_no_resueltas.append(
            indice
        )

        palabras_no_resueltas.append(
            palabra
        )

    return {
        "componentes":
            componentes,

        "ambiguos":
            ambiguos,

        "palabras_no_resueltas":
            palabras_no_resueltas,

        "posiciones_no_resueltas":
            posiciones_no_resueltas,

        "palabras":
            palabras,
    }


# ============================================================
# CONSISTENCIA DEL MODELO
# ============================================================


def _resolver_modelo_componentes(
    componentes: list[dict[str, Any]],
) -> dict[str, Any]:

    entidades = [
        componente
        for componente
        in componentes
        if componente.get(
            "tipo"
        )
        == "entidad"
    ]

    if not entidades:

        return {
            "ok":
                False,

            "estado":
                "entidad_no_resuelta",

            "modelo":
                None,
        }

    modelos_entidad = {
        componente[
            "resultado"
        ].get(
            "modelo"
        )
        for componente
        in entidades
        if componente[
            "resultado"
        ].get(
            "modelo"
        )
    }

    if len(
        modelos_entidad
    ) != 1:

        return {
            "ok":
                False,

            "estado":
                "entidades_incompatibles",

            "modelos":
                sorted(
                    modelos_entidad
                ),
        }

    modelo = next(
        iter(
            modelos_entidad
        )
    )

    # Los campos y valores que llevan modelo propio
    # deben coincidir con la entidad explícita.

    incompatibles = []

    for componente in componentes:

        resultado = componente.get(
            "resultado",
            {},
        )

        modelo_componente = (
            resultado.get(
                "modelo"
            )
        )

        if (
            modelo_componente
            and modelo_componente != modelo
        ):

            incompatibles.append(
                {
                    "fragmento":
                        componente.get(
                            "fragmento"
                        ),

                    "tipo":
                        componente.get(
                            "tipo"
                        ),

                    "modelo":
                        modelo_componente,
                }
            )

    if incompatibles:

        return {
            "ok":
                False,

            "estado":
                "componentes_incompatibles",

            "modelo":
                modelo,

            "incompatibles":
                incompatibles,
        }

    return {
        "ok":
            True,

        "estado":
            "modelo_resuelto",

        "modelo":
            modelo,
    }


# ============================================================
# FILTROS
# ============================================================


def _construir_filtros(
    componentes: list[dict[str, Any]],
    *,
    modelo: str,
) -> dict[str, Any]:

    valores = [
        componente
        for componente
        in componentes
        if componente.get(
            "tipo"
        )
        == "valor"
    ]

    filtros = []

    campos_usados = {}

    for componente in valores:

        resultado = componente.get(
            "resultado",
            {},
        )

        if (
            resultado.get(
                "modelo"
            )
            != modelo
        ):
            continue

        campo = resultado.get(
            "campo"
        )

        valor = resultado.get(
            "valor"
        )

        if not campo:

            return {
                "ok":
                    False,

                "estado":
                    "valor_sin_campo",
            }

        filtro = {
            "campo":
                campo,

            "operador":
                "exact",

            "valor":
                valor,
        }

        if campo in campos_usados:

            anterior = campos_usados[
                campo
            ]

            if (
                anterior.get(
                    "valor"
                )
                != valor
            ):

                return {
                    "ok":
                        False,

                    "estado":
                        "filtros_incompatibles",

                    "campo":
                        campo,

                    "valores": [
                        anterior.get(
                            "valor"
                        ),
                        valor,
                    ],
                }

            # Misma condición repetida.
            continue

        campos_usados[
            campo
        ] = filtro

        filtros.append(
            filtro
        )

    return {
        "ok":
            True,

        "estado":
            "filtros_construidos",

        "filtros":
            filtros,
    }


# ============================================================
# CAMPOS AISLADOS
# ============================================================


def _validar_campos_aislados(
    componentes: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    BRIDGE002 todavía no interpreta:

        campo + texto libre

    Ejemplo:
        "listar documentos tema arquitectura"

    porque 'arquitectura' todavía no es un valor semántico
    validado.

    Un campo aislado sin un componente VALOR correspondiente
    deja la consulta incompleta.
    """

    campos = [
        componente
        for componente
        in componentes
        if componente.get(
            "tipo"
        )
        == "campo"
    ]

    if not campos:

        return {
            "ok":
                True,

            "estado":
                "sin_campos_aislados",
        }

    return {
        "ok":
            False,

        "estado":
            "campo_sin_valor",

        "campos": [
            {
                "fragmento":
                    componente.get(
                        "fragmento"
                    ),

                "modelo":
                    componente[
                        "resultado"
                    ].get(
                        "modelo"
                    ),

                "campo":
                    componente[
                        "resultado"
                    ].get(
                        "campo"
                    ),
            }
            for componente
            in campos
        ],
    }


# ============================================================
# COMPOSITOR PRINCIPAL
# ============================================================


def componer_sem_a_host(
    expresion: str,
    *,
    limite: int | None = LIMITE_MUESTRA_PREDETERMINADO,
) -> dict[str, Any]:
    """
    IA-BRIDGE002.

    Compone componentes SEM parciales:

        operación
        + entidad
        + cero o más valores semánticos

    y genera una propuesta HOST.

    NO ejecuta ORM.
    NO invoca LLM.
    """

    expresion_normalizada = (
        normalizar_texto(
            expresion
        )
    )

    base = {
        "ok":
            False,

        "version":
            VERSION,

        "expresion":
            expresion,

        "expresion_normalizada":
            expresion_normalizada,

        "llm_invocado":
            False,

        "ejecutado":
            False,

        "propuesta_host":
            None,

        "validacion_host":
            None,
    }

    if not expresion_normalizada:

        return {
            **base,

            "estado":
                "expresion_vacia",
        }

    # --------------------------------------------------------
    # OPERACIÓN
    # --------------------------------------------------------

    operacion = _resolver_operacion(
        expresion_normalizada
    )

    base[
        "operacion"
    ] = {
        clave:
            valor
        for clave, valor
        in operacion.items()
        if clave != "posiciones"
    }

    if not operacion.get(
        "resuelto"
    ):

        return {
            **base,

            "estado":
                operacion.get(
                    "estado"
                ),
        }

    # --------------------------------------------------------
    # COMPONENTES SEM
    # --------------------------------------------------------

    analisis = _extraer_componentes(
        expresion_normalizada,
        posiciones_operacion=(
            operacion[
                "posiciones"
            ]
        ),
    )

    base[
        "componentes"
    ] = analisis[
        "componentes"
    ]

    base[
        "ambiguos"
    ] = analisis[
        "ambiguos"
    ]

    base[
        "palabras_no_resueltas"
    ] = analisis[
        "palabras_no_resueltas"
    ]

    # No permitimos que una ambigüedad quede oculta.

    if analisis[
        "ambiguos"
    ]:

        return {
            **base,

            "estado":
                "componente_ambiguo",

            "razon":
                (
                    "Uno o más fragmentos tienen varias "
                    "interpretaciones semánticas."
                ),
        }

    # Texto sustantivo desconocido = consulta incompleta.

    if analisis[
        "palabras_no_resueltas"
    ]:

        return {
            **base,

            "estado":
                "componentes_no_resueltos",

            "razon":
                (
                    "Quedaron términos relevantes de la "
                    "consulta sin interpretación segura."
                ),
        }

    # --------------------------------------------------------
    # MODELO
    # --------------------------------------------------------

    modelo = _resolver_modelo_componentes(
        analisis[
            "componentes"
        ]
    )

    base[
        "resolucion_modelo"
    ] = modelo

    if not modelo.get(
        "ok"
    ):

        return {
            **base,

            "estado":
                modelo.get(
                    "estado"
                ),
        }

    modelo_label = modelo[
        "modelo"
    ]

    # --------------------------------------------------------
    # CAMPOS AISLADOS
    # --------------------------------------------------------

    campos = _validar_campos_aislados(
        analisis[
            "componentes"
        ]
    )

    if not campos.get(
        "ok"
    ):

        return {
            **base,

            "estado":
                campos.get(
                    "estado"
                ),

            "detalle":
                campos,
        }

    # --------------------------------------------------------
    # FILTROS DESDE VALORES SEM004
    # --------------------------------------------------------

    resultado_filtros = _construir_filtros(
        analisis[
            "componentes"
        ],
        modelo=modelo_label,
    )

    base[
        "resolucion_filtros"
    ] = resultado_filtros

    if not resultado_filtros.get(
        "ok"
    ):

        return {
            **base,

            "estado":
                resultado_filtros.get(
                    "estado"
                ),
        }

    # --------------------------------------------------------
    # PROPUESTA HOST
    # --------------------------------------------------------

    propuesta_host = {
        "modelo":
            modelo_label,

        "operacion":
            operacion[
                "operacion"
            ],

        "filtros":
            resultado_filtros[
                "filtros"
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

    # --------------------------------------------------------
    # HOST SIGUE SIENDO AUTORIDAD FINAL
    # --------------------------------------------------------

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

            "razon":
                (
                    "BRIDGE compuso el plan, pero HOST "
                    "lo rechazó durante la validación."
                ),
        }

    return {
        **base,

        "ok":
            True,

        "estado":
            "plan_host_compuesto_validado",

        "plan_host":
            validacion_host.get(
                "plan"
            ),

        "razon":
            (
                "Los componentes SEM parciales fueron "
                "compuestos y HOST validó el plan sin "
                "ejecutar ORM."
            ),
    }