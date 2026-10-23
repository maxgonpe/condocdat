"""Aclaración de filtros vinculada a sesión Django.

Sin ORM, sin FINAL y sin modificaciones a LLM007.
"""
import hmac
import secrets
import time

from ia_local.services.host.desambiguacion_filtros import (
    preparar_aclaracion_filtro,
    verificar_eleccion_filtro,
)

VERSION = "IA-LLM008-F5-05-09A-v1"
SESSION_KEY = "ia_local_llm007_aclaracion"
TTL_SECONDS = 300
MAX_PREGUNTA = 4000


def _identidad(request):
    usuario = getattr(request, "user", None)
    if usuario is not None and usuario.is_authenticated:
        return "user:" + str(usuario.pk)
    return "anonymous"


def _base(estado):
    return {
        "ok": False,
        "version": VERSION,
        "estado": estado,
        "tipo_aclaracion": "filtro",
        "requiere_aclaracion": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }


def iniciar_aclaracion_filtro(
    request, pregunta, modelo, evidencia
):
    if not hasattr(request, "session"):
        return _base("sesion_no_disponible")

    # Una nueva solicitud invalida la anterior,
    # igual que la vista original LLM007.
    request.session.pop(SESSION_KEY, None)
    request.session.modified = True

    if (
        not isinstance(pregunta, str)
        or not pregunta.strip()
        or len(pregunta) > MAX_PREGUNTA
        or not isinstance(modelo, str)
        or not isinstance(evidencia, str)
    ):
        return _base("entrada_invalida")

    aclaracion = preparar_aclaracion_filtro(
        modelo, evidencia
    )

    if (
        aclaracion.get("ok") is not True
        or aclaracion.get("requiere_aclaracion") is not True
        or len(aclaracion.get("opciones", [])) < 2
    ):
        return _base("aclaracion_no_disponible")

    token = secrets.token_urlsafe(32)

    request.session[SESSION_KEY] = {
        "tipo_aclaracion": "filtro",
        "pregunta": pregunta,
        "modelo": aclaracion["modelo"],
        "evidencia": evidencia,
        "token": token,
        "identidad": _identidad(request),
        "creado": time.time(),
    }
    request.session.modified = True

    return {
        **_base("requiere_aclaracion_filtro"),
        "ok": True,
        "requiere_aclaracion": True,
        "pregunta": pregunta,
        "opciones": [
            {
                "id": opcion["id"],
                "etiqueta": opcion["etiqueta"],
            }
            for opcion in aclaracion["opciones"]
        ],
        "token_aclaracion": token,
    }


def continuar_aclaracion_filtro(
    request, pregunta, opcion_id, token
):
    if not hasattr(request, "session"):
        return _base("sesion_no_disponible")

    # Consumir el estado antes de cualquier comprobación.
    pendiente = request.session.pop(SESSION_KEY, None)
    request.session.modified = True

    if (
        not isinstance(pendiente, dict)
        or pendiente.get("tipo_aclaracion") != "filtro"
    ):
        return _base("aclaracion_no_vigente")

    if (
        not isinstance(pregunta, str)
        or not isinstance(opcion_id, str)
        or not isinstance(token, str)
        or not opcion_id
        or len(opcion_id) > 200
        or not token
        or len(token) > 256
    ):
        return _base("continuacion_invalida")

    if not hmac.compare_digest(
        token, str(pendiente.get("token", ""))
    ):
        return _base("token_invalido")

    if pendiente.get("identidad") != _identidad(request):
        return _base("identidad_invalida")

    creado = pendiente.get("creado")
    if type(creado) not in (int, float):
        return _base("fecha_sesion_invalida")

    edad = time.time() - creado
    if not 0 <= edad <= TTL_SECONDS:
        return _base("aclaracion_vencida")

    if pregunta != pendiente.get("pregunta"):
        return _base("pregunta_no_coincide")

    seleccion = verificar_eleccion_filtro(
        pendiente.get("modelo"),
        pendiente.get("evidencia"),
        opcion_id,
    )

    if (
        seleccion.get("ok") is not True
        or seleccion.get("certificada_host") is not True
        or seleccion.get("estado")
            != "eleccion_filtro_certificada"
    ):
        return _base("eleccion_no_certificada")

    return {
        **_base("filtro_seleccionado_pendiente_plan"),
        "ok": True,
        "pregunta_original": pregunta,
        "modelo": seleccion["modelo"],
        "evidencia_textual": seleccion["evidencia_textual"],
        "seleccion": seleccion["seleccion"],
        "requiere_validacion_plan_completo": True,
    }



# IA-LLM008-F5-07-08-B
def iniciar_aclaracion_relacional(request, plan):
    """Inicia una aclaración relacional diagnóstica."""
    from ia_local.services.llm.trazabilidad_compuesta import (
        preparar_alcance_relacional_certificado,
    )

    if not hasattr(request, "session"):
        return _base("sesion_no_disponible")

    # Política existente: una aclaración activa por sesión.
    request.session.pop(SESSION_KEY, None)
    request.session.modified = True

    if not isinstance(plan, dict):
        return _base("entrada_invalida")

    pregunta = plan.get("pregunta_original")

    if (
        not isinstance(pregunta, str)
        or not pregunta.strip()
        or len(pregunta) > MAX_PREGUNTA
    ):
        return _base("entrada_invalida")

    preparacion = preparar_alcance_relacional_certificado(
        plan
    )

    if (
        preparacion.get("ok") is not True
        or preparacion.get("estado")
            != "requiere_aclaracion_alcance_relacional"
        or preparacion.get("requiere_aclaracion") is not True
        or len(preparacion.get("opciones", [])) != 2
    ):
        return _base("aclaracion_relacional_no_disponible")

    token = secrets.token_urlsafe(32)

    # Se guarda el plan diagnóstico original para volver a
    # recertificar la relación antes de aceptar la elección.
    # Este estado nunca debe utilizarse directamente en FINAL.
    request.session[SESSION_KEY] = {
        "tipo_aclaracion": "alcance_relacional",
        "pregunta": pregunta,
        "plan_diagnostico": plan,
        "token": token,
        "identidad": _identidad(request),
        "creado": time.time(),
    }
    request.session.modified = True

    return {
        **_base("requiere_aclaracion_alcance_relacional"),
        "ok": True,
        "pregunta": pregunta,
        "opciones": preparacion["opciones"],
        "token_aclaracion": token,
        "requiere_aclaracion": True,
    }


def continuar_aclaracion_relacional(
    request, pregunta, opcion_id, token
):
    """Consume una elección, revalidando su procedencia."""
    from ia_local.services.llm.trazabilidad_compuesta import (
        preparar_alcance_relacional_certificado,
    )

    if not hasattr(request, "session"):
        return _base("sesion_no_disponible")

    pendiente = request.session.pop(SESSION_KEY, None)
    request.session.modified = True

    if (
        not isinstance(pendiente, dict)
        or pendiente.get("tipo_aclaracion")
            != "alcance_relacional"
    ):
        return _base("aclaracion_no_vigente")

    if (
        not isinstance(pregunta, str)
        or not isinstance(opcion_id, str)
        or not isinstance(token, str)
        or opcion_id not in {"contexto", "restriccion"}
        or not token
        or len(token) > 256
    ):
        return _base("continuacion_invalida")

    if not hmac.compare_digest(
        token,
        str(pendiente.get("token", "")),
    ):
        return _base("token_invalido")

    if pendiente.get("identidad") != _identidad(request):
        return _base("identidad_invalida")

    creado = pendiente.get("creado")

    if type(creado) not in (int, float):
        return _base("fecha_sesion_invalida")

    edad = time.time() - creado

    if not 0 <= edad <= TTL_SECONDS:
        return _base("aclaracion_vencida")

    if pregunta != pendiente.get("pregunta"):
        return _base("pregunta_no_coincide")

    plan = pendiente.get("plan_diagnostico")

    if not isinstance(plan, dict):
        return _base("plan_no_disponible")

    # No aceptar una elección basándose solamente en el
    # contenido guardado: se vuelve a ejecutar QUERY007/HOST025.
    preparacion = preparar_alcance_relacional_certificado(
        plan
    )

    if (
        preparacion.get("ok") is not True
        or preparacion.get("pregunta_original") != pregunta
        or preparacion.get("requiere_aclaracion") is not True
    ):
        return _base("relacion_no_recertificada")

    opciones = preparacion.get("opciones", [])

    coincidencias = [
        o for o in opciones
        if isinstance(o, dict)
        and o.get("id") == opcion_id
        and o.get("tipo") == opcion_id
    ]

    if len(coincidencias) != 1:
        return _base("eleccion_no_certificada")

    return {
        **_base("alcance_relacional_seleccionado"),
        "ok": True,
        "pregunta_original": pregunta,
        "decision": opcion_id,
        "evidencia_relacional": preparacion[
            "evidencia_relacional"
        ],
        "residuo_semantico": preparacion[
            "residuo_semantico"
        ],
        "requiere_validacion_plan_completo": True,
        "cobertura_verificada": False,
        "integridad_completa": False,
        "ejecutable": False,
        "ejecutado": False,
    }
