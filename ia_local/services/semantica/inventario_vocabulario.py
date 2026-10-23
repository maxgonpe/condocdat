from __future__ import annotations

from typing import Any

from django.apps import apps

from ia_local.services.host.catalogo_datos import (
    construir_catalogo_datos,
)

from .normalizacion import (
    deduplicar_terminos,
    normalizar_texto,
    separar_nombre_tecnico,
    texto_limpio,
)


VERSION = "IA-SEM001-v1"


# ============================================================
# UTILIDADES
# ============================================================


def _terminos_con_origen(
    pares,
) -> list[dict[str, str]]:
    """
    Construye vocabulario deduplicado conservando el origen
    estructural de cada expresión.
    """

    resultado = []
    posiciones = {}

    for valor, origen in pares:

        texto = texto_limpio(
            valor
        )

        normalizado = normalizar_texto(
            texto
        )

        if (
            not texto
            or not normalizado
        ):
            continue

        if normalizado in posiciones:

            posicion = posiciones[
                normalizado
            ]

            origenes = resultado[
                posicion
            ][
                "origenes"
            ]

            if origen not in origenes:
                origenes.append(
                    origen
                )

            continue

        posiciones[
            normalizado
        ] = len(
            resultado
        )

        resultado.append(
            {
                "texto":
                    texto,

                "normalizado":
                    normalizado,

                "origenes":
                    [
                        origen
                    ],
            }
        )

    return resultado


def _cardinalidad(
    campo,
) -> str:

    if bool(
        getattr(
            campo,
            "many_to_many",
            False,
        )
    ):
        return "muchos_a_muchos"

    if bool(
        getattr(
            campo,
            "one_to_many",
            False,
        )
    ):
        return "uno_a_muchos"

    if bool(
        getattr(
            campo,
            "many_to_one",
            False,
        )
    ):
        return "muchos_a_uno"

    if bool(
        getattr(
            campo,
            "one_to_one",
            False,
        )
    ):
        return "uno_a_uno"

    return "relacion"


def _choices_campo(
    campo,
) -> list[dict[str, str]]:
    """
    Extrae choices declarados por Django.

    No consulta valores de la base de datos.
    """

    resultado = []

    try:
        choices = list(
            campo.flatchoices
        )

    except Exception:
        choices = []

    vistos = set()

    for valor, etiqueta in choices:

        valor_texto = texto_limpio(
            valor
        )

        etiqueta_texto = texto_limpio(
            etiqueta
        )

        clave = (
            valor_texto,
            normalizar_texto(
                etiqueta_texto
            ),
        )

        if clave in vistos:
            continue

        vistos.add(
            clave
        )

        resultado.append(
            {
                "valor":
                    valor_texto,

                "etiqueta":
                    etiqueta_texto,

                "normalizada":
                    normalizar_texto(
                        etiqueta_texto
                    ),
            }
        )

    return resultado


# ============================================================
# ENTIDAD
# ============================================================


def _vocabulario_entidad(
    modelo,
) -> list[dict[str, Any]]:

    meta = modelo._meta

    return _terminos_con_origen(
        [
            (
                meta.object_name,
                "modelo",
            ),
            (
                separar_nombre_tecnico(
                    meta.object_name
                ),
                "modelo_legible",
            ),
            (
                meta.verbose_name,
                "verbose_name",
            ),
            (
                meta.verbose_name_plural,
                "verbose_name_plural",
            ),
        ]
    )


# ============================================================
# CAMPOS
# ============================================================


def _describir_campo_semantico(
    campo,
    *,
    descriptor_host: dict[str, Any],
) -> dict[str, Any]:

    verbose_name = texto_limpio(
        getattr(
            campo,
            "verbose_name",
            "",
        )
    )

    help_text = texto_limpio(
        getattr(
            campo,
            "help_text",
            "",
        )
    )

    vocabulario = _terminos_con_origen(
        [
            (
                campo.name,
                "nombre_campo",
            ),
            (
                separar_nombre_tecnico(
                    campo.name
                ),
                "nombre_campo_legible",
            ),
            (
                verbose_name,
                "verbose_name",
            ),
        ]
    )

    return {
        "nombre":
            campo.name,

        "tipo":
            campo.__class__.__name__,

        "consultable":
            bool(
                descriptor_host.get(
                    "consultable",
                    False,
                )
            ),

        "primary_key":
            bool(
                getattr(
                    campo,
                    "primary_key",
                    False,
                )
            ),

        "verbose_name":
            verbose_name,

        "help_text":
            help_text,

        "vocabulario":
            vocabulario,

        "choices":
            _choices_campo(
                campo
            ),

        "origen":
            "automatico_django",
    }


# ============================================================
# RELACIONES
# ============================================================


def _describir_relacion_semantica(
    campo,
) -> dict[str, Any]:

    related_model = getattr(
        campo,
        "related_model",
        None,
    )

    modelo_destino = None

    if related_model is not None:
        modelo_destino = (
            related_model._meta.label
        )

    verbose_name = texto_limpio(
        getattr(
            campo,
            "verbose_name",
            "",
        )
    )

    vocabulario = _terminos_con_origen(
        [
            (
                campo.name,
                "nombre_relacion",
            ),
            (
                separar_nombre_tecnico(
                    campo.name
                ),
                "nombre_relacion_legible",
            ),
            (
                verbose_name,
                "verbose_name",
            ),
        ]
    )

    return {
        "nombre":
            campo.name,

        "tipo":
            campo.__class__.__name__,

        "modelo_destino":
            modelo_destino,

        "cardinalidad":
            _cardinalidad(
                campo
            ),

        "vocabulario":
            vocabulario,

        "origen":
            "automatico_django",
    }


# ============================================================
# MODELO
# ============================================================


def construir_vocabulario_modelo(
    descriptor: dict[str, Any],
) -> dict[str, Any]:

    app_label = descriptor[
        "app_label"
    ]

    nombre_modelo = descriptor[
        "modelo"
    ]

    modelo = apps.get_model(
        app_label,
        nombre_modelo,
    )

    descriptores_campos = {
        item[
            "nombre"
        ]:
            item

        for item
        in descriptor.get(
            "campos",
            [],
        )
    }

    campos = []
    relaciones = []

    for campo in modelo._meta.get_fields():

        descriptor_host = (
            descriptores_campos.get(
                campo.name,
                {},
            )
        )

        if bool(
            getattr(
                campo,
                "is_relation",
                False,
            )
        ):

            relaciones.append(
                _describir_relacion_semantica(
                    campo
                )
            )

            continue

        campos.append(
            _describir_campo_semantico(
                campo,
                descriptor_host=descriptor_host,
            )
        )

    campos.sort(
        key=lambda item:
            item[
                "nombre"
            ]
    )

    relaciones.sort(
        key=lambda item:
            item[
                "nombre"
            ]
    )

    return {
        "label":
            descriptor[
                "label"
            ],

        "app_label":
            app_label,

        "modelo":
            nombre_modelo,

        "tabla":
            descriptor[
                "tabla"
            ],

        "verbose_name":
            descriptor.get(
                "verbose_name",
                "",
            ),

        "verbose_name_plural":
            descriptor.get(
                "verbose_name_plural",
                "",
            ),

        "vocabulario_entidad":
            _vocabulario_entidad(
                modelo
            ),

        "campos":
            campos,

        "relaciones":
            relaciones,

        "referencias_tecnicas": {
            "label":
                descriptor[
                    "label"
                ],

            "tabla":
                descriptor[
                    "tabla"
                ],
        },

        "origen":
            "automatico_django",

        "llm_invocado":
            False,
    }


# ============================================================
# INVENTARIO GLOBAL
# ============================================================


def construir_inventario_vocabulario(
    *,
    incluir_ia_local: bool = False,
    incluir_django: bool = False,
) -> dict[str, Any]:
    """
    Construye el inventario semántico automático del host.

    No ejecuta consultas de datos.
    No invoca LLM.
    No utiliza reglas locales.
    No contiene conocimiento específico del proyecto anfitrión.
    """

    catalogo = construir_catalogo_datos(
        incluir_ia_local=incluir_ia_local,
        incluir_django=incluir_django,
    )

    modelos = [
        construir_vocabulario_modelo(
            descriptor
        )
        for descriptor
        in catalogo
    ]

    modelos.sort(
        key=lambda item: (
            item[
                "app_label"
            ],
            item[
                "modelo"
            ],
        )
    )

    total_campos = sum(
        len(
            modelo[
                "campos"
            ]
        )
        for modelo
        in modelos
    )

    total_relaciones = sum(
        len(
            modelo[
                "relaciones"
            ]
        )
        for modelo
        in modelos
    )

    total_terminos_entidad = sum(
        len(
            modelo[
                "vocabulario_entidad"
            ]
        )
        for modelo
        in modelos
    )

    return {
        "ok":
            True,

        "version":
            VERSION,

        "fuente":
            "django_meta_catalogo_host",

        "politica": {
            "llm":
                "no_invocado",

            "reglas_locales":
                "no_aplicadas",

            "valores_bd":
                "no_consultados",

            "inferencias":
                "no_generadas",
        },

        "total_modelos":
            len(
                modelos
            ),

        "total_campos":
            total_campos,

        "total_relaciones":
            total_relaciones,

        "total_terminos_entidad":
            total_terminos_entidad,

        "modelos":
            modelos,

        "llm_invocado":
            False,
    }


# ============================================================
# BÚSQUEDA
# ============================================================


def buscar_vocabulario_modelo(
    referencia: str,
) -> list[dict[str, Any]]:
    """
    Busca un modelo dentro del inventario SEM001 utilizando únicamente
    evidencia automática.

    No resuelve ambigüedades: devuelve todos los candidatos.
    """

    objetivo = normalizar_texto(
        referencia
    )

    if not objetivo:
        return []

    inventario = (
        construir_inventario_vocabulario()
    )

    resultado = []

    for modelo in inventario[
        "modelos"
    ]:

        referencias = {
            normalizar_texto(
                modelo.get(
                    "label"
                )
            ),
            normalizar_texto(
                modelo.get(
                    "modelo"
                )
            ),
            normalizar_texto(
                modelo.get(
                    "tabla"
                )
            ),
        }

        referencias.update(
            item[
                "normalizado"
            ]
            for item
            in modelo.get(
                "vocabulario_entidad",
                [],
            )
        )

        if objetivo in referencias:
            resultado.append(
                modelo
            )

    return resultado

# ============================================================
# IA-LLM006-E2
# VOCABULARIO AUTOMÁTICO DE ENTIDAD DENTRO DE TEXTO
# ============================================================

def buscar_vocabulario_entidad_en_texto(
    texto: str,
) -> dict[str, Any]:
    """
    Busca términos automáticos de entidad SEM001 dentro de
    una pregunta natural.

    Política:

    - sólo usa vocabulario derivado de Django;
    - no consulta aliases locales;
    - no consulta valores de BD;
    - no invoca LLM;
    - prioriza la coincidencia más específica;
    - si la mejor expresión corresponde a varios modelos,
      devuelve ambigüedad;
    - nunca inventa singular/plural ni sinónimos.
    """

    texto_normalizado = normalizar_texto(
        texto
    )

    if not texto_normalizado:

        return {
            "ok": True,
            "resuelto": False,
            "ambiguo": False,
            "estado": "texto_vacio",
            "llm_invocado": False,
            "coincidencias": [],
        }

    inventario = construir_inventario_vocabulario()

    texto_delimitado = (
        f" {texto_normalizado} "
    )

    coincidencias = []

    for modelo in inventario.get(
        "modelos",
        [],
    ):

        label = modelo.get(
            "label"
        )

        if not label:
            continue

        for termino in modelo.get(
            "vocabulario_entidad",
            [],
        ):

            normalizado = normalizar_texto(
                termino.get(
                    "normalizado"
                )
                or termino.get(
                    "texto"
                )
            )

            if not normalizado:
                continue

            termino_delimitado = (
                f" {normalizado} "
            )

            if (
                termino_delimitado
                not in texto_delimitado
            ):
                continue

            coincidencias.append(
                {
                    "modelo":
                        label,

                    "texto":
                        termino.get(
                            "texto"
                        ),

                    "normalizado":
                        normalizado,

                    "origenes":
                        termino.get(
                            "origenes",
                            [],
                        ),

                    "longitud":
                        len(
                            normalizado
                        ),
                }
            )

    if not coincidencias:

        return {
            "ok": True,
            "resuelto": False,
            "ambiguo": False,
            "estado":
                "sin_vocabulario_entidad_en_texto",
            "llm_invocado": False,
            "coincidencias": [],
        }

    coincidencias.sort(
        key=lambda item: (
            -item[
                "longitud"
            ],
            str(
                item[
                    "modelo"
                ]
            ),
        )
    )

    longitud_maxima = (
        coincidencias[0][
            "longitud"
        ]
    )

    mejores = [
        item
        for item
        in coincidencias
        if item[
            "longitud"
        ] == longitud_maxima
    ]

    modelos = {
        item[
            "modelo"
        ]
        for item
        in mejores
    }

    if len(modelos) != 1:

        return {
            "ok": True,
            "resuelto": False,
            "ambiguo": True,
            "estado":
                "vocabulario_entidad_ambiguo_en_texto",
            "llm_invocado": False,
            "coincidencias":
                mejores,
        }

    elegido = mejores[0]

    return {
        "ok": True,
        "resuelto": True,
        "ambiguo": False,
        "estado":
            "vocabulario_entidad_en_texto_resuelto",
        "modelo":
            elegido[
                "modelo"
            ],
        "texto":
            elegido[
                "texto"
            ],
        "normalizado":
            elegido[
                "normalizado"
            ],
        "origenes":
            elegido[
                "origenes"
            ],
        "llm_invocado": False,
        "coincidencias":
            coincidencias,
    }
