from __future__ import annotations

import re
import unicodedata
from typing import Any

from django.apps import apps

from .catalogo_datos import (
    obtener_modelo_django,
)


# ============================================================
# IA-HOST023 / IA-HOST023-C01 / IA-HOST023-C02
# RESOLUCIÓN SEMÁNTICA DE CAMPO / RELACIÓN OBJETIVO
# ============================================================
#
# Responsabilidad:
#
#   pregunta + modelo principal ya validado
#       ↓
#   identificar qué campo o relación REAL del modelo constituye
#   el objetivo semántico de la pregunta
#
# Ejemplo conceptual:
#
#   "¿Cuántos archivos adjuntos tienen los correos enviados
#    cuyo asunto contiene 'reportes diarios'?"
#
# HOST023 NO:
#   - ejecuta ORM;
#   - modifica filtros;
#   - agrega datos;
#   - genera SQL;
#   - invoca LLM;
#   - inventa relaciones;
#   - decide todavía cómo contar/sumar/agrupar.
#
# Sólo resuelve candidatos existentes en Django._meta.
# ============================================================


# ============================================================
# CONSTANTES
# ============================================================

_STOPWORDS = {
    "a",
    "al",
    "algo",
    "como",
    "con",
    "cual",
    "cuales",
    "cuando",
    "cuanto",
    "cuantos",
    "cuanta",
    "cuantas",
    "de",
    "del",
    "desde",
    "donde",
    "el",
    "ella",
    "ellas",
    "ellos",
    "en",
    "es",
    "esta",
    "estan",
    "este",
    "estos",
    "ha",
    "hay",
    "la",
    "las",
    "lo",
    "los",
    "me",
    "para",
    "por",
    "que",
    "se",
    "sin",
    "su",
    "sus",
    "tiene",
    "tienen",
    "un",
    "una",
    "uno",
    "unos",
    "y",
}


_PATRONES_FOCO = (
    # ¿Cuántos archivos adjuntos tienen ...?
    re.compile(
        r"\bcuant(?:o|os|a|as)\b\s+"
        r"(?P<foco>.+?)\s+"
        r"\b(?:tiene|tienen|hay|existen|posee|poseen)\b",
        re.IGNORECASE,
    ),

    # C02:
    # ¿Cuál es la suma de destinatarios_count de ...?
    # ¿Cuál es el promedio de destinatarios_count de ...?
    # ¿Cuál es el máximo de destinatarios_count de ...?
    # ¿Cuál es el mínimo de destinatarios_count de ...?
    #
    # La palabra de agregación NO es el foco.
    re.compile(
        r"\bcual\s+es\s+(?:el|la)\s+"
        r"(?:suma|sumatoria|promedio|media|maximo|minimo|total)\s+"
        r"\bde\b\s+"
        r"(?P<foco>.+?)"
        r"(?:\s+\b(?:de|del|en|para|por|con|cuyo|cuya|cuyos|cuyas)\b|$)",
        re.IGNORECASE,
    ),

    # suma de X / promedio de X / máximo de X / mínimo de X
    re.compile(
        r"\b(?:suma|sumatoria|promedio|media|maximo|minimo|total)\s+"
        r"\bde\b\s+"
        r"(?P<foco>.+?)"
        r"(?:\s+\b(?:de|del|en|para|por|con|cuyo|cuya|cuyos|cuyas)\b|$)",
        re.IGNORECASE,
    ),

    # ¿Cuál es el monto total de ...?
    #
    # Patrón genérico deliberadamente posterior a los patrones
    # de agregación para no capturar "suma", "promedio", etc.
    re.compile(
        r"\bcual\s+es\s+(?:el|la)\s+"
        r"(?P<foco>.+?)\s+"
        r"\bde\b",
        re.IGNORECASE,
    ),
)


# ============================================================
# NORMALIZACIÓN
# ============================================================

def _texto(
    valor: Any,
) -> str:

    return str(
        valor
        or ""
    ).strip()


def _separar_camel(
    texto: str,
) -> str:

    return re.sub(
        r"(?<=[a-z0-9])(?=[A-Z])",
        " ",
        texto,
    )


def _normalizar(
    valor: Any,
) -> str:

    texto = _texto(
        valor
    )

    texto = _separar_camel(
        texto
    )

    texto = texto.replace(
        "_",
        " ",
    )

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        caracter
        for caracter
        in texto
        if not unicodedata.combining(
            caracter
        )
    )

    texto = texto.lower()

    texto = re.sub(
        r"[^a-z0-9]+",
        " ",
        texto,
    )

    return re.sub(
        r"\s+",
        " ",
        texto,
    ).strip()


def _singular_aproximado(
    token: str,
) -> str:
    """
    Normalización morfológica mínima y conservadora.

    No intenta comprender idioma completo. Sólo permite que
    variantes triviales singular/plural aporten evidencia.
    """

    token = _normalizar(
        token
    )

    if len(
        token
    ) <= 4:
        return token

    if token.endswith(
        "es"
    ) and len(
        token
    ) > 5:

        return token[:-2]

    if token.endswith(
        "s"
    ) and len(
        token
    ) > 4:

        return token[:-1]

    return token


def _tokens(
    valor: Any,
) -> set[str]:

    resultado = set()

    for token in _normalizar(
        valor
    ).split():

        if len(
            token
        ) < 3:
            continue

        if token in _STOPWORDS:
            continue

        resultado.add(
            token
        )

        singular = (
            _singular_aproximado(
                token
            )
        )

        if singular:
            resultado.add(
                singular
            )

    return resultado


# ============================================================
# FOCO SEMÁNTICO
# ============================================================

def _extraer_foco(
    pregunta: str,
) -> str:
    """
    Extrae, cuando es posible, la frase que gramaticalmente
    parece ser el OBJETIVO de la consulta.

    C01 aplica los patrones sobre texto normalizado para que:
        Cuántos -> cuantos
        máximo  -> maximo

    Si no se reconoce una forma segura, devuelve cadena vacía.
    """

    texto = _normalizar(
        pregunta
    )

    if not texto:
        return ""

    for patron in _PATRONES_FOCO:

        coincidencia = patron.search(
            texto
        )

        if not coincidencia:
            continue

        foco = _texto(
            coincidencia.group(
                "foco"
            )
        )

        if foco:
            return foco

    return ""


# ============================================================
# DESCRIPCIÓN DE CANDIDATOS REALES
# ============================================================

def _nombre_accessor(
    campo,
) -> str | None:

    funcion = getattr(
        campo,
        "get_accessor_name",
        None,
    )

    if not callable(
        funcion
    ):
        return None

    try:

        valor = funcion()

    except Exception:
        return None

    valor = _texto(
        valor
    )

    return (
        valor
        or None
    )


def _related_query_name(
    campo,
) -> str | None:

    funcion = getattr(
        campo,
        "related_query_name",
        None,
    )

    if callable(
        funcion
    ):

        try:

            valor = funcion()

        except Exception:

            valor = None

    else:

        valor = funcion

    valor = _texto(
        valor
    )

    return (
        valor
        or None
    )


def _aliases_campo(
    campo,
) -> list[str]:
    """
    Alias semánticos del objetivo.

    C01 distingue la semántica de una relación directa de los
    nombres utilizados por Django para consultarla desde el lado
    inverso.

    Ejemplo:
        CorreoEnviado.document
        related_query_name = correos_enviados

    "correos_enviados" describe cómo Document consulta hacia
    CorreoEnviado; no es un alias semántico del campo "document"
    dentro de CorreoEnviado.

    Por eso accessor/related_query_name sólo se usan como alias
    cuando el campo es una relación inversa auto-creada.
    """

    aliases = []

    def agregar(
        valor: Any,
    ) -> None:

        valor = _texto(
            valor
        )

        if (
            valor
            and valor not in aliases
        ):
            aliases.append(
                valor
            )

    agregar(
        getattr(
            campo,
            "name",
            None,
        )
    )

    agregar(
        getattr(
            campo,
            "verbose_name",
            None,
        )
    )

    es_inversa = bool(
        getattr(
            campo,
            "auto_created",
            False,
        )
        and getattr(
            campo,
            "is_relation",
            False,
        )
    )

    if es_inversa:

        agregar(
            _nombre_accessor(
                campo
            )
        )

        agregar(
            _related_query_name(
                campo
            )
        )

    relacionado = getattr(
        campo,
        "related_model",
        None,
    )

    if relacionado is not None:

        meta = relacionado._meta

        agregar(
            meta.object_name
        )

        agregar(
            meta.verbose_name
        )

        agregar(
            meta.verbose_name_plural
        )

    return aliases


def _tipo_relacion(
    campo,
) -> str | None:

    if not bool(
        getattr(
            campo,
            "is_relation",
            False,
        )
    ):
        return None

    if bool(
        getattr(
            campo,
            "many_to_many",
            False,
        )
    ):
        return "many_to_many"

    if bool(
        getattr(
            campo,
            "one_to_many",
            False,
        )
    ):
        return "one_to_many"

    if bool(
        getattr(
            campo,
            "many_to_one",
            False,
        )
    ):
        return "many_to_one"

    if bool(
        getattr(
            campo,
            "one_to_one",
            False,
        )
    ):
        return "one_to_one"

    return "relacion"


def _describir_candidato(
    campo,
) -> dict[str, Any]:

    relacionado = getattr(
        campo,
        "related_model",
        None,
    )

    modelo_relacionado = (
        relacionado._meta.label
        if relacionado is not None
        else None
    )

    nombre = _texto(
        getattr(
            campo,
            "name",
            None,
        )
    )

    accessor = (
        _nombre_accessor(
            campo
        )
    )

    query_name = (
        _related_query_name(
            campo
        )
    )

    # Para rutas ORM de QuerySet la fuente primaria es field.name.
    # En relaciones inversas, Django expone allí el related_query_name
    # efectivo cuando corresponde.
    ruta_orm = (
        nombre
        or query_name
    )

    return {
        "nombre":
            nombre,

        "ruta_orm":
            ruta_orm,

        "tipo_objetivo":
            (
                "relacion"
                if bool(
                    getattr(
                        campo,
                        "is_relation",
                        False,
                    )
                )
                else "campo"
            ),

        "tipo_django":
            campo.__class__.__name__,

        "relacion":
            bool(
                getattr(
                    campo,
                    "is_relation",
                    False,
                )
            ),

        "tipo_relacion":
            _tipo_relacion(
                campo
            ),

        "modelo_relacionado":
            modelo_relacionado,

        "auto_created":
            bool(
                getattr(
                    campo,
                    "auto_created",
                    False,
                )
            ),

        "concrete":
            bool(
                getattr(
                    campo,
                    "concrete",
                    False,
                )
            ),

        "accessor":
            accessor,

        "related_query_name":
            query_name,

        "aliases":
            _aliases_campo(
                campo
            ),
    }


def _candidatos_modelo(
    modelo_django,
) -> list[dict[str, Any]]:

    resultado = []

    for campo in modelo_django._meta.get_fields():

        candidato = (
            _describir_candidato(
                campo
            )
        )

        if not candidato.get(
            "nombre"
        ):
            continue

        resultado.append(
            candidato
        )

    resultado.sort(
        key=lambda item: (
            item[
                "tipo_objetivo"
            ],
            _normalizar(
                item[
                    "nombre"
                ]
            ),
        )
    )

    return resultado


# ============================================================
# PUNTAJE DE EVIDENCIA
# ============================================================

def _puntuar_alias(
    *,
    pregunta: str,
    foco: str,
    alias: str,
) -> dict[str, Any]:

    alias_n = _normalizar(
        alias
    )

    if not alias_n:

        return {
            "puntaje":
                0,

            "razones":
                [],
        }

    pregunta_n = _normalizar(
        pregunta
    )

    foco_n = _normalizar(
        foco
    )

    alias_tokens = _tokens(
        alias
    )

    pregunta_tokens = _tokens(
        pregunta
    )

    foco_tokens = _tokens(
        foco
    )

    puntaje = 0
    razones = []

    # --------------------------------------------------------
    # FOCO: evidencia principal
    # --------------------------------------------------------

    if foco_n:

        if alias_n == foco_n:

            puntaje += 220

            razones.append(
                "alias_exacto_en_foco"
            )

        elif alias_n in foco_n:

            puntaje += 170

            razones.append(
                "alias_contenido_en_foco"
            )

        elif (
            alias_tokens
            and alias_tokens.issubset(
                foco_tokens
            )
        ):

            puntaje += (
                110
                + 20
                * len(
                    alias_tokens
                )
            )

            razones.append(
                "tokens_alias_en_foco"
            )

        else:

            interseccion_foco = (
                alias_tokens
                & foco_tokens
            )

            if interseccion_foco:

                cobertura_alias = (
                    len(
                        interseccion_foco
                    )
                    / max(
                        1,
                        len(
                            alias_tokens
                        ),
                    )
                )

                puntaje += (
                    70
                    * len(
                        interseccion_foco
                    )
                )

                if cobertura_alias >= 0.5:

                    puntaje += 30

                    razones.append(
                        "cobertura_relevante_del_alias_en_foco"
                    )

                razones.append(
                    "tokens_compartidos_con_foco"
                )

    # --------------------------------------------------------
    # PREGUNTA COMPLETA: evidencia secundaria
    # --------------------------------------------------------

    if alias_n in pregunta_n:

        puntaje += 80

        razones.append(
            "alias_en_pregunta"
        )

    interseccion = (
        alias_tokens
        & pregunta_tokens
    )

    if interseccion:

        puntaje += (
            20
            * len(
                interseccion
            )
        )

        razones.append(
            "tokens_compartidos_con_pregunta"
        )

    return {
        "puntaje":
            puntaje,

        "razones":
            razones,
    }


def _puntuar_candidato(
    *,
    pregunta: str,
    foco: str,
    candidato: dict[str, Any],
) -> dict[str, Any]:

    mejor_puntaje = 0
    mejor_alias = None
    razones = []

    for alias in candidato.get(
        "aliases",
        [],
    ):

        evidencia = (
            _puntuar_alias(
                pregunta=pregunta,
                foco=foco,
                alias=alias,
            )
        )

        puntaje = int(
            evidencia.get(
                "puntaje",
                0,
            )
            or 0
        )

        if puntaje > mejor_puntaje:

            mejor_puntaje = puntaje
            mejor_alias = alias
            razones = list(
                evidencia.get(
                    "razones",
                    [],
                )
            )

    return {
        **candidato,

        "puntaje":
            mejor_puntaje,

        "alias_coincidente":
            mejor_alias,

        "evidencia":
            razones,
    }


# ============================================================
# RESOLUCIÓN
# ============================================================

def resolver_objetivo_datos(
    pregunta: str,
    *,
    modelo: str,
) -> dict[str, Any]:
    """
    Resuelve un campo o relación objetivo real dentro del modelo.

    Política conservadora:
    - sólo candidatos de Django._meta;
    - no LLM;
    - no similitud difusa arbitraria;
    - si no hay evidencia clara, resuelto=False;
    - si los mejores candidatos son equivalentes, resuelto=False.
    """

    modelo_django = (
        obtener_modelo_django(
            modelo
        )
    )

    if modelo_django is None:

        return {
            "ok":
                False,

            "resuelto":
                False,

            "modelo":
                modelo,

            "objetivo":
                None,

            "foco":
                "",

            "candidatos":
                [],

            "razon":
                (
                    "El modelo principal no pudo resolverse "
                    "de forma inequívoca."
                ),
        }

    label = (
        modelo_django._meta.label
    )

    foco = (
        _extraer_foco(
            pregunta
        )
    )

    candidatos = [
        _puntuar_candidato(
            pregunta=pregunta,
            foco=foco,
            candidato=candidato,
        )
        for candidato
        in _candidatos_modelo(
            modelo_django
        )
    ]

    candidatos = [
        item
        for item
        in candidatos
        if item.get(
            "puntaje",
            0,
        ) > 0
    ]

    candidatos.sort(
        key=lambda item: (
            -int(
                item.get(
                    "puntaje",
                    0,
                )
                or 0
            ),
            _normalizar(
                item.get(
                    "nombre"
                )
            ),
        )
    )

    if not candidatos:

        return {
            "ok":
                True,

            "resuelto":
                False,

            "modelo":
                label,

            "objetivo":
                None,

            "foco":
                foco,

            "candidatos":
                [],

            "razon":
                (
                    "No existe evidencia léxica suficiente para "
                    "asociar el objetivo de la pregunta con un "
                    "campo o relación real del modelo."
                ),
        }

    primero = (
        candidatos[0]
    )

    segundo = (
        candidatos[1]
        if len(
            candidatos
        ) > 1
        else None
    )

    puntaje_primero = int(
        primero.get(
            "puntaje",
            0,
        )
        or 0
    )

    # Exigimos evidencia razonable.
    if puntaje_primero < 80:

        return {
            "ok":
                True,

            "resuelto":
                False,

            "modelo":
                label,

            "objetivo":
                None,

            "foco":
                foco,

            "candidatos":
                candidatos[
                    :10
                ],

            "razon":
                (
                    "Existen candidatos reales, pero ninguno "
                    "tiene evidencia suficiente para resolver "
                    "el objetivo de forma segura."
                ),
        }

    if segundo is not None:

        puntaje_segundo = int(
            segundo.get(
                "puntaje",
                0,
            )
            or 0
        )

        diferencia = (
            puntaje_primero
            - puntaje_segundo
        )

        # Un empate o diferencia mínima se considera ambigüedad.
        if diferencia < 40:

            return {
                "ok":
                    True,

                "resuelto":
                    False,

                "modelo":
                    label,

                "objetivo":
                    None,

                "foco":
                    foco,

                "candidatos":
                    candidatos[
                        :10
                    ],

                "razon":
                    (
                        "Existen varios campos o relaciones con "
                        "evidencia comparable; HOST023 no elige "
                        "arbitrariamente entre ellos."
                    ),
            }

    objetivo = {
        clave:
            valor
        for clave, valor
        in primero.items()
        if clave not in {
            "puntaje",
        }
    }

    return {
        "ok":
            True,

        "resuelto":
            True,

        "modelo":
            label,

        "objetivo":
            objetivo,

        "foco":
            foco,

        "candidatos":
            candidatos[
                :10
            ],

        "razon":
            (
                "El objetivo fue resuelto contra campos y "
                "relaciones reales expuestos por Django._meta."
            ),

        "origen":
            "determinista",

        "llm_invocado":
            False,
    }
