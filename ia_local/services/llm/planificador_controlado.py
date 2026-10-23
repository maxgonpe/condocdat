from __future__ import annotations

from typing import Any

from ia_local.services.host.resolvedor_entidad_datos import (
    resolver_entidad_datos,
)

from ia_local.services.host.desambiguacion_controlada import (
    verificar_eleccion,
)

from ia_local.services.host.interprete_datos import (
    interpretar_consulta_datos,
)

from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)


# ============================================================
# IA-LLM001
# PLANIFICADOR QWEN CONTROLADO
# ============================================================
#
# Responsabilidad:
#
#   transformar una pregunta natural que no pudo ser resuelta
#   determinísticamente en un PLAN HOST VALIDADO.
#
# IA-LLM001:
#
#   - puede usar Qwen;
#   - puede consultar evidencia HOST para resolver entidad;
#   - NO ejecuta el plan resultante;
#   - NO llama ejecutar_plan_datos;
#   - NO construye QuerySets;
#   - NO genera SQL;
#   - NO ejecuta ORM arbitrario;
#   - NO modifica datos;
#   - HOST conserva autoridad sobre modelo, campo, operador,
#     orden, límite y contrato final.
#
# ============================================================


VERSION = "IA-LLM001-v1"


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
    llm_invocado: bool = False,
    **extra: Any,
) -> dict[str, Any]:

    salida = {
        "ok":
            False,

        "version":
            VERSION,

        "estado":
            estado,

        "pregunta":
            pregunta,

        "plan_validado":
            False,

        "ejecutable":
            False,

        "ejecutado":
            False,

        "llm_invocado":
            bool(
                llm_invocado
            ),

        "razon":
            razon,

        "plan":
            None,
    }

    salida.update(
        extra
    )

    return salida


def construir_plan_llm(
    pregunta: str,
    *,
    entidad_aclarada: str | None = None,
) -> dict[str, Any]:
    """
    IA-LLM001.

    Produce exclusivamente un plan HOST validado.

    NO ejecuta el plan.
    """

    pregunta = _texto(
        pregunta
    )

    if not pregunta:

        return _error(
            pregunta=pregunta,
            estado="pregunta_vacia",
            razon=(
                "La pregunta está vacía."
            ),
        )

    # ========================================================
    # 1. RESOLUCIÓN DE ENTIDAD
    # ========================================================

    # IA-LLM007-F3-02 - REANUDACION CERTIFICADA
    # La vía antigua no cambia cuando entidad_aclarada es None.
    if entidad_aclarada is None:
        resolucion_entidad = resolver_entidad_datos(pregunta)
    else:
        # Una etiqueta externa nunca se acepta sin recertificar la ambiguedad.
        seleccion = verificar_eleccion(pregunta, entidad_aclarada)
        if seleccion.get("ok") is not True or seleccion.get("entidad_seleccionada") != entidad_aclarada:
            return _error(
                pregunta=pregunta,
                estado="eleccion_no_certificada",
                razon="La entidad seleccionada no pertenece a las alternativas certificadas de la pregunta.",
                entidad_aclarada=entidad_aclarada,
            )
        resolucion_entidad = {
            "ok": True,
            "resuelto": True,
            "entidad": entidad_aclarada,
            "estado_resolucion": "resuelto",
            "tipo_evidencia": "aclaracion_usuario_certificada",
            "tipo_evidencia_normalizada": "aclaracion_usuario_certificada",
            "confianza": {"nivel": "alta", "metodo": "aclaracion_usuario_certificada", "puntaje": None, "margen": None},
            "razon": "Eleccion explicita recertificada por HOST para esta pregunta.",
            "pregunta_original": pregunta,
        }


    if not isinstance(
        resolucion_entidad,
        dict,
    ):

        return _error(
            pregunta=pregunta,
            estado="resolucion_entidad_invalida",
            razon=(
                "HOST no devolvió una resolución "
                "de entidad válida."
            ),
            resolucion_entidad=None,
        )

    if (
        resolucion_entidad.get(
            "resuelto"
        )
        is not True
    ):

        return _error(
            pregunta=pregunta,
            estado="entidad_no_resuelta",
            razon=(
                resolucion_entidad.get(
                    "razon"
                )
                or (
                    "No existe una entidad suficientemente "
                    "demostrada para invocar el intérprete LLM."
                )
            ),
            resolucion_entidad=(
                resolucion_entidad
            ),
        )

    modelo = _texto(
        resolucion_entidad.get(
            "entidad"
        )
    )

    if not modelo:

        return _error(
            pregunta=pregunta,
            estado="entidad_no_resuelta",
            razon=(
                "La resolución HOST no produjo "
                "un modelo utilizable."
            ),
            resolucion_entidad=(
                resolucion_entidad
            ),
        )

    # ========================================================
    # 2. INTERPRETACIÓN QWEN
    # ========================================================

    interpretacion = (
        interpretar_consulta_datos(
            pregunta,
            modelo=modelo,
            evidencia_entidad=(
                resolucion_entidad
            ),
        )
    )

    if not isinstance(
        interpretacion,
        dict,
    ):

        return _error(
            pregunta=pregunta,
            estado="interpretacion_invalida",
            razon=(
                "El intérprete LLM devolvió una "
                "estructura inválida."
            ),
            llm_invocado=True,
            modelo=modelo,
            resolucion_entidad=(
                resolucion_entidad
            ),
        )

    llm_invocado = bool(
        interpretacion.get(
            "llm_invocado"
        )
    )

    if (
        interpretacion.get(
            "ok"
        )
        is not True
    ):

        return _error(
            pregunta=pregunta,
            estado="interpretacion_llm_rechazada",
            razon=(
                "Qwen no produjo una propuesta "
                "de consulta utilizable."
            ),
            llm_invocado=(
                llm_invocado
            ),
            modelo=modelo,
            resolucion_entidad=(
                resolucion_entidad
            ),
            interpretacion=(
                interpretacion
            ),
        )

    propuesta = interpretacion.get(
        "propuesta"
    )

    if not isinstance(
        propuesta,
        dict,
    ):

        return _error(
            pregunta=pregunta,
            estado="propuesta_llm_invalida",
            razon=(
                "La interpretación no contiene "
                "una propuesta declarativa válida."
            ),
            llm_invocado=(
                llm_invocado
            ),
            modelo=modelo,
            resolucion_entidad=(
                resolucion_entidad
            ),
            interpretacion=(
                interpretacion
            ),
        )

    # La interpretacion de Qwen no puede reemplazar la entidad aclarada.
    if entidad_aclarada is not None and propuesta.get("modelo") != modelo:
        return _error(
            pregunta=pregunta,
            estado="entidad_aclarada_alterada_por_llm",
            razon="Qwen propuso una entidad distinta de la elegida y certificada.",
            llm_invocado=llm_invocado,
            resolucion_entidad=resolucion_entidad,
            interpretacion=interpretacion,
        )

    # ========================================================
    # 3. VALIDACIÓN HOST
    # ========================================================

    validacion = (
        validar_plan_datos(
            propuesta
        )
    )

    if not isinstance(
        validacion,
        dict,
    ):

        return _error(
            pregunta=pregunta,
            estado="validacion_host_invalida",
            razon=(
                "HOST devolvió una validación "
                "de plan inválida."
            ),
            llm_invocado=(
                llm_invocado
            ),
            modelo=modelo,
            resolucion_entidad=(
                resolucion_entidad
            ),
            interpretacion=(
                interpretacion
            ),
        )

    if (
        validacion.get(
            "ok"
        )
        is not True
    ):

        errores = validacion.get(
            "errores",
            [],
        )

        return _error(
            pregunta=pregunta,
            estado="plan_llm_rechazado_por_host",
            razon=(
                "Qwen produjo una propuesta, "
                "pero HOST no la certificó."
            ),
            llm_invocado=(
                llm_invocado
            ),
            modelo=modelo,
            resolucion_entidad=(
                resolucion_entidad
            ),
            interpretacion=(
                interpretacion
            ),
            validacion=(
                validacion
            ),
            errores=(
                errores
            ),
        )

    plan = validacion.get(
        "plan"
    )

    if not isinstance(
        plan,
        dict,
    ):

        return _error(
            pregunta=pregunta,
            estado="plan_host_ausente",
            razon=(
                "HOST aprobó la validación pero "
                "no devolvió un plan certificado."
            ),
            llm_invocado=(
                llm_invocado
            ),
            modelo=modelo,
            resolucion_entidad=(
                resolucion_entidad
            ),
            interpretacion=(
                interpretacion
            ),
            validacion=(
                validacion
            ),
        )

    # HOST valido un plan, pero tambien debe conservar la entidad elegida.
    if entidad_aclarada is not None and plan.get("modelo") != modelo:
        return _error(
            pregunta=pregunta,
            estado="entidad_aclarada_alterada_en_plan",
            razon="El plan final no conserva la entidad certificada.",
            llm_invocado=llm_invocado,
            resolucion_entidad=resolucion_entidad,
            validacion=validacion,
        )

    # ========================================================
    # 4. SALIDA CERTIFICADA
    # ========================================================

    return {
        "ok":
            True,

        "version":
            VERSION,

        "estado":
            "plan_llm_validado",

        "pregunta":
            pregunta,

        "modelo":
            modelo,

        "plan_validado":
            True,

        "ejecutable":
            True,

        # IA-LLM001 TERMINA AQUÍ.
        "ejecutado":
            False,

        "llm_invocado":
            llm_invocado,

        "plan":
            plan,

        "resolucion_entidad":
            resolucion_entidad,

        "interpretacion":
            interpretacion,

        "intencion_operacional":
            interpretacion.get(
                "intencion_operacional"
            ),

        "validacion":
            validacion,
    }