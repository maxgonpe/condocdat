
"""Aclaraciones individuales sobre colecciones LLM008."""

import hmac
import secrets
import time
from copy import deepcopy

from ia_local.services.llm.trazabilidad_compuesta import (
    _verificar_coleccion_identificada,
    preparar_opciones_restriccion,
    incorporar_eleccion_restriccion,
)

SESSION_KEY = "ia_local_llm008_restricciones"
TTL_SECONDS = 300


def _identidad(request):
    usuario = getattr(request, "user", None)
    if usuario is not None and usuario.is_authenticated:
        return f"user:{usuario.pk}"
    return "anonymous"


def _error(estado):
    return {
        "ok": False,
        "estado": estado,
        "ejecutable": False,
        "ejecutado": False,
    }


def iniciar_aclaracion_restriccion(
    request, coleccion, restriccion_id, modelo
):
    if not hasattr(request, "session"):
        return _error("sesion_no_disponible")

    # Reemplazar cualquier desafío anterior.
    request.session.pop(SESSION_KEY, None)

    if (
        not _verificar_coleccion_identificada(coleccion)
        or not isinstance(restriccion_id, str)
        or not isinstance(modelo, str)
    ):
        return _error("entrada_invalida")

    opciones = preparar_opciones_restriccion(
        coleccion, restriccion_id, modelo
    )

    if opciones.get("ok") is not True:
        return _error("aclaracion_no_disponible")

    token = secrets.token_urlsafe(32)

    request.session[SESSION_KEY] = {
        "tipo": "restriccion_identificada",
        "identidad": _identidad(request),
        "creado": time.time(),
        "token": token,
        "pregunta": coleccion["pregunta_original"],
        "modelo": modelo,
        "restriccion_id": restriccion_id,
        "identificador_coleccion":
            coleccion["identificador_coleccion"],
        "coleccion": deepcopy(coleccion),
        "opciones_ids": [
            opcion["id"] for opcion in opciones["opciones"]
        ],
    }

    request.session.modified = True

    return {
        "ok": True,
        "estado": "aclaracion_restriccion_iniciada",
        "pregunta_original": coleccion["pregunta_original"],
        "identificador_coleccion":
            coleccion["identificador_coleccion"],
        "restriccion_id": restriccion_id,
        "token": token,
        "opciones": deepcopy(opciones["opciones"]),
        "ejecutable": False,
        "ejecutado": False,
    }


def continuar_aclaracion_restriccion(
    request, pregunta, restriccion_id, opcion_id, token
):
    if not hasattr(request, "session"):
        return _error("sesion_no_disponible")

    # Consumo único, incluso ante una elección inválida.
    pendiente = request.session.pop(SESSION_KEY, None)
    request.session.modified = True

    if (
        not isinstance(pendiente, dict)
        or pendiente.get("tipo") != "restriccion_identificada"
    ):
        return _error("aclaracion_no_disponible")

    if not all(
        isinstance(valor, str) and valor
        for valor in (
            pregunta, restriccion_id, opcion_id, token
        )
    ):
        return _error("entrada_invalida")

    if (
        len(pregunta) > 4000
        or len(restriccion_id) > 256
        or len(opcion_id) > 256
        or len(token) > 256
    ):
        return _error("entrada_invalida")

    if not hmac.compare_digest(
        token, str(pendiente.get("token", ""))
    ):
        return _error("token_invalido")

    if pendiente.get("identidad") != _identidad(request):
        return _error("identidad_distinta")

    creado = pendiente.get("creado")
    if (
        type(creado) not in (int, float)
        or not 0 <= time.time() - creado <= TTL_SECONDS
    ):
        return _error("aclaracion_expirada")

    if (
        pendiente.get("pregunta") != pregunta
        or pendiente.get("restriccion_id") != restriccion_id
        or opcion_id not in pendiente.get("opciones_ids", [])
    ):
        return _error("decision_no_corresponde")

    coleccion = pendiente.get("coleccion")
    modelo = pendiente.get("modelo")

    if (
        not _verificar_coleccion_identificada(coleccion)
        or coleccion["pregunta_original"] != pregunta
        or coleccion["identificador_coleccion"]
            != pendiente.get("identificador_coleccion")
    ):
        return _error("coleccion_incompatible")

    resultado = incorporar_eleccion_restriccion(
        coleccion, restriccion_id, modelo, opcion_id
    )

    if resultado.get("ok") is not True:
        return _error("eleccion_rechazada_host")

    return {
        "ok": True,
        "estado": "restriccion_confirmada_en_sesion",
        "pregunta_original": pregunta,
        "restriccion_id": restriccion_id,
        "coleccion": resultado,
        "ejecutable": False,
        "ejecutado": False,
    }
