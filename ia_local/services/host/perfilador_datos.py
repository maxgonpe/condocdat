from __future__ import annotations

from typing import Any

from django.db import DatabaseError
from django.db import models
from django.db.models import Count

from .catalogo_datos import (
    obtener_modelo_django,
)


# ============================================================
# CONSTANTES
# ============================================================


MAX_VALORES_PREDETERMINADO = 25
MAX_VALORES_ABSOLUTO = 100

# Un campo categórico útil no se determina por max_length.
# Se evalúa posteriormente según sus valores reales.
MAX_DISTINTOS_CATEGORICO = 50


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


def _serializar_valor(
    valor: Any,
) -> Any:

    if valor is None:
        return None

    if isinstance(
        valor,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return valor

    return str(
        valor
    )


# ============================================================
# ELEGIBILIDAD
# ============================================================


def campo_perfilable(
    campo,
) -> bool:
    """
    Decide si un campo puede ser evaluado automáticamente
    como posible categoría.

    Esta función solamente determina elegibilidad técnica.

    La decisión semántica final se toma después de observar
    cuántos valores distintos existen realmente.
    """

    if getattr(
        campo,
        "is_relation",
        False,
    ):
        return False

    if getattr(
        campo,
        "primary_key",
        False,
    ):
        return False

    if getattr(
        campo,
        "unique",
        False,
    ):
        return False

    if isinstance(
        campo,
        models.BooleanField,
    ):
        return True

    if isinstance(
        campo,
        models.CharField,
    ):
        return True

    return False


# ============================================================
# PERFIL DE CAMPO
# ============================================================


def perfilar_campo(
    modelo: str,
    campo: str,
    *,
    max_valores: int = MAX_VALORES_PREDETERMINADO,
) -> dict[str, Any]:
    """
    Obtiene valores distintos y frecuencia para un campo real.

    Solo lectura.
    """

    modelo_django = obtener_modelo_django(
        modelo
    )

    if modelo_django is None:

        return {
            "ok":
                False,

            "modelo":
                modelo,

            "campo":
                campo,

            "error":
                "modelo_no_resuelto",
        }

    try:

        campo_django = (
            modelo_django._meta.get_field(
                campo
            )
        )

    except Exception:

        return {
            "ok":
                False,

            "modelo":
                modelo_django._meta.label,

            "campo":
                campo,

            "error":
                "campo_no_resuelto",
        }

    if getattr(
        campo_django,
        "is_relation",
        False,
    ):

        return {
            "ok":
                False,

            "modelo":
                modelo_django._meta.label,

            "campo":
                campo,

            "error":
                "campo_relacional_no_permitido",
        }

    try:

        max_valores = int(
            max_valores
        )

    except (
        TypeError,
        ValueError,
    ):

        max_valores = (
            MAX_VALORES_PREDETERMINADO
        )

    max_valores = max(
        1,
        min(
            max_valores,
            MAX_VALORES_ABSOLUTO,
        ),
    )

    try:

        queryset = (
            modelo_django.objects
            .values(
                campo
            )
            .annotate(
                total=Count(
                    "pk"
                )
            )
            .order_by(
                "-total",
                campo,
            )
        )

        filas = list(
            queryset[
                :max_valores
            ]
        )

        total_registros = (
            modelo_django.objects.count()
        )

        total_distintos = (
            modelo_django.objects
            .values(
                campo
            )
            .distinct()
            .count()
        )

    except DatabaseError as exc:

        return {
            "ok":
                False,

            "modelo":
                modelo_django._meta.label,

            "campo":
                campo,

            "error":
                "database_error",

            "detalle":
                str(
                    exc
                ),
        }

    valores = []

    for fila in filas:

        valores.append(
            {
                "valor":
                    _serializar_valor(
                        fila.get(
                            campo
                        )
                    ),

                "frecuencia":
                    fila.get(
                        "total",
                        0,
                    ),
            }
        )

    return {
        "ok":
            True,

        "modelo":
            modelo_django._meta.label,

        "tabla":
            modelo_django._meta.db_table,

        "campo":
            campo,

        "tipo":
            campo_django.__class__.__name__,

        "perfilable_automaticamente":
            campo_perfilable(
                campo_django
            ),

        "total_registros":
            total_registros,

        "total_distintos":
            total_distintos,

        "valores_mostrados":
            len(
                valores
            ),

        "truncado":
            (
                total_distintos
                > len(
                    valores
                )
            ),

        "valores":
            valores,
    }


# ============================================================
# CAMPOS CANDIDATOS
# ============================================================


def campos_perfilables_modelo(
    modelo: str,
) -> list[str]:

    modelo_django = obtener_modelo_django(
        modelo
    )

    if modelo_django is None:
        return []

    return [
        campo.name
        for campo
        in modelo_django._meta.fields
        if campo_perfilable(
            campo
        )
    ]


# ============================================================
# UTILIDAD SEMÁNTICA DEL PERFIL
# ============================================================


def perfil_categorico_util(
    perfil: dict[str, Any],
) -> bool:
    """
    Decide usando evidencia real de la base si un perfil
    tiene una cardinalidad razonable para interpretación
    semántica automática.
    """

    if not perfil.get(
        "ok"
    ):
        return False

    tipo = perfil.get(
        "tipo"
    )

    valores = perfil.get(
        "valores"
    )

    if not isinstance(
        valores,
        list,
    ):
        return False

    valores_informativos = [
        item
        for item
        in valores
        if (
            isinstance(
                item,
                dict,
            )
            and item.get(
                "valor"
            )
            not in {
                None,
                "",
            }
        )
    ]

    if tipo == "BooleanField":
        return bool(
            valores
        )

    if tipo != "CharField":
        return False

    if not valores_informativos:
        return False

    try:

        total_distintos = int(
            perfil.get(
                "total_distintos",
                0,
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        return False

    return (
        1
        <= total_distintos
        <= MAX_DISTINTOS_CATEGORICO
    )


# ============================================================
# PERFIL DE MODELO
# ============================================================


def perfilar_modelo(
    modelo: str,
    *,
    campos: list[str] | None = None,
    max_valores: int = MAX_VALORES_PREDETERMINADO,
) -> dict[str, Any]:

    modelo_django = obtener_modelo_django(
        modelo
    )

    if modelo_django is None:

        return {
            "ok":
                False,

            "modelo":
                modelo,

            "error":
                "modelo_no_resuelto",

            "perfiles":
                [],
        }

    if campos is None:

        campos = (
            campos_perfilables_modelo(
                modelo
            )
        )

    perfiles = []

    for nombre in campos:

        perfil = perfilar_campo(
            modelo_django._meta.label,
            nombre,
            max_valores=max_valores,
        )

        if perfil_categorico_util(
            perfil
        ):

            perfiles.append(
                perfil
            )

    return {
        "ok":
            True,

        "modelo":
            modelo_django._meta.label,

        "tabla":
            modelo_django._meta.db_table,

        "campos_perfilados":
            len(
                perfiles
            ),

        "perfiles":
            perfiles,
    }
