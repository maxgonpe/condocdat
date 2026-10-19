from __future__ import annotations

from django.contrib.admin.views.decorators import (
    staff_member_required,
)
from django.http import JsonResponse
from django.views.decorators.http import (
    require_http_methods,
)




from .services.bridge.orquestador_principal import (
    consultar_orquestado,
)






def _hacer_json_serializable(
    valor,
):
    """
    Convierte recursivamente estructuras Python
    válidas internamente pero no serializables
    directamente por JSON.

    IA-BRIDGE010-C01.

    No modifica el significado de la respuesta
    ni ejecuta lógica de negocio.
    """

    if isinstance(
        valor,
        dict,
    ):

        return {
            clave:
                _hacer_json_serializable(
                    contenido
                )
            for clave, contenido
            in valor.items()
        }

    if isinstance(
        valor,
        (
            list,
            tuple,
        ),
    ):

        return [
            _hacer_json_serializable(
                contenido
            )
            for contenido
            in valor
        ]

    if isinstance(
        valor,
        (
            set,
            frozenset,
        ),
    ):

        return [
            _hacer_json_serializable(
                contenido
            )
            for contenido
            in valor
        ]

    return valor




# ============================================================
# IA-BRIDGE006
# ENDPOINT WEB DEL NUEVO PIPELINE
# ============================================================


@staff_member_required
@require_http_methods(
    [
        "POST",
    ]
)
def consulta_bridge_json(
    request,
):
    """
    Endpoint web controlado para el pipeline:

        SEM
        → BRIDGE
        → HOST
        → ORM
        → respuesta compacta

    No reemplaza todavía el endpoint histórico /ia/consultar/.
    """

    pregunta = (
        request.POST.get(
            "pregunta"
        )
        or ""
    ).strip()

    if not pregunta:

        return JsonResponse(
            {
                "ok":
                    False,

                "version":
                    "IA-BRIDGE006-v1",

                "ejecutado":
                    False,

                "estado":
                    "pregunta_vacia",

                "mensaje":
                    "La pregunta está vacía.",
            },
            status=400,
            json_dumps_params={
                "ensure_ascii":
                    False,
            },
        )

    # --------------------------------------------------------
    # LÍMITE
    # --------------------------------------------------------

    limite_raw = (
        request.POST.get(
            "limite"
        )
        or "20"
    ).strip()

    try:

        limite = int(
            limite_raw
        )

    except (
        TypeError,
        ValueError,
    ):

        return JsonResponse(
            {
                "ok":
                    False,

                "version":
                    "IA-BRIDGE006-v1",

                "pregunta":
                    pregunta,

                "ejecutado":
                    False,

                "estado":
                    "limite_invalido",

                "mensaje":
                    (
                        "El límite debe ser "
                        "un número entero."
                    ),
            },
            status=400,
            json_dumps_params={
                "ensure_ascii":
                    False,
            },
        )

    # --------------------------------------------------------
    # DIAGNÓSTICO OPCIONAL
    # --------------------------------------------------------

    diagnostico_raw = (
        request.POST.get(
            "diagnostico"
        )
        or ""
    ).strip().lower()

    incluir_diagnostico = (
        diagnostico_raw
        in {
            "1",
            "true",
            "si",
            "sí",
            "yes",
            "on",
        }
    )

    # --------------------------------------------------------
    # PIPELINE BRIDGE005
    # --------------------------------------------------------

    try:

        resultado = consultar_orquestado(
            pregunta,
            limite=limite,
            diagnostico=(
                incluir_diagnostico
            ),

            # IA-BRIDGE009:
            # fallback histórico deliberadamente desactivado
            # en la interfaz principal.
            permitir_fallback_legado=False,
        )

    except Exception as exc:

        return JsonResponse(
            {
                "ok":
                    False,

                "version":
                    "IA-BRIDGE006-v1",

                "pregunta":
                    pregunta,

                "ejecutado":
                    False,

                "estado":
                    "error_interno",

                "mensaje":
                    str(
                        exc
                    ),
            },
            status=500,
            json_dumps_params={
                "ensure_ascii":
                    False,
            },
        )

    # --------------------------------------------------------
    # RESPUESTA HTTP
    # --------------------------------------------------------
    #
    # Una consulta semánticamente inválida sigue siendo una
    # respuesta válida del endpoint. Por eso dejamos HTTP 200:
    #
    #   ok=false
    #   estado=no_ejecutado
    #
    # permite al frontend distinguir correctamente entre:
    #
    #   error de transporte / servidor
    #   consulta rechazada por seguridad semántica
    #
    # --------------------------------------------------------

    resultado_json = (
        _hacer_json_serializable(
            resultado
        )
    )

    return JsonResponse(
        resultado_json,
        status=200,
        json_dumps_params={
            "ensure_ascii":
                False,
        },
    )