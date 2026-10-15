from __future__ import annotations

import re
import unicodedata
from typing import Any

from django.apps import apps
from django.db import (
    DatabaseError,
    models,
)
from django.db.models import Q

from .catalogo_datos import (
    construir_catalogo_datos,
)
from .perfilador_datos import (
    perfilar_modelo,
)


# ============================================================
# NORMALIZACIÓN
# ============================================================


def _normalizar(
    valor: Any,
) -> str:

    texto = str(
        valor
        or ""
    ).strip().lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        caracter
        for caracter
        in texto
        if not unicodedata.combining(
            caracter
        )
    )

    texto = re.sub(
        r"[^a-z0-9]+",
        " ",
        texto,
    )

    return re.sub(
        r"\s+",
        " ",
        texto,
    ).strip()


def _tokens(
    valor: Any,
) -> set[str]:

    return {
        token
        for token
        in _normalizar(
            valor
        ).split()
        if len(
            token
        ) >= 3
    }


# ============================================================
# EVIDENCIA LÉXICA
# ============================================================


def _puntaje_lexico(
    pregunta: str,
    modelo: dict[str, Any],
) -> int:

    pregunta_n = _normalizar(
        pregunta
    )

    tokens_pregunta = _tokens(
        pregunta
    )

    label = _normalizar(
        modelo.get(
            "label"
        )
    )

    app = _normalizar(
        modelo.get(
            "app_label"
        )
    )

    nombre = _normalizar(
        modelo.get(
            "modelo"
        )
    )

    verbose = _normalizar(
        modelo.get(
            "verbose_name"
        )
    )

    verbose_plural = _normalizar(
        modelo.get(
            "verbose_name_plural"
        )
    )

    puntaje = 0

    if label and label in pregunta_n:
        puntaje += 100

    if nombre and nombre in pregunta_n:
        puntaje += 80

    if verbose and verbose in pregunta_n:
        puntaje += 60

    if (
        verbose_plural
        and verbose_plural in pregunta_n
    ):
        puntaje += 60

    if (
        app
        and app in tokens_pregunta
    ):
        puntaje += 25

    terminos_modelo = set()

    for valor in (
        app,
        nombre,
        verbose,
        verbose_plural,
    ):
        terminos_modelo.update(
            _tokens(
                valor
            )
        )

    puntaje += (
        len(
            tokens_pregunta
            & terminos_modelo
        )
        * 5
    )

    return puntaje


# ============================================================
# EVIDENCIA EN VALORES REALES
# ============================================================


def _evidencia_valores(
    pregunta: str,
    modelo: dict[str, Any],
) -> dict[str, Any]:

    label = modelo.get(
        "label"
    )

    if not label:

        return {
            "puntaje":
                0,

            "soporte":
                0,

            "coincidencias":
                [],
        }

    perfil = perfilar_modelo(
        label,
        max_valores=15,
    )

    if not perfil.get(
        "ok"
    ):

        return {
            "puntaje":
                0,

            "soporte":
                0,

            "coincidencias":
                [],
        }

    pregunta_n = _normalizar(
        pregunta
    )

    coincidencias = []
    soporte = 0

    for perfil_campo in perfil.get(
        "perfiles",
        [],
    ):

        campo = perfil_campo.get(
            "campo"
        )

        for item in perfil_campo.get(
            "valores",
            [],
        ):

            valor = item.get(
                "valor"
            )

            valor_n = _normalizar(
                valor
            )

            if not valor_n:
                continue

            # Evitamos coincidencias demasiado pequeñas,
            # por ejemplo "si", "no", "0", etc.
            if len(
                valor_n
            ) < 4:
                continue

            if valor_n in pregunta_n:

                frecuencia = item.get(
                    "frecuencia"
                )

                try:
                    frecuencia = int(
                        frecuencia
                        or 0
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    frecuencia = 0

                soporte += max(
                    frecuencia,
                    0,
                )

                coincidencias.append(
                    {
                        "campo":
                            campo,

                        "valor":
                            valor,

                        "frecuencia":
                            frecuencia,
                    }
                )

    return {
        # El puntaje semántico continúa midiendo cuántas
        # coincidencias reales distintas existen.
        "puntaje":
            len(
                coincidencias
            )
            * 75,

        # El soporte NO sustituye el puntaje.
        # Solo sirve para desempatar evidencia equivalente.
        "soporte":
            soporte,

        "coincidencias":
            coincidencias,
    }



# ============================================================
# EVIDENCIA TEXTUAL REAL
# ============================================================


_STOPWORDS_BUSQUEDA = {
    "lista",
    "listar",
    "muestra",
    "muestrame",
    "mostrar",
    "todos",
    "todas",
    "todo",
    "toda",
    "los",
    "las",
    "del",
    "de",
    "para",
    "por",
    "con",
    "que",
    "quiero",
    "dame",
    "ver",
}


def _terminos_busqueda_textual(
    pregunta: str,
) -> list[str]:
    """
    Obtiene términos significativos de una pregunta para buscar
    evidencia textual real en campos CharField.

    Prioriza frases de varias palabras antes que tokens aislados.
    """

    texto = _normalizar(
        pregunta
    )

    tokens = [
        token
        for token in texto.split()
        if (
            len(token) >= 4
            and token not in _STOPWORDS_BUSQUEDA
        )
    ]

    if not tokens:
        return []

    resultado = []

    # Frases de tres palabras.
    for indice in range(
        max(
            0,
            len(tokens) - 2,
        )
    ):
        resultado.append(
            " ".join(
                tokens[
                    indice:
                    indice + 3
                ]
            )
        )

    # Frases de dos palabras.
    for indice in range(
        max(
            0,
            len(tokens) - 1,
        )
    ):
        resultado.append(
            " ".join(
                tokens[
                    indice:
                    indice + 2
                ]
            )
        )

    # Tokens individuales.
    resultado.extend(
        tokens
    )

    # Conservamos orden y eliminamos duplicados.
    unicos = []

    for termino in resultado:

        if termino not in unicos:
            unicos.append(
                termino
            )

    # Evitamos generar un número excesivo de consultas.
    return unicos[
        :8
    ]


def _buscar_evidencia_textual(
    pregunta: str,
    catalogo: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Busca evidencia textual real exclusivamente en CharField.

    Esta función:

        - solo lee la base de datos;
        - no usa TextField;
        - no usa JSONField;
        - no usa FileField;
        - no ejecuta SQL arbitrario;
        - no decide por sí misma qué modelo debe utilizarse.

    Su resultado sirve como evidencia para diagnóstico y
    desambiguación posterior.
    """

    terminos = _terminos_busqueda_textual(
        pregunta
    )

    if not terminos:
        return []

    candidatos = []

    for modelo_catalogo in catalogo:

        app_label = modelo_catalogo.get(
            "app_label"
        )

        nombre_modelo = modelo_catalogo.get(
            "modelo"
        )

        if (
            not app_label
            or not nombre_modelo
        ):
            continue

        try:

            modelo_django = apps.get_model(
                app_label,
                nombre_modelo,
            )

        except LookupError:
            continue

        if modelo_django is None:
            continue

        coincidencias_campos = []
        soporte_total = 0
        puntaje_total = 0

        for campo in modelo_django._meta.fields:

            if not getattr(
                campo,
                "concrete",
                False,
            ):
                continue

            if getattr(
                campo,
                "is_relation",
                False,
            ):
                continue

            if not isinstance(
                campo,
                models.CharField,
            ):
                continue

            # Evitamos campos de texto anormalmente grandes.
            max_length = getattr(
                campo,
                "max_length",
                None,
            )

            if (
                max_length
                and max_length > 1000
            ):
                continue

            filtro = Q()

            for termino in terminos:

                filtro |= Q(
                    **{
                        f"{campo.name}__icontains":
                            termino
                    }
                )

            try:

                valores = list(
                    modelo_django.objects
                    .filter(
                        filtro
                    )
                    .exclude(
                        **{
                            f"{campo.name}":
                                ""
                        }
                    )
                    .values_list(
                        campo.name,
                        flat=True,
                    )[
                        :25
                    ]
                )

            except (
                DatabaseError,
                TypeError,
                ValueError,
            ):
                continue

            if not valores:
                continue

            terminos_encontrados = []

            for termino in terminos:

                termino_n = _normalizar(
                    termino
                )

                if any(
                    termino_n
                    in _normalizar(
                        valor
                    )
                    for valor in valores
                ):
                    terminos_encontrados.append(
                        termino
                    )

            if not terminos_encontrados:
                continue

            soporte = len(
                valores
            )

            # Una frase de varias palabras es evidencia más fuerte
            # que una coincidencia de un solo token.
            puntaje = sum(
                100
                if " " in termino
                else 30
                for termino
                in terminos_encontrados
            )

            soporte_total += soporte
            puntaje_total += puntaje

            coincidencias_campos.append(
                {
                    "campo":
                        campo.name,

                    "tipo":
                        campo.__class__.__name__,

                    "terminos":
                        terminos_encontrados,

                    "soporte_muestra":
                        soporte,

                    "muestras":
                        [
                            str(
                                valor
                            )
                            for valor
                            in valores[
                                :5
                            ]
                        ],
                }
            )

        if not coincidencias_campos:
            continue

        candidatos.append(
            {
                "modelo":
                    modelo_catalogo.get(
                        "label"
                    ),

                "app_label":
                    app_label,

                "nombre":
                    nombre_modelo,

                "verbose_name":
                    modelo_catalogo.get(
                        "verbose_name"
                    ),

                "puntaje_lexico":
                    0,

                "puntaje_valores":
                    0,

                "soporte_valores":
                    0,

                "puntaje_textual":
                    puntaje_total,

                "soporte_textual":
                    soporte_total,

                "puntaje_total":
                    puntaje_total,

                "coincidencias_valores":
                    [],

                "coincidencias_textuales":
                    coincidencias_campos,
            }
        )

    candidatos.sort(
        key=lambda item: (
            -item.get(
                "puntaje_textual",
                0,
            ),
            -item.get(
                "soporte_textual",
                0,
            ),
            str(
                item.get(
                    "modelo",
                    "",
                )
            ),
        )
    )

    return candidatos[
        :10
    ]


# ============================================================
# RESOLUCIÓN
# ============================================================


def resolver_entidad_datos(
    pregunta: str,
) -> dict[str, Any]:
    """
    Intenta resolver un modelo real utilizando únicamente:

        - catálogo dinámico del host
        - nombres/verbose names reales
        - app labels reales
        - valores categóricos observados realmente

    Nunca inventa un modelo.

    Si no existe un ganador inequívoco, devuelve resuelto=False.
    """

    catalogo = construir_catalogo_datos(
        incluir_ia_local=False,
        incluir_django=False,
    )

    candidatos = []

    for modelo in catalogo:

        puntaje_lexico = _puntaje_lexico(
            pregunta,
            modelo,
        )

        # Sin ninguna relación léxica con la pregunta,
        # no consultamos su perfil de datos.
        if puntaje_lexico <= 0:
            continue

        evidencia = _evidencia_valores(
            pregunta,
            modelo,
        )

        puntaje_total = (
            puntaje_lexico
            + evidencia[
                "puntaje"
            ]
        )

        candidatos.append(
            {
                "modelo":
                    modelo.get(
                        "label"
                    ),

                "app_label":
                    modelo.get(
                        "app_label"
                    ),

                "nombre":
                    modelo.get(
                        "modelo"
                    ),

                "verbose_name":
                    modelo.get(
                        "verbose_name"
                    ),

                "puntaje_lexico":
                    puntaje_lexico,

                "puntaje_valores":
                    evidencia[
                        "puntaje"
                    ],

                "soporte_valores":
                    evidencia[
                        "soporte"
                    ],

                "puntaje_total":
                    puntaje_total,

                "coincidencias_valores":
                    evidencia[
                        "coincidencias"
                    ],
            }
        )

    candidatos.sort(
        key=lambda item: (
            -item[
                "puntaje_total"
            ],
            -item.get(
                "soporte_valores",
                0,
            ),
            str(
                item[
                    "modelo"
                ]
            ),
        )
    )

        # --------------------------------------------------------
    # FALLBACK: EVIDENCIA TEXTUAL REAL
    # --------------------------------------------------------

    if not candidatos:

        candidatos_textuales = (
            _buscar_evidencia_textual(
                pregunta,
                catalogo,
            )
        )

        if candidatos_textuales:

            primero_textual = (
                candidatos_textuales[
                    0
                ]
            )

            frases_fuertes = []

            for coincidencia in primero_textual.get(
                "coincidencias_textuales",
                [],
            ):

                for termino in coincidencia.get(
                    "terminos",
                    [],
                ):

                    if " " in str(
                        termino
                    ).strip():

                        frases_fuertes.append(
                            termino
                        )

            # Resolución textual automática únicamente cuando:
            #
            # - existe exactamente un modelo candidato;
            # - existe al menos una coincidencia de frase completa.
            #
            # Una palabra aislada nunca basta para resolver.
            if (
                len(
                    candidatos_textuales
                ) == 1
                and frases_fuertes
            ):

                return {
                    "ok":
                        True,

                    "resuelto":
                        True,

                    "entidad":
                        primero_textual[
                            "modelo"
                        ],

                    "razon":
                        (
                            "La entidad fue resuelta mediante "
                            "evidencia textual real inequívoca: "
                            "existe un único modelo candidato y "
                            "se encontró una frase significativa "
                            "de la pregunta en sus datos."
                        ),

                    "tipo_evidencia":
                        "texto_real_inequivoco",

                    "evidencia":
                        primero_textual,

                    "frases_fuertes":
                        frases_fuertes,

                    "candidatos":
                        candidatos_textuales,
                }

            return {
                "ok":
                    True,

                "resuelto":
                    False,

                "entidad":
                    None,

                "razon":
                    (
                        "Se encontraron coincidencias textuales "
                        "reales en datos del host, pero la "
                        "evidencia no es suficientemente "
                        "inequívoca para elegir una entidad."
                    ),

                "tipo_evidencia":
                    "texto_real_ambiguo",

                "candidatos":
                    candidatos_textuales,
            }

        return {
            "ok":
                True,

            "resuelto":
                False,

            "entidad":
                None,

            "razon":
                (
                    "No existen candidatos reales "
                    "relacionados con la pregunta."
                ),

            "tipo_evidencia":
                "ninguna",

            "candidatos":
                [],
        }

    primero = candidatos[
        0
    ]

    segundo = (
        candidatos[
            1
        ]
        if len(
            candidatos
        ) > 1
        else None
    )

    # Para resolver una referencia genérica exigimos
    # evidencia particularmente fuerte:
    #
    # - coincidencia explícita con un valor real, o
    # - nombre/modelo suficientemente específico.
    evidencia_fuerte = bool(
        primero[
            "coincidencias_valores"
        ]
        or primero[
            "puntaje_lexico"
        ] >= 60
    )

    if not evidencia_fuerte:

        return {
            "ok":
                True,

            "resuelto":
                False,

            "entidad":
                None,

            "razon":
                (
                    "Los candidatos existentes no tienen "
                    "evidencia suficiente para elegir uno."
                ),

            "candidatos":
                candidatos[
                    :10
                ],
        }

    # Si dos modelos obtienen el mismo puntaje semántico,
    # estudiamos la fuerza de la evidencia observada.
    #
    # No elegimos simplemente el que tenga más registros.
    # Exigimos dominancia clara para evitar decisiones
    # arbitrarias ante diferencias pequeñas.

    if (
        segundo
        and segundo[
            "puntaje_total"
        ]
        == primero[
            "puntaje_total"
        ]
    ):

        soporte_primero = int(
            primero.get(
                "soporte_valores",
                0,
            )
            or 0
        )

        soporte_segundo = int(
            segundo.get(
                "soporte_valores",
                0,
            )
            or 0
        )

        dominancia_clara = (
            soporte_primero >= 3
            and soporte_primero
            >= max(
                1,
                soporte_segundo
            ) * 2
        )

        if not dominancia_clara:

            return {
                "ok":
                    True,

                "resuelto":
                    False,

                "entidad":
                    None,

                "razon":
                    (
                        "Existen varios modelos con evidencia "
                        "equivalente y ninguno tiene soporte "
                        "observado suficientemente dominante."
                    ),

                "candidatos":
                    candidatos[
                        :10
                    ],
            }

    return {
        "ok":
            True,

        "resuelto":
            True,

        "entidad":
            primero[
                "modelo"
            ],

        "razon":
            (
                "La entidad fue resuelta mediante evidencia "
                "dinámica del catálogo y de los valores reales."
            ),

        "evidencia":
            primero,

        "candidatos":
            candidatos[
                :10
            ],
    }