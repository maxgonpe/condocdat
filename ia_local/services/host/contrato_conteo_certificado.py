"""
IA-LLM008-D06-C2

Reconstruye un contrato HOST exclusivamente desde una
certificacion positiva de conteo simple.

No consume planes propuestos por Qwen.
No ejecuta consultas.
No concede autorizacion FINAL.
"""

from copy import deepcopy

from ia_local.services.host.certificador_conteo_simple import (
    certificar_conteo_simple,
)

from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)


VERSION = "IA-LLM008-D06-C2-v1"


def _error(estado, **datos):
    return {
        "ok": False,
        "version": VERSION,
        "estado": estado,
        "contrato_preparado": False,
        "ejecutable": False,
        "ejecutado": False,
        **datos,
    }


def reconstruir_contrato_conteo(
    request,
    identificador,
    version,
):
    """
    Recupera una certificacion positiva desde el servidor.

    Solo se aceptan expedientes que cumplan D06-C1.
    La propuesta se construye localmente.
    """

    certificacion = certificar_conteo_simple(
        request,
        identificador,
        version,
    )

    if not isinstance(certificacion, dict):
        return _error("certificacion_invalida")

    if (
        certificacion.get("ok") is not True
        or certificacion.get("certificable") is not True
        or certificacion.get("cobertura_plantilla_verificada")
            is not True
        or certificacion.get("estado")
            != "conteo_simple_certificado"
        or certificacion.get("alcance_certificacion")
            != "conteo_simple"
        or certificacion.get("version_expediente")
            != version
    ):
        return _error(
            "certificacion_no_disponible",
            estado_certificacion=certificacion.get("estado"),
        )

    modelo = certificacion.get("modelo")

    if (
        not isinstance(modelo, str)
        or not modelo.strip()
        or certificacion.get("operacion") != "contar"
    ):
        return _error("certificacion_inconsistente")

    # Plan nuevo, construido solo desde datos HOST.
    propuesta = {
        "modelo": modelo,
        "operacion": "contar",
        "filtros": [],
        "orden": [],
        "limite": None,
        "condiciones_no_resueltas": [],
    }

    try:
        validacion = validar_plan_datos(
            deepcopy(propuesta)
        )
    except Exception as exc:
        return _error(
            "error_validacion_host",
            tipo_error=type(exc).__name__,
        )

    if not isinstance(validacion, dict):
        return _error("respuesta_host_invalida")

    if validacion.get("ok") is not True:
        return _error(
            "plan_rechazado_host",
            estado_validacion=validacion.get("estado"),
            errores=validacion.get("errores", []),
        )

    plan = validacion.get("plan")

    if not isinstance(plan, dict):
        return _error("plan_host_ausente")

    # Comprobar que HOST no introdujo restricciones
    # ni cambió el significado del conteo simple.
    if (
        plan.get("modelo") != modelo
        or plan.get("operacion") != "contar"
        or plan.get("filtros") != []
        or plan.get("orden") != []
        or plan.get("limite") is not None
        or plan.get("condiciones_no_resueltas", [])
            not in ([], None)
    ):
        return _error("plan_host_no_equivalente")

    return {
        "ok": True,
        "version": VERSION,
        "estado": "contrato_conteo_preparado",
        "identificador": certificacion["identificador"],
        "version_expediente": version,
        "modelo": modelo,
        "tipo_contrato": "plan_host",
        "contrato": deepcopy(plan),
        "contrato_preparado": True,
        "certificacion": {
            "estado": "conteo_simple_certificado",
            "alcance": "conteo_simple",
        },
        # NO es una autorización de ejecución.
        "ejecutable": False,
        "ejecutado": False,
    }
