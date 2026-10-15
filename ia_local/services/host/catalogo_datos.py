from __future__ import annotations

from typing import Any

from django.apps import apps
from django.db import models


# ============================================================
# CONSTANTES
# ============================================================


TIPOS_CONSULTABLES = (
    models.CharField,
    models.TextField,
    models.BooleanField,
    models.IntegerField,
    models.BigIntegerField,
    models.SmallIntegerField,
    models.PositiveIntegerField,
    models.PositiveSmallIntegerField,
    models.FloatField,
    models.DecimalField,
    models.DateField,
    models.DateTimeField,
    models.TimeField,
    models.UUIDField,
    models.EmailField,
    models.SlugField,
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


def _es_app_ia_local(
    app_label: str,
) -> bool:

    return (
        _texto(
            app_label
        ).lower()
        == "ia_local"
    )


def _es_app_django(
    app_config,
) -> bool:

    nombre = _texto(
        getattr(
            app_config,
            "name",
            "",
        )
    )

    return nombre.startswith(
        "django."
    )


def _tipo_campo(
    campo,
) -> str:

    return campo.__class__.__name__


def _es_relacion(
    campo,
) -> bool:

    return bool(
        getattr(
            campo,
            "is_relation",
            False,
        )
    )


def _es_consultable(
    campo,
) -> bool:

    if _es_relacion(
        campo
    ):
        return False

    return isinstance(
        campo,
        TIPOS_CONSULTABLES,
    )


# ============================================================
# CAMPOS
# ============================================================


def describir_campo(
    campo,
) -> dict[str, Any]:

    relacion = _es_relacion(
        campo
    )

    modelo_relacionado = None

    if relacion:

        related_model = getattr(
            campo,
            "related_model",
            None,
        )

        if related_model is not None:

            modelo_relacionado = (
                related_model._meta.label
            )

    return {
        "nombre":
            campo.name,

        "tipo":
            _tipo_campo(
                campo
            ),

        "primary_key":
            bool(
                getattr(
                    campo,
                    "primary_key",
                    False,
                )
            ),

        "null":
            bool(
                getattr(
                    campo,
                    "null",
                    False,
                )
            ),

        "blank":
            bool(
                getattr(
                    campo,
                    "blank",
                    False,
                )
            ),

        "editable":
            bool(
                getattr(
                    campo,
                    "editable",
                    False,
                )
            ),

        "relacion":
            relacion,

        "many_to_many":
            bool(
                getattr(
                    campo,
                    "many_to_many",
                    False,
                )
            ),

        "many_to_one":
            bool(
                getattr(
                    campo,
                    "many_to_one",
                    False,
                )
            ),

        "one_to_one":
            bool(
                getattr(
                    campo,
                    "one_to_one",
                    False,
                )
            ),

        "modelo_relacionado":
            modelo_relacionado,

        "consultable":
            _es_consultable(
                campo
            ),
    }


# ============================================================
# MODELOS
# ============================================================


def describir_modelo(
    modelo,
) -> dict[str, Any]:

    meta = modelo._meta

    campos = [
        describir_campo(
            campo
        )
        for campo
        in meta.get_fields()
    ]

    return {
        "label":
            meta.label,

        "app_label":
            meta.app_label,

        "modelo":
            meta.object_name,

        "tabla":
            meta.db_table,

        "verbose_name":
            _texto(
                meta.verbose_name
            ),

        "verbose_name_plural":
            _texto(
                meta.verbose_name_plural
            ),

        "abstract":
            bool(
                meta.abstract
            ),

        "proxy":
            bool(
                meta.proxy
            ),

        "managed":
            bool(
                meta.managed
            ),

        "campos":
            campos,

        "campos_consultables":
            [
                campo[
                    "nombre"
                ]
                for campo
                in campos
                if campo[
                    "consultable"
                ]
            ],

        "relaciones":
            [
                campo
                for campo
                in campos
                if campo[
                    "relacion"
                ]
            ],
    }


# ============================================================
# CATÁLOGO
# ============================================================


def construir_catalogo_datos(
    *,
    incluir_ia_local: bool = False,
    incluir_django: bool = False,
) -> list[dict[str, Any]]:
    """
    Descubre modelos reales del proyecto Django cargado.

    No utiliza imports específicos del host.
    """

    resultado = []

    for modelo in apps.get_models():

        meta = modelo._meta
        app_config = apps.get_app_config(
            meta.app_label
        )

        if (
            not incluir_ia_local
            and _es_app_ia_local(
                meta.app_label
            )
        ):
            continue

        if (
            not incluir_django
            and _es_app_django(
                app_config
            )
        ):
            continue

        if meta.abstract:
            continue

        resultado.append(
            describir_modelo(
                modelo
            )
        )

    resultado.sort(
        key=lambda item: (
            item[
                "app_label"
            ],
            item[
                "modelo"
            ],
        )
    )

    return resultado


# ============================================================
# BÚSQUEDA
# ============================================================


def buscar_modelo_datos(
    referencia: str,
) -> list[dict[str, Any]]:
    """
    Busca modelos por:

        app.Model
        Model
        nombre verbose
        nombre plural
        tabla

    Devuelve candidatos; no decide por similitud difusa.
    """

    objetivo = _texto(
        referencia
    ).lower()

    if not objetivo:
        return []

    resultado = []

    for modelo in construir_catalogo_datos():

        valores = {
            _texto(
                modelo.get(
                    "label"
                )
            ).lower(),

            _texto(
                modelo.get(
                    "modelo"
                )
            ).lower(),

            _texto(
                modelo.get(
                    "tabla"
                )
            ).lower(),

            _texto(
                modelo.get(
                    "verbose_name"
                )
            ).lower(),

            _texto(
                modelo.get(
                    "verbose_name_plural"
                )
            ).lower(),
        }

        if objetivo in valores:

            resultado.append(
                modelo
            )

    return resultado


def obtener_modelo_django(
    referencia: str,
):
    """
    Resuelve únicamente un modelo inequívoco.

    Si hay 0 o más de 1 candidatos, devuelve None.
    """

    candidatos = buscar_modelo_datos(
        referencia
    )

    if len(
        candidatos
    ) != 1:
        return None

    item = candidatos[
        0
    ]

    try:

        return apps.get_model(
            item[
                "app_label"
            ],
            item[
                "modelo"
            ],
        )

    except LookupError:
        return None
