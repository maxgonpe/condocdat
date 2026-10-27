"""
ARC003-B06-B03-A — Frontera web compartida.

La configuracion del servidor decide el circuito.
No acepta planes, certificados ni filtros del cliente.

No expone endpoints ni realiza consultas ORM directamente.
"""

from django.conf import settings

from ia_local.services.final.formateador_respuesta import (
    responder_consulta,
)
from ia_local.services.final.entrada_http_certificada import (
    responder_consulta_http,
)


VERSION = "IA-ARC003-B06-B03-A-v1"


def _rechazo(estado, pregunta):
    return {
        "ok": False,
        "version": VERSION,
        "estado": estado,
        "pregunta": pregunta,
        "respuesta": "La consulta no pudo ser certificada.",
        "tipo": "resultado",
        "total": None,
        "registros": [],
        "campos": [],
        "ejecutado": False,
        "llm_invocado": False,
    }


def responder_consulta_web(
    request,
    pregunta,
    *,
    entidad_aclarada=None,
):
    """
    Punto comun de entrada desde vistas Django.

    Modo legado:
        conserva FINAL existente.

    Modo certificado:
        utiliza exclusivamente el adaptador certificado.
        No permite fallback hacia FINAL.
    """

    habilitado = (
        getattr(
            settings,
            "IA_LOCAL_HTTP_CERTIFICADO_HABILITADO",
            False,
        )
        is True
    )

    if not habilitado:
        # No alterar el comportamiento historico.
        if entidad_aclarada is None:
            return responder_consulta(pregunta)

        return responder_consulta(
            pregunta,
            entidad_aclarada=entidad_aclarada,
        )

    # La aclaracion necesita un contrato certificado
    # propio. No ejecutar por FINAL antiguo.
    if entidad_aclarada is not None:
        return _rechazo(
            "aclaracion_no_certificada_en_http",
            pregunta,
        )

    return responder_consulta_http(
        request,
        pregunta,
    )
