from __future__ import annotations

from ia_local.config.cardinalidad import LIMITE_MUESTRA_PREDETERMINADO

from importlib import import_module
from typing import Any

from django.conf import settings


VERSION = "IA-BRIDGE009-FALLBACK-v2"

SETTING_FALLBACK = (
    "IA_LOCAL_LEGACY_FALLBACK_CALLABLE"
)


def _cargar_callable(
    ruta: str,
):
    """
    Carga un callable mediante ruta dotted:

        paquete.modulo.funcion
    """

    if not isinstance(
        ruta,
        str,
    ) or "." not in ruta:

        raise ValueError(
            "La ruta del fallback legado no es válida."
        )

    modulo_nombre, funcion_nombre = (
        ruta.rsplit(
            ".",
            1,
        )
    )

    modulo = import_module(
        modulo_nombre
    )

    funcion = getattr(
        modulo,
        funcion_nombre,
        None,
    )

    if not callable(
        funcion
    ):

        raise ValueError(
            (
                "El fallback configurado no apunta "
                "a una función invocable."
            )
        )

    return funcion


def obtener_estado_fallback_legado(
) -> dict[str, Any]:
    """
    Informa si este proyecto tiene realmente instalado
    un proveedor de fallback histórico.

    El núcleo BRIDGE no conoce ni importa motores
    específicos del proyecto.
    """

    ruta = getattr(
        settings,
        SETTING_FALLBACK,
        None,
    )

    if not ruta:

        return {
            "disponible":
                False,

            "configurado":
                False,

            "ruta":
                None,

            "razon":
                (
                    "Este proyecto no tiene configurado "
                    "un proveedor de fallback legado."
                ),
        }

    try:

        funcion = _cargar_callable(
            ruta
        )

    except Exception as exc:

        return {
            "disponible":
                False,

            "configurado":
                True,

            "ruta":
                ruta,

            "razon":
                str(
                    exc
                ),
        }

    return {
        "disponible":
            True,

        "configurado":
            True,

        "ruta":
            ruta,

        "callable":
            funcion,

        "razon":
            (
                "Proveedor de fallback legado "
                "disponible."
            ),
    }


def ejecutar_fallback_legado(
    pregunta: str,
    *,
    limite: int = LIMITE_MUESTRA_PREDETERMINADO,
) -> dict[str, Any]:
    """
    Ejecuta un fallback sólo cuando el proyecto anfitrión
    ha configurado explícitamente uno.

    BRIDGE no contiene imports del motor histórico.
    """

    estado = (
        obtener_estado_fallback_legado()
    )

    if not estado.get(
        "disponible",
        False,
    ):

        return {
            "ok":
                False,

            "version":
                VERSION,

            "ejecutado":
                False,

            "estado":
                "fallback_no_disponible",

            "mensaje":
                estado.get(
                    "razon"
                ),

            "proveedor":
                estado.get(
                    "ruta"
                ),
        }

    funcion = estado[
        "callable"
    ]

    try:

        resultado = funcion(
            pregunta,
            limite=limite,
        )

    except TypeError:

        # Compatibilidad con posibles proveedores
        # históricos que solamente acepten pregunta.
        resultado = funcion(
            pregunta
        )

    if not isinstance(
        resultado,
        dict,
    ):

        return {
            "ok":
                False,

            "version":
                VERSION,

            "ejecutado":
                False,

            "estado":
                "fallback_resultado_invalido",

            "mensaje":
                (
                    "El proveedor legado no devolvió "
                    "un diccionario estructurado."
                ),

            "proveedor":
                estado.get(
                    "ruta"
                ),
        }

    return {
        **resultado,

        "fallback_adapter_version":
            VERSION,

        "proveedor_fallback":
            estado.get(
                "ruta"
            ),
    }