from __future__ import annotations

from typing import Any

from ia_local.models import (
    IAAliasCampo,
    IAAliasEntidad,
    IAAliasValor,
    IAReglaDeclarativa,
)

from .resolvedor_ambiguedades import (
    resolver_expresion_semantica,
)


VERSION = "IA-SEM008-v1"


# ============================================================
# POLÍTICA
# ============================================================


RANGO_ORIGEN = {
    "MANUAL": 10,
    "APRENDIDO": 20,
    "AUTOMATICO": 30,
    "LLM": 90,
    "DESCONOCIDO": 100,
}


def describir_politica() -> dict[str, Any]:

    return {
        "version":
            VERSION,

        "autoridad_estructural": {
            "fuente":
                "DJANGO",

            "descripcion":
                (
                    "Modelos, campos, relaciones, tipos y choices "
                    "reales constituyen la frontera estructural. "
                    "Ningún conocimiento semántico puede "
                    "contradecirla."
                ),
        },

        "orden_resolucion": [
            {
                "nivel": 1,
                "nombre": "contexto_explicito",
                "descripcion": (
                    "Modelo y campo proporcionados explícitamente "
                    "restringen el universo de candidatos."
                ),
            },
            {
                "nivel": 2,
                "nombre": "regla_declarativa_exacta",
                "descripcion": (
                    "Una regla SEM005 exacta representa un concepto "
                    "compuesto previamente validado."
                ),
            },
            {
                "nivel": 3,
                "nombre": "manual",
                "descripcion": (
                    "Conocimiento local introducido deliberadamente."
                ),
            },
            {
                "nivel": 4,
                "nombre": "aprendido",
                "descripcion": (
                    "Conocimiento nacido de una corrección, validado "
                    "y confirmado mediante SEM007."
                ),
            },
            {
                "nivel": 5,
                "nombre": "automatico",
                "descripcion": (
                    "Vocabulario inferido directamente desde metadata "
                    "Django."
                ),
            },
            {
                "nivel": 6,
                "nombre": "llm",
                "descripcion": (
                    "Inferencia futura. No puede sobreescribir "
                    "conocimiento estructural o confirmado."
                ),
            },
        ],

        "regla_ambiguedad": (
            "La prioridad de origen nunca elimina por sí sola "
            "una ambigüedad entre contextos semánticos distintos."
        ),

        "llm_invocado":
            False,
    }


# ============================================================
# ORIGEN REAL DEL CONOCIMIENTO
# ============================================================


def _origen_alias_entidad(
    alias_id: int | None,
) -> str:

    if not alias_id:
        return "DESCONOCIDO"

    valor = (
        IAAliasEntidad.objects
        .filter(
            pk=alias_id
        )
        .values_list(
            "origen",
            flat=True,
        )
        .first()
    )

    return valor or "DESCONOCIDO"


def _origen_alias_campo(
    alias_id: int | None,
) -> str:

    if not alias_id:
        return "DESCONOCIDO"

    valor = (
        IAAliasCampo.objects
        .filter(
            pk=alias_id
        )
        .values_list(
            "origen",
            flat=True,
        )
        .first()
    )

    return valor or "DESCONOCIDO"


def _origen_alias_valor(
    alias_id: int | None,
) -> str:

    if not alias_id:
        return "DESCONOCIDO"

    valor = (
        IAAliasValor.objects
        .filter(
            pk=alias_id
        )
        .values_list(
            "origen",
            flat=True,
        )
        .first()
    )

    return valor or "DESCONOCIDO"


def _origen_regla(
    regla_id: int | None,
) -> str:

    if not regla_id:
        return "DESCONOCIDO"

    valor = (
        IAReglaDeclarativa.objects
        .filter(
            pk=regla_id
        )
        .values_list(
            "origen",
            flat=True,
        )
        .first()
    )

    return valor or "DESCONOCIDO"


# ============================================================
# ENRIQUECER CANDIDATOS
# ============================================================


def enriquecer_candidato(
    candidato: dict[str, Any],
) -> dict[str, Any]:

    candidato = dict(
        candidato
    )

    origen_capa = candidato.get(
        "origen"
    )

    tipo = candidato.get(
        "tipo"
    )

    origen_conocimiento = (
        "DESCONOCIDO"
    )

    if origen_capa == "SEM001":

        origen_conocimiento = (
            "AUTOMATICO"
        )

    elif origen_capa == "SEM002":

        origen_conocimiento = (
            _origen_alias_entidad(
                candidato.get(
                    "alias_id"
                )
            )
        )

    elif origen_capa == "SEM003":

        origen_conocimiento = (
            _origen_alias_campo(
                candidato.get(
                    "alias_id"
                )
            )
        )

    elif origen_capa == "SEM004":

        origen_conocimiento = (
            _origen_alias_valor(
                candidato.get(
                    "alias_id"
                )
            )
        )

    elif origen_capa == "SEM005":

        origen_conocimiento = (
            _origen_regla(
                candidato.get(
                    "regla_id"
                )
            )
        )

    elif origen_capa == "LLM":

        origen_conocimiento = "LLM"

    candidato[
        "origen_conocimiento"
    ] = origen_conocimiento

    candidato[
        "rango_origen"
    ] = RANGO_ORIGEN.get(
        origen_conocimiento,
        RANGO_ORIGEN[
            "DESCONOCIDO"
        ],
    )

    candidato[
        "es_regla_declarativa"
    ] = (
        tipo
        == "regla_declarativa"
    )

    return candidato


# ============================================================
# CONTEXTO SEMÁNTICO
# ============================================================


def _clave_contexto(
    candidato: dict[str, Any],
):

    tipo = candidato.get(
        "tipo"
    )

    if tipo == "entidad":

        return (
            "entidad",
            candidato.get(
                "modelo"
            ),
        )

    if tipo == "campo":

        return (
            "campo",
            candidato.get(
                "modelo"
            ),
            candidato.get(
                "campo"
            ),
        )

    if tipo == "valor":

        return (
            "valor",
            candidato.get(
                "modelo"
            ),
            candidato.get(
                "campo"
            ),
        )

    if tipo == "regla_declarativa":

        return (
            "regla_declarativa",
            candidato.get(
                "modelo"
            ),
            candidato.get(
                "regla_id"
            ),
        )

    return (
        tipo,
        candidato.get(
            "modelo"
        ),
        candidato.get(
            "campo"
        ),
    )


def _hay_contextos_distintos(
    candidatos: list[dict[str, Any]],
) -> bool:

    claves = {
        _clave_contexto(
            candidato
        )
        for candidato
        in candidatos
    }

    return len(
        claves
    ) > 1


# ============================================================
# ELECCIÓN POR PRIORIDAD
# ============================================================


def _seleccionar_por_prioridad(
    candidatos: list[dict[str, Any]],
) -> dict[str, Any]:

    if not candidatos:

        return {
            "resuelto":
                False,

            "razon":
                "sin_candidatos",
        }

    # Una regla declarativa exacta tiene máxima
    # especificidad semántica dentro del mismo contexto.

    reglas = [
        candidato
        for candidato
        in candidatos
        if candidato.get(
            "es_regla_declarativa"
        )
    ]

    if len(
        reglas
    ) == 1:

        return {
            "resuelto":
                True,

            "criterio":
                "regla_declarativa_exacta",

            "resultado":
                reglas[
                    0
                ],
        }

    if len(
        reglas
    ) > 1:

        candidatos = reglas

    mejor_rango = min(
        candidato.get(
            "rango_origen",
            100,
        )
        for candidato
        in candidatos
    )

    mejores = [
        candidato
        for candidato
        in candidatos
        if candidato.get(
            "rango_origen",
            100,
        )
        == mejor_rango
    ]

    # prioridad numérica local:
    # número menor = más prioritario

    mejor_prioridad = min(
        candidato.get(
            "prioridad",
            100,
        )
        for candidato
        in mejores
    )

    mejores = [
        candidato
        for candidato
        in mejores
        if candidato.get(
            "prioridad",
            100,
        )
        == mejor_prioridad
    ]

    if len(
        mejores
    ) == 1:

        return {
            "resuelto":
                True,

            "criterio":
                "prioridad_semantica",

            "resultado":
                mejores[
                    0
                ],

            "rango_origen":
                mejor_rango,

            "prioridad":
                mejor_prioridad,
        }

    return {
        "resuelto":
            False,

        "razon":
            "empate_semantico",

        "candidatos":
            mejores,
    }


# ============================================================
# RESOLUCIÓN POLÍTICA
# ============================================================


def resolver_con_politica(
    expresion: str,
    *,
    modelo_contexto: str | None = None,
    campo_contexto: str | None = None,
    incluir_reglas: bool = True,
) -> dict[str, Any]:

    base = resolver_expresion_semantica(
        expresion,
        modelo_contexto=(
            modelo_contexto
        ),
        campo_contexto=(
            campo_contexto
        ),
        incluir_reglas=(
            incluir_reglas
        ),
    )

    salida = dict(
        base
    )

    salida[
        "politica_version"
    ] = VERSION

    candidatos = [
        enriquecer_candidato(
            candidato
        )
        for candidato
        in base.get(
            "candidatos",
            [],
        )
    ]

    salida[
        "candidatos"
    ] = candidatos

    # --------------------------------------------------------
    # ERROR / NO RESUELTO
    # --------------------------------------------------------

    if not base.get(
        "ok",
        True,
    ):

        salida[
            "politica_aplicada"
        ] = False

        return salida

    if (
        base.get(
            "estado"
        )
        == "no_resuelto"
    ):

        salida[
            "politica_aplicada"
        ] = True

        salida[
            "decision_politica"
        ] = "sin_conocimiento_disponible"

        return salida

    # --------------------------------------------------------
    # YA RESUELTO POR SEM006
    # --------------------------------------------------------

    if (
        base.get(
            "estado"
        )
        == "resuelto"
    ):

        resultado = base.get(
            "resultado"
        )

        if resultado:

            resultado = (
                enriquecer_candidato(
                    resultado
                )
            )

            salida[
                "resultado"
            ] = resultado

        salida[
            "politica_aplicada"
        ] = True

        salida[
            "decision_politica"
        ] = (
            "resolucion_semantica_confirmada"
        )

        return salida

    # --------------------------------------------------------
    # AMBIGÜEDAD
    # --------------------------------------------------------

    if (
        base.get(
            "estado"
        )
        != "ambiguo"
    ):

        salida[
            "politica_aplicada"
        ] = False

        return salida

    # Regla de seguridad:
    # si los candidatos pertenecen a contextos diferentes,
    # la prioridad NO puede eliminar la ambigüedad.

    if _hay_contextos_distintos(
        candidatos
    ):

        salida[
            "estado"
        ] = "ambiguo"

        salida[
            "requiere_contexto"
        ] = True

        salida[
            "politica_aplicada"
        ] = True

        salida[
            "decision_politica"
        ] = (
            "ambiguedad_contextual"
        )

        salida[
            "razon_politica"
        ] = (
            "Los candidatos pertenecen a contextos "
            "semánticos distintos. La prioridad de "
            "origen no puede escoger entre ellos."
        )

        return salida

    decision = (
        _seleccionar_por_prioridad(
            candidatos
        )
    )

    if decision.get(
        "resuelto"
    ):

        salida[
            "estado"
        ] = "resuelto"

        salida[
            "requiere_contexto"
        ] = False

        salida[
            "criterio"
        ] = decision.get(
            "criterio"
        )

        salida[
            "resultado"
        ] = decision.get(
            "resultado"
        )

        salida[
            "politica_aplicada"
        ] = True

        salida[
            "decision_politica"
        ] = "prioridad_aplicada"

        return salida

    salida[
        "estado"
    ] = "ambiguo"

    salida[
        "requiere_contexto"
    ] = True

    salida[
        "politica_aplicada"
    ] = True

    salida[
        "decision_politica"
    ] = "empate_semantico"

    return salida