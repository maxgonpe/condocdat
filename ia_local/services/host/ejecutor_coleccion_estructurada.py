from __future__ import annotations

from typing import Any

from django.db import DatabaseError

from .catalogo_datos import obtener_modelo_django
from .descriptor_colecciones_estructuradas import (
    obtener_coleccion_estructurada,
)


# ============================================================
# IA-HOST030
# EVALUADOR Y CONTADOR SEGURO DE COLECCIONES ESTRUCTURADAS
# ============================================================
#
# Objetivo:
#   ejecutar sobre datos reales una colección detectada por HOST029
#   con una regla genérica de presencia:
#
#       slot_ocupado = cualquier atributo del slot tiene valor no vacío
#
# Razón:
#   no se asume un "atributo identificador".
#
# Ejemplo actual:
#   en Transmital, item_XX_documento puede repetir el código del
#   transmittal y por tanto NO identifica inequívocamente al contenido
#   del slot.
#
# HOST030:
#   - reutiliza la estructura descubierta por HOST029;
#   - no hardcodea modelo, prefijo, número de slots ni atributos;
#   - no usa LLM;
#   - no usa SQL crudo;
#   - sólo lee los campos declarados por HOST029;
#   - permite filtrar únicamente por parámetros ORM ya construidos
#     por el llamador cuando se use la función de bajo nivel.
#
# La primera API pública recomendada NO recibe filtros arbitrarios:
#   contar_coleccion_estructurada_modelo()
#
# Para filtros seguros desde lenguaje natural se integrará después
# con el plan validado existente.
# ============================================================


ITERATOR_CHUNK_SIZE = 1000


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _valor_presente(valor: Any) -> bool:
    if valor is None:
        return False

    if isinstance(valor, str):
        return bool(valor.strip())

    return True


def _resultado_error(
    *,
    fase: str,
    mensaje: str,
    modelo: str | None = None,
    prefijo: str | None = None,
) -> dict[str, Any]:

    salida = {
        "ok": False,
        "ejecutado": False,
        "fase": fase,
        "errores": [mensaje],
        "llm_invocado": False,
    }

    if modelo:
        salida["modelo"] = modelo

    if prefijo:
        salida["prefijo"] = prefijo

    return salida


def _campos_coleccion(
    coleccion: dict[str, Any],
) -> list[str]:

    campos = []

    for slot in coleccion.get(
        "slots",
        [],
    ):
        for atributo in slot.get(
            "atributos_presentes",
            [],
        ):
            descripcion = (
                slot.get(
                    "campos",
                    {},
                ).get(
                    atributo
                )
            )

            if not isinstance(
                descripcion,
                dict,
            ):
                continue

            nombre = _texto(
                descripcion.get(
                    "nombre"
                )
            )

            if nombre:
                campos.append(
                    nombre
                )

    return list(
        dict.fromkeys(
            campos
        )
    )


def _mapa_slots(
    coleccion: dict[str, Any],
) -> list[dict[str, Any]]:

    resultado = []

    for slot in coleccion.get(
        "slots",
        [],
    ):

        indice = _texto(
            slot.get(
                "indice"
            )
        )

        campos = []

        for atributo in slot.get(
            "atributos_presentes",
            [],
        ):

            descripcion = (
                slot.get(
                    "campos",
                    {},
                ).get(
                    atributo
                )
            )

            if not isinstance(
                descripcion,
                dict,
            ):
                continue

            nombre = _texto(
                descripcion.get(
                    "nombre"
                )
            )

            if not nombre:
                continue

            campos.append(
                {
                    "atributo":
                        atributo,

                    "campo":
                        nombre,
                }
            )

        if indice and campos:
            resultado.append(
                {
                    "indice":
                        indice,

                    "campos":
                        campos,
                }
            )

    return resultado


def analizar_ocupacion_coleccion_estructurada(
    *,
    modelo: str,
    prefijo: str,
) -> dict[str, Any]:
    """
    Analiza todos los registros del modelo y mide ocupación real de
    los slots descubiertos por HOST029.

    Regla:
        un slot está ocupado si cualquier atributo tiene valor.
    """

    estructura = obtener_coleccion_estructurada(
        modelo=modelo,
        prefijo=prefijo,
    )

    if not estructura.get(
        "resuelto"
    ):
        return _resultado_error(
            fase="estructura",
            mensaje=estructura.get(
                "razon",
                "HOST029 no resolvió la colección estructurada.",
            ),
            modelo=modelo,
            prefijo=prefijo,
        )

    coleccion = estructura.get(
        "coleccion"
    )

    if not isinstance(
        coleccion,
        dict,
    ):
        return _resultado_error(
            fase="estructura",
            mensaje="HOST029 no entregó una estructura válida.",
            modelo=modelo,
            prefijo=prefijo,
        )

    modelo_label = _texto(
        estructura.get(
            "modelo",
            modelo,
        )
    )

    modelo_django = obtener_modelo_django(
        modelo_label
    )

    if modelo_django is None:
        return _resultado_error(
            fase="modelo",
            mensaje="El modelo no pudo resolverse mediante Django.",
            modelo=modelo_label,
            prefijo=prefijo,
        )

    mapa_slots = _mapa_slots(
        coleccion
    )

    campos = _campos_coleccion(
        coleccion
    )

    if not mapa_slots or not campos:
        return _resultado_error(
            fase="estructura",
            mensaje="La colección no contiene slots/campos utilizables.",
            modelo=modelo_label,
            prefijo=prefijo,
        )

    atributos = list(
        coleccion.get(
            "atributos",
            [],
        )
    )

    presencia_por_atributo = {
        atributo: 0
        for atributo
        in atributos
    }

    try:
        filas = (
            modelo_django.objects
            .all()
            .values_list(
                *campos
            )
            .iterator(
                chunk_size=ITERATOR_CHUNK_SIZE
            )
        )

        indices_campo = {
            nombre: indice
            for indice, nombre
            in enumerate(
                campos
            )
        }

        registros_evaluados = 0
        slots_posibles = 0
        slots_ocupados = 0
        slots_vacios = 0

        for fila in filas:
            registros_evaluados += 1

            for slot in mapa_slots:
                slots_posibles += 1

                valores_slot = []

                for item in slot[
                    "campos"
                ]:
                    nombre_campo = item[
                        "campo"
                    ]

                    atributo = item[
                        "atributo"
                    ]

                    valor = fila[
                        indices_campo[
                            nombre_campo
                        ]
                    ]

                    presente = (
                        _valor_presente(
                            valor
                        )
                    )

                    valores_slot.append(
                        presente
                    )

                    if presente:
                        presencia_por_atributo[
                            atributo
                        ] += 1

                if any(
                    valores_slot
                ):
                    slots_ocupados += 1
                else:
                    slots_vacios += 1

        cobertura_atributos = {}

        for atributo in atributos:

            presentes = (
                presencia_por_atributo[
                    atributo
                ]
            )

            cobertura = (
                presentes
                / slots_ocupados
                if slots_ocupados
                else 0.0
            )

            cobertura_atributos[
                atributo
            ] = {
                "presentes":
                    presentes,

                "slots_ocupados":
                    slots_ocupados,

                "cobertura":
                    round(
                        cobertura,
                        6,
                    ),
            }

        return {
            "ok": True,
            "ejecutado": True,
            "modelo": modelo_label,
            "tabla": modelo_django._meta.db_table,
            "prefijo": coleccion.get(
                "prefijo"
            ),
            "tipo_representacion": (
                "coleccion_estructurada_campos_repetidos"
            ),
            "regla_ocupacion": "cualquier_atributo_no_vacio",
            "cantidad_slots_por_registro": (
                coleccion.get(
                    "cantidad_slots"
                )
            ),
            "atributos": atributos,
            "registros_evaluados": registros_evaluados,
            "slots_posibles": slots_posibles,
            "slots_ocupados": slots_ocupados,
            "slots_vacios": slots_vacios,
            "presencia_por_atributo": cobertura_atributos,
            "origen": "orm_seguro_django_meta",
            "llm_invocado": False,
        }

    except DatabaseError as exc:
        return {
            "ok": False,
            "ejecutado": False,
            "fase": "orm",
            "errores": [
                str(exc)
            ],
            "modelo": modelo_label,
            "prefijo": prefijo,
            "llm_invocado": False,
        }

    except Exception as exc:
        return {
            "ok": False,
            "ejecutado": False,
            "fase": "general",
            "errores": [
                str(exc)
            ],
            "modelo": modelo_label,
            "prefijo": prefijo,
            "llm_invocado": False,
        }


def contar_coleccion_estructurada_modelo(
    *,
    modelo: str,
    prefijo: str,
) -> dict[str, Any]:
    """
    Cuenta elementos lógicos ocupados en TODOS los registros del modelo.

    Cada slot ocupado cuenta como un elemento lógico.
    """

    analisis = analizar_ocupacion_coleccion_estructurada(
        modelo=modelo,
        prefijo=prefijo,
    )

    if not analisis.get(
        "ok"
    ):
        return analisis

    return {
        "ok": True,
        "ejecutado": True,
        "operacion": (
            "contar_elementos_coleccion_estructurada"
        ),
        "modelo": analisis[
            "modelo"
        ],
        "tabla": analisis[
            "tabla"
        ],
        "prefijo": analisis[
            "prefijo"
        ],
        "tipo_representacion": analisis[
            "tipo_representacion"
        ],
        "regla_ocupacion": analisis[
            "regla_ocupacion"
        ],
        "registros_evaluados": analisis[
            "registros_evaluados"
        ],
        "cantidad_slots_por_registro": analisis[
            "cantidad_slots_por_registro"
        ],
        "slots_posibles": analisis[
            "slots_posibles"
        ],
        "slots_ocupados": analisis[
            "slots_ocupados"
        ],
        "slots_vacios": analisis[
            "slots_vacios"
        ],
        "total": analisis[
            "slots_ocupados"
        ],
        "presencia_por_atributo": analisis[
            "presencia_por_atributo"
        ],
        "origen": analisis[
            "origen"
        ],
        "llm_invocado": False,
    }
