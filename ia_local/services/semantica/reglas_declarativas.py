from __future__ import annotations

from typing import Any

from django.apps import apps
from django.db import transaction
from django.db.models import F

from ia_local.models import (
    IAReglaDeclarativa,
)

from .aliases_valor import (
    convertir_valor_campo,
    describir_choices_campo,
)

from .normalizacion import (
    normalizar_texto,
    texto_limpio,
)


VERSION = "IA-SEM005-v1"


OPERACIONES_PERMITIDAS = {
    "listar",
    "contar",
}


OPERADORES_PERMITIDOS = {
    "exact",
    "iexact",
    "contains",
    "icontains",
    "gt",
    "gte",
    "lt",
    "lte",
    "isnull",
}


# ============================================================
# MODELO / CAMPO
# ============================================================


def _resolver_modelo(
    referencia: str,
):

    referencia = texto_limpio(
        referencia
    )

    if (
        not referencia
        or "." not in referencia
    ):
        return None

    app_label, nombre = referencia.split(
        ".",
        1,
    )

    try:

        return apps.get_model(
            app_label,
            nombre,
        )

    except LookupError:

        return None


def _resolver_campo(
    modelo,
    nombre: str,
):

    nombre = texto_limpio(
        nombre
    )

    if not nombre:
        return None

    try:

        return modelo._meta.get_field(
            nombre
        )

    except Exception:

        return None


# ============================================================
# NORMALIZACIÓN DE CONDICIONES
# ============================================================


def _normalizar_operador(
    valor: Any,
) -> str:

    valor = normalizar_texto(
        valor
    )

    return (
        valor
        or "exact"
    )


def _normalizar_condicion(
    condicion: dict[str, Any],
) -> dict[str, Any]:

    return {
        "campo":
            texto_limpio(
                condicion.get(
                    "campo"
                )
            ),

        "operador":
            _normalizar_operador(
                condicion.get(
                    "operador",
                    "exact",
                )
            ),

        "valor":
            condicion.get(
                "valor"
            ),
    }


# ============================================================
# VALIDACIÓN DE UNA CONDICIÓN
# ============================================================


def validar_condicion(
    *,
    modelo_django,
    condicion: dict[str, Any],
) -> dict[str, Any]:

    condicion = _normalizar_condicion(
        condicion
    )

    nombre_campo = condicion[
        "campo"
    ]

    operador = condicion[
        "operador"
    ]

    valor_original = condicion[
        "valor"
    ]

    if not nombre_campo:

        return {
            "ok":
                False,

            "estado":
                "campo_vacio",

            "condicion":
                condicion,
        }

    campo = _resolver_campo(
        modelo_django,
        nombre_campo,
    )

    if campo is None:

        return {
            "ok":
                False,

            "estado":
                "campo_invalido",

            "campo":
                nombre_campo,

            "condicion":
                condicion,
        }

    if bool(
        getattr(
            campo,
            "is_relation",
            False,
        )
    ):

        return {
            "ok":
                False,

            "estado":
                "campo_relacional",

            "campo":
                campo.name,

            "condicion":
                condicion,
        }

    if (
        operador
        not in OPERADORES_PERMITIDOS
    ):

        return {
            "ok":
                False,

            "estado":
                "operador_invalido",

            "campo":
                campo.name,

            "operador":
                operador,

            "operadores_permitidos":
                sorted(
                    OPERADORES_PERMITIDOS
                ),
        }

    # --------------------------------------------------------
    # ISNULL
    # --------------------------------------------------------

    if operador == "isnull":

        normalizado = normalizar_texto(
            valor_original
        )

        if normalizado in {
            "true",
            "1",
            "si",
            "sí",
        }:

            valor_python = True

        elif normalizado in {
            "false",
            "0",
            "no",
        }:

            valor_python = False

        else:

            return {
                "ok":
                    False,

                "estado":
                    "valor_isnull_invalido",

                "campo":
                    campo.name,
            }

        return {
            "ok":
                True,

            "campo":
                campo.name,

            "operador":
                operador,

            "valor":
                valor_python,

            "tipo":
                campo.__class__.__name__,
        }

    # --------------------------------------------------------
    # CONVERSIÓN AL TIPO DEL CAMPO
    # --------------------------------------------------------

    try:

        valor_python = convertir_valor_campo(
            campo,
            valor_original,
        )

    except ValueError as exc:

        return {
            "ok":
                False,

            "estado":
                "valor_invalido",

            "campo":
                campo.name,

            "operador":
                operador,

            "razon":
                str(
                    exc
                ),
        }

    # --------------------------------------------------------
    # CHOICES
    # --------------------------------------------------------

    choices = describir_choices_campo(
        campo
    )

    if (
        choices
        and operador
        in {
            "exact",
            "iexact",
        }
    ):

        permitidos = {
            item[
                "valor"
            ]
            for item
            in choices
        }

        valor_texto = str(
            valor_python
        )

        if valor_texto not in permitidos:

            return {
                "ok":
                    False,

                "estado":
                    "valor_fuera_de_choices",

                "campo":
                    campo.name,

                "valor":
                    valor_texto,

                "valores_permitidos":
                    sorted(
                        permitidos
                    ),
            }

    return {
        "ok":
            True,

        "campo":
            campo.name,

        "operador":
            operador,

        "valor":
            valor_python,

        "tipo":
            campo.__class__.__name__,
    }


# ============================================================
# VALIDACIÓN DE REGLA
# ============================================================


def validar_regla_declarativa(
    *,
    expresion: str,
    modelo: str,
    operacion: str,
    condiciones: list[dict[str, Any]],
) -> dict[str, Any]:

    expresion = texto_limpio(
        expresion
    )

    expresion_normalizada = (
        normalizar_texto(
            expresion
        )
    )

    operacion = normalizar_texto(
        operacion
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

        "modelo":
            modelo,

        "operacion":
            operacion,

        "llm_invocado":
            False,
    }

    if not expresion_normalizada:

        return {
            **base,

            "estado":
                "expresion_vacia",
        }

    modelo_django = _resolver_modelo(
        modelo
    )

    if modelo_django is None:

        return {
            **base,

            "estado":
                "modelo_invalido",
        }

    modelo_real = (
        modelo_django._meta.label
    )

    base[
        "modelo"
    ] = modelo_real

    if (
        operacion
        not in OPERACIONES_PERMITIDAS
    ):

        return {
            **base,

            "estado":
                "operacion_invalida",

            "operaciones_permitidas":
                sorted(
                    OPERACIONES_PERMITIDAS
                ),
        }

    if not isinstance(
        condiciones,
        list,
    ):

        return {
            **base,

            "estado":
                "condiciones_invalidas",
        }

    condiciones_validadas = []

    for indice, condicion in enumerate(
        condiciones
    ):

        if not isinstance(
            condicion,
            dict,
        ):

            return {
                **base,

                "estado":
                    "condicion_invalida",

                "indice":
                    indice,
            }

        validacion = validar_condicion(
            modelo_django=modelo_django,
            condicion=condicion,
        )

        if not validacion.get(
            "ok"
        ):

            return {
                **base,

                "estado":
                    "condicion_rechazada",

                "indice":
                    indice,

                "detalle":
                    validacion,
            }

        condiciones_validadas.append(
            {
                "campo":
                    validacion[
                        "campo"
                    ],

                "operador":
                    validacion[
                        "operador"
                    ],

                "valor":
                    validacion[
                        "valor"
                    ],
            }
        )

    existente = (
        IAReglaDeclarativa.objects
        .filter(
            expresion_normalizada=(
                expresion_normalizada
            )
        )
        .first()
    )

    if existente:

        misma = (
            existente.modelo
            == modelo_real

            and existente.operacion
            == operacion

            and existente.condiciones
            == condiciones_validadas
        )

        if misma:

            return {
                **base,

                "estado":
                    "duplicado_local",

                "regla_existente_id":
                    existente.pk,
            }

        return {
            **base,

            "estado":
                "conflicto_local",

            "regla_existente_id":
                existente.pk,

            "modelo_existente":
                existente.modelo,

            "operacion_existente":
                existente.operacion,

            "condiciones_existentes":
                existente.condiciones,
        }

    return {
        **base,

        "ok":
            True,

        "estado":
            "valido",

        "condiciones":
            condiciones_validadas,
    }


# ============================================================
# GUARDAR
# ============================================================


@transaction.atomic
def guardar_regla_declarativa(
    *,
    expresion: str,
    modelo: str,
    operacion: str,
    condiciones: list[dict[str, Any]],
    observacion: str = "",
    origen: str = (
        IAReglaDeclarativa.ORIGEN_MANUAL
    ),
    prioridad: int = 100,
) -> dict[str, Any]:

    validacion = validar_regla_declarativa(
        expresion=expresion,
        modelo=modelo,
        operacion=operacion,
        condiciones=condiciones,
    )

    if not validacion.get(
        "ok"
    ):

        return {
            "ok":
                False,

            "creada":
                False,

            "validacion":
                validacion,

            "llm_invocado":
                False,
        }

    regla = IAReglaDeclarativa.objects.create(
        expresion=expresion,
        modelo=validacion[
            "modelo"
        ],
        operacion=validacion[
            "operacion"
        ],
        condiciones=validacion[
            "condiciones"
        ],
        origen=origen,
        prioridad=prioridad,
        observacion=texto_limpio(
            observacion
        ),
    )

    return {
        "ok":
            True,

        "creada":
            True,

        "regla": {
            "id":
                regla.pk,

            "expresion":
                regla.expresion,

            "expresion_normalizada":
                regla.expresion_normalizada,

            "modelo":
                regla.modelo,

            "operacion":
                regla.operacion,

            "condiciones":
                regla.condiciones,

            "origen":
                regla.origen,

            "activa":
                regla.activa,

            "prioridad":
                regla.prioridad,
        },

        "llm_invocado":
            False,
    }


# ============================================================
# RESOLVER
# ============================================================


def buscar_regla_declarativa(
    expresion: str,
) -> dict[str, Any]:

    normalizada = normalizar_texto(
        expresion
    )

    regla = (
        IAReglaDeclarativa.objects
        .filter(
            expresion_normalizada=normalizada,
            activa=True,
        )
        .order_by(
            "prioridad",
            "pk",
        )
        .first()
    )

    if regla is None:

        return {
            "ok":
                True,

            "resuelto":
                False,

            "expresion":
                expresion,

            "expresion_normalizada":
                normalizada,

            "llm_invocado":
                False,
        }

    IAReglaDeclarativa.objects.filter(
        pk=regla.pk
    ).update(
        veces_usada=F(
            "veces_usada"
        )
        + 1
    )

    return {
        "ok":
            True,

        "resuelto":
            True,

        "regla_id":
            regla.pk,

        "expresion":
            regla.expresion,

        "expresion_normalizada":
            regla.expresion_normalizada,

        "modelo":
            regla.modelo,

        "operacion":
            regla.operacion,

        "condiciones":
            regla.condiciones,

        "origen":
            regla.origen,

        "prioridad":
            regla.prioridad,

        "llm_invocado":
            False,
    }