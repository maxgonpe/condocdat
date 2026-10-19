from __future__ import annotations

from typing import Any

from django.apps import apps
from django.db import transaction
from django.db.models import F

from ia_local.models import (
    IAAliasCampo,
)

from .normalizacion import (
    normalizar_texto,
    texto_limpio,
)


VERSION = "IA-SEM003-v1"


# ============================================================
# MODELO
# ============================================================


def _resolver_modelo(
    referencia: str,
):

    referencia = texto_limpio(
        referencia
    )

    if (
        not referencia
        or "." not in referencia
    ):
        return None

    app_label, nombre_modelo = (
        referencia.split(
            ".",
            1,
        )
    )

    try:

        return apps.get_model(
            app_label,
            nombre_modelo,
        )

    except LookupError:

        return None


# ============================================================
# CAMPO
# ============================================================


def _resolver_campo(
    modelo,
    nombre_campo: str,
):

    nombre_campo = texto_limpio(
        nombre_campo
    )

    if not nombre_campo:
        return None

    try:

        return modelo._meta.get_field(
            nombre_campo
        )

    except Exception:

        return None


# ============================================================
# VOCABULARIO AUTOMÁTICO DEL CAMPO
# ============================================================


def _terminos_automaticos_campo(
    campo,
) -> list[dict[str, Any]]:

    candidatos = [
        (
            campo.name,
            "nombre_campo",
        ),
        (
            getattr(
                campo,
                "verbose_name",
                "",
            ),
            "verbose_name",
        ),
    ]

    resultado = []
    vistos = set()

    for texto, origen in candidatos:

        texto = texto_limpio(
            texto
        )

        normalizado = normalizar_texto(
            texto
        )

        if (
            not normalizado
            or normalizado in vistos
        ):
            continue

        vistos.add(
            normalizado
        )

        resultado.append(
            {
                "texto":
                    texto,

                "normalizado":
                    normalizado,

                "origen":
                    origen,
            }
        )

    return resultado


def buscar_colisiones_automaticas_campo(
    *,
    modelo: str,
    expresion: str,
) -> list[dict[str, Any]]:

    modelo_django = (
        _resolver_modelo(
            modelo
        )
    )

    if modelo_django is None:
        return []

    objetivo = normalizar_texto(
        expresion
    )

    if not objetivo:
        return []

    resultado = []

    for campo in modelo_django._meta.get_fields():

        if bool(
            getattr(
                campo,
                "is_relation",
                False,
            )
        ):
            continue

        for termino in (
            _terminos_automaticos_campo(
                campo
            )
        ):

            if (
                termino[
                    "normalizado"
                ]
                != objetivo
            ):
                continue

            resultado.append(
                {
                    "campo":
                        campo.name,

                    "texto":
                        termino[
                            "texto"
                        ],

                    "normalizado":
                        termino[
                            "normalizado"
                        ],

                    "origen":
                        termino[
                            "origen"
                        ],
                }
            )

    return resultado


# ============================================================
# VALIDACIÓN
# ============================================================


def validar_alias_campo(
    *,
    modelo: str,
    expresion: str,
    campo_destino: str,
) -> dict[str, Any]:

    expresion = texto_limpio(
        expresion
    )

    expresion_normalizada = (
        normalizar_texto(
            expresion
        )
    )

    base = {
        "ok":
            False,

        "version":
            VERSION,

        "modelo":
            modelo,

        "expresion":
            expresion,

        "expresion_normalizada":
            expresion_normalizada,

        "campo_destino":
            campo_destino,

        "llm_invocado":
            False,
    }

    if not expresion_normalizada:

        return {
            **base,

            "estado":
                "expresion_vacia",

            "razon":
                (
                    "La expresión no contiene "
                    "vocabulario utilizable."
                ),
        }

    modelo_django = (
        _resolver_modelo(
            modelo
        )
    )

    if modelo_django is None:

        return {
            **base,

            "estado":
                "modelo_invalido",

            "razon":
                (
                    "El modelo no existe en el "
                    "registro Django del host."
                ),
        }

    modelo_real = (
        modelo_django._meta.label
    )

    base[
        "modelo"
    ] = modelo_real

    campo = _resolver_campo(
        modelo_django,
        campo_destino,
    )

    if campo is None:

        return {
            **base,

            "estado":
                "campo_invalido",

            "razon":
                (
                    "El campo destino no existe "
                    "en el modelo indicado."
                ),
        }

    if bool(
        getattr(
            campo,
            "is_relation",
            False,
        )
    ):

        return {
            **base,

            "estado":
                "campo_relacional",

            "razon":
                (
                    "SEM003 sólo admite aliases de campos "
                    "escalares. Las relaciones se tratarán "
                    "como conocimiento relacional."
                ),
        }

    base[
        "campo_destino"
    ] = campo.name

    # --------------------------------------------------------
    # VOCABULARIO AUTOMÁTICO
    # --------------------------------------------------------

    automaticas = (
        buscar_colisiones_automaticas_campo(
            modelo=modelo_real,
            expresion=expresion,
        )
    )

    if automaticas:

        campos_automaticos = {
            item[
                "campo"
            ]
            for item
            in automaticas
        }

        if campos_automaticos == {
            campo.name
        }:

            return {
                **base,

                "estado":
                    "redundante_automatico",

                "razon":
                    (
                        "La expresión ya pertenece "
                        "al vocabulario automático "
                        "del campo destino."
                    ),

                "colisiones_automaticas":
                    automaticas,
            }

        return {
            **base,

            "estado":
                "conflicto_automatico",

            "razon":
                (
                    "La expresión identifica "
                    "automáticamente otro campo "
                    "del mismo modelo."
                ),

            "colisiones_automaticas":
                automaticas,
        }

    # --------------------------------------------------------
    # ALIAS LOCAL
    # --------------------------------------------------------

    existente = (
        IAAliasCampo.objects
        .filter(
            modelo=modelo_real,
            expresion_normalizada=(
                expresion_normalizada
            ),
        )
        .first()
    )

    if existente:

        if (
            existente.campo_destino
            == campo.name
        ):

            return {
                **base,

                "estado":
                    "duplicado_local",

                "razon":
                    (
                        "El alias ya está registrado "
                        "para este mismo campo."
                    ),

                "alias_existente_id":
                    existente.pk,
            }

        return {
            **base,

            "estado":
                "conflicto_local",

            "razon":
                (
                    "La expresión ya está registrada "
                    "para otro campo del mismo modelo."
                ),

            "alias_existente_id":
                existente.pk,

            "campo_existente":
                existente.campo_destino,
        }

    return {
        **base,

        "ok":
            True,

        "estado":
            "valido",

        "razon":
            (
                "La expresión puede registrarse "
                "como alias local del campo."
            ),
    }


# ============================================================
# GUARDAR
# ============================================================


@transaction.atomic
def guardar_alias_campo(
    *,
    modelo: str,
    expresion: str,
    campo_destino: str,
    observacion: str = "",
    origen: str = IAAliasCampo.ORIGEN_MANUAL,
    prioridad: int = 100,
) -> dict[str, Any]:

    validacion = (
        validar_alias_campo(
            modelo=modelo,
            expresion=expresion,
            campo_destino=campo_destino,
        )
    )

    if not validacion.get(
        "ok"
    ):

        return {
            "ok":
                False,

            "creado":
                False,

            "validacion":
                validacion,

            "llm_invocado":
                False,
        }

    alias = IAAliasCampo.objects.create(
        modelo=validacion[
            "modelo"
        ],

        expresion=texto_limpio(
            expresion
        ),

        campo_destino=validacion[
            "campo_destino"
        ],

        origen=origen,

        prioridad=prioridad,

        observacion=texto_limpio(
            observacion
        ),
    )

    return {
        "ok":
            True,

        "creado":
            True,

        "alias": {
            "id":
                alias.pk,

            "modelo":
                alias.modelo,

            "expresion":
                alias.expresion,

            "expresion_normalizada":
                alias.expresion_normalizada,

            "campo_destino":
                alias.campo_destino,

            "origen":
                alias.origen,

            "activa":
                alias.activa,

            "prioridad":
                alias.prioridad,
        },

        "validacion":
            validacion,

        "llm_invocado":
            False,
    }


# ============================================================
# BÚSQUEDA
# ============================================================


def buscar_alias_campo(
    *,
    modelo: str,
    expresion: str,
) -> dict[str, Any]:

    modelo_django = (
        _resolver_modelo(
            modelo
        )
    )

    if modelo_django is None:

        return {
            "ok":
                False,

            "resuelto":
                False,

            "estado":
                "modelo_invalido",

            "llm_invocado":
                False,
        }

    modelo_real = (
        modelo_django._meta.label
    )

    normalizada = (
        normalizar_texto(
            expresion
        )
    )

    alias = (
        IAAliasCampo.objects
        .filter(
            modelo=modelo_real,
            expresion_normalizada=normalizada,
            activa=True,
        )
        .order_by(
            "prioridad",
            "pk",
        )
        .first()
    )

    if alias is None:

        return {
            "ok":
                True,

            "resuelto":
                False,

            "modelo":
                modelo_real,

            "expresion":
                expresion,

            "expresion_normalizada":
                normalizada,

            "llm_invocado":
                False,
        }

    IAAliasCampo.objects.filter(
        pk=alias.pk
    ).update(
        veces_usada=F(
            "veces_usada"
        )
        + 1
    )

    return {
        "ok":
            True,

        "resuelto":
            True,

        "modelo":
            alias.modelo,

        "expresion":
            alias.expresion,

        "expresion_normalizada":
            alias.expresion_normalizada,

        "campo_destino":
            alias.campo_destino,

        "alias_id":
            alias.pk,

        "origen":
            alias.origen,

        "prioridad":
            alias.prioridad,

        "llm_invocado":
            False,
    }


# ============================================================
# LISTADO
# ============================================================


def listar_aliases_campo(
    *,
    modelo: str | None = None,
    incluir_inactivos: bool = False,
) -> list[dict[str, Any]]:

    queryset = (
        IAAliasCampo.objects
        .all()
    )

    if modelo:

        modelo_django = (
            _resolver_modelo(
                modelo
            )
        )

        if modelo_django is None:
            return []

        queryset = queryset.filter(
            modelo=(
                modelo_django._meta.label
            )
        )

    if not incluir_inactivos:

        queryset = queryset.filter(
            activa=True
        )

    return [
        {
            "id":
                alias.pk,

            "modelo":
                alias.modelo,

            "expresion":
                alias.expresion,

            "expresion_normalizada":
                alias.expresion_normalizada,

            "campo_destino":
                alias.campo_destino,

            "origen":
                alias.origen,

            "activa":
                alias.activa,

            "prioridad":
                alias.prioridad,

            "veces_usada":
                alias.veces_usada,

            "observacion":
                alias.observacion,
        }

        for alias
        in queryset
    ]