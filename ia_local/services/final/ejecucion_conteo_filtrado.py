"""
ARC003-B05-E03-A.

Despacho transaccional de conteo filtrado certificado.

No recibe preguntas, planes ni certificados externos.
Sin endpoint HTTP.
E01 reconstruye certificacion y autorizacion desde el
expediente persistido.
"""

from django.db import transaction

from ia_local.services.host.expediente_consulta import (
    _obtener_bloqueado,
    _vigente,
)
from ia_local.services.final.preparacion_conteo_filtrado import (
    preparar_conteo_filtrado_certificado,
)
from ia_local.services.host.ejecutor_datos import (
    ejecutar_plan_datos,
)


VERSION = "IA-ARC003-B05-E03-A-v1"


def _rechazo(estado):
    return {
        "ok": False,
        "version": VERSION,
        "estado": estado,
        "ejecutado": False,
        "resultado": None,
    }


def ejecutar_conteo_filtrado_certificado(
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
                request, identificador
            )

            if expediente is None:
                return _rechazo(
                    "expediente_no_disponible"
                )

            if not _vigente(expediente):
                return _rechazo(
                    "expediente_no_vigente"
                )

            if expediente.version != version:
                return _rechazo("version_obsoleta")

            if expediente.estado != "ABIERTO":
                return _rechazo(
                    "expediente_no_abierto"
                )

            # E01 reconstruye pregunta y plan desde
            # el expediente, y recalcula la autorizacion.
            preparado = preparar_conteo_filtrado_certificado(
                request, identificador, version
            )

            if (
                not isinstance(preparado, dict)
                or preparado.get("ok") is not True
                or preparado.get("contrato_preparado")
                    is not True
                or preparado.get("estado")
                    != "conteo_filtrado_preparado"
                or preparado.get("ejecutable") is not False
                or preparado.get("ejecutado") is not False
                or preparado.get("identificador")
                    != str(expediente.pk)
                or preparado.get("version_expediente")
                    != version
                or preparado.get("modelo")
                    != expediente.modelo_contexto
            ):
                return _rechazo(
                    "preparacion_no_autorizada"
                )

            plan = preparado.get("contrato")

            if (
                not isinstance(plan, dict)
                or plan.get("modelo")
                    != expediente.modelo_contexto
                or plan.get("operacion") != "contar"
                or not isinstance(
                    plan.get("filtros"), list
                )
                or len(plan["filtros"]) != 1
                or plan.get("orden") != []
                or plan.get(
                    "condiciones_no_resueltas"
                ) != []
            ):
                return _rechazo(
                    "contrato_no_autorizado"
                )

            # Consumo unico ANTES del despacho.
            # El bloqueo se mantiene hasta terminar
            # la transaccion.
            expediente.estado = "COMPLETADO"
            expediente.version += 1
            expediente.save(
                update_fields=[
                    "estado",
                    "version",
                    "actualizado",
                ]
            )

            # En E03-A se sustituye este ejecutor
            # mediante mock en todas las pruebas.
            # ARC003-B05-E03-B02:
            # Aislar posibles errores SQL en un savepoint.
            # Capturar la excepcion DESPUES de salir del
            # atomic interno evita invalidar la transaccion
            # que registra el consumo del expediente.
            try:
                with transaction.atomic():
                    resultado = ejecutar_plan_datos(plan)
            except Exception:
                return _rechazo(
                    "ejecutor_no_disponible"
                )

            correcto = (
                isinstance(resultado, dict)
                and resultado.get("ok") is True
                and resultado.get("ejecutado") is True
                and resultado.get("operacion") == "contar"
                and resultado.get("modelo")
                    == expediente.modelo_contexto
                and type(resultado.get("total")) is int
                and resultado["total"] >= 0
            )

            if not correcto:
                return _rechazo(
                    "ejecucion_host_rechazada"
                )

            return {
                "ok": True,
                "version": VERSION,
                "estado": "conteo_filtrado_ejecutado",
                "identificador": str(expediente.pk),
                "version_expediente": expediente.version,
                "modelo": expediente.modelo_contexto,
                "operacion": "contar",
                "total": resultado["total"],
                "ejecutado": True,
                "resultado": resultado,
            }

    except Exception:
        return _rechazo(
            "error_transaccional"
        )
