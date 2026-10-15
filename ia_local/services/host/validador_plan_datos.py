from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from django.db import models

from .catalogo_datos import (
    buscar_modelo_datos,
    obtener_modelo_django,
)


# ============================================================
# CONSTANTES
# ============================================================


OPERACIONES_PERMITIDAS = {
    "listar",
    "contar",
}


OPERADORES_TEXTO = {
    "exact",
    "iexact",
    "contains",
    "icontains",
}


OPERADORES_COMPARACION = {
    "exact",
    "gt",
    "gte",
    "lt",
    "lte",
}


OPERADORES_FECHA = {
    "exact",
    "gt",
    "gte",
    "lt",
    "lte",
    "year",
    "month",
    "day",
}


OPERADORES_BOOLEANOS = {
    "exact",
}


OPERADOR_NULO = {
    "isnull",
}


LIMITE_PREDETERMINADO = 20
LIMITE_MAXIMO = 100


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


def _normalizar_bool(
    valor: Any,
) -> bool:

    if isinstance(
        valor,
        bool,
    ):
        return valor

    if isinstance(
        valor,
        int,
    ):
        if valor == 1:
            return True

        if valor == 0:
            return False

    texto = _texto(
        valor
    ).lower()

    verdaderos = {
        "true",
        "1",
        "si",
        "sí",
        "yes",
        "verdadero",
    }

    falsos = {
        "false",
        "0",
        "no",
        "falso",
    }

    if texto in verdaderos:
        return True

    if texto in falsos:
        return False

    raise ValueError(
        f"No se puede convertir {valor!r} a booleano."
    )


# ============================================================
# MODELO Y CAMPO
# ============================================================


def _descripcion_modelo(
    referencia: str,
) -> dict[str, Any] | None:

    candidatos = buscar_modelo_datos(
        referencia
    )

    if len(
        candidatos
    ) != 1:
        return None

    return candidatos[
        0
    ]


def _campo_descrito(
    modelo: dict[str, Any],
    nombre: str,
) -> dict[str, Any] | None:

    for campo in modelo.get(
        "campos",
        [],
    ):

        if (
            campo.get(
                "nombre"
            )
            == nombre
        ):
            return campo

    return None


# ============================================================
# OPERADORES SEGÚN TIPO
# ============================================================


def _operadores_para_campo(
    campo,
) -> set[str]:

    operadores = set()

    if isinstance(
        campo,
        (
            models.CharField,
            models.TextField,
            models.EmailField,
            models.SlugField,
            models.UUIDField,
        ),
    ):

        operadores.update(
            OPERADORES_TEXTO
        )

    elif isinstance(
        campo,
        models.BooleanField,
    ):

        operadores.update(
            OPERADORES_BOOLEANOS
        )

    elif isinstance(
        campo,
        (
            models.IntegerField,
            models.BigIntegerField,
            models.SmallIntegerField,
            models.PositiveIntegerField,
            models.PositiveSmallIntegerField,
            models.FloatField,
            models.DecimalField,
        ),
    ):

        operadores.update(
            OPERADORES_COMPARACION
        )

    elif isinstance(
        campo,
        (
            models.DateField,
            models.DateTimeField,
        ),
    ):

        operadores.update(
            OPERADORES_FECHA
        )

    elif isinstance(
        campo,
        models.TimeField,
    ):

        operadores.update(
            OPERADORES_COMPARACION
        )

    else:

        operadores.add(
            "exact"
        )

    operadores.update(
        OPERADOR_NULO
    )

    return operadores


# ============================================================
# CONVERSIÓN DE VALORES
# ============================================================


def _convertir_valor(
    campo,
    operador: str,
    valor: Any,
) -> Any:

    if operador == "isnull":

        return _normalizar_bool(
            valor
        )

    if operador in {
        "year",
        "month",
        "day",
    }:

        try:

            valor_entero = int(
                valor
            )

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise ValueError(
                (
                    f"El operador {operador} requiere "
                    "un valor entero."
                )
            ) from exc

        if (
            operador == "month"
            and not 1 <= valor_entero <= 12
        ):

            raise ValueError(
                "El mes debe estar entre 1 y 12."
            )

        if (
            operador == "day"
            and not 1 <= valor_entero <= 31
        ):

            raise ValueError(
                "El día debe estar entre 1 y 31."
            )

        return valor_entero

    if isinstance(
        campo,
        models.BooleanField,
    ):

        return _normalizar_bool(
            valor
        )

    try:

        convertido = campo.to_python(
            valor
        )

    except Exception as exc:

        raise ValueError(
            (
                f"No se puede convertir {valor!r} "
                f"al tipo {campo.__class__.__name__}."
            )
        ) from exc

    tipos_permitidos = (
        str,
        int,
        float,
        bool,
        Decimal,
        date,
        datetime,
        time,
    )

    if (
        convertido is not None
        and not isinstance(
            convertido,
            tipos_permitidos,
        )
    ):

        convertido = str(
            convertido
        )

    return convertido


# ============================================================
# VALIDACIÓN PRINCIPAL
# ============================================================


def validar_plan_datos(
    propuesta: dict[str, Any],
) -> dict[str, Any]:
    """
    Valida un plan declarativo antes de cualquier ORM.

    Esta función NO ejecuta consultas.
    """

    errores = []
    advertencias = []

    if not isinstance(
        propuesta,
        dict,
    ):

        return {
            "ok":
                False,

            "plan_validado":
                False,

            "errores": [
                "La propuesta no es un diccionario."
            ],

            "advertencias":
                [],

            "plan":
                None,
        }

    # --------------------------------------------------------
    # MODELO
    # --------------------------------------------------------

    referencia_modelo = _texto(
        propuesta.get(
            "modelo"
        )
    )

    descripcion = _descripcion_modelo(
        referencia_modelo
    )

    modelo_django = obtener_modelo_django(
        referencia_modelo
    )

    if (
        descripcion is None
        or modelo_django is None
    ):

        return {
            "ok":
                False,

            "plan_validado":
                False,

            "errores": [
                (
                    "El modelo no existe o no puede "
                    "resolverse de forma inequívoca."
                )
            ],

            "advertencias":
                [],

            "plan":
                None,
        }

    # --------------------------------------------------------
    # OPERACIÓN
    # --------------------------------------------------------

    operacion = _texto(
        propuesta.get(
            "operacion"
        )
    ).lower()

    if operacion not in OPERACIONES_PERMITIDAS:

        errores.append(
            (
                f"Operación no permitida: "
                f"{operacion!r}."
            )
        )

    # --------------------------------------------------------
    # FILTROS
    # --------------------------------------------------------

    filtros_crudos = propuesta.get(
        "filtros"
    )

    if not isinstance(
        filtros_crudos,
        list,
    ):

        errores.append(
            "Los filtros deben ser una lista."
        )

        filtros_crudos = []

    filtros_validados = []

    for indice, filtro in enumerate(
        filtros_crudos
    ):

        if not isinstance(
            filtro,
            dict,
        ):

            errores.append(
                (
                    f"Filtro {indice}: "
                    "formato inválido."
                )
            )

            continue

        nombre_campo = _texto(
            filtro.get(
                "campo"
            )
        )

        operador = _texto(
            filtro.get(
                "operador"
            )
        ).lower()

        valor = filtro.get(
            "valor"
        )

        descripcion_campo = (
            _campo_descrito(
                descripcion,
                nombre_campo,
            )
        )

        if descripcion_campo is None:

            errores.append(
                (
                    f"Filtro {indice}: "
                    f"el campo {nombre_campo!r} "
                    "no existe."
                )
            )

            continue

        if not descripcion_campo.get(
            "consultable"
        ):

            errores.append(
                (
                    f"Filtro {indice}: "
                    f"el campo {nombre_campo!r} "
                    "no está habilitado para consulta."
                )
            )

            continue

        try:

            campo_django = (
                modelo_django._meta.get_field(
                    nombre_campo
                )
            )

        except Exception:

            errores.append(
                (
                    f"Filtro {indice}: "
                    f"Django no pudo resolver "
                    f"el campo {nombre_campo!r}."
                )
            )

            continue

        operadores_permitidos = (
            _operadores_para_campo(
                campo_django
            )
        )

        if operador not in operadores_permitidos:

            errores.append(
                (
                    f"Filtro {indice}: "
                    f"operador {operador!r} "
                    f"no permitido para "
                    f"{campo_django.__class__.__name__}."
                )
            )

            continue

        try:

            valor_convertido = (
                _convertir_valor(
                    campo_django,
                    operador,
                    valor,
                )
            )

        except ValueError as exc:

            errores.append(
                (
                    f"Filtro {indice}: "
                    f"{exc}"
                )
            )

            continue

        lookup = nombre_campo

        if operador != "exact":

            lookup = (
                f"{nombre_campo}"
                f"__{operador}"
            )

        filtros_validados.append(
            {
                "campo":
                    nombre_campo,

                "operador":
                    operador,

                "lookup":
                    lookup,

                "valor":
                    valor_convertido,

                "tipo":
                    campo_django.__class__.__name__,
            }
        )

    # --------------------------------------------------------
    # ORDEN
    # --------------------------------------------------------

    orden_crudo = propuesta.get(
        "orden"
    )

    if not isinstance(
        orden_crudo,
        list,
    ):

        errores.append(
            "El orden debe ser una lista."
        )

        orden_crudo = []

    orden_validado = []

    for indice, item in enumerate(
        orden_crudo
    ):

        if not isinstance(
            item,
            dict,
        ):

            errores.append(
                (
                    f"Orden {indice}: "
                    "formato inválido."
                )
            )

            continue

        nombre_campo = _texto(
            item.get(
                "campo"
            )
        )

        direccion = _texto(
            item.get(
                "direccion"
            )
        ).lower()

        descripcion_campo = (
            _campo_descrito(
                descripcion,
                nombre_campo,
            )
        )

        if descripcion_campo is None:

            errores.append(
                (
                    f"Orden {indice}: "
                    f"el campo {nombre_campo!r} "
                    "no existe."
                )
            )

            continue

        if not descripcion_campo.get(
            "consultable"
        ):

            errores.append(
                (
                    f"Orden {indice}: "
                    f"el campo {nombre_campo!r} "
                    "no es consultable."
                )
            )

            continue

        if direccion not in {
            "asc",
            "desc",
        }:

            errores.append(
                (
                    f"Orden {indice}: "
                    f"dirección {direccion!r} "
                    "no permitida."
                )
            )

            continue

        expresion = nombre_campo

        if direccion == "desc":

            expresion = (
                f"-{nombre_campo}"
            )

        orden_validado.append(
            {
                "campo":
                    nombre_campo,

                "direccion":
                    direccion,

                "expresion":
                    expresion,
            }
        )

    # --------------------------------------------------------
    # LÍMITE
    # --------------------------------------------------------

    limite_crudo = propuesta.get(
        "limite",
        LIMITE_PREDETERMINADO,
    )

    if limite_crudo is None:
        limite = None
    else:
        try:
            limite = int(limite_crudo)
        except (TypeError, ValueError):
            errores.append(
                "El límite no es un entero válido."
            )
            limite = LIMITE_PREDETERMINADO

        if limite < 1:
            errores.append(
                "El límite debe ser mayor que cero."
            )

        if limite > LIMITE_MAXIMO:
            errores.append(
                (
                    f"El límite máximo permitido "
                    f"es {LIMITE_MAXIMO}."
                )
            )

    # --------------------------------------------------------
    # CONDICIONES NO RESUELTAS
    # --------------------------------------------------------

    condiciones = propuesta.get(
        "condiciones_no_resueltas"
    )

    if not isinstance(
        condiciones,
        list,
    ):

        errores.append(
            (
                "condiciones_no_resueltas "
                "debe ser una lista."
            )
        )

        condiciones = []

    condiciones = [
        _texto(
            item
        )
        for item
        in condiciones
        if _texto(
            item
        )
    ]

    if condiciones:

        errores.append(
            (
                "Existen condiciones de la pregunta "
                "que no pudieron resolverse de forma "
                "segura."
            )
        )

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    plan_validado = (
        len(
            errores
        )
        == 0
    )

    plan = {
        "modelo":
            descripcion[
                "label"
            ],

        "tabla":
            descripcion[
                "tabla"
            ],

        "operacion":
            operacion,

        "filtros":
            filtros_validados,

        "orden":
            orden_validado,

        "limite":
            limite,

        "condiciones_no_resueltas":
            condiciones,
    }

    return {
        "ok":
            plan_validado,

        "plan_validado":
            plan_validado,

        "errores":
            errores,

        "advertencias":
            advertencias,

        "plan":
            plan,

        "catalogo": {
            "modelo":
                descripcion[
                    "label"
                ],

            "tabla":
                descripcion[
                    "tabla"
                ],

            "campos_consultables":
                descripcion[
                    "campos_consultables"
                ],
        },
    }
