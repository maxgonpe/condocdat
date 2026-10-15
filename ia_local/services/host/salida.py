from __future__ import annotations

from typing import Any


# ============================================================
# SALIDA PÚBLICA PORTABLE
# ============================================================


def _lista_resultados(
    ejecucion: dict[str, Any],
) -> list[Any]:
    resultados = ejecucion.get(
        "resultados"
    )

    if isinstance(
        resultados,
        list,
    ):
        return resultados

    return []


def _columnas_resultados(
    ejecucion: dict[str, Any],
    resultados: list[Any],
) -> list[str]:
    """
    Obtiene las columnas sin conocer modelos ni apps del host.

    Prioridad:
        1. proyección real informada por el ejecutor ORM;
        2. unión ordenada de claves presentes en los resultados.
    """

    campos = ejecucion.get(
        "campos"
    )

    if isinstance(
        campos,
        list,
    ):
        columnas = [
            str(campo)
            for campo in campos
            if campo not in (
                None,
                "",
            )
        ]

        if columnas:
            return columnas

    columnas = []

    for registro in resultados:
        if not isinstance(
            registro,
            dict,
        ):
            continue

        for clave in registro.keys():
            clave = str(
                clave
            )

            if clave not in columnas:
                columnas.append(
                    clave
                )

    return columnas


def normalizar_salida(
    resultado: dict[str, Any],
) -> dict[str, Any]:
    """
    Convierte el contrato interno del router HOST en un contrato
    público, estable y portable para UI, PDF, Excel y futuras APIs.

    Esta función no conoce apps, modelos concretos ni reglas del
    negocio del anfitrión. Sólo consume información que el router
    y el ejecutor ORM ya demostraron.
    """

    if not isinstance(
        resultado,
        dict,
    ):
        raise ValueError(
            "El resultado del router debe ser un objeto." 
        )

    intencion = resultado.get(
        "intencion"
    )

    if not isinstance(
        intencion,
        dict,
    ):
        intencion = {}

    estructurada = resultado.get(
        "respuesta_estructurada"
    )

    if not isinstance(
        estructurada,
        dict,
    ):
        estructurada = {}

    ejecucion = resultado.get(
        "ejecucion_datos"
    )

    if not isinstance(
        ejecucion,
        dict,
    ):
        ejecucion = estructurada.get(
            "ejecucion"
        )

    if not isinstance(
        ejecucion,
        dict,
    ):
        ejecucion = {}

    destino = resultado.get(
        "destino"
    )

    tipo_intencion = intencion.get(
        "tipo"
    )

    if destino == "datos":
        tipo = "datos"
    elif destino == "host":
        tipo = "estructura"
    else:
        tipo = (
            tipo_intencion
            or "desconocido"
        )

    resultados = _lista_resultados(
        ejecucion
    )

    columnas = _columnas_resultados(
        ejecucion,
        resultados,
    )

    operacion = (
        ejecucion.get(
            "operacion"
        )
        or intencion.get(
            "accion"
        )
    )

    modelo = (
        ejecucion.get(
            "modelo"
        )
        or intencion.get(
            "entidad"
        )
        or estructurada.get(
            "entidad"
        )
    )

    total = None

    if operacion == "contar":
        total = ejecucion.get(
            "total"
        )
    else:
        total = ejecucion.get(
            "total_devuelto"
        )

    if total is None and resultados:
        total = len(
            resultados
        )

    respuesta = resultado.get(
        "respuesta"
    )

    if respuesta is None:
        respuesta = ""

    salida = {
        "tipo":
            tipo,

        "destino":
            destino,

        "origen":
            intencion.get(
                "origen"
            ),

        "modelo":
            modelo,

        "operacion":
            operacion,

        "tabla":
            ejecucion.get(
                "tabla"
            ),

        "total":
            total,

        "limite":
            ejecucion.get(
                "limite"
            ),

        "respuesta":
            str(
                respuesta
            ),

        "columnas":
            columnas,

        "resultados":
            resultados,

        "llm_invocado":
            bool(
                resultado.get(
                    "llm_invocado"
                )
            ),

        "filtros":
            ejecucion.get(
                "filtros"
            )
            or [],

        "orden":
            ejecucion.get(
                "orden"
            )
            or [],

        "meta": {
            "tipo_intencion":
                tipo_intencion,

            "subtipo_intencion":
                intencion.get(
                    "subtipo"
                ),

            "entidad_validada":
                intencion.get(
                    "validado"
                ),

            "fase":
                estructurada.get(
                    "fase"
                ),

            "ejecutado":
                estructurada.get(
                    "ejecutado"
                ),
        },
    }

    return salida
