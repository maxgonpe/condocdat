from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.apps import apps
from django.db import models, transaction
from django.db.models import F

from ia_local.models import (
    IAAliasValor,
)

from .normalizacion import (
    normalizar_texto,
    texto_limpio,
)


VERSION = "IA-SEM004-v1"


# ============================================================
# MODELO / CAMPO
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


def _resolver_campo(
    modelo,
    nombre: str,
):

    nombre = texto_limpio(
        nombre
    )

    if not nombre:
        return None

    try:

        return modelo._meta.get_field(
            nombre
        )

    except Exception:

        return None


# ============================================================
# VALORES CANÓNICOS
# ============================================================


def _valor_a_texto(
    valor: Any,
) -> str:

    if valor is None:
        return "null"

    if isinstance(
        valor,
        bool,
    ):
        return (
            "true"
            if valor
            else "false"
        )

    if isinstance(
        valor,
        (
            date,
            datetime,
            time,
        ),
    ):
        return valor.isoformat()

    if isinstance(
        valor,
        (
            Decimal,
            UUID,
        ),
    ):
        return str(
            valor
        )

    return str(
        valor
    )


def _convertir_booleano(
    valor: str,
):

    normalizado = normalizar_texto(
        valor
    )

    if normalizado in {
        "true",
        "1",
    }:
        return True

    if normalizado in {
        "false",
        "0",
    }:
        return False

    raise ValueError(
        "Valor booleano inválido. "
        "Use true, false, 1 o 0."
    )


def convertir_valor_campo(
    campo,
    valor: Any,
):
    """
    Convierte una representación textual al tipo Python
    aceptado por el campo Django.
    """

    if valor is None:
        return None

    texto = str(
        valor
    ).strip()

    if (
        normalizar_texto(
            texto
        )
        == "null"
    ):

        if getattr(
            campo,
            "null",
            False,
        ):
            return None

        raise ValueError(
            "El campo no admite NULL."
        )

    if isinstance(
        campo,
        models.BooleanField,
    ):

        return _convertir_booleano(
            texto
        )

    try:

        return campo.to_python(
            texto
        )

    except Exception as exc:

        raise ValueError(
            (
                f"El valor {texto!r} no es válido "
                f"para {campo.__class__.__name__}."
            )
        ) from exc


# ============================================================
# CHOICES AUTOMÁTICOS
# ============================================================


def describir_choices_campo(
    campo,
) -> list[dict[str, Any]]:

    try:

        choices = list(
            campo.flatchoices
        )

    except Exception:

        choices = []

    resultado = []

    for valor, etiqueta in choices:

        resultado.append(
            {
                "valor":
                    _valor_a_texto(
                        valor
                    ),

                "etiqueta":
                    texto_limpio(
                        etiqueta
                    ),

                "etiqueta_normalizada":
                    normalizar_texto(
                        etiqueta
                    ),
            }
        )

    return resultado


def _representaciones_automaticas(
    campo,
) -> list[dict[str, Any]]:

    resultado = []

    for choice in describir_choices_campo(
        campo
    ):

        resultado.append(
            {
                "expresion":
                    choice[
                        "etiqueta"
                    ],

                "normalizada":
                    choice[
                        "etiqueta_normalizada"
                    ],

                "valor":
                    choice[
                        "valor"
                    ],

                "origen":
                    "choice_etiqueta",
            }
        )

        valor_normalizado = normalizar_texto(
            choice[
                "valor"
            ]
        )

        if valor_normalizado:

            resultado.append(
                {
                    "expresion":
                        choice[
                            "valor"
                        ],

                    "normalizada":
                        valor_normalizado,

                    "valor":
                        choice[
                            "valor"
                        ],

                    "origen":
                        "choice_valor",
                }
            )

    if isinstance(
        campo,
        models.BooleanField,
    ):

        resultado.extend(
            [
                {
                    "expresion":
                        "true",

                    "normalizada":
                        "true",

                    "valor":
                        "true",

                    "origen":
                        "booleano",
                },
                {
                    "expresion":
                        "false",

                    "normalizada":
                        "false",

                    "valor":
                        "false",

                    "origen":
                        "booleano",
                },
            ]
        )

    return resultado


# ============================================================
# INSPECCIÓN
# ============================================================


def inspeccionar_campo_valores(
    *,
    modelo: str,
    campo: str,
) -> dict[str, Any]:

    modelo_django = _resolver_modelo(
        modelo
    )

    if modelo_django is None:

        return {
            "ok":
                False,

            "estado":
                "modelo_invalido",

            "llm_invocado":
                False,
        }

    campo_django = _resolver_campo(
        modelo_django,
        campo,
    )

    if campo_django is None:

        return {
            "ok":
                False,

            "estado":
                "campo_invalido",

            "llm_invocado":
                False,
        }

    return {
        "ok":
            True,

        "version":
            VERSION,

        "modelo":
            modelo_django._meta.label,

        "campo":
            campo_django.name,

        "tipo":
            campo_django.__class__.__name__,

        "null":
            bool(
                getattr(
                    campo_django,
                    "null",
                    False,
                )
            ),

        "relacion":
            bool(
                getattr(
                    campo_django,
                    "is_relation",
                    False,
                )
            ),

        "choices":
            describir_choices_campo(
                campo_django
            ),

        "llm_invocado":
            False,
    }


# ============================================================
# VALIDACIÓN
# ============================================================


def validar_alias_valor(
    *,
    modelo: str,
    campo: str,
    expresion: str,
    valor_destino: str,
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

        "campo":
            campo,

        "expresion":
            expresion,

        "expresion_normalizada":
            expresion_normalizada,

        "valor_destino":
            valor_destino,

        "llm_invocado":
            False,
    }

    if not expresion_normalizada:

        return {
            **base,

            "estado":
                "expresion_vacia",

            "razon":
                "La expresión está vacía.",
        }

    modelo_django = _resolver_modelo(
        modelo
    )

    if modelo_django is None:

        return {
            **base,

            "estado":
                "modelo_invalido",

            "razon":
                "El modelo no existe.",
        }

    modelo_real = (
        modelo_django._meta.label
    )

    base[
        "modelo"
    ] = modelo_real

    campo_django = _resolver_campo(
        modelo_django,
        campo,
    )

    if campo_django is None:

        return {
            **base,

            "estado":
                "campo_invalido",

            "razon":
                "El campo no existe.",
        }

    if bool(
        getattr(
            campo_django,
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
                    "SEM004 sólo interpreta valores "
                    "de campos escalares."
                ),
        }

    base[
        "campo"
    ] = campo_django.name

    try:

        valor_python = (
            convertir_valor_campo(
                campo_django,
                valor_destino,
            )
        )

    except ValueError as exc:

        return {
            **base,

            "estado":
                "valor_invalido",

            "razon":
                str(
                    exc
                ),
        }

    valor_canonico = (
        _valor_a_texto(
            valor_python
        )
    )

    base[
        "valor_destino"
    ] = valor_canonico

    # --------------------------------------------------------
    # VALIDAR CHOICE DESTINO
    # --------------------------------------------------------

    choices = describir_choices_campo(
        campo_django
    )

    if choices:

        valores_permitidos = {
            item[
                "valor"
            ]
            for item
            in choices
        }

        if (
            valor_canonico
            not in valores_permitidos
        ):

            return {
                **base,

                "estado":
                    "valor_fuera_de_choices",

                "razon":
                    (
                        "El valor destino no pertenece "
                        "a los choices declarados por Django."
                    ),

                "valores_permitidos":
                    sorted(
                        valores_permitidos
                    ),
            }

    # --------------------------------------------------------
    # CONOCIMIENTO AUTOMÁTICO
    # --------------------------------------------------------

    automaticas = [
        item

        for item
        in _representaciones_automaticas(
            campo_django
        )

        if item[
            "normalizada"
        ]
        == expresion_normalizada
    ]

    if automaticas:

        valores = {
            item[
                "valor"
            ]
            for item
            in automaticas
        }

        if valores == {
            valor_canonico
        }:

            return {
                **base,

                "estado":
                    "redundante_automatico",

                "razon":
                    (
                        "Django ya permite interpretar "
                        "automáticamente esta expresión."
                    ),

                "coincidencias":
                    automaticas,
            }

        return {
            **base,

            "estado":
                "conflicto_automatico",

            "razon":
                (
                    "La expresión ya representa otro "
                    "valor según la metadata Django."
                ),

            "coincidencias":
                automaticas,
        }

    # --------------------------------------------------------
    # REGLA LOCAL
    # --------------------------------------------------------

    existente = (
        IAAliasValor.objects
        .filter(
            modelo=modelo_real,
            campo=campo_django.name,
            expresion_normalizada=(
                expresion_normalizada
            ),
        )
        .first()
    )

    if existente:

        if (
            existente.valor_destino
            == valor_canonico
        ):

            return {
                **base,

                "estado":
                    "duplicado_local",

                "razon":
                    (
                        "La equivalencia ya está "
                        "registrada."
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
                    "La expresión ya representa otro "
                    "valor dentro del mismo campo."
                ),

            "alias_existente_id":
                existente.pk,

            "valor_existente":
                existente.valor_destino,
        }

    return {
        **base,

        "ok":
            True,

        "estado":
            "valido",

        "razon":
            (
                "La equivalencia de valor puede "
                "registrarse."
            ),
    }


# ============================================================
# GUARDAR
# ============================================================


@transaction.atomic
def guardar_alias_valor(
    *,
    modelo: str,
    campo: str,
    expresion: str,
    valor_destino: str,
    observacion: str = "",
    origen: str = IAAliasValor.ORIGEN_MANUAL,
    prioridad: int = 100,
) -> dict[str, Any]:

    validacion = validar_alias_valor(
        modelo=modelo,
        campo=campo,
        expresion=expresion,
        valor_destino=valor_destino,
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

    alias = IAAliasValor.objects.create(
        modelo=validacion[
            "modelo"
        ],
        campo=validacion[
            "campo"
        ],
        expresion=expresion,
        valor_destino=validacion[
            "valor_destino"
        ],
        observacion=observacion,
        origen=origen,
        prioridad=prioridad,
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

            "campo":
                alias.campo,

            "expresion":
                alias.expresion,

            "expresion_normalizada":
                alias.expresion_normalizada,

            "valor_destino":
                alias.valor_destino,

            "origen":
                alias.origen,

            "activa":
                alias.activa,

            "prioridad":
                alias.prioridad,
        },

        "llm_invocado":
            False,
    }


# ============================================================
# RESOLUCIÓN
# ============================================================


def buscar_alias_valor(
    *,
    modelo: str,
    campo: str,
    expresion: str,
) -> dict[str, Any]:

    modelo_django = _resolver_modelo(
        modelo
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

    campo_django = _resolver_campo(
        modelo_django,
        campo,
    )

    if campo_django is None:

        return {
            "ok":
                False,
            "resuelto":
                False,
            "estado":
                "campo_invalido",
            "llm_invocado":
                False,
        }

    if bool(
        getattr(
            campo_django,
            "is_relation",
            False,
        )
    ):

        return {
            "ok":
                False,
            "resuelto":
                False,
            "estado":
                "campo_relacional",
            "llm_invocado":
                False,
        }

    expresion_normalizada = (
        normalizar_texto(
            expresion
        )
    )

    # Primero metadata Django.

    automaticas = [
        item
        for item
        in _representaciones_automaticas(
            campo_django
        )
        if item[
            "normalizada"
        ]
        == expresion_normalizada
    ]

    if len(
        automaticas
    ) == 1:

        valor_texto = (
            automaticas[
                0
            ][
                "valor"
            ]
        )

        valor_python = (
            convertir_valor_campo(
                campo_django,
                valor_texto,
            )
        )

        return {
            "ok":
                True,

            "resuelto":
                True,

            "modelo":
                modelo_django._meta.label,

            "campo":
                campo_django.name,

            "expresion":
                expresion,

            "valor_destino":
                valor_texto,

            "valor_python":
                valor_python,

            "origen":
                "AUTOMATICO_DJANGO",

            "llm_invocado":
                False,
        }

    alias = (
        IAAliasValor.objects
        .filter(
            modelo=(
                modelo_django._meta.label
            ),
            campo=campo_django.name,
            expresion_normalizada=(
                expresion_normalizada
            ),
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
                modelo_django._meta.label,

            "campo":
                campo_django.name,

            "expresion":
                expresion,

            "llm_invocado":
                False,
        }

    IAAliasValor.objects.filter(
        pk=alias.pk
    ).update(
        veces_usada=F(
            "veces_usada"
        )
        + 1
    )

    valor_python = convertir_valor_campo(
        campo_django,
        alias.valor_destino,
    )

    return {
        "ok":
            True,

        "resuelto":
            True,

        "modelo":
            alias.modelo,

        "campo":
            alias.campo,

        "expresion":
            alias.expresion,

        "expresion_normalizada":
            alias.expresion_normalizada,

        "valor_destino":
            alias.valor_destino,

        "valor_python":
            valor_python,

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
# IA-LLM005-C01
# RESOLUCIÓN DE ALIAS DE VALOR DENTRO DE TEXTO NATURAL
# ============================================================


def buscar_alias_valor_en_texto(
    *,
    modelo: str,
    campo: str,
    texto: str,
) -> dict[str, Any]:
    """
    Busca una equivalencia SEM004 activa cuyo texto aparezca
    dentro de una pregunta natural.

    Reglas:
    - siempre acotada a modelo + campo;
    - sólo aliases activos;
    - gana la expresión más específica/larga;
    - no usa LLM;
    - no ejecuta consultas de negocio;
    - devuelve únicamente conocimiento semántico.
    """

    modelo_django = _resolver_modelo(
        modelo
    )

    if modelo_django is None:

        return {
            "ok": False,
            "resuelto": False,
            "estado": "modelo_invalido",
            "llm_invocado": False,
        }

    campo_django = _resolver_campo(
        modelo_django,
        campo,
    )

    if campo_django is None:

        return {
            "ok": False,
            "resuelto": False,
            "estado": "campo_invalido",
            "llm_invocado": False,
        }

    if bool(
        getattr(
            campo_django,
            "is_relation",
            False,
        )
    ):

        return {
            "ok": False,
            "resuelto": False,
            "estado": "campo_relacional",
            "llm_invocado": False,
        }

    texto_normalizado = normalizar_texto(
        texto
    )

    if not texto_normalizado:

        return {
            "ok": True,
            "resuelto": False,
            "estado": "texto_vacio",
            "modelo": modelo_django._meta.label,
            "campo": campo_django.name,
            "llm_invocado": False,
        }

    aliases = list(
        IAAliasValor.objects
        .filter(
            modelo=modelo_django._meta.label,
            campo=campo_django.name,
            activa=True,
        )
        .order_by(
            "prioridad",
            "pk",
        )
    )

    coincidencias = []

    for alias in aliases:

        expresion_n = (
            alias.expresion_normalizada
            or ""
        ).strip()

        if not expresion_n:
            continue

        if expresion_n in texto_normalizado:

            coincidencias.append(
                alias
            )

    if not coincidencias:

        return {
            "ok": True,
            "resuelto": False,
            "estado": "sin_alias_en_texto",
            "modelo": modelo_django._meta.label,
            "campo": campo_django.name,
            "llm_invocado": False,
        }

    # La expresión más larga representa el concepto
    # más específico disponible.
    coincidencias.sort(
        key=lambda alias: (
            -len(
                alias.expresion_normalizada
                or ""
            ),
            alias.prioridad,
            alias.pk,
        )
    )

    alias = coincidencias[0]

    # Si dos expresiones igualmente específicas apuntaran
    # a valores distintos, no decidimos silenciosamente.
    longitud_ganadora = len(
        alias.expresion_normalizada
        or ""
    )

    igualmente_especificas = [
        item
        for item in coincidencias
        if len(
            item.expresion_normalizada
            or ""
        )
        == longitud_ganadora
    ]

    valores = {
        item.valor_destino
        for item in igualmente_especificas
    }

    if len(
        valores
    ) != 1:

        return {
            "ok": True,
            "resuelto": False,
            "estado": "alias_ambiguo_en_texto",
            "modelo": modelo_django._meta.label,
            "campo": campo_django.name,
            "candidatos": [
                {
                    "expresion":
                        item.expresion,

                    "valor_destino":
                        item.valor_destino,

                    "alias_id":
                        item.pk,
                }
                for item
                in igualmente_especificas
            ],
            "llm_invocado": False,
        }

    valor_python = convertir_valor_campo(
        campo_django,
        alias.valor_destino,
    )

    IAAliasValor.objects.filter(
        pk=alias.pk
    ).update(
        veces_usada=F(
            "veces_usada"
        )
        + 1
    )

    return {
        "ok": True,
        "resuelto": True,
        "estado": "alias_valor_en_texto_resuelto",
        "modelo": alias.modelo,
        "campo": alias.campo,
        "expresion": alias.expresion,
        "expresion_normalizada":
            alias.expresion_normalizada,
        "valor_destino":
            alias.valor_destino,
        "valor_python":
            valor_python,
        "alias_id":
            alias.pk,
        "origen": "SEM004",
        "prioridad":
            alias.prioridad,
        "llm_invocado": False,
    }
