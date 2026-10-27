"""
ARC003-B05-D02
Resolucion de la politica de lectura desde Django settings.

La solicitud HTTP, Qwen y los contratos de consulta
no pueden proporcionar la ruta de la politica.

No ejecuta ORM.
No concede permisos por defecto.
"""

from django.conf import settings
from django.utils.module_loading import import_string

from ia_local.services.host.autorizacion_lectura import (
    autorizar_lectura,
)


VERSION = "IA-ARC003-B05-D02-v1"
AJUSTE = "IA_LOCAL_POLITICA_LECTURA"


def _rechazo(estado):
    return {
        "ok": False,
        "version": VERSION,
        "estado": estado,
        "autorizado": False,
        "ejecutable": False,
        "ejecutado": False,
    }


def resolver_politica_lectura():
    """
    Resuelve exclusivamente una ruta Python definida
    en la configuracion confiable de Django.

    No admite funciones o decisiones suministradas
    mediante parametros de consulta.
    """

    ruta = getattr(settings, AJUSTE, None)

    if (
        not isinstance(ruta, str)
        or not ruta.strip()
        or ruta != ruta.strip()
        or "." not in ruta
    ):
        return None

    try:
        politica = import_string(ruta)
    except (ImportError, AttributeError, ValueError):
        return None

    if not callable(politica):
        return None

    return politica


def autorizar_lectura_configurada(usuario, plan_host):
    """
    Unico punto de entrada D02 para usar la politica
    configurada por el servidor.

    La decision sigue sin autorizar ejecucion.
    """

    politica = resolver_politica_lectura()

    if politica is None:
        return _rechazo("politica_no_configurada")

    resultado = autorizar_lectura(
        usuario,
        plan_host,
        politica=politica,
    )

    if (
        not isinstance(resultado, dict)
        or resultado.get("ok") is not True
        or resultado.get("autorizado") is not True
        or resultado.get("ejecutable") is not False
        or resultado.get("ejecutado") is not False
    ):
        return _rechazo("lectura_no_autorizada")

    return {
        **resultado,
        "version_registro": VERSION,
        "origen_politica": "configuracion_django",
    }
