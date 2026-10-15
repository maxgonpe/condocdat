from __future__ import annotations

from collections import deque
from typing import Any

from .catalogo_datos import (
    obtener_modelo_django,
)


# ============================================================
# IA-HOST025
# RESOLUCIÓN Y VALIDACIÓN DE RUTAS ORM RELACIONALES
# ============================================================
#
# Fuente de verdad:
#     Django._meta
#
# HOST025:
#   - valida relaciones reales salto por salto;
#   - construye rutas ORM con "__";
#   - distingue ruta de QuerySet de accessor de instancia;
#   - admite relaciones directas e inversas;
#   - puede enumerar rutas relacionales hasta profundidad acotada;
#   - no ejecuta ORM;
#   - no invoca LLM;
#   - no inventa related_name ni modelos.
#
# ============================================================


PROFUNDIDAD_MAXIMA_PREDETERMINADA = 3
PROFUNDIDAD_MAXIMA_ABSOLUTA = 5


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


def _profundidad_segura(
    valor: Any,
) -> int:

    try:
        profundidad = int(
            valor
        )
    except (
        TypeError,
        ValueError,
    ):
        profundidad = PROFUNDIDAD_MAXIMA_PREDETERMINADA

    return max(
        1,
        min(
            profundidad,
            PROFUNDIDAD_MAXIMA_ABSOLUTA,
        ),
    )


def _tipo_relacion(
    campo,
) -> str:

    if bool(
        getattr(
            campo,
            "many_to_many",
            False,
        )
    ):
        return "many_to_many"

    if bool(
        getattr(
            campo,
            "one_to_many",
            False,
        )
    ):
        return "one_to_many"

    if bool(
        getattr(
            campo,
            "many_to_one",
            False,
        )
    ):
        return "many_to_one"

    if bool(
        getattr(
            campo,
            "one_to_one",
            False,
        )
    ):
        return "one_to_one"

    return "relacion"


def _accessor_instancia(
    campo,
) -> str | None:

    funcion = getattr(
        campo,
        "get_accessor_name",
        None,
    )

    if not callable(
        funcion
    ):
        return None

    try:
        valor = funcion()
    except Exception:
        return None

    valor = _texto(
        valor
    )

    return (
        valor
        or None
    )


def _related_query_name(
    campo,
) -> str | None:

    valor = getattr(
        campo,
        "related_query_name",
        None,
    )

    if callable(
        valor
    ):

        try:
            valor = valor()
        except Exception:
            valor = None

    valor = _texto(
        valor
    )

    return (
        valor
        or None
    )


def _ruta_query_campo(
    campo,
) -> str:

    """
    Nombre que Django acepta como segmento de QuerySet.

    Para relaciones inversas, ``campo.name`` representa el nombre
    de consulta inversa expuesto por _meta. El accessor de instancia
    puede ser diferente (por ejemplo *_set) y se informa aparte.
    """

    return _texto(
        getattr(
            campo,
            "name",
            None,
        )
    )


def _describir_paso(
    *,
    modelo_origen,
    campo,
    indice: int,
) -> dict[str, Any]:

    modelo_destino = getattr(
        campo,
        "related_model",
        None,
    )

    return {
        "indice":
            indice,

        "modelo_origen":
            modelo_origen._meta.label,

        "segmento_orm":
            _ruta_query_campo(
                campo
            ),

        "tipo_django":
            campo.__class__.__name__,

        "tipo_relacion":
            _tipo_relacion(
                campo
            ),

        "directa":
            not bool(
                getattr(
                    campo,
                    "auto_created",
                    False,
                )
            ),

        "inversa":
            bool(
                getattr(
                    campo,
                    "auto_created",
                    False,
                )
            ),

        "multiple":
            bool(
                getattr(
                    campo,
                    "many_to_many",
                    False,
                )
                or getattr(
                    campo,
                    "one_to_many",
                    False,
                )
            ),

        "accessor_instancia":
            _accessor_instancia(
                campo
            ),

        "related_query_name":
            _related_query_name(
                campo
            ),

        "modelo_destino":
            (
                modelo_destino._meta.label
                if modelo_destino is not None
                else None
            ),
    }


# ============================================================
# RESOLUCIÓN DE SEGMENTO
# ============================================================

def _resolver_relacion(
    modelo_django,
    segmento: str,
):

    segmento = _texto(
        segmento
    )

    if not segmento:
        return None

    try:

        campo = (
            modelo_django._meta.get_field(
                segmento
            )
        )

    except Exception:
        return None

    if not bool(
        getattr(
            campo,
            "is_relation",
            False,
        )
    ):
        return None

    if getattr(
        campo,
        "related_model",
        None,
    ) is None:
        return None

    return campo


# ============================================================
# VALIDACIÓN DE RUTA EXPLÍCITA
# ============================================================

def validar_ruta_orm_relacional(
    *,
    modelo: str,
    ruta_orm: str,
) -> dict[str, Any]:
    """
    Valida una ruta relacional ORM completa.

    Ejemplo:
        documents__attachments

    Cada segmento debe existir realmente como relación Django.
    """

    modelo_django = (
        obtener_modelo_django(
            modelo
        )
    )

    if modelo_django is None:

        return {
            "ok":
                False,

            "valida":
                False,

            "modelo_origen":
                modelo,

            "ruta_orm":
                _texto(
                    ruta_orm
                ),

            "pasos":
                [],

            "modelo_destino":
                None,

            "error":
                "El modelo de origen no pudo resolverse inequívocamente.",

            "llm_invocado":
                False,
        }

    ruta = _texto(
        ruta_orm
    )

    segmentos = [
        segmento.strip()
        for segmento
        in ruta.split(
            "__"
        )
        if segmento.strip()
    ]

    if not segmentos:

        return {
            "ok":
                True,

            "valida":
                False,

            "modelo_origen":
                modelo_django._meta.label,

            "ruta_orm":
                ruta,

            "pasos":
                [],

            "modelo_destino":
                None,

            "error":
                "La ruta ORM está vacía.",

            "llm_invocado":
                False,
        }

    actual = modelo_django
    pasos = []

    for indice, segmento in enumerate(
        segmentos,
        start=1,
    ):

        campo = _resolver_relacion(
            actual,
            segmento,
        )

        if campo is None:

            return {
                "ok":
                    True,

                "valida":
                    False,

                "modelo_origen":
                    modelo_django._meta.label,

                "ruta_orm":
                    "__".join(
                        segmentos
                    ),

                "pasos":
                    pasos,

                "modelo_destino":
                    actual._meta.label,

                "segmento_invalido":
                    segmento,

                "indice_segmento_invalido":
                    indice,

                "error":
                    (
                        f"El segmento {segmento!r} no es una "
                        f"relación real navegable desde "
                        f"{actual._meta.label}."
                    ),

                "llm_invocado":
                    False,
            }

        paso = _describir_paso(
            modelo_origen=actual,
            campo=campo,
            indice=indice,
        )

        pasos.append(
            paso
        )

        actual = campo.related_model

    return {
        "ok":
            True,

        "valida":
            True,

        "modelo_origen":
            modelo_django._meta.label,

        "ruta_orm":
            "__".join(
                segmentos
            ),

        "pasos":
            pasos,

        "modelo_destino":
            actual._meta.label,

        "profundidad":
            len(
                pasos
            ),

        "contiene_relacion_multiple":
            any(
                paso[
                    "multiple"
                ]
                for paso
                in pasos
            ),

        "llm_invocado":
            False,

        "origen":
            "django_meta",
    }


# ============================================================
# ENUMERACIÓN DE RUTAS
# ============================================================

def enumerar_rutas_relacionales(
    *,
    modelo: str,
    profundidad_max: int = PROFUNDIDAD_MAXIMA_PREDETERMINADA,
) -> dict[str, Any]:
    """
    Enumera rutas reales desde un modelo, sin ejecutar consultas.

    Se evita repetir un mismo modelo dentro de una ruta para
    contener ciclos. Las autorrelaciones aparecen como paso directo,
    pero no se expanden recursivamente.
    """

    modelo_django = (
        obtener_modelo_django(
            modelo
        )
    )

    if modelo_django is None:

        return {
            "ok":
                False,

            "modelo_origen":
                modelo,

            "profundidad_max":
                _profundidad_segura(
                    profundidad_max
                ),

            "rutas":
                [],

            "total":
                0,

            "error":
                "El modelo de origen no pudo resolverse inequívocamente.",

            "llm_invocado":
                False,
        }

    profundidad = (
        _profundidad_segura(
            profundidad_max
        )
    )

    rutas = []

    cola = deque(
        [
            (
                modelo_django,
                [],
                [],
                {
                    modelo_django._meta.label
                },
            )
        ]
    )

    while cola:

        (
            actual,
            segmentos_previos,
            pasos_previos,
            modelos_visitados,
        ) = cola.popleft()

        if len(
            segmentos_previos
        ) >= profundidad:
            continue

        relaciones = []

        for campo in actual._meta.get_fields():

            if not bool(
                getattr(
                    campo,
                    "is_relation",
                    False,
                )
            ):
                continue

            if getattr(
                campo,
                "related_model",
                None,
            ) is None:
                continue

            segmento = _ruta_query_campo(
                campo
            )

            if not segmento:
                continue

            relaciones.append(
                (
                    segmento,
                    campo,
                )
            )

        relaciones.sort(
            key=lambda item: item[0]
        )

        for segmento, campo in relaciones:

            paso = _describir_paso(
                modelo_origen=actual,
                campo=campo,
                indice=(
                    len(
                        pasos_previos
                    )
                    + 1
                ),
            )

            segmentos = [
                *segmentos_previos,
                segmento,
            ]

            pasos = [
                *pasos_previos,
                paso,
            ]

            destino = (
                campo.related_model
            )

            rutas.append(
                {
                    "ruta_orm":
                        "__".join(
                            segmentos
                        ),

                    "modelo_destino":
                        destino._meta.label,

                    "profundidad":
                        len(
                            segmentos
                        ),

                    "multiple":
                        any(
                            item[
                                "multiple"
                            ]
                            for item
                            in pasos
                        ),

                    "pasos":
                        pasos,
                }
            )

            label_destino = (
                destino._meta.label
            )

            if label_destino in modelos_visitados:
                continue

            if len(
                segmentos
            ) >= profundidad:
                continue

            cola.append(
                (
                    destino,
                    segmentos,
                    pasos,
                    {
                        *modelos_visitados,
                        label_destino,
                    },
                )
            )

    rutas.sort(
        key=lambda item: (
            item[
                "profundidad"
            ],
            item[
                "ruta_orm"
            ],
        )
    )

    return {
        "ok":
            True,

        "modelo_origen":
            modelo_django._meta.label,

        "profundidad_max":
            profundidad,

        "rutas":
            rutas,

        "total":
            len(
                rutas
            ),

        "llm_invocado":
            False,

        "origen":
            "django_meta",
    }


# ============================================================
# RUTA DEL OBJETIVO HOST023
# ============================================================

def resolver_ruta_objetivo_datos(
    *,
    modelo: str,
    objetivo_host: dict[str, Any],
) -> dict[str, Any]:
    """
    Valida la ruta relacional asociada a un objetivo ya resuelto
    por HOST023.

    HOST025 no convierte campos escalares en relaciones.
    """

    if not isinstance(
        objetivo_host,
        dict,
    ):

        return {
            "ok":
                False,

            "resuelto":
                False,

            "valida":
                False,

            "modelo_origen":
                modelo,

            "ruta_orm":
                None,

            "pasos":
                [],

            "razon":
                "El resultado HOST023 no tiene formato válido.",

            "llm_invocado":
                False,
        }

    if not bool(
        objetivo_host.get(
            "resuelto"
        )
    ):

        return {
            "ok":
                True,

            "resuelto":
                False,

            "valida":
                False,

            "modelo_origen":
                _texto(
                    objetivo_host.get(
                        "modelo",
                        modelo,
                    )
                ),

            "ruta_orm":
                None,

            "pasos":
                [],

            "razon":
                "HOST023 no resolvió un objetivo inequívoco.",

            "llm_invocado":
                False,
        }

    objetivo = objetivo_host.get(
        "objetivo"
    )

    if not isinstance(
        objetivo,
        dict,
    ):

        return {
            "ok":
                True,

            "resuelto":
                False,

            "valida":
                False,

            "modelo_origen":
                _texto(
                    objetivo_host.get(
                        "modelo",
                        modelo,
                    )
                ),

            "ruta_orm":
                None,

            "pasos":
                [],

            "razon":
                "HOST023 no entregó una descripción válida del objetivo.",

            "llm_invocado":
                False,
        }

    if not bool(
        objetivo.get(
            "relacion"
        )
    ):

        return {
            "ok":
                True,

            "resuelto":
                True,

            "valida":
                False,

            "modelo_origen":
                _texto(
                    objetivo_host.get(
                        "modelo",
                        modelo,
                    )
                ),

            "ruta_orm":
                objetivo.get(
                    "ruta_orm"
                ),

            "pasos":
                [],

            "objetivo":
                objetivo,

            "razon":
                (
                    "El objetivo HOST023 es un campo escalar, "
                    "no una relación navegable."
                ),

            "llm_invocado":
                False,
        }

    modelo_real = _texto(
        objetivo_host.get(
            "modelo",
            modelo,
        )
    )

    ruta = _texto(
        objetivo.get(
            "ruta_orm",
            objetivo.get(
                "nombre"
            ),
        )
    )

    validacion = validar_ruta_orm_relacional(
        modelo=modelo_real,
        ruta_orm=ruta,
    )

    return {
        "ok":
            bool(
                validacion.get(
                    "ok"
                )
            ),

        "resuelto":
            True,

        "valida":
            bool(
                validacion.get(
                    "valida"
                )
            ),

        "modelo_origen":
            modelo_real,

        "ruta_orm":
            validacion.get(
                "ruta_orm"
            ),

        "pasos":
            validacion.get(
                "pasos",
                [],
            ),

        "modelo_destino":
            validacion.get(
                "modelo_destino"
            ),

        "objetivo":
            objetivo,

        "razon":
            (
                "La ruta del objetivo fue validada salto por salto "
                "contra Django._meta."
                if validacion.get(
                    "valida"
                )
                else validacion.get(
                    "error",
                    "La ruta relacional no pudo validarse.",
                )
            ),

        "llm_invocado":
            False,

        "origen":
            "django_meta",
    }
