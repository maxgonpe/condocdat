from __future__ import annotations

import json

from django.contrib.admin.views.decorators import (
    staff_member_required,
)
from django.http import JsonResponse
from django.views.decorators.http import (
    require_http_methods,
)

from .services.final.correccion_semantica import (
    proponer_correccion_semantica,
)


@staff_member_required
@require_http_methods(
    [
        "POST",
    ]
)
def proponer_correccion_json(
    request,
):
    """
    IA-FINAL008

    Endpoint administrativo para crear una propuesta
    semántica pendiente.

    Nunca confirma ni aplica conocimiento automáticamente.
    """

    tipo = (
        request.POST.get(
            "tipo"
        )
        or ""
    ).strip()

    expresion = (
        request.POST.get(
            "expresion"
        )
        or ""
    ).strip()

    motivo = (
        request.POST.get(
            "motivo"
        )
        or ""
    ).strip()

    datos_raw = (
        request.POST.get(
            "datos"
        )
        or "{}"
    ).strip()

    try:

        datos = json.loads(
            datos_raw
        )

    except json.JSONDecodeError:

        return JsonResponse(
            {
                "ok": False,
                "version": "IA-FINAL008-v1",
                "estado": "datos_json_invalidos",
                "propuesta_creada": False,
                "llm_invocado": False,
            },
            status=400,
            json_dumps_params={
                "ensure_ascii": False,
            },
        )

    if not isinstance(
        datos,
        dict,
    ):

        return JsonResponse(
            {
                "ok": False,
                "version": "IA-FINAL008-v1",
                "estado": "datos_no_objeto",
                "propuesta_creada": False,
                "llm_invocado": False,
            },
            status=400,
            json_dumps_params={
                "ensure_ascii": False,
            },
        )

    try:

        resultado = proponer_correccion_semantica(
            tipo=tipo,
            expresion=expresion,
            datos=datos,
            motivo=motivo,
        )

    except Exception as exc:

        return JsonResponse(
            {
                "ok": False,
                "version": "IA-FINAL008-v1",
                "estado": "error_interno",
                "propuesta_creada": False,
                "mensaje": str(
                    exc
                ),
                "llm_invocado": False,
            },
            status=500,
            json_dumps_params={
                "ensure_ascii": False,
            },
        )

    return JsonResponse(
        resultado,
        status=200,
        json_dumps_params={
            "ensure_ascii": False,
        },
    )