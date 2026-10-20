from __future__ import annotations

from typing import Any, Callable


from ia_local.services.bridge.campo_operador_valor import (
    componer_campo_operador_valor,
)

from ia_local.services.query.condiciones_and import (
    construir_plan_and,
)

from ia_local.services.query.condiciones_or import (
    componer_condiciones_or,
)

from ia_local.services.query.grupos_logicos import (
    componer_grupos_logicos,
)

from ia_local.services.query.ordenamiento_natural import (
    componer_ordenamiento_natural,
)

from ia_local.services.query.fechas_absolutas import (
    componer_fechas_absolutas,
)

from ia_local.services.query.fechas_relativas import (
    componer_fechas_relativas,
)

from ia_local.services.query.relaciones_orm import (
    componer_relacion_orm,
)

from ia_local.services.query.colecciones_estructuras import (
    describir_coleccion_natural,
)

from ia_local.services.query.agregaciones import (
    componer_agregacion,
)

from ia_local.services.query.agrupamientos import (
    componer_agrupamiento,
)

from ia_local.services.query.consultas_relacionales import (
    componer_consulta_relacional,
)


# ============================================================
# IA-FINAL001
# ORQUESTADOR ÚNICO DE INTERPRETACIÓN
# ============================================================
#
# Responsabilidad:
#
#   recibir una pregunta natural y determinar cuál de las
#   capacidades BRIDGE / QUERY existentes puede resolverla.
#
# FINAL001:
#
#   - NO ejecuta ORM;
#   - NO genera SQL;
#   - NO usa LLM;
#   - NO modifica datos;
#   - NO reemplaza HOST;
#   - NO inventa modelos, campos ni relaciones;
#   - NO duplica la lógica interna de QUERY.
#
# Cada componente conserva su autoridad.
#
# ============================================================


VERSION = "IA-FINAL001-v1"


def _texto(
    valor: Any,
) -> str:

    return str(
        valor or ""
    ).strip()


def _error(
    *,
    pregunta: str,
    estado: str,
    razon: str,
    **extra: Any,
) -> dict[str, Any]:

    salida = {
        "ok": False,
        "version": VERSION,
        "estado": estado,
        "pregunta": pregunta,
        "resuelto": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
        "razon": razon,
    }

    salida.update(
        extra
    )

    return salida


# ============================================================
# EXTRACCIÓN DE PLAN
# ============================================================


def _extraer_plan(
    resultado: dict[str, Any],
) -> tuple[
    dict[str, Any] | None,
    str | None,
]:

    if not isinstance(
        resultado,
        dict,
    ):

        return None, None

    # --------------------------------------------------------
    # HOST033 / QUERY011
    # --------------------------------------------------------

    plan_unificado = resultado.get(
        "plan_unificado"
    )

    if isinstance(
        plan_unificado,
        dict,
    ):

        return (
            plan_unificado,
            "plan_unificado",
        )

    # --------------------------------------------------------
    # QUERY005 / QUERY006 / QUERY004...
    # --------------------------------------------------------

    plan = resultado.get(
        "plan"
    )

    if isinstance(
        plan,
        dict,
    ):

        return (
            plan,
            "plan",
        )

    # --------------------------------------------------------
    # BRIDGE003
    # --------------------------------------------------------

    plan_host = resultado.get(
        "plan_host"
    )

    if isinstance(
        plan_host,
        dict,
    ):

        return (
            plan_host,
            "plan_host",
        )

    validacion_host = resultado.get(
        "validacion_host"
    )

    if isinstance(
        validacion_host,
        dict,
    ):

        plan_validado = (
            validacion_host.get(
                "plan"
            )
        )

        if isinstance(
            plan_validado,
            dict,
        ):

            return (
                plan_validado,
                "validacion_host.plan",
            )

    return None, None


# ============================================================
# EJECUTABILIDAD
# ============================================================


def _es_ejecutable(
    *,
    resultado: dict[str, Any],
    tipo_plan: str | None,
) -> bool:

    # --------------------------------------------------------
    # Un plan unificado HOST033 ya declara explícitamente
    # si existe un ejecutor autorizado.
    # --------------------------------------------------------

    if (
        tipo_plan
        == "plan_unificado"
    ):

        ejecucion = resultado.get(
            "plan_unificado",
            {},
        ).get(
            "ejecucion",
            {},
        )

        return (
            isinstance(
                ejecucion,
                dict,
            )
            and ejecucion.get(
                "permitida"
            )
            is True
        )

    # --------------------------------------------------------
    # Los planes HOST ordinarios pueden ser ejecutables
    # posteriormente por la capa FINAL003.
    #
    # FINAL001 NO los ejecuta.
    # --------------------------------------------------------

    if tipo_plan in {
        "plan",
        "plan_host",
        "validacion_host.plan",
    }:

        return True

    return False


# ============================================================
# CATÁLOGO DE MOTORES
# ============================================================


def _motores() -> list[
    tuple[
        str,
        str,
        Callable[
            [str],
            dict[str, Any],
        ],
    ]
]:

    # --------------------------------------------------------
    # El orden es intencional:
    #
    # primero las gramáticas más específicas;
    # al final BRIDGE003 como consulta simple.
    # --------------------------------------------------------

    return [
        (
            "consulta_relacional",
            "IA-QUERY011",
            componer_consulta_relacional,
        ),
        (
            "agrupamiento",
            "IA-QUERY010",
            componer_agrupamiento,
        ),
        (
            "agregacion",
            "IA-QUERY009",
            componer_agregacion,
        ),
        (
            "fecha_relativa",
            "IA-QUERY006",
            componer_fechas_relativas,
        ),
        (
            "fecha_absoluta",
            "IA-QUERY005",
            componer_fechas_absolutas,
        ),
        (
            "ordenamiento",
            "IA-QUERY004",
            componer_ordenamiento_natural,
        ),
        
        (
            "condiciones_or",
            "IA-QUERY002",
            componer_condiciones_or,
        ),
        (
            "condiciones_and",
            "IA-QUERY001",
            construir_plan_and,
        ),
        (
            "grupo_logico",
            "IA-QUERY003",
            componer_grupos_logicos,
        ),
        (
            "coleccion",
            "IA-QUERY008",
            describir_coleccion_natural,
        ),
        (
            "relacion",
            "IA-QUERY007",
            componer_relacion_orm,
        ),
        (
            "consulta_simple",
            "IA-BRIDGE003",
            componer_campo_operador_valor,
        ),
    ]


# ============================================================
# API PÚBLICA
# ============================================================


def resolver_consulta(
    pregunta: str,
) -> dict[str, Any]:

    pregunta = _texto(
        pregunta
    )

    if not pregunta:

        return _error(
            pregunta=pregunta,
            estado="pregunta_vacia",
            razon="La consulta está vacía.",
        )

    intentos: list[
        dict[str, Any]
    ] = []

    for (
        intencion,
        componente,
        resolver,
    ) in _motores():

        try:

            resultado = resolver(
                pregunta
            )

        except Exception as exc:

            # ------------------------------------------------
            # Un componente que no puede procesar una forma
            # concreta no debe derribar el orquestador.
            # ------------------------------------------------

            intentos.append(
                {
                    "intencion":
                        intencion,

                    "componente":
                        componente,

                    "ok":
                        False,

                    "estado":
                        "excepcion_controlada",

                    "error":
                        str(
                            exc
                        ),
                }
            )

            continue

        if not isinstance(
            resultado,
            dict,
        ):

            intentos.append(
                {
                    "intencion":
                        intencion,

                    "componente":
                        componente,

                    "ok":
                        False,

                    "estado":
                        "resultado_invalido",
                }
            )

            continue

        intentos.append(
            {
                "intencion":
                    intencion,

                "componente":
                    componente,

                "ok":
                    resultado.get(
                        "ok"
                    ),

                "estado":
                    resultado.get(
                        "estado"
                    ),

                "version":
                    resultado.get(
                        "version"
                    ),
            }
        )

        # ----------------------------------------------------
        # Sólo una resolución afirmativa puede ganar.
        # Los rechazos seguros de cada QUERY simplemente
        # permiten probar el siguiente componente.
        # ----------------------------------------------------

        if (
            resultado.get(
                "ok"
            )
            is not True
        ):

            continue

        plan, tipo_plan = (
            _extraer_plan(
                resultado
            )
        )

        ejecutable = (
            _es_ejecutable(
                resultado=resultado,
                tipo_plan=tipo_plan,
            )
        )

        return {
            "ok": True,
            "version": VERSION,

            "estado":
                "consulta_interpretada",

            "pregunta":
                pregunta,

            "resuelto":
                True,

            "intencion":
                intencion,

            "componente":
                componente,

            "componente_version":
                resultado.get(
                    "version"
                ),

            "ejecutable":
                ejecutable,

            "tipo_plan":
                tipo_plan,

            "plan_ejecutable":
                plan,

            "resultado_interpretacion":
                resultado,

            "intentos":
                intentos,

            "ejecutado":
                False,

            "llm_invocado":
                False,

            "razon": (
                "FINAL001 seleccionó una capacidad "
                "determinista existente sin ejecutar ORM."
            ),
        }

    return _error(
        pregunta=pregunta,
        estado="consulta_no_resuelta",
        razon=(
            "Ningún componente BRIDGE/QUERY pudo "
            "resolver la consulta de forma segura."
        ),
        intentos=intentos,
    )