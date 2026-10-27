from __future__ import annotations

from django.contrib.admin.views.decorators import (
    staff_member_required,
)
from django.http import JsonResponse
from django.views.decorators.http import (
    require_http_methods,
)

from .services.final.formateador_respuesta import (
    responder_consulta,
)
from .services.final.trazabilidad import (
    registrar_traza_consulta,
)
from .services.final.politica_respuesta import (
    aplicar_politica_respuesta,
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
            clave: _hacer_json_serializable(
                contenido
            )
            for clave, contenido in valor.items()
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
            for contenido in valor
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
            for contenido in valor
        ]

    return valor


# ============================================================
# IA-FINAL005
# ENDPOINT WEB DEL PIPELINE FINAL
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
    Endpoint web controlado para el pipeline FINAL:

        pregunta
            → FINAL001
            → FINAL002
            → FINAL003
            → HOST
            → FINAL004
            → respuesta pública

    IA-FINAL007 agrega trazabilidad compacta después de
    obtener la respuesta, sin modificar la lógica de negocio.
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
                    "IA-FINAL005-v1",

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
                    "IA-FINAL005-v1",

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
    # IA-FINAL005
    # PIPELINE FINAL
    # --------------------------------------------------------
    #
    # La vista NO ejecuta ORM de negocio directamente.
    # --------------------------------------------------------

    try:

        from django.conf import settings

        modo_certificado = (
            getattr(
                settings,
                "IA_LOCAL_HTTP_CERTIFICADO_HABILITADO",
                False,
            ) is True
        )

        if modo_certificado:
            from .services.final.entrada_web_compartida import (
                responder_consulta_web,
            )
            resultado = responder_consulta_web(
                request,
                pregunta,
            )
        else:
            # Conservar la referencia historica del bridge.
            resultado = responder_consulta(
                pregunta
            )

        resultado = aplicar_politica_respuesta(
            pregunta=pregunta,
            respuesta=resultado,
        )

    except Exception as exc:

        return JsonResponse(
            {
                "ok":
                    False,

                "version":
                    "IA-FINAL005-v1",

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
    # IA-FINAL007
    # TRAZABILIDAD COMPACTA
    # --------------------------------------------------------
    #
    # Un fallo de trazabilidad NO debe romper una consulta
    # que ya fue procesada correctamente.
    # --------------------------------------------------------

    try:

        usuario_traza = (
            request.user.get_username()
            if request.user.is_authenticated
            else ""
        )

        traza = registrar_traza_consulta(
            pregunta=pregunta,
            resultado=resultado,
            usuario=usuario_traza,
        )

    except Exception:

        traza = {
            "ok":
                False,

            "version":
                "IA-FINAL007-v1",

            "estado":
                "error_registro_traza",

            "registrado":
                False,
        }

    # --------------------------------------------------------
    # COMPATIBILIDAD TEMPORAL CON LA UI
    # --------------------------------------------------------
    #
    # FINAL004 usa:
    #
    #   respuesta
    #   registros
    #
    # La interfaz puede mantener temporalmente:
    #
    #   mensaje
    #   resultados
    #
    # hasta completar la transición definitiva.
    # --------------------------------------------------------

    if isinstance(
        resultado,
        dict,
    ):

        resultado = dict(
            resultado
        )

        if incluir_diagnostico:

            resultado[
                "trazabilidad"
            ] = traza

        if (
            "mensaje"
            not in resultado
        ):

            resultado[
                "mensaje"
            ] = (
                resultado.get(
                    "respuesta"
                )
                or ""
            )

        if (
            "resultados"
            not in resultado
        ):

            registros = resultado.get(
                "registros",
                [],
            )

            resultado[
                "resultados"
            ] = (
                registros
                if isinstance(
                    registros,
                    list,
                )
                else []
            )

        resultado[
            "limite_solicitado"
        ] = limite

        if not incluir_diagnostico:

            resultado.pop(
                "diagnostico",
                None,
            )

    # --------------------------------------------------------
    # RESPUESTA HTTP
    # --------------------------------------------------------
    #
    # Una consulta funcionalmente no ejecutable puede seguir
    # respondiendo HTTP 200.
    #
    # Esto permite distinguir:
    #
    #   - error HTTP / servidor
    #   - consulta rechazada o no ejecutable
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
