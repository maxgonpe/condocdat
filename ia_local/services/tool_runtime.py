"""IA-RESTART002: Qwen tool-calling, primer contrato de lectura controlada.

Punto único utilizado por ambas interfaces. No evalúa SQL ni ejecuta herramientas
arbitrarias solicitadas por el modelo. Ampliar operaciones tras pruebas separadas.
"""
import json
import os
import urllib.error
import urllib.request

from django.conf import settings
from ia_local.services.host.catalogo_datos import buscar_modelo_datos
from ia_local.services.host.validador_plan_datos import validar_plan_datos
from ia_local.services.host.ejecutor_datos import ejecutar_plan_datos

MODEL = "documents.Document"
TOOL_NAME = "contar_registros"
MODEL_QWEN = "qwen3:4b-instruct-2507-q4_K_M"
MAX_QUESTION = 1000


def habilitado():
    # Doble condición: solo entorno DEBUG y activación expresa del proceso.
    return settings.DEBUG is True and os.getenv("IA_LOCAL_TOOLS_POC", "") == "1"


def _ollama(messages, tools=None):
    payload = {
        "model": os.getenv("IA_LOCAL_TOOLS_MODEL", MODEL_QWEN),
        "stream": False,
        "options": {"temperature": 0},
        "messages": messages,
    }
    if tools is not None:
        payload["tools"] = tools
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]


def _respuesta_error(pregunta, mensaje, estado="rechazado", diagnostico=None):
    return {
        "ok": False, "ejecutado": False, "estado": estado,
        "version": "IA-RESTART002-tools-v1", "pregunta": pregunta,
        "respuesta": mensaje, "modelo": None, "tipo": None,
        "total": None, "total_disponible": None, "total_devuelto": None,
        "truncado": False, "registros": [], "campos": [],
        "diagnostico": diagnostico or {"circuito": "Qwen-tools"},
    }


def resolver_pregunta(request, pregunta):
    """Devuelve el mismo contrato de consulta para API e interfaz diagnóstica."""
    if not habilitado():
        return _respuesta_error(pregunta, "Ensayo de herramientas deshabilitado", "deshabilitado")
    pregunta = (pregunta or "").strip()
    if not pregunta or len(pregunta) > MAX_QUESTION:
        return _respuesta_error(pregunta, "Pregunta vacía o demasiado larga", "entrada_invalida")

    usuario = getattr(request, "user", None)
    if (usuario is None or not usuario.is_authenticated or not usuario.is_active
            or not usuario.is_staff or not usuario.has_perm("documents.view_document")):
        return _respuesta_error(pregunta, "Usuario sin autorización de lectura", "no_autorizado")

    diagnostico = {"circuito": "Qwen-tools", "modelo_qwen": os.getenv("IA_LOCAL_TOOLS_MODEL", MODEL_QWEN)}
    tools = [{
        "type": "function",
        "function": {
            "name": TOOL_NAME,
            "description": "Contar registros existentes de una entidad Django, si el usuario está autorizado.",
            "parameters": {
                "type": "object",
                "properties": {"entidad": {"type": "string"}, "alcance": {"type": "string", "enum": ["global", "filtrado", "otro"]}},
                "required": ["entidad", "alcance"],
            },
        },
    }]
    messages = [
        {"role": "system", "content": (
            "Eres asistente de Condocdat. Para preguntas que requieren datos actuales, "
            "solicita la herramienta disponible. No inventes registros, cantidades o resultados. "
            "El alcance es global SOLO cuando se pide contar TODOS los registros de la entidad, "
            "sin restricciones de fecha, estado, proyecto u otras condiciones. "
            "Para filtros usa alcance=filtrado (no ejecutable por ahora). "
            "Si la herramienta no permite responder, reconócelo. Responde en español."
        )},
        {"role": "user", "content": pregunta},
    ]
    try:
        first = _ollama(messages, tools=tools)
        calls = first.get("tool_calls") or []
        diagnostico["tool_calls"] = calls
        if (len(calls) != 1 or not isinstance(calls[0], dict)
                or calls[0].get("function", {}).get("name") != TOOL_NAME):
            return _respuesta_error(pregunta, "Qwen no solicitó una herramienta de conteo admitida", "sin_herramienta", diagnostico)

        args = calls[0]["function"].get("arguments", {})
        if not isinstance(args, dict) or not isinstance(args.get("entidad"), str) or args.get("alcance") not in ("global", "filtrado", "otro"):
            return _respuesta_error(pregunta, "Argumentos de herramienta inválidos", "argumentos_invalidos", diagnostico)

        diagnostico["alcance"] = args["alcance"]
        if args["alcance"] != "global":
            return _respuesta_error(pregunta, "El ensayo aún no permite conteos filtrados", "alcance_no_admitido", diagnostico)

        candidatos = buscar_modelo_datos(args["entidad"])
        diagnostico["candidatos"] = [c.get("label") for c in candidatos]
        if len(candidatos) != 1 or candidatos[0].get("label") != MODEL:
            return _respuesta_error(pregunta, "Entidad no encontrada, ambigua o no habilitada en este ensayo", "entidad_no_admitida", diagnostico)

        # Alcance inicial: un conteo global de documentos, sin filtros ni listas.
        plan = {"modelo": MODEL, "operacion": "contar", "filtros": [],
                "orden": [], "limite": 1, "condiciones_no_resueltas": []}
        validacion = validar_plan_datos(plan)
        if not validacion.get("plan_validado"):
            diagnostico["errores"] = validacion.get("errores", [])
            return _respuesta_error(pregunta, "HOST no validó el plan", "plan_rechazado", diagnostico)
        diagnostico["plan"] = validacion["plan"]

        # La pregunta puede incluir condiciones que el conteo global no satisface.
        # No devolver un total global como si fuera filtrado.
        # Esta POC solo habilita una pregunta equivalente a un conteo global:
        # la comprobación semántica queda limitada deliberadamente a la prueba inicial.
        # Para ampliar se necesitará planificación de filtros verificada.
        resultado = ejecutar_plan_datos(validacion["plan"])
        diagnostico["resultado_host"] = {k: resultado.get(k) for k in ("ok", "ejecutado", "total", "modelo", "operacion")}
        if resultado.get("ok") is not True or resultado.get("ejecutado") is not True or type(resultado.get("total")) is not int:
            return _respuesta_error(pregunta, "HOST no pudo ejecutar el conteo", "ejecucion_rechazada", diagnostico)

        total = resultado["total"]
        messages.append(first)
        tool_message = {"role": "tool", "name": TOOL_NAME,
                        "content": json.dumps({"modelo": MODEL, "total": total, "ok": True}, ensure_ascii=False)}
        if calls[0].get("id"):
            tool_message["tool_call_id"] = calls[0]["id"]
        messages.append(tool_message)
        answer = _ollama(messages).get("content", "").strip()
        # No dejar que la reformulación de Qwen altere la cantidad verificada.
        import re
        if not answer or str(total) not in re.findall(r"\d+", answer):
            answer = f"Hay {total} documentos registrados."
        diagnostico["respuesta_qwen"] = answer
        return {"ok": True, "ejecutado": True, "estado": "respuesta_formateada",
                "version": "IA-RESTART002-tools-v1", "pregunta": pregunta,
                "respuesta": answer, "modelo": MODEL, "tipo": "conteo",
                "total": total, "total_disponible": total, "total_devuelto": 0,
                "truncado": False, "registros": [], "campos": [],
                "diagnostico": diagnostico}
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
        diagnostico["error_tipo"] = type(exc).__name__
        return _respuesta_error(pregunta, "No se pudo completar la consulta con Ollama/HOST", "error_herramientas", diagnostico)
