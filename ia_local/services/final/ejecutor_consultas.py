from __future__ import annotations

from typing import Any

from ia_local.services.final.contrato_respuesta import (
    construir_contrato_respuesta,
)

from ia_local.services.host.ejecutor_datos import (
    ejecutar_plan_datos,
)

from ia_local.services.host.orquestador_plan_unificado import (
    ejecutar_plan_unificado_datos,
)


# ============================================================
# IA-FINAL003
# EJECUCIÓN SEGURA DE CONSULTAS
# ============================================================
#
# Responsabilidad:
#
#   recibir una pregunta natural, obtener el contrato FINAL002
#   y ejecutar únicamente contratos que hoy tienen un ejecutor
#   HOST real y autorizado.
#
# FINAL003:
#
#   - NO ejecuta ORM directamente;
#   - NO construye QuerySets;
#   - NO usa django.db;
#   - NO usa LLM;
#   - NO inventa modelos/campos/rutas;
#   - delega toda ejecución en HOST.
#
# ============================================================


VERSION = "IA-FINAL003-v1"


EJECUTORES_PERMITIDOS = {
    "ejecutor_datos",
    "orquestador_plan_unificado",
}


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
    mensaje: str,
    contrato_final: dict[str, Any] | None = None,
) -> dict[str, Any]:

    return {
        "ok": False,
        "version": VERSION,
        "estado": estado,
        "pregunta": pregunta,
        "ejecutado": False,
        "llm_invocado": bool(
            isinstance(
                contrato_final,
                dict,
            )
            and contrato_final.get(
                "llm_invocado"
            )
        ),
        "mensaje": mensaje,
        "contrato_final": contrato_final,
        "resultado": None,
    }


def _ejecutar_contrato(
    contrato_final: dict[str, Any],
) -> dict[str, Any]:

    tipo_contrato = _texto(
        contrato_final.get(
            "tipo_contrato"
        )
    )

    ejecutor = _texto(
        contrato_final.get(
            "ejecutor_sugerido"
        )
    )

    contrato = contrato_final.get(
        "contrato"
    )

    if not isinstance(
        contrato,
        dict,
    ):

        return {
            "ok": False,
            "ejecutado": False,
            "fase": "contrato",
            "errores": [
                "El contrato FINAL002 no contiene una estructura ejecutable."
            ],
            "llm_invocado": False,
        }

    # --------------------------------------------------------
    # PLAN HOST ORDINARIO
    # --------------------------------------------------------

    if (
        tipo_contrato == "plan_host"
        and ejecutor == "ejecutor_datos"
    ):

        return ejecutar_plan_datos(
            contrato
        )

    # --------------------------------------------------------
    # PLAN UNIFICADO HOST033
    # --------------------------------------------------------

    if (
        tipo_contrato == "plan_unificado"
        and ejecutor == "orquestador_plan_unificado"
    ):

        return ejecutar_plan_unificado_datos(
            contrato
        )

    return {
        "ok": False,
        "ejecutado": False,
        "fase": "dispatch",
        "errores": [
            (
                "El tipo de contrato no dispone todavía "
                "de un ejecutor FINAL autorizado."
            )
        ],
        "tipo_contrato": tipo_contrato,
        "ejecutor_sugerido": ejecutor or None,
        "llm_invocado": False,
    }


def ejecutar_consulta(
    pregunta: str,
    *,
    entidad_aclarada: str | None = None,
) -> dict[str, Any]:

    pregunta = _texto(
        pregunta
    )

    if not pregunta:

        return _error(
            pregunta=pregunta,
            estado="pregunta_vacia",
            mensaje="La consulta está vacía.",
        )

    contrato_final = (
        construir_contrato_respuesta(
            pregunta,
            entidad_aclarada=entidad_aclarada,
        )
    )

    if not contrato_final.get(
        "ok"
    ):

        return _error(
            pregunta=pregunta,
            estado="contrato_no_disponible",
            mensaje=(
                "FINAL002 no pudo construir "
                "un contrato válido."
            ),
            contrato_final=contrato_final,
        )

    if not contrato_final.get(
        "ejecutable"
    ):

        return {
            "ok": False,
            "version": VERSION,

            "estado":
                "contrato_no_ejecutable",

            "pregunta":
                pregunta,

            "intencion":
                contrato_final.get(
                    "intencion"
                ),

            "componente":
                contrato_final.get(
                    "componente"
                ),

            "modelo":
                contrato_final.get(
                    "modelo"
                ),

            "tipo_contrato":
                contrato_final.get(
                    "tipo_contrato"
                ),

            "ejecutor":
                contrato_final.get(
                    "ejecutor_sugerido"
                ),

            "ejecutado":
                False,

            "llm_invocado":
                bool(
                    contrato_final.get(
                        "llm_invocado"
                    )
                ),

            "resultado":
                None,

            "contrato_final":
                contrato_final,

            "mensaje": (
                "La consulta fue interpretada correctamente, "
                "pero este tipo de contrato todavía no dispone "
                "de un ejecutor HOST habilitado."
            ),
        }

    ejecutor = _texto(
        contrato_final.get(
            "ejecutor_sugerido"
        )
    )

    if ejecutor not in EJECUTORES_PERMITIDOS:

        return _error(
            pregunta=pregunta,
            estado="ejecutor_no_permitido",
            mensaje=(
                "FINAL003 rechazó un ejecutor "
                "fuera de la lista blanca."
            ),
            contrato_final=contrato_final,
        )

    # ARC002-C08-B04: barrera negativa previa al despacho.
    # No autoriza semantica ni modifica los contratos HOST.
    if contrato_final.get("tipo_contrato") in (
        "plan_host",
        "plan_unificado",
    ):
        try:
            from ia_local.services.llm.auditoria_sustituciones import (
                auditar_sustituciones_semanticas,
            )

            auditoria_negativa = auditar_sustituciones_semanticas(
                pregunta,
                contrato_final.get("contrato"),
            )

            # ARC002-C08-B05:
            # Una negacion detectada no puede avanzar sin
            # certificacion semantica integral independiente.
            # Los indicadores del propio plan no la certifican.
            if (
                auditoria_negativa.get("ok") is not True
                or auditoria_negativa.get("discrepancias")
                or auditoria_negativa.get(
                    "negacion_original_detectada"
                ) is True
            ):
                return _error(
                    pregunta=pregunta,
                    estado="revision_semantica_negativa_pendiente",
                    mensaje=(
                        "La representacion de las negaciones "
                        "requiere revision antes de ejecutar."
                    ),
                    contrato_final=contrato_final,
                )

        except Exception:
            return _error(
                pregunta=pregunta,
                estado="auditoria_negativa_no_disponible",
                mensaje=(
                    "No fue posible completar la auditoria "
                    "preventiva antes del despacho."
                ),
                contrato_final=contrato_final,
            )

    resultado = _ejecutar_contrato(
        contrato_final
    )

    if not isinstance(
        resultado,
        dict,
    ):

        return _error(
            pregunta=pregunta,
            estado="resultado_host_invalido",
            mensaje=(
                "HOST devolvió una estructura "
                "de resultado no válida."
            ),
            contrato_final=contrato_final,
        )

    ok_host = (
        resultado.get(
            "ok"
        )
        is True
    )

    ejecutado_host = (
        resultado.get(
            "ejecutado"
        )
        is True
    )

    return {
        "ok":
            ok_host,

        "version":
            VERSION,

        "estado": (
            "consulta_ejecutada"
            if (
                ok_host
                and ejecutado_host
            )
            else "ejecucion_host_rechazada"
        ),

        "pregunta":
            pregunta,

        "intencion":
            contrato_final.get(
                "intencion"
            ),

        "intencion_operacional":
            contrato_final.get(
                "intencion_operacional"
            ),

        "componente":
            contrato_final.get(
                "componente"
            ),

        "componente_version":
            contrato_final.get(
                "componente_version"
            ),

        "modelo":
            contrato_final.get(
                "modelo"
            ),

        "tipo_contrato":
            contrato_final.get(
                "tipo_contrato"
            ),

        "ejecutor":
            ejecutor,

        "ejecutado":
            ejecutado_host,

        "llm_invocado":
            bool(
                contrato_final.get(
                    "llm_invocado"
                )
            ),

        "resultado":
            resultado,

        "contrato_final":
            contrato_final,

        "mensaje": (
            "Consulta ejecutada mediante HOST."
            if (
                ok_host
                and ejecutado_host
            )
            else (
                "HOST rechazó o no pudo completar "
                "la ejecución."
            )
        ),
    }