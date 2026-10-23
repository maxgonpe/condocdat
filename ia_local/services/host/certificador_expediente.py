"""
IA-LLM008-D06-B — Verificacion persistente del expediente.

Control de identidad, sesion, version, vigencia e integridad.

No ejecuta ORM de negocio.
No certifica cobertura semantica integral.
No concede autorizacion de ejecucion.
"""

from django.db import transaction

from ia_local.services.host.expediente_consulta import (
    _obtener_bloqueado,
    _vigente,
)

from ia_local.services.llm.trazabilidad_compuesta import (
    _verificar_coleccion_identificada,
)


VERSION = "IA-LLM008-D06-B-v1"


def _respuesta(estado, pendientes=None, **datos):
    return {
        "ok": False,
        "version_certificador": VERSION,
        "estado": estado,
        "pendientes": pendientes or [],
        "cobertura_verificada": False,
        "ejecutable": False,
        "ejecutado": False,
        **datos,
    }


def certificar_expediente(request, identificador, version):
    """
    Lee el expediente del servidor.

    El cliente solo proporciona identificador y version.
    No acepta colecciones ni arboles externos.
    """

    if type(version) is not int or version < 1:
        return _respuesta("version_invalida")

    if not identificador:
        return _respuesta("identificador_invalido")

    with transaction.atomic():
        expediente = _obtener_bloqueado(
            request, identificador
        )

        if expediente is None:
            return _respuesta("expediente_no_disponible")

        if not _vigente(expediente):
            return _respuesta("expediente_no_vigente")

        if expediente.version != version:
            return _respuesta("version_obsoleta")

        if expediente.estado != "ABIERTO":
            return _respuesta(
                "estado_no_certificable",
                ["expediente_no_abierto"],
            )

        coleccion = expediente.coleccion
        arbol = expediente.arbol_logico
        asociaciones = expediente.asociaciones

        if (
            not isinstance(coleccion, dict)
            or not _verificar_coleccion_identificada(coleccion)
            or coleccion.get("ejecutable") is not False
            or coleccion.get("pregunta_original")
                != expediente.pregunta_original
        ):
            return _respuesta(
                "coleccion_invalida",
                ["coleccion_no_verificable"],
            )

        if not isinstance(arbol, dict):
            return _respuesta("arbol_invalido")

        if not isinstance(asociaciones, dict):
            return _respuesta("asociaciones_invalidas")

        if "_desafio" in arbol:
            return _respuesta(
                "decision_pendiente",
                ["aclaracion_sin_confirmar"],
            )

        pendientes = []

        restricciones = coleccion.get("restricciones", [])

        if not isinstance(restricciones, list):
            return _respuesta(
                "restricciones_invalidas"
            )

        # Las selecciones individuales no demuestran
        # la cobertura de la pregunta completa.
        if coleccion.get("pendientes"):
            pendientes.append(
                "restricciones_sin_resolver"
            )

        if restricciones and not arbol:
            pendientes.append(
                "arbol_logico_no_vinculado"
            )

        if arbol and not asociaciones:
            pendientes.append(
                "asociaciones_no_disponibles"
            )

        # Bloqueo obligatorio hasta contar con
        # certificacion de cobertura independiente.
        pendientes.append(
            "cobertura_semantica_integral_no_certificada"
        )

        return _respuesta(
            "certificacion_pendiente",
            pendientes,
            identificador=str(expediente.pk),
            version_expediente=expediente.version,
            modelo_contexto=expediente.modelo_contexto,
        )
