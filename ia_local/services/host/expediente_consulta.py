
"""IA-LLM008-F5-07-13-B02: expediente transaccional."""

import hashlib
import hmac
import secrets
from copy import deepcopy
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from ia_local.models import IAExpedienteConsulta

from ia_local.services.llm.trazabilidad_compuesta import (
    _verificar_coleccion_identificada,
    preparar_opciones_restriccion,
    incorporar_eleccion_restriccion,
    reconstruir_arbol_logico_certificado,
)

TTL = 300


def _error(estado):
    return {
        "ok": False,
        "estado": estado,
        "ejecutable": False,
        "ejecutado": False,
    }


def _identidad(request):
    usuario = getattr(request, "user", None)

    if (
        usuario is None
        or not usuario.is_authenticated
        or usuario.pk is None
    ):
        return None

    return str(usuario.pk)


def _sesion(request, crear=False):
    sesion = getattr(request, "session", None)

    if sesion is None:
        return None

    if crear and not sesion.session_key:
        sesion.save()

    return sesion.session_key


def _token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _obtener_bloqueado(request, identificador):
    identidad = _identidad(request)
    sesion = _sesion(request)

    if not identidad or not sesion:
        return None

    try:
        expediente = (
            IAExpedienteConsulta.objects
            .select_for_update()
            .get(pk=identificador)
        )
    except (
        IAExpedienteConsulta.DoesNotExist,
        ValueError,
        TypeError,
    ):
        return None

    if (
        expediente.usuario_id != identidad
        or expediente.session_key != sesion
    ):
        return None

    return expediente


def _vigente(expediente):
    return (
        expediente.estado in ("ABIERTO", "PENDIENTE")
        and expediente.fecha_expiracion > timezone.now()
    )


def crear_expediente(request, coleccion, modelo):
    """
    SOLO para uso interno desde un flujo confiable.

    El caller debe haber producido y validado la colección
    en el servidor. No acepta datos directamente del navegador.
    """
    identidad = _identidad(request)
    sesion = _sesion(request, crear=True)

    if not identidad or not sesion:
        return _error("identidad_o_sesion_no_disponible")

    if (
        not _verificar_coleccion_identificada(coleccion)
        or not isinstance(modelo, str)
        or not modelo.strip()
    ):
        return _error("coleccion_invalida")

    if coleccion.get("ejecutable") is not False:
        return _error("coleccion_no_diagnostica")

    try:
        with transaction.atomic():
            expediente = IAExpedienteConsulta.objects.create(
                session_key=sesion,
                usuario_id=identidad,
                pregunta_original=coleccion["pregunta_original"],
                modelo_contexto=modelo,
                coleccion=deepcopy(coleccion),
                arbol_logico={},
                asociaciones={},
                estado="ABIERTO",
                version=1,
                fecha_expiracion=(
                    timezone.now() + timedelta(seconds=TTL)
                ),
            )
    except (TypeError, ValueError, KeyError):
        return _error("expediente_no_creado")

    return {
        "ok": True,
        "estado": "expediente_creado",
        "identificador": str(expediente.pk),
        "version": expediente.version,
        "ejecutable": False,
        "ejecutado": False,
    }


def iniciar_decision(
    request, identificador, restriccion_id, version
):
    """
    Crea un desafío de un solo uso vinculado
    a expediente, identidad, sesión y versión.
    """
    if (
        type(version) is not int
        or type(restriccion_id) is not str
        or not restriccion_id
    ):
        return _error("entrada_invalida")

    with transaction.atomic():
        expediente = _obtener_bloqueado(
            request, identificador
        )

        if expediente is None:
            return _error("expediente_no_disponible")

        if not _vigente(expediente):
            return _error("expediente_no_vigente")

        if expediente.version != version:
            return _error("version_obsoleta")

        if expediente.arbol_logico.get("_desafio"):
            return _error("decision_ya_pendiente")

        opciones = preparar_opciones_restriccion(
            expediente.coleccion,
            restriccion_id,
            expediente.modelo_contexto,
        )

        alternativas = opciones.get("opciones", [])

        if (
            opciones.get("ok") is not True
            or not isinstance(alternativas, list)
            or not alternativas
            or any(
                not isinstance(o, dict)
                or not isinstance(o.get("id"), str)
                for o in alternativas
            )
        ):
            return _error("opciones_no_certificadas")

        token = secrets.token_urlsafe(32)

        expediente.arbol_logico = {
            "_desafio": {
                "token_hash": _token_hash(token),
                "restriccion_id": restriccion_id,
                "version": version,
                "opciones": [o["id"] for o in alternativas],
                "creado": timezone.now().timestamp(),
            }
        }

        expediente.estado = "PENDIENTE"
        expediente.save(
            update_fields=[
                "arbol_logico",
                "estado",
                "actualizado",
            ]
        )

    return {
        "ok": True,
        "estado": "decision_iniciada",
        "identificador": str(expediente.pk),
        "restriccion_id": restriccion_id,
        "version": version,
        "token": token,
        "opciones": deepcopy(alternativas),
        "ejecutable": False,
        "ejecutado": False,
    }


def confirmar_decision(
    request,
    identificador,
    restriccion_id,
    opcion_id,
    token,
    version,
):
    """
    Confirmación atómica; el bloqueo de fila impide
    consumir dos veces una misma versión.
    """
    if (
        type(version) is not int
        or not all(
            isinstance(v, str) and 0 < len(v) <= 256
            for v in (restriccion_id, opcion_id, token)
        )
    ):
        return _error("entrada_invalida")

    with transaction.atomic():
        expediente = _obtener_bloqueado(
            request, identificador
        )

        if expediente is None:
            return _error("expediente_no_disponible")

        if not _vigente(expediente):
            return _error("expediente_no_vigente")

        if expediente.version != version:
            return _error("version_obsoleta")

        desafio = expediente.arbol_logico.get("_desafio")

        if not isinstance(desafio, dict):
            return _error("decision_no_disponible")

        if (
            desafio.get("version") != version
            or desafio.get("restriccion_id")
                != restriccion_id
        ):
            return _error("decision_no_corresponde")

        if not hmac.compare_digest(
            _token_hash(token),
            str(desafio.get("token_hash", "")),
        ):
            return _error("token_invalido")

        creado = desafio.get("creado")

        if (
            type(creado) not in (int, float)
            or not 0 <= timezone.now().timestamp() - creado <= TTL
        ):
            return _error("decision_expirada")

        if opcion_id not in desafio.get("opciones", []):
            return _error("opcion_no_ofrecida")

        resultado = incorporar_eleccion_restriccion(
            expediente.coleccion,
            restriccion_id,
            expediente.modelo_contexto,
            opcion_id,
        )

        if (
            resultado.get("ok") is not True
            or not _verificar_coleccion_identificada(resultado)
            or resultado.get("ejecutable") is not False
        ):
            return _error("eleccion_rechazada_host")

        expediente.coleccion = deepcopy(resultado)
        expediente.arbol_logico = {}
        expediente.estado = "ABIERTO"
        expediente.version += 1
        expediente.save(
            update_fields=[
                "coleccion",
                "arbol_logico",
                "estado",
                "version",
                "actualizado",
            ]
        )

        return {
            "ok": True,
            "estado": "decision_confirmada",
            "identificador": str(expediente.pk),
            "version": expediente.version,
            "pendientes": deepcopy(resultado.get("pendientes", [])),
            "ejecutable": False,
            "ejecutado": False,
        }


def vincular_arbol_diagnostico(
    request,
    identificador,
    resultado_query,
    asociaciones,
    version,
):
    """
    SOLO para resultados QUERY generados internamente.

    No certifica autenticidad de las asociaciones ni
    cobertura de la pregunta original.
    """
    if type(version) is not int:
        return _error("version_invalida")

    with transaction.atomic():
        expediente = _obtener_bloqueado(
            request, identificador
        )

        if expediente is None:
            return _error("expediente_no_disponible")

        if not _vigente(expediente):
            return _error("expediente_no_vigente")

        if expediente.version != version:
            return _error("version_obsoleta")

        if expediente.arbol_logico.get("_desafio"):
            return _error("decision_pendiente")

        if expediente.arbol_logico:
            return _error("arbol_ya_vinculado")

        reconstruccion = reconstruir_arbol_logico_certificado(
            expediente.coleccion,
            resultado_query,
            asociaciones,
        )

        if (
            reconstruccion.get("ok") is not True
            or reconstruccion.get("arbol_derivado_validado_host")
                is not True
            or reconstruccion.get("ejecutable") is not False
            or reconstruccion.get("modelo")
                != expediente.modelo_contexto
        ):
            return _error("reconstruccion_rechazada")

        expediente.arbol_logico = deepcopy(
            reconstruccion["arbol_derivado"]
        )

        expediente.asociaciones = deepcopy(asociaciones)
        expediente.version += 1

        expediente.save(
            update_fields=[
                "arbol_logico",
                "asociaciones",
                "version",
                "actualizado",
            ]
        )

        return {
            "ok": True,
            "estado": "arbol_vinculado_diagnostico",
            "identificador": str(expediente.pk),
            "version": expediente.version,
            "cobertura_verificada": False,
            "ejecutable": False,
            "ejecutado": False,
        }
