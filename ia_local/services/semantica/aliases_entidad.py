from __future__ import annotations

from typing import Any

from django.apps import apps
from django.db import transaction
from django.db.models import F

from ia_local.models import (
    IAAliasEntidad,
)

from .inventario_vocabulario import (
    construir_inventario_vocabulario,
)

from .normalizacion import (
    normalizar_texto,
    texto_limpio,
)


VERSION = "IA-SEM002-v1"


# ============================================================
# MODELO DESTINO
# ============================================================


def _resolver_modelo_destino(
    referencia: str,
):
    """
    Sólo acepta labels Django canónicos:

        app_label.Model
    """

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
# EVIDENCIA AUTOMÁTICA SEM001
# ============================================================


def buscar_colisiones_automaticas(
    expresion: str,
) -> list[dict[str, Any]]:
    """
    Busca la expresión dentro del vocabulario automático SEM001.

    No consulta aliases locales.
    """

    objetivo = normalizar_texto(
        expresion
    )

    if not objetivo:
        return []

    inventario = (
        construir_inventario_vocabulario()
    )

    coincidencias = []

    for modelo in inventario.get(
        "modelos",
        [],
    ):

        for termino in modelo.get(
            "vocabulario_entidad",
            [],
        ):

            if (
                termino.get(
                    "normalizado"
                )
                != objetivo
            ):
                continue

            coincidencias.append(
                {
                    "modelo":
                        modelo.get(
                            "label"
                        ),

                    "texto":
                        termino.get(
                            "texto"
                        ),

                    "normalizado":
                        termino.get(
                            "normalizado"
                        ),

                    "origenes":
                        termino.get(
                            "origenes",
                            [],
                        ),
                }
            )

    return coincidencias


# ============================================================
# VALIDACIÓN
# ============================================================


def validar_alias_entidad(
    *,
    expresion: str,
    modelo_destino: str,
) -> dict[str, Any]:
    """
    Valida un alias antes de almacenarlo.

    Estados posibles:

        valido
        expresion_vacia
        destino_invalido
        redundante_automatico
        conflicto_automatico
        duplicado_local
        conflicto_local
    """

    expresion = texto_limpio(
        expresion
    )

    expresion_normalizada = (
        normalizar_texto(
            expresion
        )
    )

    modelo = (
        _resolver_modelo_destino(
            modelo_destino
        )
    )

    resultado_base = {
        "ok":
            False,

        "version":
            VERSION,

        "expresion":
            expresion,

        "expresion_normalizada":
            expresion_normalizada,

        "modelo_destino":
            modelo_destino,

        "llm_invocado":
            False,
    }

    if not expresion_normalizada:

        return {
            **resultado_base,
            "estado":
                "expresion_vacia",

            "razon":
                "La expresión no contiene vocabulario utilizable.",
        }

    if modelo is None:

        return {
            **resultado_base,
            "estado":
                "destino_invalido",

            "razon":
                (
                    "El modelo destino no existe en el "
                    "registro Django del host."
                ),
        }

    modelo_destino_real = (
        modelo._meta.label
    )

    resultado_base[
        "modelo_destino"
    ] = modelo_destino_real

    # --------------------------------------------------------
    # COLISIONES CON VOCABULARIO AUTOMÁTICO
    # --------------------------------------------------------

    automaticas = (
        buscar_colisiones_automaticas(
            expresion
        )
    )

    if automaticas:

        destinos_automaticos = {
            item[
                "modelo"
            ]
            for item
            in automaticas
        }

        if destinos_automaticos == {
            modelo_destino_real
        }:

            return {
                **resultado_base,

                "estado":
                    "redundante_automatico",

                "razon":
                    (
                        "La expresión ya pertenece al "
                        "vocabulario automático de la entidad."
                    ),

                "colisiones_automaticas":
                    automaticas,
            }

        return {
            **resultado_base,

            "estado":
                "conflicto_automatico",

            "razon":
                (
                    "La expresión ya identifica automáticamente "
                    "otra entidad del host."
                ),

            "colisiones_automaticas":
                automaticas,
        }

    # --------------------------------------------------------
    # COLISIONES CON ALIASES LOCALES
    # --------------------------------------------------------

    existente = (
        IAAliasEntidad.objects
        .filter(
            expresion_normalizada=(
                expresion_normalizada
            )
        )
        .first()
    )

    if existente:

        if (
            existente.modelo_destino
            == modelo_destino_real
        ):

            return {
                **resultado_base,

                "estado":
                    "duplicado_local",

                "razon":
                    (
                        "El alias ya está registrado "
                        "para esta misma entidad."
                    ),

                "alias_existente_id":
                    existente.pk,
            }

        return {
            **resultado_base,

            "estado":
                "conflicto_local",

            "razon":
                (
                    "La expresión ya está registrada "
                    "para otra entidad."
                ),

            "alias_existente_id":
                existente.pk,

            "modelo_existente":
                existente.modelo_destino,
        }

    return {
        **resultado_base,

        "ok":
            True,

        "estado":
            "valido",

        "razon":
            (
                "La expresión puede registrarse "
                "como alias local de entidad."
            ),
    }


# ============================================================
# ALTA
# ============================================================


@transaction.atomic
def guardar_alias_entidad(
    *,
    expresion: str,
    modelo_destino: str,
    observacion: str = "",
    origen: str = IAAliasEntidad.ORIGEN_MANUAL,
    prioridad: int = 100,
) -> dict[str, Any]:

    validacion = (
        validar_alias_entidad(
            expresion=expresion,
            modelo_destino=modelo_destino,
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

    alias = IAAliasEntidad.objects.create(
        expresion=texto_limpio(
            expresion
        ),
        modelo_destino=validacion[
            "modelo_destino"
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

            "expresion":
                alias.expresion,

            "expresion_normalizada":
                alias.expresion_normalizada,

            "modelo_destino":
                alias.modelo_destino,

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


def buscar_alias_entidad(
    expresion: str,
) -> dict[str, Any]:

    normalizada = normalizar_texto(
        expresion
    )

    alias = (
        IAAliasEntidad.objects
        .filter(
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

            "expresion":
                expresion,

            "expresion_normalizada":
                normalizada,

            "llm_invocado":
                False,
        }

    IAAliasEntidad.objects.filter(
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

        "expresion":
            alias.expresion,

        "expresion_normalizada":
            alias.expresion_normalizada,

        "modelo_destino":
            alias.modelo_destino,

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


def listar_aliases_entidad(
    *,
    incluir_inactivos: bool = False,
) -> list[dict[str, Any]]:

    queryset = (
        IAAliasEntidad.objects
        .all()
    )

    if not incluir_inactivos:

        queryset = queryset.filter(
            activa=True
        )

    return [
        {
            "id":
                alias.pk,

            "expresion":
                alias.expresion,

            "expresion_normalizada":
                alias.expresion_normalizada,

            "modelo_destino":
                alias.modelo_destino,

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