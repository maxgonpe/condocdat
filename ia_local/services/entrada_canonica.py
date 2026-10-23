"""
IA-ARC001-B01

Contrato de entrada canonica de ia_local.

Esta version NO interpreta ni ejecuta consultas.
No invoca HOST, BRIDGE, QUERY, LLM ni FINAL.

La autorizacion y ejecucion se integraran en ARC001-B02.
"""

VERSION = "IA-ARC001-C03-v1"


def _respuesta(pregunta, estado, *, contexto_valido=False):
    return {
        "version": VERSION,
        "pregunta_original": pregunta,
        "estado": estado,
        "ok": False,
        "resuelto": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
        "contexto_valido": contexto_valido,
        "interpretacion": None,
        "certificacion": None,
        "resultado": None,
        "diagnostico": {
            "componente": "IA-ARC001-B01",
            "ejecucion_habilitada": False,
        },
    }


def procesar_consulta_canonica(
    request,
    pregunta,
    *,
    contexto=None,
    modo="inspeccionar",
):
    """
    Valida la entrada sin producir efectos secundarios.

    En B01 el contexto externo no esta habilitado.
    Solo se admite el modo inspeccionar, sin ejecucion.
    """

    if not isinstance(pregunta, str):
        return _respuesta(
            "",
            "pregunta_invalida",
        )

    if not pregunta.strip():
        return _respuesta(
            pregunta,
            "pregunta_vacia",
        )

    if len(pregunta) > 10000:
        return _respuesta(
            pregunta,
            "pregunta_demasiado_larga",
        )

    if modo not in ("inspeccionar", "preparar"):
        return _respuesta(
            pregunta,
            "modo_no_habilitado",
        )

    # Los metadatos externos no pueden autorizar
    # planes, permisos o certificaciones.
    if contexto is not None:
        return _respuesta(
            pregunta,
            "contexto_no_habilitado",
        )

    if request is None:
        return _respuesta(
            pregunta,
            "request_invalido",
        )

    usuario = getattr(request, "user", None)

    if (
        usuario is None
        or getattr(usuario, "is_authenticated", False)
        is not True
    ):
        return _respuesta(
            pregunta,
            "identidad_no_autenticada",
        )

    if getattr(usuario, "pk", None) is None:
        return _respuesta(
            pregunta,
            "identidad_invalida",
        )

    sesion = getattr(request, "session", None)

    if sesion is None:
        return _respuesta(
            pregunta,
            "sesion_no_disponible",
        )

    clave = getattr(sesion, "session_key", None)

    if not isinstance(clave, str) or not clave:
        return _respuesta(
            pregunta,
            "sesion_no_identificada",
        )

    if modo == "preparar":
        # Importacion diferida: inspeccionar no invoca Qwen.
        from ia_local.services.host.preparador_consulta_datos import (
            preparar_consulta_datos,
        )

        try:
            preparado = preparar_consulta_datos(pregunta)
        except Exception:
            return _respuesta(
                pregunta,
                "error_preparacion",
                contexto_valido=True,
            )

        if not isinstance(preparado, dict):
            return _respuesta(
                pregunta,
                "preparacion_invalida",
                contexto_valido=True,
            )

        if (
            preparado.get("ok") is not True
            or preparado.get("estado") != "plan_host_preparado"
            or preparado.get("ejecutado") is not False
            or preparado.get("ejecutable") is not False
            or preparado.get("certificacion_semantica") is not False
        ):
            respuesta = _respuesta(
                pregunta,
                "preparacion_no_disponible",
                contexto_valido=True,
            )
            respuesta["diagnostico"]["estado_host"] = (
                preparado.get("estado")
            )
            return respuesta

        plan = preparado.get("plan")

        if (
            not isinstance(plan, dict)
            or plan.get("modelo") != preparado.get("modelo")
            or not isinstance(preparado.get("interpretacion"), dict)
        ):
            return _respuesta(
                pregunta,
                "plan_preparado_invalido",
                contexto_valido=True,
            )

        respuesta = _respuesta(
            pregunta,
            "pendiente_certificacion_semantica",
            contexto_valido=True,
        )

        # ARC001-C03: auditoria negativa, nunca autorizacion.
        from ia_local.services.llm.auditor_preparacion import (
            auditar_plan_preparado,
        )

        try:
            auditoria = auditar_plan_preparado(
                pregunta,
                plan,
            )
        except Exception:
            auditoria = {
                "estado": "revision_pendiente",
                "pendientes": ["error_auditoria_preventiva"],
            }

        if not isinstance(auditoria, dict):
            auditoria = {
                "estado": "revision_pendiente",
                "pendientes": ["respuesta_auditoria_invalida"],
            }

        estados_admitidos = (
            "sin_omision_demostrada",
            "revision_pendiente",
            "omision_detectada",
        )

        estado_auditoria = auditoria.get("estado")

        if estado_auditoria not in estados_admitidos:
            estado_auditoria = "revision_pendiente"
            auditoria = {
                "estado": estado_auditoria,
                "pendientes": ["estado_auditoria_no_reconocido"],
            }

        if estado_auditoria != "sin_omision_demostrada":
            respuesta["estado"] = "revision_semantica_pendiente"

        respuesta["auditoria_semantica"] = {
            "estado": estado_auditoria,
            "pendientes": auditoria.get("pendientes", []),
            "cobertura_certificada": False,
        }

        respuesta["interpretacion"] = preparado.get(
            "interpretacion"
        )
        respuesta["llm_invocado"] = bool(
            preparado["interpretacion"].get("llm_invocado")
        )
        respuesta["diagnostico"] = {
            "componente": "IA-ARC001-B03",
            "estado_host": preparado["estado"],
            "modelo": preparado["modelo"],
            "plan_host_preparado": plan,
            "ejecucion_habilitada": False,
        }

        return respuesta

    return _respuesta(
        pregunta,
        "pendiente_integracion",
        contexto_valido=True,
    )
