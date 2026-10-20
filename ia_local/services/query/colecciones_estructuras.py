from __future__ import annotations

import re
import unicodedata
from typing import Any

from ia_local.services.semantica.resolvedor_ambiguedades import (
    resolver_expresion_semantica,
)

from ia_local.services.host.resolvedor_objetivo_datos import (
    resolver_objetivo_datos,
)

from ia_local.services.host.descriptor_colecciones_datos import (
    resolver_representacion_coleccion,
)

from ia_local.services.host.descriptor_colecciones_estructuradas import (
    obtener_coleccion_estructurada,
)

from ia_local.services.host.validador_coleccion_serializada import (
    validar_coleccion_serializada,
)


VERSION = "IA-QUERY008-v1"


# ============================================================
# UTILIDADES
# ============================================================


def _texto(
    valor: Any,
) -> str:

    if valor is None:
        return ""

    return str(valor).strip()


def _normalizar(
    texto: str,
) -> str:

    texto = _texto(
        texto
    ).lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(
            caracter
        )
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()


def _singularizar_prefijo(
    expresion: str,
) -> str:

    """
    Singularización mínima y conservadora.

    items       -> item
    documentos  -> documento
    adjuntos    -> adjunto

    No intenta resolver morfología general.
    """

    texto = _normalizar(
        expresion
    )

    texto = texto.replace(
        " ",
        "_",
    )

    if (
        texto.endswith("es")
        and len(texto) > 4
    ):
        candidato = texto[:-2]

        # "items" no termina realmente en "es",
        # queda cubierto por la siguiente regla.
        if candidato:
            return candidato

    if (
        texto.endswith("s")
        and len(texto) > 3
    ):
        return texto[:-1]

    return texto


def _error(
    *,
    pregunta: str,
    estado: str,
    razon: str,
    **extra: Any,
) -> dict[str, Any]:

    salida = {
        "ok": False,
        "version": VERSION,
        "ejecutado": False,
        "estado": estado,
        "modo": "colecciones_estructuras",
        "pregunta": pregunta,
        "razon": razon,
        "llm_invocado": False,
    }

    salida.update(
        extra
    )

    return salida


# ============================================================
# PARSER NATURAL
# ============================================================


def _extraer_componentes(
    pregunta: str,
) -> dict[str, Any] | None:

    """
    Formas soportadas:

    coleccion correos enviados de documentos

    colección correos enviados de documentos

    describir coleccion correos enviados de documentos

    describir colección items de transmitales
    """

    texto = _texto(
        pregunta
    )

    patron = re.compile(
        r"""
        ^\s*
        (?:
            describir
            \s+
        )?
        colecci[oó]n
        \s+
        (?P<objetivo>.+?)
        \s+
        de
        \s+
        (?P<entidad>.+?)
        \s*$
        """,
        flags=(
            re.IGNORECASE
            | re.VERBOSE
        ),
    )

    coincidencia = patron.match(
        texto
    )

    if not coincidencia:
        return None

    objetivo = _texto(
        coincidencia.group(
            "objetivo"
        )
    )

    entidad = _texto(
        coincidencia.group(
            "entidad"
        )
    )

    if (
        not objetivo
        or not entidad
    ):
        return None

    return {
        "objetivo":
            objetivo,

        "entidad":
            entidad,
    }


# ============================================================
# ENTIDAD
# ============================================================


def _resolver_entidad(
    expresion: str,
) -> dict[str, Any]:

    resolucion = (
        resolver_expresion_semantica(
            expresion,
            incluir_reglas=False,
        )
    )

    if (
        not isinstance(
            resolucion,
            dict,
        )
        or resolucion.get(
            "ok"
        )
        is not True
        or resolucion.get(
            "estado"
        )
        != "resuelto"
    ):
        return {
            "ok":
                False,

            "resolucion":
                resolucion,
        }

    resultado = (
        resolucion.get(
            "resultado"
        )
    )

    if (
        not isinstance(
            resultado,
            dict,
        )
        or resultado.get(
            "tipo"
        )
        != "entidad"
    ):
        return {
            "ok":
                False,

            "resolucion":
                resolucion,
        }

    modelo = _texto(
        resultado.get(
            "modelo"
        )
    )

    if not modelo:
        return {
            "ok":
                False,

            "resolucion":
                resolucion,
        }

    return {
        "ok":
            True,

        "modelo":
            modelo,

        "resolucion":
            resolucion,
    }


# ============================================================
# COLECCIÓN ESTRUCTURADA
# ============================================================


def _intentar_estructura_repetida(
    *,
    modelo: str,
    expresion: str,
) -> dict[str, Any]:

    prefijos = []

    expresion_normalizada = (
        _normalizar(
            expresion
        )
        .replace(
            " ",
            "_",
        )
    )

    prefijo_singular = (
        _singularizar_prefijo(
            expresion
        )
    )

    for candidato in (
        expresion_normalizada,
        prefijo_singular,
    ):
        if (
            candidato
            and candidato
            not in prefijos
        ):
            prefijos.append(
                candidato
            )

    intentos = []

    for prefijo in prefijos:

        resultado = (
            obtener_coleccion_estructurada(
                modelo=modelo,
                prefijo=prefijo,
            )
        )

        intentos.append(
            {
                "prefijo":
                    prefijo,

                "resultado":
                    resultado,
            }
        )

        if (
            isinstance(
                resultado,
                dict,
            )
            and resultado.get(
                "ok"
            )
            is True
            and resultado.get(
                "resuelto"
            )
            is True
        ):

            return {
                "ok":
                    True,

                "resuelto":
                    True,

                "prefijo":
                    prefijo,

                "resultado":
                    resultado,

                "intentos":
                    intentos,
            }

    return {
        "ok":
            True,

        "resuelto":
            False,

        "prefijo":
            None,

        "resultado":
            None,

        "intentos":
            intentos,
    }


# ============================================================
# API PÚBLICA
# ============================================================


def describir_coleccion_natural(
    pregunta: str,
) -> dict[str, Any]:

    pregunta = _texto(
        pregunta
    )

    if not pregunta:

        return _error(
            pregunta=pregunta,
            estado="pregunta_vacia",
            razon="La consulta está vacía.",
        )

    componentes = (
        _extraer_componentes(
            pregunta
        )
    )

    if componentes is None:

        return _error(
            pregunta=pregunta,
            estado="estructura_coleccion_no_detectada",
            razon=(
                "No se encontró una estructura del tipo "
                "'colección objetivo de entidad'."
            ),
        )

    # --------------------------------------------------------
    # ENTIDAD
    # --------------------------------------------------------

    entidad = (
        _resolver_entidad(
            componentes[
                "entidad"
            ]
        )
    )

    if entidad.get(
        "ok"
    ) is not True:

        return _error(
            pregunta=pregunta,
            estado="entidad_no_resuelta",
            razon=(
                "La entidad no pudo resolverse "
                "de forma inequívoca."
            ),
            entidad_solicitada=(
                componentes[
                    "entidad"
                ]
            ),
            resolucion_entidad=(
                entidad.get(
                    "resolucion"
                )
            ),
        )

    modelo = entidad[
        "modelo"
    ]

    # --------------------------------------------------------
    # HOST023 - OBJETIVO
    # --------------------------------------------------------

    objetivo_host = (
        resolver_objetivo_datos(
            componentes[
                "objetivo"
            ],
            modelo=modelo,
        )
    )

    # --------------------------------------------------------
    # OBJETIVO REAL RESUELTO
    # --------------------------------------------------------

    if (
        isinstance(
            objetivo_host,
            dict,
        )
        and objetivo_host.get(
            "ok"
        )
        is True
        and objetivo_host.get(
            "resuelto"
        )
        is True
    ):

        representacion = (
            resolver_representacion_coleccion(
                modelo=modelo,
                objetivo_host=objetivo_host,
            )
        )

        if (
            not isinstance(
                representacion,
                dict,
            )
            or representacion.get(
                "ok"
            )
            is not True
            or representacion.get(
                "resuelto"
            )
            is not True
        ):

            return _error(
                pregunta=pregunta,
                estado="representacion_no_resuelta",
                razon=(
                    "HOST no pudo determinar la "
                    "representación real del objetivo."
                ),
                modelo=modelo,
                objetivo_host=objetivo_host,
                representacion_host=(
                    representacion
                ),
            )

        tipo = _texto(
            representacion.get(
                "tipo_representacion"
            )
        )

        # ----------------------------------------------------
        # RELACIÓN MULTIVALUADA
        # ----------------------------------------------------

        if (
            tipo
            == "relacion_multivaluada"
            and representacion.get(
                "contable_como_coleccion"
            )
            is True
        ):

            return {
                "ok":
                    True,

                "version":
                    VERSION,

                "ejecutado":
                    False,

                "estado":
                    "coleccion_relacional_validada",

                "modo":
                    "colecciones_estructuras",

                "pregunta":
                    pregunta,

                "entidad_solicitada":
                    componentes[
                        "entidad"
                    ],

                "objetivo_solicitado":
                    componentes[
                        "objetivo"
                    ],

                "modelo":
                    modelo,

                "tipo_coleccion":
                    "relacional",

                "tipo_representacion":
                    tipo,

                "nombre":
                    representacion.get(
                        "nombre"
                    ),

                "tipo_django":
                    representacion.get(
                        "tipo_django"
                    ),

                "tipo_relacion":
                    representacion.get(
                        "tipo_relacion"
                    ),

                "modelo_relacionado":
                    representacion.get(
                        "modelo_relacionado"
                    ),

                "multiple":
                    True,

                "contable_como_coleccion":
                    True,

                "objetivo_host":
                    objetivo_host,

                "representacion_host":
                    representacion,

                "resolucion_entidad":
                    entidad[
                        "resolucion"
                    ],

                "llm_invocado":
                    False,

                "razon":
                    (
                        "QUERY008 confirmó mediante HOST "
                        "una relación multivaluada real."
                    ),
            }

        # ----------------------------------------------------
        # COLECCIÓN SERIALIZADA
        # ----------------------------------------------------

        if (
            tipo
            == "coleccion_serializada"
        ):

            validacion = (
                validar_coleccion_serializada(
                    modelo=modelo,
                    representacion_host=(
                        representacion
                    ),
                )
            )

            if (
                isinstance(
                    validacion,
                    dict,
                )
                and validacion.get(
                    "ok"
                )
                is True
                and validacion.get(
                    "resuelto"
                )
                is True
                and validacion.get(
                    "validado"
                )
                is True
            ):

                return {
                    "ok":
                        True,

                    "version":
                        VERSION,

                    "ejecutado":
                        False,

                    "estado":
                        "coleccion_serializada_validada",

                    "modo":
                        "colecciones_estructuras",

                    "pregunta":
                        pregunta,

                    "entidad_solicitada":
                        componentes[
                            "entidad"
                        ],

                    "objetivo_solicitado":
                        componentes[
                            "objetivo"
                        ],

                    "modelo":
                        modelo,

                    "tipo_coleccion":
                        "serializada",

                    "tipo_representacion":
                        tipo,

                    "nombre":
                        representacion.get(
                            "nombre"
                        ),

                    "tipo_django":
                        representacion.get(
                            "tipo_django"
                        ),

                    "multiple":
                        True,

                    "contable_como_coleccion":
                        True,

                    "representacion_host":
                        representacion,

                    "validacion_serializada":
                        validacion,

                    "objetivo_host":
                        objetivo_host,

                    "resolucion_entidad":
                        entidad[
                            "resolucion"
                        ],

                    "llm_invocado":
                        False,

                    "razon":
                        (
                            "QUERY008 confirmó una colección "
                            "serializada declarada y HOST validó "
                            "su uso contra código real."
                        ),
                }

            return _error(
                pregunta=pregunta,
                estado="coleccion_serializada_no_validada",
                razon=(
                    "Existe evidencia declarativa de colección "
                    "serializada, pero HOST no pudo validarla "
                    "contra código real."
                ),
                modelo=modelo,
                objetivo_host=objetivo_host,
                representacion_host=(
                    representacion
                ),
                validacion_serializada=(
                    validacion
                ),
            )

        # ----------------------------------------------------
        # OBJETIVO REAL PERO NO ES COLECCIÓN
        # ----------------------------------------------------

        return _error(
            pregunta=pregunta,
            estado="objetivo_no_es_coleccion",
            razon=(
                "HOST resolvió el objetivo, pero su "
                "representación real no es una colección."
            ),
            modelo=modelo,
            tipo_representacion=tipo,
            objetivo_host=objetivo_host,
            representacion_host=(
                representacion
            ),
        )

    # --------------------------------------------------------
    # FALLBACK:
    # COLECCIÓN ESTRUCTURADA POR CAMPOS REPETIDOS
    # --------------------------------------------------------

    estructura = (
        _intentar_estructura_repetida(
            modelo=modelo,
            expresion=componentes[
                "objetivo"
            ],
        )
    )

    if estructura.get(
        "resuelto"
    ) is True:

        resultado = estructura[
            "resultado"
        ]

        coleccion = resultado.get(
            "coleccion"
        )

        return {
            "ok":
                True,

            "version":
                VERSION,

            "ejecutado":
                False,

            "estado":
                "coleccion_estructurada_validada",

            "modo":
                "colecciones_estructuras",

            "pregunta":
                pregunta,

            "entidad_solicitada":
                componentes[
                    "entidad"
                ],

            "objetivo_solicitado":
                componentes[
                    "objetivo"
                ],

            "modelo":
                modelo,

            "tipo_coleccion":
                "estructurada",

            "tipo_representacion":
                (
                    coleccion.get(
                        "tipo_representacion"
                    )
                    if isinstance(
                        coleccion,
                        dict,
                    )
                    else None
                ),

            "prefijo":
                estructura[
                    "prefijo"
                ],

            "coleccion":
                coleccion,

            "objetivo_host":
                objetivo_host,

            "estructura_host":
                resultado,

            "resolucion_entidad":
                entidad[
                    "resolucion"
                ],

            "llm_invocado":
                False,

            "razon":
                (
                    "QUERY008 no encontró un campo o relación "
                    "individual, pero HOST confirmó una colección "
                    "estructurada por campos repetidos."
                ),
        }

    # --------------------------------------------------------
    # NADA DEMOSTRABLE
    # --------------------------------------------------------

    return _error(
        pregunta=pregunta,
        estado="coleccion_no_resuelta",
        razon=(
            "No existe evidencia suficiente para tratar "
            "el objetivo solicitado como colección."
        ),
        modelo=modelo,
        objetivo_host=objetivo_host,
        estructura_host=estructura,
        resolucion_entidad=(
            entidad[
                "resolucion"
            ]
        ),
    )