"""IA-LLM007-F4: aclaraciones de entidad vinculadas a una sesión.

Las consultas ordinarias conservan su vista y contrato FINAL004.
"""

from django.contrib.admin.views.decorators import staff_member_required
import hmac
import secrets
import time

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .services.host.desambiguacion_controlada import (
    preparar_aclaracion,
    verificar_eleccion,
)
from .services.final.formateador_respuesta import responder_consulta
from .views import consulta_ia_json

SESSION_KEY = "ia_local_llm007_aclaracion"
TTL_SECONDS = 300
MAX_PREGUNTA = 4000


def _identidad(request):
    usuario = getattr(request, "user", None)
    if usuario is not None and usuario.is_authenticated:
        return "user:" + str(usuario.pk)
    return "anonymous"


def _respuesta(payload, status=200):
    return JsonResponse(payload, status=status, json_dumps_params={"ensure_ascii": False})


def _rechazo(estado, mensaje):
    return _respuesta({
        "ok": False,
        "estado": estado,
        "respuesta": mensaje,
        "requiere_aclaracion": False,
        "ejecutado": False,
        "llm_invocado": False,
    })


@staff_member_required
@require_POST
def consultar_con_aclaracion(request):
    """Un solo endpoint para pregunta y continuación de aclaración."""
    if not hasattr(request, "session"):
        return _rechazo("sesion_no_disponible", "No existe una sesión Django habilitada.")

    pregunta = (request.POST.get("pregunta") or "").strip()
    opcion = (request.POST.get("opcion_id") or "").strip()
    token = (request.POST.get("token_aclaracion") or "").strip()
    continuar = bool(opcion or token)

    # ARC003-B06-B03-B04-B
    # En modo certificado, no iniciar ni continuar
    # desambiguaciones mediante FINAL tradicional.
    from django.conf import settings

    modo_certificado = (
        getattr(
            settings,
            "IA_LOCAL_HTTP_CERTIFICADO_HABILITADO",
            False,
        ) is True
    )

    if modo_certificado:
        # Invalidar cualquier aclaracion anterior.
        request.session.pop(SESSION_KEY, None)
        request.session.modified = True

        if continuar:
            return _rechazo(
                "aclaracion_no_certificada_en_http",
                "La continuación contextual no está "
                "habilitada en el circuito certificado.",
            )

        if not pregunta:
            return _rechazo(
                "pregunta_vacia",
                "Escribe una pregunta.",
            )

        if len(pregunta) > MAX_PREGUNTA:
            return _rechazo(
                "pregunta_demasiado_larga",
                "La pregunta supera la longitud admitida.",
            )

        # El circuito JSON ya aplica la certificacion E03.
        # No llamar a preparar_aclaracion ni a FINAL legado.
        return consulta_ia_json(request)

    if continuar:
        # Consumir antes de invocar Qwen/FINAL, aun cuando la elección falle.
        pendiente = request.session.pop(SESSION_KEY, None)
        request.session.modified = True
        if not isinstance(pendiente, dict):
            return _rechazo("aclaracion_no_vigente", "La aclaración ya no está vigente.")
        if not opcion or not token or len(token) > 256 or len(opcion) > 200:
            return _rechazo("aclaracion_incompleta", "La selección de aclaración está incompleta.")
        if not hmac.compare_digest(token, str(pendiente.get("token", ""))):
            return _rechazo("aclaracion_token_invalido", "La solicitud de aclaración no coincide.")
        if pendiente.get("identidad") != _identidad(request):
            return _rechazo("aclaracion_identidad_invalida", "La aclaración pertenece a otra identidad.")
        if time.time() - float(pendiente.get("creado", 0)) > TTL_SECONDS:
            return _rechazo("aclaracion_vencida", "La aclaración ha vencido. Realiza nuevamente tu pregunta.")
        original = pendiente.get("pregunta", "")
        if not isinstance(original, str) or not original or pregunta != original:
            return _rechazo("aclaracion_pregunta_invalida", "La pregunta original no coincide.")

        certificacion = verificar_eleccion(original, opcion)
        if (not isinstance(certificacion, dict)
                or certificacion.get("estado") != "eleccion_certificada"
                or certificacion.get("ok") is not True):
            return _rechazo("eleccion_no_certificada", "HOST no certificó la entidad elegida.")

        try:
            resultado = responder_consulta(original, entidad_aclarada=opcion)
        except Exception:
            # No exponer detalles internos en HTTP.
            return _rechazo("error_continuacion", "No fue posible completar la consulta aclarada.")
        if not isinstance(resultado, dict):
            return _rechazo("respuesta_final_invalida", "FINAL devolvió una respuesta inválida.")
        # Mismo patrón de serialización defensiva que la vista actual.
        import json
        seguro = json.loads(json.dumps(resultado, ensure_ascii=False, default=str))
        seguro["aclaracion_completada"] = True
        return _respuesta(seguro)

    # Una nueva pregunta invalida cualquier aclaración anterior.
    request.session.pop(SESSION_KEY, None)
    request.session.modified = True
    if not pregunta:
        return _rechazo("pregunta_vacia", "Escribe una pregunta.")
    if len(pregunta) > MAX_PREGUNTA:
        return _rechazo("pregunta_demasiado_larga", "La pregunta supera la longitud admitida.")

    try:
        aclaracion = preparar_aclaracion(pregunta)
    except Exception:
        return _rechazo("error_desambiguacion", "No fue posible analizar la desambiguación.")

    if isinstance(aclaracion, dict) and aclaracion.get("estado") == "requiere_aclaracion":
        opciones = aclaracion.get("opciones") or []
        if not isinstance(opciones, list) or len(opciones) < 2:
            return _rechazo("aclaracion_sin_opciones", "No existen suficientes alternativas certificadas.")
        publicas = []
        for opcion_item in opciones:
            if not isinstance(opcion_item, dict):
                continue
            ident = opcion_item.get("id")
            etiqueta = opcion_item.get("etiqueta")
            if isinstance(ident, str) and isinstance(etiqueta, str):
                publicas.append({"id": ident, "etiqueta": etiqueta})
        if len(publicas) < 2:
            return _rechazo("aclaracion_sin_opciones", "No existen suficientes alternativas certificadas.")
        codigo = secrets.token_urlsafe(32)
        request.session[SESSION_KEY] = {
            "pregunta": pregunta,
            "token": codigo,
            "identidad": _identidad(request),
            "creado": time.time(),
        }
        request.session.modified = True
        return _respuesta({
            "ok": False,
            "estado": "requiere_aclaracion",
            "requiere_aclaracion": True,
            "pregunta": pregunta,
            "respuesta": "Encontré varias entidades posibles. Selecciona la que corresponde a tu consulta.",
            "opciones": publicas,
            "token_aclaracion": codigo,
            "ejecutado": False,
            "llm_invocado": False,
            "registros": [],
            "campos": [],
        })

    # No duplicar el contrato existente: una pregunta normal se delega intacta.
    return consulta_ia_json(request)
