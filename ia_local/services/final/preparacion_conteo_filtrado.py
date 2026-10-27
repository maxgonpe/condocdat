"""
ARC003-B05-E01.

Preparacion transaccional de un conteo filtrado certificado.

No ejecuta consultas de negocio.
No consume expedientes.
No recibe planes ni certificados del navegador.
No autoriza ejecucion.
"""

from copy import deepcopy

from django.db import transaction

from ia_local.services.host.expediente_consulta import (
    _obtener_bloqueado,
    _vigente,
)
from ia_local.services.host.catalogo_datos import (
    buscar_modelo_datos,
)
from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)
from ia_local.services.host.registro_politicas import (
    autorizar_lectura_configurada,
)
from ia_local.services.llm.certificador_limitado import (
    PATRON,
    certificar_consulta_limitada,
)
from ia_local.services.llm.trazabilidad_compuesta import (
    _verificar_coleccion_identificada,
)


VERSION = "IA-ARC003-B05-E01-v1"


def _rechazo(estado):
    return {
        "ok": False,
        "version": VERSION,
        "estado": estado,
        "contrato_preparado": False,
        "ejecutable": False,
        "ejecutado": False,
    }


def preparar_conteo_filtrado_certificado(
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

            pregunta = expediente.pregunta_original
            coleccion = expediente.coleccion

            if (
                not isinstance(pregunta, str)
                or not isinstance(coleccion, dict)
                or not _verificar_coleccion_identificada(
                    coleccion
                )
                or coleccion.get("pregunta_original")
                    != pregunta
                or not isinstance(
                    coleccion.get("pendientes"), list
                )
                or expediente.arbol_logico != {}
                or expediente.asociaciones != {}
            ):
                return _rechazo(
                    "coleccion_no_certificable"
                )

            # Solo una restriccion para esta gramatica.
            restricciones = coleccion.get(
                "restricciones"
            )

            if (
                not isinstance(restricciones, list)
                or len(restricciones) != 1
            ):
                return _rechazo(
                    "restricciones_fuera_de_alcance"
                )

            coincidencia = PATRON.fullmatch(pregunta)

            if coincidencia is None:
                return _rechazo(
                    "gramatica_no_certificable"
                )

            entidad = coincidencia.group("entidad")
            campo = coincidencia.group("campo")
            valor = coincidencia.group("valor")

            evidencia = pregunta[
                coincidencia.start("campo"):
                coincidencia.end("valor")
            ]

            restriccion = restricciones[0]

            # La unica restriccion pendiente debe ser
            # exactamente la que certificaremos ahora.
            if (
                coleccion["pendientes"]
                != [restriccion.get("id")]
            ):
                return _rechazo(
                    "pendientes_no_equivalentes"
                )

            if (
                restriccion.get("tipo") != "filtro"
                or restriccion.get("evidencia_textual")
                    != evidencia
                or restriccion.get(
                    "estado_certificacion"
                ) != "pendiente"
                or restriccion.get("seleccion") is not None
            ):
                return _rechazo(
                    "restriccion_no_equivalente"
                )

            candidatos = buscar_modelo_datos(
                entidad
            )

            if len(candidatos) != 1:
                return _rechazo(
                    "entidad_no_inequivoca"
                )

            modelo = candidatos[0].get("label")

            if modelo != expediente.modelo_contexto:
                return _rechazo(
                    "modelo_contexto_no_equivalente"
                )

            # Construccion local, desde la pregunta
            # persistida y no desde un plan externo.
            propuesta = {
                "modelo": modelo,
                "operacion": "contar",
                "filtros": [{
                    "campo": campo,
                    "operador": "exact",
                    "valor": valor,
                }],
                "orden": [],
                "limite": 10,
                "condiciones_no_resueltas": [],
            }

            validacion = validar_plan_datos(
                propuesta
            )

            if (
                not isinstance(validacion, dict)
                or validacion.get("ok") is not True
                or validacion.get("plan_validado")
                    is not True
            ):
                return _rechazo(
                    "plan_host_no_validado"
                )

            plan = validacion.get("plan")

            if not isinstance(plan, dict):
                return _rechazo("plan_host_ausente")

            certificacion = certificar_consulta_limitada(
                pregunta,
                deepcopy(plan),
            )

            if (
                certificacion.get("ok") is not True
                or certificacion.get(
                    "certificacion_limitada"
                ) is not True
                or certificacion.get("estado")
                    != "certificado_limitado"
                or certificacion.get("ejecutable")
                    is not False
            ):
                return _rechazo(
                    "certificacion_no_disponible"
                )

            autorizacion = autorizar_lectura_configurada(
                request.user,
                deepcopy(plan),
            )

            if (
                autorizacion.get("ok") is not True
                or autorizacion.get("autorizado")
                    is not True
                or autorizacion.get("ejecutable")
                    is not False
            ):
                return _rechazo(
                    "lectura_no_autorizada"
                )

            return {
                "ok": True,
                "version": VERSION,
                "estado": "conteo_filtrado_preparado",
                "identificador": str(expediente.pk),
                "version_expediente": version,
                "modelo": modelo,
                "tipo_contrato": "plan_host",
                "contrato": deepcopy(plan),
                "contrato_preparado": True,
                "certificacion": {
                    "estado": "certificado_limitado",
                    "gramatica":
                        "conteo_igualdad_textual_v1",
                },
                "autorizacion": {
                    "estado": "lectura_autorizada",
                    "alcance": "universo_completo",
                },
                "ejecutable": False,
                "ejecutado": False,
            }

    except Exception:
        # No revelar detalles internos al consumidor.
        return _rechazo("preparacion_no_disponible")
