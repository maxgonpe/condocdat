from __future__ import annotations

import re
import unicodedata
from typing import Any

from django.db import models

from .catalogo_datos import (
    obtener_modelo_django,
)
from .resolvedor_objetivo_datos import (
    resolver_objetivo_datos,
)


# ============================================================
# IA-HOST024
# RESOLUCIÓN DE OPERACIÓN SEMÁNTICA
# ============================================================
#
# Responsabilidad:
#
#   pregunta
#      +
#   modelo principal validado
#      +
#   objetivo HOST023
#
#          ↓
#
#   operación semántica solicitada
#   +
#   compatibilidad con el tipo Django real
#
#
# HOST024 NO:
#   - ejecuta ORM;
#   - genera SQL;
#   - modifica filtros;
#   - invoca LLM;
#   - convierte todavía la operación semántica en un plan ORM;
#   - interpreta contenidos serializados dentro de TextField/JSON.
#
# ============================================================


# ============================================================
# OPERACIONES SEMÁNTICAS
# ============================================================

OPERACIONES_SEMANTICAS = {
    "listar_registros",
    "contar_registros",
    "contar_objetivo",
    "sumar_objetivo",
    "promediar_objetivo",
    "minimo_objetivo",
    "maximo_objetivo",
}


# ============================================================
# TIPOS
# ============================================================

TIPOS_NUMERICOS = (
    models.IntegerField,
    models.BigIntegerField,
    models.SmallIntegerField,
    models.PositiveIntegerField,
    models.PositiveSmallIntegerField,
    models.FloatField,
    models.DecimalField,
)

TIPOS_ORDENABLES = (
    *TIPOS_NUMERICOS,
    models.DateField,
    models.DateTimeField,
    models.TimeField,
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


def _normalizar(
    valor: Any,
) -> str:

    texto = _texto(
        valor
    )

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

    texto = texto.lower()

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()


def _resolver_campo_django(
    *,
    modelo: str,
    objetivo: dict[str, Any],
):

    modelo_django = (
        obtener_modelo_django(
            modelo
        )
    )

    if modelo_django is None:
        return (
            None,
            None,
        )

    nombre = _texto(
        objetivo.get(
            "nombre"
        )
    )

    if not nombre:
        return (
            modelo_django,
            None,
        )

    try:

        campo = (
            modelo_django._meta.get_field(
                nombre
            )
        )

    except Exception:

        campo = None

    return (
        modelo_django,
        campo,
    )


# ============================================================
# DETECCIÓN DE OPERACIÓN PEDIDA
# ============================================================

def _detectar_operacion_semantica(
    pregunta: str,
    *,
    objetivo_resuelto: bool,
) -> str:

    texto = _normalizar(
        pregunta
    )

    # --------------------------------------------------------
    # PROMEDIO
    # --------------------------------------------------------

    if re.search(
        r"\b(promedio|media|promedi[oa])\b",
        texto,
    ):
        return "promediar_objetivo"

    # --------------------------------------------------------
    # SUMA / TOTAL NUMÉRICO
    # --------------------------------------------------------

    if re.search(
        r"\b(suma|sumar|sumatoria|importe total|monto total|valor total)\b",
        texto,
    ):
        return "sumar_objetivo"

    # --------------------------------------------------------
    # MÁXIMO
    # --------------------------------------------------------

    if re.search(
        r"\b(maximo|mayor|mas alto|mas grande)\b",
        texto,
    ):
        return "maximo_objetivo"

    # --------------------------------------------------------
    # MÍNIMO
    # --------------------------------------------------------

    if re.search(
        r"\b(minimo|menor|mas bajo|mas pequeno)\b",
        texto,
    ):
        return "minimo_objetivo"

    # --------------------------------------------------------
    # CONTEO
    # --------------------------------------------------------

    if re.search(
        r"\b(cuantos|cuantas|cantidad|numero de|nro de|total de)\b",
        texto,
    ):

        if objetivo_resuelto:
            return "contar_objetivo"

        return "contar_registros"

    # --------------------------------------------------------
    # LISTADO
    # --------------------------------------------------------

    if re.search(
        r"\b(listar|lista|mostrar|muestra|muestrame|dame|ver)\b",
        texto,
    ):
        return "listar_registros"

    # Conservador:
    # sin señal clara no inventamos operación.
    return ""


# ============================================================
# COMPATIBILIDAD
# ============================================================

def _compatibilidad_contar_objetivo(
    campo,
    objetivo: dict[str, Any],
) -> tuple[
    bool,
    str,
    str | None,
]:

    if campo is None:

        return (
            False,
            (
                "Django no pudo resolver el objetivo como "
                "campo o relación real."
            ),
            None,
        )

    es_relacion = bool(
        getattr(
            campo,
            "is_relation",
            False,
        )
    )

    if es_relacion:

        many_to_many = bool(
            getattr(
                campo,
                "many_to_many",
                False,
            )
        )

        one_to_many = bool(
            getattr(
                campo,
                "one_to_many",
                False,
            )
        )

        if (
            many_to_many
            or one_to_many
        ):

            return (
                True,
                (
                    "El objetivo es una relación multivaluada "
                    "Django y su cardinalidad puede contarse."
                ),
                "contar_relacion",
            )

        return (
            False,
            (
                "El objetivo es una relación escalar "
                "(ForeignKey/OneToOne o equivalente), no una "
                "colección multivaluada que pueda interpretarse "
                "como cantidad del objetivo."
            ),
            None,
        )

    # Un campo escalar NO se interpreta como colección.
    #
    # Especialmente:
    #   TextField con nombres separados
    # no demuestra cuántos elementos contiene.
    return (
        False,
        (
            f"El objetivo es un campo escalar "
            f"{campo.__class__.__name__}; Django no demuestra "
            "que su contenido represente una colección contable."
        ),
        None,
    )


def _compatibilidad_suma_promedio(
    campo,
    *,
    operacion: str,
) -> tuple[
    bool,
    str,
    str | None,
]:

    if campo is None:

        return (
            False,
            (
                "Django no pudo resolver el objetivo como "
                "campo real."
            ),
            None,
        )

    if bool(
        getattr(
            campo,
            "is_relation",
            False,
        )
    ):

        return (
            False,
            (
                "La suma o promedio requiere un campo escalar "
                "numérico, no una relación."
            ),
            None,
        )

    if not isinstance(
        campo,
        TIPOS_NUMERICOS,
    ):

        return (
            False,
            (
                f"La operación requiere un campo numérico y "
                f"{campo.__class__.__name__} no está habilitado "
                "como objetivo numérico."
            ),
            None,
        )

    accion = (
        "sumar_campo"
        if operacion == "sumar_objetivo"
        else "promediar_campo"
    )

    return (
        True,
        (
            "El objetivo es un campo numérico real compatible "
            "con la agregación solicitada."
        ),
        accion,
    )


def _compatibilidad_min_max(
    campo,
    *,
    operacion: str,
) -> tuple[
    bool,
    str,
    str | None,
]:

    if campo is None:

        return (
            False,
            (
                "Django no pudo resolver el objetivo como "
                "campo real."
            ),
            None,
        )

    if bool(
        getattr(
            campo,
            "is_relation",
            False,
        )
    ):

        return (
            False,
            (
                "Mínimo/máximo requiere un campo escalar "
                "ordenable, no una relación."
            ),
            None,
        )

    if not isinstance(
        campo,
        TIPOS_ORDENABLES,
    ):

        return (
            False,
            (
                f"{campo.__class__.__name__} no está habilitado "
                "como objetivo determinista para mínimo/máximo."
            ),
            None,
        )

    accion = (
        "minimo_campo"
        if operacion == "minimo_objetivo"
        else "maximo_campo"
    )

    return (
        True,
        (
            "El objetivo es un campo escalar ordenable "
            "compatible con la agregación solicitada."
        ),
        accion,
    )


def _evaluar_compatibilidad(
    *,
    operacion: str,
    campo,
    objetivo: dict[str, Any] | None,
) -> tuple[
    bool,
    str,
    str | None,
]:

    if operacion == "listar_registros":

        return (
            True,
            (
                "Listar registros no requiere una agregación "
                "sobre el objetivo."
            ),
            "listar",
        )

    if operacion == "contar_registros":

        return (
            True,
            (
                "Contar registros opera sobre el QuerySet del "
                "modelo principal."
            ),
            "contar_registros",
        )

    if objetivo is None:

        return (
            False,
            (
                "La operación requiere un objetivo semántico "
                "resuelto y HOST023 no proporcionó uno."
            ),
            None,
        )

    if operacion == "contar_objetivo":

        return (
            _compatibilidad_contar_objetivo(
                campo,
                objetivo,
            )
        )

    if operacion in {
        "sumar_objetivo",
        "promediar_objetivo",
    }:

        return (
            _compatibilidad_suma_promedio(
                campo,
                operacion=operacion,
            )
        )

    if operacion in {
        "minimo_objetivo",
        "maximo_objetivo",
    }:

        return (
            _compatibilidad_min_max(
                campo,
                operacion=operacion,
            )
        )

    return (
        False,
        "La operación semántica no está soportada.",
        None,
    )


# ============================================================
# RESOLUCIÓN PRINCIPAL
# ============================================================

def resolver_operacion_datos(
    pregunta: str,
    *,
    modelo: str,
    objetivo_host: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Determina la operación semántica solicitada y comprueba si
    es compatible con el objetivo Django real.

    Si ``objetivo_host`` no se entrega, ejecuta HOST023.
    """

    if objetivo_host is None:

        objetivo_host = (
            resolver_objetivo_datos(
                pregunta,
                modelo=modelo,
            )
        )

    if not isinstance(
        objetivo_host,
        dict,
    ):

        return {
            "ok":
                False,

            "resuelto":
                False,

            "compatible":
                False,

            "modelo":
                modelo,

            "operacion_semantica":
                None,

            "accion_plan":
                None,

            "objetivo":
                None,

            "razon":
                "El resultado HOST023 no tiene formato válido.",

            "llm_invocado":
                False,
        }

    objetivo_resuelto = bool(
        objetivo_host.get(
            "resuelto"
        )
    )

    objetivo = (
        objetivo_host.get(
            "objetivo"
        )
        if objetivo_resuelto
        else None
    )

    operacion = (
        _detectar_operacion_semantica(
            pregunta,
            objetivo_resuelto=objetivo_resuelto,
        )
    )

    if not operacion:

        return {
            "ok":
                True,

            "resuelto":
                False,

            "compatible":
                False,

            "modelo":
                objetivo_host.get(
                    "modelo",
                    modelo,
                ),

            "operacion_semantica":
                None,

            "accion_plan":
                None,

            "objetivo":
                objetivo,

            "objetivo_host":
                objetivo_host,

            "razon":
                (
                    "No se encontró una operación semántica "
                    "inequívoca en la pregunta."
                ),

            "origen":
                "determinista",

            "llm_invocado":
                False,
        }

    modelo_real = _texto(
        objetivo_host.get(
            "modelo",
            modelo,
        )
    )

    campo = None

    if objetivo is not None:

        (
            _modelo_django,
            campo,
        ) = _resolver_campo_django(
            modelo=modelo_real,
            objetivo=objetivo,
        )

    (
        compatible,
        razon_compatibilidad,
        accion_plan,
    ) = _evaluar_compatibilidad(
        operacion=operacion,
        campo=campo,
        objetivo=objetivo,
    )

    return {
        "ok":
            True,

        "resuelto":
            True,

        "compatible":
            compatible,

        "modelo":
            modelo_real,

        "operacion_semantica":
            operacion,

        "accion_plan":
            accion_plan,

        "objetivo":
            objetivo,

        "tipo_django_objetivo":
            (
                campo.__class__.__name__
                if campo is not None
                else None
            ),

        "objetivo_host":
            objetivo_host,

        "razon":
            razon_compatibilidad,

        "origen":
            "determinista",

        "llm_invocado":
            False,
    }
