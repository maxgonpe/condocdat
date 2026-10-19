from __future__ import annotations

from typing import Any

from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)

from ia_local.services.semantica.politica_prioridad import (
    resolver_con_politica,
)


VERSION = "IA-BRIDGE001-v1"

LIMITE_PREDETERMINADO = 20


# ============================================================
# UTILIDADES
# ============================================================


def _construir_filtros_desde_condiciones(
    condiciones: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Traduce condiciones SEM005 al contrato de filtros
    que espera HOST.

    No valida estructura Django aquí:
    HOST vuelve a hacerlo mediante validar_plan_datos().
    """

    filtros = []

    for condicion in condiciones:

        if not isinstance(
            condicion,
            dict,
        ):
            continue

        filtros.append(
            {
                "campo":
                    condicion.get(
                        "campo"
                    ),

                "operador":
                    condicion.get(
                        "operador",
                        "exact",
                    ),

                "valor":
                    condicion.get(
                        "valor"
                    ),
            }
        )

    return filtros


def _construir_propuesta_host(
    resultado_sem: dict[str, Any],
    *,
    limite: int | None = LIMITE_PREDETERMINADO,
) -> dict[str, Any]:
    """
    Convierte una regla declarativa SEM005 en
    una propuesta compatible con HOST014/HOST015.
    """

    condiciones = resultado_sem.get(
        "condiciones",
        [],
    )

    if not isinstance(
        condiciones,
        list,
    ):
        condiciones = []

    return {
        "modelo":
            resultado_sem.get(
                "modelo"
            ),

        "operacion":
            resultado_sem.get(
                "operacion",
                "listar",
            ),

        "filtros":
            _construir_filtros_desde_condiciones(
                condiciones
            ),

        "orden":
            [],

        "limite":
            limite,

        "condiciones_no_resueltas":
            [],
    }


# ============================================================
# ADAPTADOR PRINCIPAL
# ============================================================


def adaptar_sem_a_host(
    expresion: str,
    *,
    modelo_contexto: str | None = None,
    campo_contexto: str | None = None,
    limite: int | None = LIMITE_PREDETERMINADO,
) -> dict[str, Any]:
    """
    IA-BRIDGE001.

    Convierte una resolución semántica completa en una
    propuesta de plan HOST y solicita a HOST que la valide.

    NO ejecuta ORM.
    NO invoca LLM.
    """

    resolucion_sem = resolver_con_politica(
        expresion,
        modelo_contexto=modelo_contexto,
        campo_contexto=campo_contexto,
        incluir_reglas=True,
    )

    base = {
        "ok":
            False,

        "version":
            VERSION,

        "expresion":
            expresion,

        "llm_invocado":
            False,

        "sem":
            resolucion_sem,

        "propuesta_host":
            None,

        "validacion_host":
            None,

        "ejecutado":
            False,
    }

    # --------------------------------------------------------
    # ERROR SEM
    # --------------------------------------------------------

    if not resolucion_sem.get(
        "ok",
        False,
    ):

        return {
            **base,

            "estado":
                "error_sem",

            "razon":
                (
                    "SEM no pudo procesar de forma "
                    "válida la expresión."
                ),
        }

    estado_sem = resolucion_sem.get(
        "estado"
    )

    # --------------------------------------------------------
    # AMBIGÜEDAD
    # --------------------------------------------------------

    if estado_sem == "ambiguo":

        return {
            **base,

            "estado":
                "sem_ambiguo",

            "razon":
                (
                    "La expresión tiene más de una "
                    "interpretación semántica y requiere "
                    "contexto antes de construir un plan HOST."
                ),
        }

    # --------------------------------------------------------
    # NO RESUELTO
    # --------------------------------------------------------

    if estado_sem == "no_resuelto":

        return {
            **base,

            "estado":
                "sem_no_resuelto",

            "razon":
                (
                    "SEM no dispone de conocimiento suficiente "
                    "para construir un plan."
                ),
        }

    # --------------------------------------------------------
    # RESULTADO SEM
    # --------------------------------------------------------

    resultado_sem = resolucion_sem.get(
        "resultado"
    )

    if not isinstance(
        resultado_sem,
        dict,
    ):

        return {
            **base,

            "estado":
                "resultado_sem_invalido",

            "razon":
                (
                    "SEM indicó resolución, pero no entregó "
                    "un resultado estructurado."
                ),
        }

    tipo_sem = resultado_sem.get(
        "tipo"
    )

    # --------------------------------------------------------
    # POR AHORA SÓLO REGLAS COMPLETAS
    # --------------------------------------------------------

    if tipo_sem != "regla_declarativa":

        return {
            **base,

            "estado":
                "sem_resuelto_sin_plan_completo",

            "tipo_sem":
                tipo_sem,

            "razon":
                (
                    "La expresión fue resuelta semánticamente, "
                    "pero todavía no contiene todos los "
                    "componentes necesarios para construir "
                    "una consulta HOST completa."
                ),
        }

    # --------------------------------------------------------
    # CONSTRUIR PROPUESTA HOST
    # --------------------------------------------------------

    propuesta_host = _construir_propuesta_host(
        resultado_sem,
        limite=limite,
    )

    base[
        "propuesta_host"
    ] = propuesta_host

    # --------------------------------------------------------
    # VALIDAR MEDIANTE HOST
    # --------------------------------------------------------

    validacion_host = validar_plan_datos(
        propuesta_host
    )

    base[
        "validacion_host"
    ] = validacion_host

    if not validacion_host.get(
        "plan_validado",
        False,
    ):

        return {
            **base,

            "estado":
                "rechazado_por_host",

            "razon":
                (
                    "SEM produjo una interpretación completa, "
                    "pero HOST rechazó el plan durante su "
                    "validación estructural."
                ),
        }

    # --------------------------------------------------------
    # ÉXITO
    # --------------------------------------------------------

    return {
        **base,

        "ok":
            True,

        "estado":
            "plan_host_validado",

        "plan_host":
            validacion_host.get(
                "plan"
            ),

        "razon":
            (
                "La resolución SEM fue adaptada y validada "
                "correctamente por HOST sin ejecutar ORM."
            ),
    }