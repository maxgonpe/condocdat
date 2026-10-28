"""Entradas HTTP del motor Qwen + HOST, sin caminos alternativos."""
import json
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from .services import tool_runtime

@staff_member_required
@require_http_methods(["GET", "POST"])
def consulta_ia(request):
    if request.method == "POST":
        return _consulta_json(request)
    return render(request, "ia_local/index.html", {})

def _consulta_json(request):
    pregunta = (request.POST.get("pregunta") or "").strip()
    return JsonResponse(tool_runtime.resolver_pregunta(request, pregunta), json_dumps_params={"ensure_ascii": False})

@staff_member_required
@require_http_methods(["POST"])
def consulta_ia_json(request):
    return _consulta_json(request)

@staff_member_required
@require_http_methods(["GET", "POST"])
def diagnostico_ia(request):
    contexto = {"pregunta": "", "resultado_final": None, "error": None}
    if request.method == "POST":
        pregunta = (request.POST.get("pregunta") or "").strip()
        resultado = tool_runtime.resolver_pregunta(request, pregunta)
        contexto.update(pregunta=pregunta, resultado_final=resultado,
                        resultado_json=json.dumps(resultado, ensure_ascii=False, indent=2, default=str),
                        diagnostico_json=json.dumps(resultado.get("diagnostico") or {}, ensure_ascii=False, indent=2, default=str))
    return render(request, "ia_local/diagnostico.html", contexto)
