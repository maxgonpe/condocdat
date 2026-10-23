from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import (
    DatabaseError,
    models,
)

from ia_local.config.cardinalidad import (
    LIMITE_MAXIMO_INTERACTIVO,
)

from .catalogo_datos import (
    obtener_modelo_django,
)
from .validador_plan_datos import (
    validar_plan_datos,
)


# ============================================================
# CONSTANTES
# ============================================================


MAX_CAMPOS_SALIDA = 30


# ============================================================
# SERIALIZACIÓN
# ============================================================


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

    if isinstance(
        valor,
        Decimal,
    ):
        return str(
            valor
        )

    if isinstance(
        valor,
        (
            date,
            datetime,
            time,
        ),
    ):
        return valor.isoformat()

    if isinstance(
        valor,
        UUID,
    ):
        return str(
            valor
        )

    return str(
        valor
    )


def _serializar_fila(
    fila: dict[str, Any],
) -> dict[str, Any]:

    return {
        clave:
            _serializar_valor(
                valor
            )
        for clave, valor
        in fila.items()
    }


# ============================================================
# CAMPOS DE SALIDA
# ============================================================


def _campos_salida(
    modelo_django,
) -> list[str]:
    """
    Selecciona una proyección segura y acotada para respuestas
    genéricas del ORM.

    No significa que un campo excluido no pueda utilizarse como
    filtro. Solamente evita devolver automáticamente contenido
    pesado, archivos o estructuras complejas.
    """

    tipos_excluidos = (
        models.FileField,
        models.BinaryField,
        models.TextField,
        models.JSONField,
    )

    campos = []

    for campo in modelo_django._meta.fields:

        if getattr(
            campo,
            "is_relation",
            False,
        ):
            continue

        if not getattr(
            campo,
            "concrete",
            True,
        ):
            continue

        if isinstance(
            campo,
            tipos_excluidos,
        ):
            continue

        nombre = getattr(
            campo,
            "name",
            None,
        )

        if not nombre:
            continue

        campos.append(
            nombre
        )

    # Conservamos la PK al principio cuando exista.
    pk = getattr(
        modelo_django._meta,
        "pk",
        None,
    )

    nombre_pk = (
        getattr(
            pk,
            "name",
            None,
        )
        if pk
        else None
    )

    if (
        nombre_pk
        and nombre_pk in campos
    ):

        campos.remove(
            nombre_pk
        )

        campos.insert(
            0,
            nombre_pk,
        )

    return campos[
        :MAX_CAMPOS_SALIDA
    ]


def ejecutar_plan_datos(
    plan: dict[str, Any],
) -> dict[str, Any]:
    """
    Ejecuta únicamente planes que vuelven a superar
    validar_plan_datos().

    Nunca recibe SQL ni expresiones ORM arbitrarias.
    """

    validacion = validar_plan_datos(
        plan
    )

    if not validacion.get(
        "plan_validado"
    ):

        return {
            "ok":
                False,

            "ejecutado":
                False,

            "fase":
                "validacion",

            "errores":
                validacion.get(
                    "errores",
                    [],
                ),

            "validacion":
                validacion,
        }

    plan_seguro = validacion[
        "plan"
    ]

    modelo_django = obtener_modelo_django(
        plan_seguro[
            "modelo"
        ]
    )

    if modelo_django is None:

        return {
            "ok":
                False,

            "ejecutado":
                False,

            "fase":
                "modelo",

            "errores": [
                (
                    "El modelo validado ya no puede "
                    "resolverse en el registro Django."
                )
            ],
        }

    # --------------------------------------------------------
    # IA-LLM005
    # FILTROS POSITIVOS Y EXCLUSIONES
    #
    # Sólo llegan aquí filtros que YA fueron nuevamente
    # certificados por validar_plan_datos().
    #
    # Una exclusión nunca contiene ORM arbitrario:
    #
    #     lookup + valor
    #
    # ambos fueron construidos previamente por HOST.
    # --------------------------------------------------------

    filtros_orm = {}

    exclusiones_orm = []

    for filtro in plan_seguro[
        "filtros"
    ]:

        lookup = filtro[
            "lookup"
        ]

        valor = filtro[
            "valor"
        ]

        if filtro.get(
            "negado"
        ) is True:

            exclusiones_orm.append(
                {
                    lookup:
                        valor,
                }
            )

            continue

        filtros_orm[
            lookup
        ] = valor

    orden_orm = [
        item[
            "expresion"
        ]
        for item
        in plan_seguro[
            "orden"
        ]
    ]

    try:

        queryset = (
            modelo_django.objects.all()
        )

        if filtros_orm:

            queryset = queryset.filter(
                **filtros_orm
            )

        # ----------------------------------------------------
        # IA-LLM005
        #
        # Cada exclusión fue certificada previamente por HOST.
        # No aceptamos Q(), expresiones, kwargs arbitrarios ni
        # SQL procedente del LLM.
        # ----------------------------------------------------

        for exclusion in exclusiones_orm:

            queryset = queryset.exclude(
                **exclusion
            )

        operacion = plan_seguro[
            "operacion"
        ]

        # ----------------------------------------------------
        # CONTAR
        # ----------------------------------------------------

        if operacion == "contar":

            total = queryset.count()

            return {
                "ok":
                    True,

                "ejecutado":
                    True,

                "operacion":
                    "contar",

                "modelo":
                    plan_seguro[
                        "modelo"
                    ],

                "tabla":
                    plan_seguro[
                        "tabla"
                    ],

                "filtros":
                    plan_seguro[
                        "filtros"
                    ],

                "orden":
                    [],

                "limite":
                    None,

                "total":
                    total,

                "resultados":
                    [],
            }

        # ----------------------------------------------------
        # LISTAR
        # ----------------------------------------------------

        if orden_orm:

            queryset = queryset.order_by(
                *orden_orm
            )

        # ----------------------------------------------------
        # IA-LLM004-D2
        # UNIVERSO REAL Y MUESTRA INTERACTIVA
        # ----------------------------------------------------
        #
        # El conteo se realiza sobre el QuerySet ya filtrado.
        #
        # Un limite=None ya NO significa materializar todo el
        # universo. Significa que el usuario no desea una muestra
        # conceptual, pero la salida interactiva sigue protegida
        # por LIMITE_MAXIMO_INTERACTIVO.
        # ----------------------------------------------------

        total_disponible = queryset.count()

        limite_plan = plan_seguro.get(
            "limite"
        )

        if limite_plan is None:

            limite = (
                LIMITE_MAXIMO_INTERACTIVO
            )

        else:

            limite = min(
                limite_plan,
                LIMITE_MAXIMO_INTERACTIVO,
            )

        campos = _campos_salida(
            modelo_django
        )

        queryset_valores = queryset.values(
            *campos
        )

        filas = list(
            queryset_valores[:limite]
        )

        resultados = [
            _serializar_fila(
                fila
            )
            for fila
            in filas
        ]

        total_devuelto = len(
            resultados
        )

        truncado = (
            total_disponible
            > total_devuelto
        )

        return {
            "ok":
                True,

            "ejecutado":
                True,

            "operacion":
                "listar",

            "modelo":
                plan_seguro[
                    "modelo"
                ],

            "tabla":
                plan_seguro[
                    "tabla"
                ],

            "filtros":
                plan_seguro[
                    "filtros"
                ],

            "orden":
                plan_seguro[
                    "orden"
                ],

            "limite_solicitado":
                limite_plan,

            "limite":
                limite,

            "total_disponible":
                total_disponible,

            "total_devuelto":
                total_devuelto,

            "truncado":
                truncado,

            "campos":
                campos,

            "resultados":
                resultados,
        }

    except DatabaseError as exc:

        return {
            "ok":
                False,

            "ejecutado":
                False,

            "fase":
                "orm",

            "errores": [
                str(
                    exc
                )
            ],

            "modelo":
                plan_seguro[
                    "modelo"
                ],
        }

    except Exception as exc:

        return {
            "ok":
                False,

            "ejecutado":
                False,

            "fase":
                "general",

            "errores": [
                str(
                    exc
                )
            ],

            "modelo":
                plan_seguro[
                    "modelo"
                ],
        }
