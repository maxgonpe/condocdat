from __future__ import annotations

from typing import Any

from django.apps import apps

from ia_local.models import (
    IAAliasCampo,
    IAAliasEntidad,
    IAAliasValor,
    IAReglaDeclarativa,
)

from .inventario_vocabulario import (
    construir_inventario_vocabulario,
)

from .normalizacion import (
    normalizar_texto,
    texto_limpio,
)


VERSION = "IA-SEM006-v1"


# ============================================================
# UTILIDADES
# ============================================================


def _resolver_modelo(
    referencia: str | None,
):

    referencia = texto_limpio(
        referencia
    )

    if not referencia:
        return None

    if "." not in referencia:
        return None

    app_label, nombre = referencia.split(
        ".",
        1,
    )

    try:

        return apps.get_model(
            app_label,
            nombre,
        )

    except LookupError:

        return None


def _deduplicar_candidatos(
    candidatos: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    resultado = []
    vistos = set()

    for candidato in candidatos:

        clave = (
            candidato.get(
                "tipo"
            ),
            candidato.get(
                "modelo"
            ),
            candidato.get(
                "campo"
            ),
            str(
                candidato.get(
                    "valor"
                )
            ),
            candidato.get(
                "regla_id"
            ),
        )

        if clave in vistos:
            continue

        vistos.add(
            clave
        )

        resultado.append(
            candidato
        )

    return resultado


# ============================================================
# REGLAS DECLARATIVAS
# ============================================================


def _candidatos_regla(
    expresion_normalizada: str,
) -> list[dict[str, Any]]:

    reglas = (
        IAReglaDeclarativa.objects
        .filter(
            expresion_normalizada=(
                expresion_normalizada
            ),
            activa=True,
        )
        .order_by(
            "prioridad",
            "pk",
        )
    )

    return [
        {
            "tipo":
                "regla_declarativa",

            "modelo":
                regla.modelo,

            "regla_id":
                regla.pk,

            "operacion":
                regla.operacion,

            "condiciones":
                regla.condiciones,

            "origen":
                "SEM005",

            "prioridad":
                regla.prioridad,
        }

        for regla
        in reglas
    ]


# ============================================================
# ENTIDADES
# ============================================================


def _candidatos_entidad_automaticos(
    expresion_normalizada: str,
) -> list[dict[str, Any]]:

    inventario = (
        construir_inventario_vocabulario()
    )

    resultado = []

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
                != expresion_normalizada
            ):
                continue

            resultado.append(
                {
                    "tipo":
                        "entidad",

                    "modelo":
                        modelo.get(
                            "label"
                        ),

                    "origen":
                        "SEM001",

                    "evidencia":
                        termino.get(
                            "origenes",
                            [],
                        ),

                    "prioridad":
                        300,
                }
            )

    return resultado


def _candidatos_entidad_locales(
    expresion_normalizada: str,
) -> list[dict[str, Any]]:

    aliases = (
        IAAliasEntidad.objects
        .filter(
            expresion_normalizada=(
                expresion_normalizada
            ),
            activa=True,
        )
        .order_by(
            "prioridad",
            "pk",
        )
    )

    return [
        {
            "tipo":
                "entidad",

            "modelo":
                alias.modelo_destino,

            "alias_id":
                alias.pk,

            "origen":
                "SEM002",

            "prioridad":
                alias.prioridad,
        }

        for alias
        in aliases
    ]


# ============================================================
# CAMPOS
# ============================================================


def _candidatos_campo_automaticos(
    expresion_normalizada: str,
    *,
    modelo_contexto: str | None = None,
) -> list[dict[str, Any]]:

    inventario = (
        construir_inventario_vocabulario()
    )

    resultado = []

    for modelo in inventario.get(
        "modelos",
        [],
    ):

        label = modelo.get(
            "label"
        )

        if (
            modelo_contexto
            and label != modelo_contexto
        ):
            continue

        for campo in modelo.get(
            "campos",
            [],
        ):

            for termino in campo.get(
                "vocabulario",
                [],
            ):

                if (
                    termino.get(
                        "normalizado"
                    )
                    != expresion_normalizada
                ):
                    continue

                resultado.append(
                    {
                        "tipo":
                            "campo",

                        "modelo":
                            label,

                        "campo":
                            campo.get(
                                "nombre"
                            ),

                        "origen":
                            "SEM001",

                        "evidencia":
                            termino.get(
                                "origenes",
                                [],
                            ),

                        "prioridad":
                            300,
                    }
                )

    return resultado


def _candidatos_campo_locales(
    expresion_normalizada: str,
    *,
    modelo_contexto: str | None = None,
) -> list[dict[str, Any]]:

    queryset = (
        IAAliasCampo.objects
        .filter(
            expresion_normalizada=(
                expresion_normalizada
            ),
            activa=True,
        )
    )

    if modelo_contexto:

        queryset = queryset.filter(
            modelo=modelo_contexto
        )

    queryset = queryset.order_by(
        "prioridad",
        "pk",
    )

    return [
        {
            "tipo":
                "campo",

            "modelo":
                alias.modelo,

            "campo":
                alias.campo_destino,

            "alias_id":
                alias.pk,

            "origen":
                "SEM003",

            "prioridad":
                alias.prioridad,
        }

        for alias
        in queryset
    ]


# ============================================================
# VALORES
# ============================================================


def _candidatos_valor_locales(
    expresion_normalizada: str,
    *,
    modelo_contexto: str | None = None,
    campo_contexto: str | None = None,
) -> list[dict[str, Any]]:

    queryset = (
        IAAliasValor.objects
        .filter(
            expresion_normalizada=(
                expresion_normalizada
            ),
            activa=True,
        )
    )

    if modelo_contexto:

        queryset = queryset.filter(
            modelo=modelo_contexto
        )

    if campo_contexto:

        queryset = queryset.filter(
            campo=campo_contexto
        )

    queryset = queryset.order_by(
        "prioridad",
        "pk",
    )

    return [
        {
            "tipo":
                "valor",

            "modelo":
                alias.modelo,

            "campo":
                alias.campo,

            "valor":
                alias.valor_destino,

            "alias_id":
                alias.pk,

            "origen":
                "SEM004",

            "prioridad":
                alias.prioridad,
        }

        for alias
        in queryset
    ]


# ============================================================
# RESOLUCIÓN
# ============================================================


def resolver_expresion_semantica(
    expresion: str,
    *,
    modelo_contexto: str | None = None,
    campo_contexto: str | None = None,
    incluir_reglas: bool = True,
) -> dict[str, Any]:
    """
    Resuelve una expresión contra SEM001-SEM005.

    No utiliza LLM.

    Estados:

        resuelto
        ambiguo
        no_resuelto
        contexto_modelo_invalido
        contexto_campo_invalido
    """

    expresion = texto_limpio(
        expresion
    )

    normalizada = normalizar_texto(
        expresion
    )

    base = {
        "ok":
            True,

        "version":
            VERSION,

        "expresion":
            expresion,

        "expresion_normalizada":
            normalizada,

        "modelo_contexto":
            modelo_contexto,

        "campo_contexto":
            campo_contexto,

        "llm_invocado":
            False,
    }

    if not normalizada:

        return {
            **base,

            "estado":
                "no_resuelto",

            "razon":
                "expresion_vacia",

            "candidatos":
                [],
        }

    # --------------------------------------------------------
    # VALIDAR CONTEXTO DE MODELO
    # --------------------------------------------------------

    modelo_real = None

    if modelo_contexto:

        modelo_django = _resolver_modelo(
            modelo_contexto
        )

        if modelo_django is None:

            return {
                **base,

                "ok":
                    False,

                "estado":
                    "contexto_modelo_invalido",

                "candidatos":
                    [],
            }

        modelo_real = (
            modelo_django._meta.label
        )

        base[
            "modelo_contexto"
        ] = modelo_real

        if campo_contexto:

            try:

                campo_django = (
                    modelo_django._meta.get_field(
                        campo_contexto
                    )
                )

            except Exception:

                return {
                    **base,

                    "ok":
                        False,

                    "estado":
                        "contexto_campo_invalido",

                    "candidatos":
                        [],
                }

            base[
                "campo_contexto"
            ] = campo_django.name

    # --------------------------------------------------------
    # 1. REGLA DECLARATIVA
    # --------------------------------------------------------

    if incluir_reglas:

        reglas = _candidatos_regla(
            normalizada
        )

        if modelo_real:

            reglas = [
                item
                for item
                in reglas
                if item.get(
                    "modelo"
                )
                == modelo_real
            ]

        reglas = _deduplicar_candidatos(
            reglas
        )

        if len(
            reglas
        ) == 1:

            return {
                **base,

                "estado":
                    "resuelto",

                "criterio":
                    "regla_declarativa_exacta",

                "resultado":
                    reglas[
                        0
                    ],

                "candidatos":
                    reglas,
            }

        if len(
            reglas
        ) > 1:

            return {
                **base,

                "estado":
                    "ambiguo",

                "criterio":
                    "multiples_reglas_declarativas",

                "requiere_contexto":
                    True,

                "candidatos":
                    reglas,
            }

    # --------------------------------------------------------
    # 2. CAMPOS
    # --------------------------------------------------------

    campos_locales = (
        _candidatos_campo_locales(
            normalizada,
            modelo_contexto=modelo_real,
        )
    )

    campos_automaticos = (
        _candidatos_campo_automaticos(
            normalizada,
            modelo_contexto=modelo_real,
        )
    )

    campos = _deduplicar_candidatos(
        campos_locales
        + campos_automaticos
    )

    if campo_contexto:

        campos = [
            item
            for item
            in campos
            if item.get(
                "campo"
            )
            == campo_contexto
        ]

    if len(
        campos
    ) == 1:

        return {
            **base,

            "estado":
                "resuelto",

            "criterio":
                (
                    "campo_por_contexto"
                    if modelo_real
                    else "campo_unico"
                ),

            "resultado":
                campos[
                    0
                ],

            "candidatos":
                campos,
        }

    if len(
        campos
    ) > 1:

        return {
            **base,

            "estado":
                "ambiguo",

            "criterio":
                "multiples_campos",

            "requiere_contexto":
                True,

            "candidatos":
                campos,
        }

    # --------------------------------------------------------
    # 3. VALORES LOCALES
    # --------------------------------------------------------

    valores = _candidatos_valor_locales(
        normalizada,
        modelo_contexto=modelo_real,
        campo_contexto=campo_contexto,
    )

    valores = _deduplicar_candidatos(
        valores
    )

    if len(
        valores
    ) == 1:

        return {
            **base,

            "estado":
                "resuelto",

            "criterio":
                (
                    "valor_por_contexto"
                    if (
                        modelo_real
                        or campo_contexto
                    )
                    else "valor_unico"
                ),

            "resultado":
                valores[
                    0
                ],

            "candidatos":
                valores,
        }

    if len(
        valores
    ) > 1:

        return {
            **base,

            "estado":
                "ambiguo",

            "criterio":
                "multiples_valores",

            "requiere_contexto":
                True,

            "candidatos":
                valores,
        }

    # --------------------------------------------------------
    # 4. ENTIDADES
    # --------------------------------------------------------

    entidades_locales = (
        _candidatos_entidad_locales(
            normalizada
        )
    )

    entidades_automaticas = (
        _candidatos_entidad_automaticos(
            normalizada
        )
    )

    entidades = _deduplicar_candidatos(
        entidades_locales
        + entidades_automaticas
    )

    if modelo_real:

        entidades = [
            item
            for item
            in entidades
            if item.get(
                "modelo"
            )
            == modelo_real
        ]

    if len(
        entidades
    ) == 1:

        return {
            **base,

            "estado":
                "resuelto",

            "criterio":
                (
                    "entidad_por_contexto"
                    if modelo_real
                    else "entidad_unica"
                ),

            "resultado":
                entidades[
                    0
                ],

            "candidatos":
                entidades,
        }

    if len(
        entidades
    ) > 1:

        return {
            **base,

            "estado":
                "ambiguo",

            "criterio":
                "multiples_entidades",

            "requiere_contexto":
                True,

            "candidatos":
                entidades,
        }

    return {
        **base,

        "estado":
            "no_resuelto",

        "criterio":
            "sin_candidatos",

        "requiere_contexto":
            False,

        "candidatos":
            [],
    }