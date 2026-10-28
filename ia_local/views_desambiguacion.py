"""Compatibilidad del endpoint contextual sin motor paralelo."""
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .services import tool_runtime

@staff_member_required
@require_POST
def consultar_con_aclaracion(request):
    if request.POST.get("opcion_id") or request.POST.get("token_aclaracion"):
        return JsonResponse({"ok": False, "ejecutado": False,
                             "estado": "aclaracion_no_soportada",
                             "respuesta": "Este circuito aún no admite aclaraciones.",
                             "diagnostico": {"circuito": "Qwen-tools"}},
                            json_dumps_params={"ensure_ascii": False})
    pregunta = (request.POST.get("pregunta") or "").strip()
    return JsonResponse(tool_runtime.resolver_pregunta(request, pregunta), json_dumps_params={"ensure_ascii": False})
