from __future__ import annotations

from ia_local.config.cardinalidad import (
    LIMITE_MUESTRA_PREDETERMINADO,
)


import re
from typing import Any, Callable

from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)

from ia_local.services.bridge import (
    campo_operador_valor as bridge003,
)


VERSION = "IA-QUERY001-v1"



# ============================================================
# CONECTORES AND SOPORTADOS
# ============================================================

PATRONES_AND = (
    r"\s+\by\b\s+",
    r"\s+\band\b\s+",
    r"\s+\bademas\b\s+",
    r"\s+\bademás\b\s+",
)


# ============================================================
# CALLABLE PÚBLICO BRIDGE003
# ============================================================
#
# QUERY001 trata BRIDGE003 como una caja negra.
#
# Como esta capa debe ser portable entre las versiones que
# construimos durante BRIDGE, localizamos únicamente funciones
# públicas conocidas del módulo.
#
# NO inspeccionamos funciones privadas.
# NO ejecutamos ORM.
# ============================================================


CANDIDATOS_BRIDGE003 = (
    "componer_campo_operador_valor",
)

def _obtener_callable_bridge003(
) -> tuple[str | None, Callable[..., Any] | None]:
    """
    Obtiene el punto público disponible de BRIDGE003.

    Esta pequeña adaptación evita acoplar QUERY a detalles
    internos del módulo.
    """

    for nombre in CANDIDATOS_BRIDGE003:

        funcion = getattr(
            bridge003,
            nombre,
            None,
        )

        if callable(
            funcion
        ):

            return (
                nombre,
                funcion,
            )

    return (
        None,
        None,
    )


# ============================================================
# NORMALIZACIÓN LOCAL
# ============================================================


def _normalizar_espacios(
    texto: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        texto,
    ).strip()


def _normalizar_para_deteccion(
    texto: str,
) -> str:

    texto = _normalizar_espacios(
        texto
    )

    return texto.lower()


# ============================================================
# DIVISIÓN AND
# ============================================================


def dividir_condiciones_and(
    pregunta: str,
) -> dict[str, Any]:
    """
    Divide una expresión en cláusulas AND simples.

    No interpreta todavía cada cláusula.
    """

    if not isinstance(
        pregunta,
        str,
    ):

        return {
            "ok":
                False,

            "version":
                VERSION,

            "estado":
                "pregunta_invalida",

            "condiciones":
                [],

            "razon":
                "La pregunta debe ser texto.",
        }

    pregunta = _normalizar_espacios(
        pregunta
    )

    if not pregunta:

        return {
            "ok":
                False,

            "version":
                VERSION,

            "estado":
                "pregunta_vacia",

            "condiciones":
                [],

            "razon":
                "La pregunta está vacía.",
        }

    patron = (
        "(?:"
        + "|".join(
            PATRONES_AND
        )
        + ")"
    )

    partes = re.split(
        patron,
        pregunta,
        flags=re.IGNORECASE,
    )

    partes = [
        _normalizar_espacios(
            parte
        )
        for parte in partes
        if _normalizar_espacios(
            parte
        )
    ]

    if len(
        partes
    ) <= 1:

        return {
            "ok":
                False,

            "version":
                VERSION,

            "estado":
                "sin_multiples_condiciones",

            "pregunta":
                pregunta,

            "condiciones":
                partes,

            "razon":
                (
                    "No se detectaron múltiples "
                    "condiciones AND."
                ),
        }

    return {
        "ok":
            True,

        "version":
            VERSION,

        "estado":
            "condiciones_detectadas",

        "pregunta":
            pregunta,

        "cantidad":
            len(
                partes
            ),

        "condiciones":
            partes,
    }


# ============================================================
# PREFIJO DE CONSULTA
# ============================================================


def _separar_prefijo_y_primera_condicion(
    primera: str,
) -> tuple[str | None, str]:
    """
    Ejemplo:

        listar documentos cuyo estado es pendiente

    produce:

        prefijo:
            listar documentos

        condición:
            cuyo estado es pendiente

    Esto permite reconstruir las siguientes condiciones
    como preguntas completas para BRIDGE003.
    """

    patron = re.compile(
        r"^(.*?)"
        r"\s+"
        r"("
        r"cuyo|cuya|cuyos|cuyas"
        r")"
        r"\s+"
        r"(.+)$",
        flags=re.IGNORECASE,
    )

    match = patron.match(
        primera
    )

    if not match:

        return (
            None,
            primera,
        )

    prefijo = (
        match.group(
            1
        )
        or ""
    ).strip()

    relativo = (
        match.group(
            2
        )
        or ""
    ).strip()

    resto = (
        match.group(
            3
        )
        or ""
    ).strip()

    condicion = (
        f"{relativo} {resto}"
    ).strip()

    return (
        prefijo or None,
        condicion,
    )


def _normalizar_condicion_relativa(
    condicion: str,
) -> str:
    """
    Las condiciones posteriores suelen llegar como:

        cuyo tema contiene estructura
        cuyo código contiene ODATA

    Si vienen sin relativo:

        tema contiene estructura

    agregamos 'cuyo' para conservar el lenguaje
    esperado por BRIDGE003.
    """

    condicion = _normalizar_espacios(
        condicion
    )

    condicion_n = (
        _normalizar_para_deteccion(
            condicion
        )
    )

    relativos = (
        "cuyo ",
        "cuya ",
        "cuyos ",
        "cuyas ",
    )

    if condicion_n.startswith(
        relativos
    ):

        return condicion

    return (
        f"cuyo {condicion}"
    )


# ============================================================
# INVOCACIÓN BRIDGE003
# ============================================================


def _invocar_bridge003(
    pregunta: str,
    *,
    limite: int,
) -> dict[str, Any]:
    """
    Invoca exclusivamente el punto público de BRIDGE003.

    Se aceptan las dos firmas habituales construidas
    durante la fase BRIDGE:

        funcion(pregunta, limite=...)
        funcion(pregunta, limite)

    No existe fallback a ORM.
    """

    nombre, funcion = (
        _obtener_callable_bridge003()
    )

    if funcion is None:

        return {
            "ok":
                False,

            "version":
                VERSION,

            "estado":
                "bridge003_no_disponible",

            "pregunta":
                pregunta,

            "razon":
                (
                    "No se encontró un punto público "
                    "compatible de IA-BRIDGE003."
                ),

            "candidatos":
                list(
                    CANDIDATOS_BRIDGE003
                ),
        }

    try:

        resultado = funcion(
            pregunta,
            limite=limite,
        )

    except TypeError:

        try:

            resultado = funcion(
                pregunta,
                limite,
            )

        except TypeError as exc:

            return {
                "ok":
                    False,

                "version":
                    VERSION,

                "estado":
                    "firma_bridge003_incompatible",

                "pregunta":
                    pregunta,

                "callable_bridge003":
                    nombre,

                "razon":
                    str(
                        exc
                    ),
            }

    except Exception as exc:

        return {
            "ok":
                False,

            "version":
                VERSION,

            "estado":
                "error_bridge003",

            "pregunta":
                pregunta,

            "callable_bridge003":
                nombre,

            "razon":
                str(
                    exc
                ),
        }

    if not isinstance(
        resultado,
        dict,
    ):

        return {
            "ok":
                False,

            "version":
                VERSION,

            "estado":
                "resultado_bridge003_invalido",

            "pregunta":
                pregunta,

            "callable_bridge003":
                nombre,

            "razon":
                (
                    "BRIDGE003 no devolvió "
                    "un diccionario."
                ),
        }

    return {
        "ok":
            True,

        "callable_bridge003":
            nombre,

        "resultado":
            resultado,
    }


# ============================================================
# EXTRACCIÓN DEL PLAN BRIDGE003
# ============================================================


def _extraer_plan_bridge003(
    resultado: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Extrae únicamente un plan que haya sido validado.

    No aceptamos propuestas no certificadas.
    """

    validacion = resultado.get(
        "validacion_host"
    )

    if isinstance(
        validacion,
        dict,
    ):

        if (
            validacion.get(
                "ok"
            )
            is True
            and
            validacion.get(
                "plan_validado"
            )
            is True
            and
            isinstance(
                validacion.get(
                    "plan"
                ),
                dict,
            )
        ):

            return validacion[
                "plan"
            ]

    # Algunos contratos BRIDGE encapsulan la salida
    # inmediatamente debajo de otra clave.
    for clave in (
        "bridge",
        "resultado",
        "bridge003",
    ):

        contenido = resultado.get(
            clave
        )

        if not isinstance(
            contenido,
            dict,
        ):
            continue

        plan = _extraer_plan_bridge003(
            contenido
        )

        if plan is not None:

            return plan

    return None


def _estado_bridge003(
    resultado: dict[str, Any],
) -> str | None:

    estado = resultado.get(
        "estado"
    )

    if estado:

        return str(
            estado
        )

    for clave in (
        "bridge",
        "resultado",
        "bridge003",
    ):

        contenido = resultado.get(
            clave
        )

        if not isinstance(
            contenido,
            dict,
        ):
            continue

        estado = _estado_bridge003(
            contenido
        )

        if estado:

            return estado

    return None


# ============================================================
# CONSTRUCCIÓN DE PREGUNTA POR CLÁUSULA
# ============================================================


def _pregunta_para_condicion(
    prefijo: str,
    condicion: str,
) -> str:

    condicion = (
        _normalizar_condicion_relativa(
            condicion
        )
    )

    return _normalizar_espacios(
        f"{prefijo} {condicion}"
    )


# ============================================================
# QUERY001
# ============================================================


def construir_plan_and(
    pregunta: str,
    *,
    limite: int = LIMITE_MUESTRA_PREDETERMINADO,
) -> dict[str, Any]:
    """
    Construye un único plan AND a partir de varias
    condiciones simples.

    QUERY001:
        - no ejecuta ORM;
        - usa BRIDGE003 para cada condición;
        - vuelve a certificar el plan combinado con HOST;
        - falla cerrado ante cualquier condición no resuelta.
    """

    division = dividir_condiciones_and(
        pregunta
    )

    if not division.get(
        "ok",
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
                division.get(
                    "estado"
                ),

            "pregunta":
                pregunta,

            "razon":
                division.get(
                    "razon"
                ),

            "division":
                division,
        }

    condiciones = division[
        "condiciones"
    ]

    primera = condiciones[
        0
    ]

    prefijo, primera_condicion = (
        _separar_prefijo_y_primera_condicion(
            primera
        )
    )

    if not prefijo:

        return {
            "ok":
                False,

            "version":
                VERSION,

            "ejecutado":
                False,

            "estado":
                "prefijo_no_resuelto",

            "pregunta":
                pregunta,

            "razon":
                (
                    "No fue posible separar la operación "
                    "y entidad de la primera condición."
                ),

            "division":
                division,
        }

    condiciones_reales = [
        primera_condicion,
        *condiciones[
            1:
        ],
    ]

    resoluciones = []

    modelo_base = None
    operacion_base = None
    filtros_combinados = []

    callable_bridge003 = None

    for indice, condicion in enumerate(
        condiciones_reales
    ):

        pregunta_condicion = (
            _pregunta_para_condicion(
                prefijo,
                condicion,
            )
        )

        llamada = _invocar_bridge003(
            pregunta_condicion,
            limite=limite,
        )

        if callable_bridge003 is None:

            callable_bridge003 = (
                llamada.get(
                    "callable_bridge003"
                )
            )

        if not llamada.get(
            "ok",
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
                    "condicion_no_resuelta",

                "pregunta":
                    pregunta,

                "condicion_indice":
                    indice,

                "condicion":
                    condicion,

                "pregunta_condicion":
                    pregunta_condicion,

                "razon":
                    (
                        "No fue posible resolver "
                        f"la condición {indice + 1}."
                    ),

                "detalle":
                    llamada,

                "resoluciones":
                    resoluciones,
            }

        resultado_bridge = llamada[
            "resultado"
        ]

        plan = _extraer_plan_bridge003(
            resultado_bridge
        )

        if plan is None:

            return {
                "ok":
                    False,

                "version":
                    VERSION,

                "ejecutado":
                    False,

                "estado":
                    "condicion_no_resuelta",

                "pregunta":
                    pregunta,

                "condicion_indice":
                    indice,

                "condicion":
                    condicion,

                "pregunta_condicion":
                    pregunta_condicion,

                "estado_bridge":
                    _estado_bridge003(
                        resultado_bridge
                    ),

                "razon":
                    (
                        "BRIDGE003 no produjo un plan "
                        "HOST validado para una de las "
                        "condiciones."
                    ),

                "bridge003":
                    resultado_bridge,

                "resoluciones":
                    resoluciones,
            }

        modelo = plan.get(
            "modelo"
        )

        operacion = plan.get(
            "operacion"
        )

        filtros = plan.get(
            "filtros"
        )

        if not isinstance(
            filtros,
            list,
        ):

            return {
                "ok":
                    False,

                "version":
                    VERSION,

                "ejecutado":
                    False,

                "estado":
                    "filtros_invalidos",

                "pregunta":
                    pregunta,

                "condicion_indice":
                    indice,

                "razon":
                    (
                        "El plan individual no contiene "
                        "una lista válida de filtros."
                    ),
            }

        # Cada cláusula de QUERY001 debe producir
        # exactamente un filtro.
        if len(
            filtros
        ) != 1:

            return {
                "ok":
                    False,

                "version":
                    VERSION,

                "ejecutado":
                    False,

                "estado":
                    "condicion_no_atomica",

                "pregunta":
                    pregunta,

                "condicion_indice":
                    indice,

                "condicion":
                    condicion,

                "cantidad_filtros":
                    len(
                        filtros
                    ),

                "razon":
                    (
                        "QUERY001 requiere que cada "
                        "cláusula AND produzca exactamente "
                        "un filtro."
                    ),
            }

        if modelo_base is None:

            modelo_base = modelo
            operacion_base = operacion

        else:

            if modelo != modelo_base:

                return {
                    "ok":
                        False,

                    "version":
                        VERSION,

                    "ejecutado":
                        False,

                    "estado":
                        "modelos_incompatibles",

                    "pregunta":
                        pregunta,

                    "modelo_base":
                        modelo_base,

                    "modelo_condicion":
                        modelo,

                    "condicion_indice":
                        indice,

                    "razon":
                        (
                            "Las condiciones AND no "
                            "resolvieron al mismo modelo."
                        ),
                }

            if operacion != operacion_base:

                return {
                    "ok":
                        False,

                    "version":
                        VERSION,

                    "ejecutado":
                        False,

                    "estado":
                        "operaciones_incompatibles",

                    "pregunta":
                        pregunta,

                    "operacion_base":
                        operacion_base,

                    "operacion_condicion":
                        operacion,

                    "condicion_indice":
                        indice,

                    "razon":
                        (
                            "Las condiciones AND no "
                            "resolvieron a la misma "
                            "operación."
                        ),
                }

        filtros_combinados.extend(
            filtros
        )

        resoluciones.append(
            {
                "indice":
                    indice,

                "condicion":
                    condicion,

                "pregunta_condicion":
                    pregunta_condicion,

                "modelo":
                    modelo,

                "operacion":
                    operacion,

                "filtro":
                    filtros[
                        0
                    ],
            }
        )

    # ========================================================
    # PLAN COMBINADO
    # ========================================================

    propuesta_host = {
        "modelo":
            modelo_base,

        "operacion":
            operacion_base,

        "filtros":
            filtros_combinados,

        "orden":
            [],

        "limite":
            limite,

        "condiciones_no_resueltas":
            [],
    }

    # ========================================================
    # RECERTIFICACIÓN HOST
    # ========================================================

    validacion_host = validar_plan_datos(
        propuesta_host
    )

    if not (
        isinstance(
            validacion_host,
            dict,
        )
        and
        validacion_host.get(
            "ok"
        )
        is True
        and
        validacion_host.get(
            "plan_validado"
        )
        is True
    ):

        return {
            "ok":
                False,

            "version":
                VERSION,

            "ejecutado":
                False,

            "estado":
                "rechazado_por_host",

            "pregunta":
                pregunta,

            "modo":
                "and",

            "propuesta_host":
                propuesta_host,

            "validacion_host":
                validacion_host,

            "resoluciones":
                resoluciones,

            "razon":
                (
                    "Las condiciones individuales "
                    "fueron resueltas, pero HOST "
                    "rechazó el plan AND combinado."
                ),
        }

    return {
        "ok":
            True,

        "version":
            VERSION,

        "ejecutado":
            False,

        "estado":
            "plan_and_validado",

        "modo":
            "and",

        "pregunta":
            pregunta,

        "cantidad_condiciones":
            len(
                condiciones_reales
            ),

        "callable_bridge003":
            callable_bridge003,

        "propuesta_host":
            propuesta_host,

        "validacion_host":
            validacion_host,

        "plan":
            validacion_host.get(
                "plan"
            ),

        "resoluciones":
            resoluciones,

        "llm_invocado":
            False,

        "razon":
            (
                "QUERY001 construyó un plan AND "
                "y HOST certificó todas las "
                "condiciones."
            ),
    }