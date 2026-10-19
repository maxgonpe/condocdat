from __future__ import annotations

import hashlib
import json
from typing import Any

from django.core.serializers.json import (
    DjangoJSONEncoder,
)
from django.db import transaction
from django.utils import timezone

from ia_local.models import (
    IAAliasCampo,
    IAAliasEntidad,
    IAAliasValor,
    IAPropuestaAprendizaje,
    IAReglaDeclarativa,
)

from .aliases_campo import (
    guardar_alias_campo,
    validar_alias_campo,
)

from .aliases_entidad import (
    guardar_alias_entidad,
    validar_alias_entidad,
)

from .aliases_valor import (
    guardar_alias_valor,
    validar_alias_valor,
)

from .normalizacion import (
    normalizar_texto,
    texto_limpio,
)

from .reglas_declarativas import (
    guardar_regla_declarativa,
    validar_regla_declarativa,
)


VERSION = "IA-SEM007-v1"


# ============================================================
# UTILIDADES
# ============================================================


def _json_seguro(
    valor: Any,
) -> Any:
    """
    Convierte estructuras con date, Decimal, UUID, etc.
    a tipos seguros para JSONField.
    """

    return json.loads(
        json.dumps(
            valor,
            cls=DjangoJSONEncoder,
            ensure_ascii=False,
        )
    )


def _normalizar_tipo(
    tipo: str,
) -> str:

    return (
        texto_limpio(
            tipo
        )
        .upper()
    )


def _huella_propuesta(
    *,
    tipo: str,
    expresion: str,
    datos: dict[str, Any],
) -> str:

    estructura = {
        "tipo":
            _normalizar_tipo(
                tipo
            ),

        "expresion":
            normalizar_texto(
                expresion
            ),

        "datos":
            datos,
    }

    serializado = json.dumps(
        estructura,
        ensure_ascii=False,
        sort_keys=True,
        cls=DjangoJSONEncoder,
        separators=(
            ",",
            ":",
        ),
    )

    return hashlib.sha256(
        serializado.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================
# VALIDACIÓN SEGÚN TIPO
# ============================================================


def validar_propuesta(
    *,
    tipo: str,
    expresion: str,
    datos: dict[str, Any],
) -> dict[str, Any]:

    tipo = _normalizar_tipo(
        tipo
    )

    if tipo == IAPropuestaAprendizaje.TIPO_ENTIDAD:

        return validar_alias_entidad(
            expresion=expresion,
            modelo_destino=datos.get(
                "modelo"
            ),
        )

    if tipo == IAPropuestaAprendizaje.TIPO_CAMPO:

        return validar_alias_campo(
            modelo=datos.get(
                "modelo"
            ),
            expresion=expresion,
            campo_destino=datos.get(
                "campo"
            ),
        )

    if tipo == IAPropuestaAprendizaje.TIPO_VALOR:

        return validar_alias_valor(
            modelo=datos.get(
                "modelo"
            ),
            campo=datos.get(
                "campo"
            ),
            expresion=expresion,
            valor_destino=datos.get(
                "valor"
            ),
        )

    if tipo == IAPropuestaAprendizaje.TIPO_REGLA:

        return validar_regla_declarativa(
            expresion=expresion,
            modelo=datos.get(
                "modelo"
            ),
            operacion=datos.get(
                "operacion",
                "listar",
            ),
            condiciones=datos.get(
                "condiciones",
                [],
            ),
        )

    return {
        "ok":
            False,

        "version":
            VERSION,

        "estado":
            "tipo_invalido",

        "tipo":
            tipo,

        "tipos_permitidos": [
            IAPropuestaAprendizaje.TIPO_ENTIDAD,
            IAPropuestaAprendizaje.TIPO_CAMPO,
            IAPropuestaAprendizaje.TIPO_VALOR,
            IAPropuestaAprendizaje.TIPO_REGLA,
        ],

        "llm_invocado":
            False,
    }


# ============================================================
# PROPONER
# ============================================================


@transaction.atomic
def proponer_aprendizaje(
    *,
    tipo: str,
    expresion: str,
    datos: dict[str, Any],
    motivo: str = "",
) -> dict[str, Any]:

    tipo = _normalizar_tipo(
        tipo
    )

    expresion = texto_limpio(
        expresion
    )

    if not isinstance(
        datos,
        dict,
    ):

        return {
            "ok":
                False,

            "creada":
                False,

            "estado":
                "datos_invalidos",

            "llm_invocado":
                False,
        }

    validacion = validar_propuesta(
        tipo=tipo,
        expresion=expresion,
        datos=datos,
    )

    if not validacion.get(
        "ok"
    ):

        return {
            "ok":
                False,

            "creada":
                False,

            "estado":
                "propuesta_rechazada",

            "validacion":
                validacion,

            "llm_invocado":
                False,
        }

    datos_seguros = _json_seguro(
        datos
    )

    huella = _huella_propuesta(
        tipo=tipo,
        expresion=expresion,
        datos=datos_seguros,
    )

    pendiente = (
        IAPropuestaAprendizaje.objects
        .filter(
            huella=huella,
            estado=(
                IAPropuestaAprendizaje
                .ESTADO_PENDIENTE
            ),
        )
        .first()
    )

    if pendiente:

        return {
            "ok":
                False,

            "creada":
                False,

            "estado":
                "propuesta_duplicada",

            "propuesta_id":
                pendiente.pk,

            "llm_invocado":
                False,
        }

    propuesta = (
        IAPropuestaAprendizaje.objects.create(
            tipo=tipo,
            expresion=expresion,
            expresion_normalizada=(
                normalizar_texto(
                    expresion
                )
            ),
            datos=datos_seguros,
            validacion=_json_seguro(
                validacion
            ),
            estado=(
                IAPropuestaAprendizaje
                .ESTADO_PENDIENTE
            ),
            huella=huella,
            motivo=texto_limpio(
                motivo
            ),
        )
    )

    return {
        "ok":
            True,

        "creada":
            True,

        "estado":
            "pendiente_confirmacion",

        "propuesta": {
            "id":
                propuesta.pk,

            "tipo":
                propuesta.tipo,

            "expresion":
                propuesta.expresion,

            "datos":
                propuesta.datos,

            "estado":
                propuesta.estado,

            "motivo":
                propuesta.motivo,
        },

        "validacion":
            propuesta.validacion,

        "llm_invocado":
            False,
    }


# ============================================================
# APLICAR SEGÚN TIPO
# ============================================================


def _aplicar_propuesta(
    propuesta: IAPropuestaAprendizaje,
) -> dict[str, Any]:

    datos = propuesta.datos

    if (
        propuesta.tipo
        == IAPropuestaAprendizaje.TIPO_ENTIDAD
    ):

        return guardar_alias_entidad(
            expresion=propuesta.expresion,
            modelo_destino=datos.get(
                "modelo"
            ),
            observacion=propuesta.motivo,
            origen=IAAliasEntidad.ORIGEN_APRENDIDO,
        )

    if (
        propuesta.tipo
        == IAPropuestaAprendizaje.TIPO_CAMPO
    ):

        return guardar_alias_campo(
            modelo=datos.get(
                "modelo"
            ),
            expresion=propuesta.expresion,
            campo_destino=datos.get(
                "campo"
            ),
            observacion=propuesta.motivo,
            origen=IAAliasCampo.ORIGEN_APRENDIDO,
        )

    if (
        propuesta.tipo
        == IAPropuestaAprendizaje.TIPO_VALOR
    ):

        return guardar_alias_valor(
            modelo=datos.get(
                "modelo"
            ),
            campo=datos.get(
                "campo"
            ),
            expresion=propuesta.expresion,
            valor_destino=datos.get(
                "valor"
            ),
            observacion=propuesta.motivo,
            origen=IAAliasValor.ORIGEN_APRENDIDO,
        )

    if (
        propuesta.tipo
        == IAPropuestaAprendizaje.TIPO_REGLA
    ):

        return guardar_regla_declarativa(
            expresion=propuesta.expresion,
            modelo=datos.get(
                "modelo"
            ),
            operacion=datos.get(
                "operacion",
                "listar",
            ),
            condiciones=datos.get(
                "condiciones",
                [],
            ),
            observacion=propuesta.motivo,
            origen=(
                IAReglaDeclarativa
                .ORIGEN_APRENDIDO
            ),
        )

    return {
        "ok":
            False,

        "estado":
            "tipo_invalido",

        "llm_invocado":
            False,
    }


# ============================================================
# CONFIRMAR
# ============================================================


@transaction.atomic
def confirmar_propuesta(
    propuesta_id: int,
) -> dict[str, Any]:

    try:

        propuesta = (
            IAPropuestaAprendizaje.objects
            .select_for_update()
            .get(
                pk=propuesta_id
            )
        )

    except IAPropuestaAprendizaje.DoesNotExist:

        return {
            "ok":
                False,

            "estado":
                "propuesta_inexistente",

            "llm_invocado":
                False,
        }

    if (
        propuesta.estado
        != IAPropuestaAprendizaje.ESTADO_PENDIENTE
    ):

        return {
            "ok":
                False,

            "estado":
                "propuesta_no_pendiente",

            "propuesta_id":
                propuesta.pk,

            "estado_actual":
                propuesta.estado,

            "llm_invocado":
                False,
        }

    # --------------------------------------------------------
    # REVALIDAR
    # --------------------------------------------------------

    validacion_actual = validar_propuesta(
        tipo=propuesta.tipo,
        expresion=propuesta.expresion,
        datos=propuesta.datos,
    )

    propuesta.validacion = _json_seguro(
        validacion_actual
    )

    if not validacion_actual.get(
        "ok"
    ):

        propuesta.estado = (
            IAPropuestaAprendizaje
            .ESTADO_INVALIDADA
        )

        propuesta.resultado = {
            "estado":
                "fallo_revalidacion",

            "validacion":
                _json_seguro(
                    validacion_actual
                ),
        }

        propuesta.resolved_at = timezone.now()

        propuesta.save(
            update_fields=[
                "validacion",
                "estado",
                "resultado",
                "resolved_at",
                "updated_at",
            ]
        )

        return {
            "ok":
                False,

            "estado":
                "propuesta_invalidada",

            "propuesta_id":
                propuesta.pk,

            "validacion":
                validacion_actual,

            "llm_invocado":
                False,
        }

    # --------------------------------------------------------
    # APLICAR
    # --------------------------------------------------------

    resultado = _aplicar_propuesta(
        propuesta
    )

    propuesta.resultado = _json_seguro(
        resultado
    )

    propuesta.resolved_at = timezone.now()

    if resultado.get(
        "ok"
    ):

        propuesta.estado = (
            IAPropuestaAprendizaje
            .ESTADO_APLICADA
        )

    else:

        propuesta.estado = (
            IAPropuestaAprendizaje
            .ESTADO_INVALIDADA
        )

    propuesta.save(
        update_fields=[
            "validacion",
            "estado",
            "resultado",
            "resolved_at",
            "updated_at",
        ]
    )

    return {
        "ok":
            bool(
                resultado.get(
                    "ok"
                )
            ),

        "estado":
            (
                "propuesta_aplicada"
                if resultado.get(
                    "ok"
                )
                else "propuesta_invalidada"
            ),

        "propuesta_id":
            propuesta.pk,

        "resultado":
            resultado,

        "llm_invocado":
            False,
    }


# ============================================================
# RECHAZAR
# ============================================================


@transaction.atomic
def rechazar_propuesta(
    propuesta_id: int,
    *,
    motivo: str = "",
) -> dict[str, Any]:

    try:

        propuesta = (
            IAPropuestaAprendizaje.objects
            .select_for_update()
            .get(
                pk=propuesta_id
            )
        )

    except IAPropuestaAprendizaje.DoesNotExist:

        return {
            "ok":
                False,

            "estado":
                "propuesta_inexistente",

            "llm_invocado":
                False,
        }

    if (
        propuesta.estado
        != IAPropuestaAprendizaje.ESTADO_PENDIENTE
    ):

        return {
            "ok":
                False,

            "estado":
                "propuesta_no_pendiente",

            "estado_actual":
                propuesta.estado,

            "llm_invocado":
                False,
        }

    motivo = texto_limpio(
        motivo
    )

    if motivo:

        propuesta.motivo = motivo

    propuesta.estado = (
        IAPropuestaAprendizaje
        .ESTADO_RECHAZADA
    )

    propuesta.resultado = {
        "estado":
            "rechazada_por_usuario",
    }

    propuesta.resolved_at = timezone.now()

    propuesta.save(
        update_fields=[
            "motivo",
            "estado",
            "resultado",
            "resolved_at",
            "updated_at",
        ]
    )

    return {
        "ok":
            True,

        "estado":
            "propuesta_rechazada",

        "propuesta_id":
            propuesta.pk,

        "llm_invocado":
            False,
    }


# ============================================================
# CONSULTA
# ============================================================


def obtener_propuesta(
    propuesta_id: int,
) -> dict[str, Any]:

    try:

        propuesta = (
            IAPropuestaAprendizaje.objects.get(
                pk=propuesta_id
            )
        )

    except IAPropuestaAprendizaje.DoesNotExist:

        return {
            "ok":
                False,

            "estado":
                "propuesta_inexistente",

            "llm_invocado":
                False,
        }

    return {
        "ok":
            True,

        "propuesta": {
            "id":
                propuesta.pk,

            "tipo":
                propuesta.tipo,

            "expresion":
                propuesta.expresion,

            "expresion_normalizada":
                propuesta.expresion_normalizada,

            "datos":
                propuesta.datos,

            "validacion":
                propuesta.validacion,

            "estado":
                propuesta.estado,

            "motivo":
                propuesta.motivo,

            "resultado":
                propuesta.resultado,

            "created_at":
                propuesta.created_at,

            "resolved_at":
                propuesta.resolved_at,
        },

        "llm_invocado":
            False,
    }


def listar_propuestas(
    *,
    estado: str | None = None,
) -> list[dict[str, Any]]:

    queryset = (
        IAPropuestaAprendizaje.objects
        .all()
    )

    if estado:

        queryset = queryset.filter(
            estado=_normalizar_tipo(
                estado
            )
        )

    return [
        {
            "id":
                propuesta.pk,

            "tipo":
                propuesta.tipo,

            "expresion":
                propuesta.expresion,

            "estado":
                propuesta.estado,

            "motivo":
                propuesta.motivo,

            "created_at":
                propuesta.created_at,

            "resolved_at":
                propuesta.resolved_at,
        }

        for propuesta
        in queryset
    ]