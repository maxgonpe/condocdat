"""
IA-LLM008-D06-C3

Ejecucion controlada de conteos simples certificados.
No recibe contratos ni filtros externos.
"""

from django.db import transaction

from ia_local.services.host.expediente_consulta import (
    _obtener_bloqueado,
    _vigente,
)
from ia_local.services.host.contrato_conteo_certificado import (
    reconstruir_contrato_conteo,
)
from ia_local.services.final.ejecutor_consultas import (
    ejecutar_plan_datos,
)


VERSION = "IA-LLM008-D06-C3-v1"


def _rechazo(estado):
    return {
        "ok": False,
        "version": VERSION,
        "estado": estado,
        "ejecutado": False,
        "resultado": None,
    }


def ejecutar_conteo_certificado(
    request,
    identificador,
    version,
):
    if type(version) is not int or version < 1:
        return _rechazo("version_invalida")

    if not identificador:
        return _rechazo("identificador_invalido")

    try:
        with transaction.atomic():
            expediente = _obtener_bloqueado(
                request,
                identificador,
            )

            if expediente is None:
                return _rechazo("expediente_no_disponible")

            if not _vigente(expediente):
                return _rechazo("expediente_no_vigente")

            if expediente.version != version:
                return _rechazo("version_obsoleta")

            if expediente.estado != "ABIERTO":
                return _rechazo("expediente_no_abierto")

            # Reconstruye el contrato desde el expediente
            # dentro de la misma transaccion y bloqueo.
            preparado = reconstruir_contrato_conteo(
                request,
                identificador,
                version,
            )

            if (
                preparado.get("ok") is not True
                or preparado.get("contrato_preparado") is not True
                or preparado.get("estado")
                    != "contrato_conteo_preparado"
            ):
                return _rechazo(
                    "certificacion_no_disponible"
                )

            plan = preparado.get("contrato")

            if (
                not isinstance(plan, dict)
                or plan.get("modelo")
                    != expediente.modelo_contexto
                or plan.get("operacion") != "contar"
                or plan.get("filtros") != []
                or plan.get("orden") != []
                or plan.get("limite") is not None
                or plan.get("condiciones_no_resueltas") != []
            ):
                return _rechazo("contrato_no_autorizado")

            # Consumir el expediente ANTES de ejecutar.
            # La fila permanece bloqueada hasta finalizar
            # esta transaccion.
            expediente.estado = "COMPLETADO"
            expediente.version += 1
            expediente.save(
                update_fields=[
                    "estado",
                    "version",
                    "actualizado",
                ]
            )

            # Reutilizar el ejecutor HOST existente.
            resultado = ejecutar_plan_datos(plan)

            if not isinstance(resultado, dict):
                resultado = {
                    "ok": False,
                    "ejecutado": False,
                }

            correcto = (
                resultado.get("ok") is True
                and resultado.get("ejecutado") is True
            )

            return {
                "ok": correcto,
                "version": VERSION,
                "estado": (
                    "conteo_certificado_ejecutado"
                    if correcto
                    else "ejecucion_host_rechazada"
                ),
                "identificador": str(expediente.pk),
                "version_expediente": expediente.version,
                "modelo": expediente.modelo_contexto,
                "operacion": "contar",
                "ejecutado": correcto,
                "resultado": resultado,
            }

    except Exception:
        # Sin exponer detalles internos de base de datos.
        return _rechazo("error_ejecucion_certificada")
