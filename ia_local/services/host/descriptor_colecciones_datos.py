from __future__ import annotations

import re
import unicodedata
from typing import Any

from django.db import models

from .catalogo_datos import obtener_modelo_django


# ============================================================
# IA-HOST026
# DESCRIPTOR DETERMINISTA DE REPRESENTACIONES DE COLECCIÓN
# ============================================================
#
# Objetivo:
#   describir CÓMO representa Django un objetivo ya resuelto:
#
#     - relacion_multivaluada
#     - archivo_escalar
#     - coleccion_serializada
#     - campo_escalar
#
# Fuente de verdad:
#   - Django._meta
#   - metadatos declarativos del propio campo (help_text)
#
# HOST026 NO:
#   - ejecuta QuerySets;
#   - inspecciona filas de la BD;
#   - genera SQL;
#   - invoca LLM;
#   - inventa relaciones;
#   - convierte automáticamente una colección indirecta en equivalente
#     semántico de otra colección;
#   - interpreta un TextField como colección sin evidencia declarativa.
#
# ============================================================


# ============================================================
# UTILIDADES
# ============================================================

def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _normalizar(valor: Any) -> str:
    texto = unicodedata.normalize(
        "NFKD",
        _texto(valor),
    )

    texto = "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    )

    texto = texto.lower()
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def _tipo_relacion(campo) -> str | None:
    if bool(getattr(campo, "many_to_many", False)):
        return "many_to_many"

    if bool(getattr(campo, "one_to_many", False)):
        return "one_to_many"

    if bool(getattr(campo, "many_to_one", False)):
        return "many_to_one"

    if bool(getattr(campo, "one_to_one", False)):
        return "one_to_one"

    if bool(getattr(campo, "is_relation", False)):
        return "relacion"

    return None


def _resolver_campo(modelo_django, nombre: str):
    try:
        return modelo_django._meta.get_field(nombre)
    except Exception:
        return None


# ============================================================
# DETECCIÓN CONSERVADORA DE SERIALIZACIÓN DECLARADA
# ============================================================

_PATRONES_SEPARACION = (
    (
        "coma",
        ",",
        (
            r"\bseparad(?:o|a|os|as)\s+por\s+coma\b",
            r"\bcomma[- ]separated\b",
            r"\bseparated\s+by\s+commas?\b",
        ),
    ),
    (
        "punto_y_coma",
        ";",
        (
            r"\bseparad(?:o|a|os|as)\s+por\s+punto\s+y\s+coma\b",
            r"\bsemicolon[- ]separated\b",
            r"\bseparated\s+by\s+semicolons?\b",
        ),
    ),
    (
        "linea",
        "\n",
        (
            r"\buno\s+por\s+linea\b",
            r"\buna\s+por\s+linea\b",
            r"\bseparad(?:o|a|os|as)\s+por\s+lineas?\b",
            r"\bone\s+per\s+line\b",
            r"\bnewline[- ]separated\b",
        ),
    ),
)


def _detectar_serializacion_declarada(
    campo,
) -> dict[str, Any] | None:

    if not isinstance(
        campo,
        (
            models.CharField,
            models.TextField,
        ),
    ):
        return None

    help_text_original = _texto(
        getattr(
            campo,
            "help_text",
            "",
        )
    )

    help_text = _normalizar(
        help_text_original
    )

    if not help_text:
        return None

    coincidencias = []

    for nombre, separador, patrones in _PATRONES_SEPARACION:

        for patron in patrones:

            if re.search(
                patron,
                help_text,
                flags=re.IGNORECASE,
            ):
                coincidencias.append(
                    {
                        "nombre_separador":
                            nombre,

                        "separador":
                            separador,

                        "patron":
                            patron,
                    }
                )
                break

    # Conservador:
    # si el help_text describe más de una convención posible
    # (p. ej. "coma o punto y coma"), no elegimos arbitrariamente.
    if len(coincidencias) != 1:
        return None

    coincidencia = coincidencias[0]

    return {
        "tipo_representacion":
            "coleccion_serializada",

        "formato":
            "texto_delimitado",

        "separador":
            coincidencia[
                "separador"
            ],

        "nombre_separador":
            coincidencia[
                "nombre_separador"
            ],

        "evidencia": [
            {
                "tipo":
                    "django_field_help_text",

                "valor":
                    help_text_original,
            }
        ],

        "confianza":
            "declarada",

        "requiere_validacion_codigo":
            True,
    }


# ============================================================
# DESCRIPTOR DE OBJETIVO
# ============================================================

def describir_representacion_objetivo(
    *,
    modelo: str,
    objetivo: dict[str, Any],
) -> dict[str, Any]:
    """
    Describe la representación real de un objetivo previamente
    resuelto. No ejecuta datos.
    """

    modelo_django = obtener_modelo_django(
        modelo
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
                objetivo,

            "tipo_representacion":
                None,

            "razon":
                "El modelo no pudo resolverse inequívocamente.",

            "llm_invocado":
                False,
        }

    if not isinstance(
        objetivo,
        dict,
    ):
        return {
            "ok":
                False,

            "resuelto":
                False,

            "modelo":
                modelo_django._meta.label,

            "objetivo":
                None,

            "tipo_representacion":
                None,

            "razon":
                "El objetivo no tiene formato válido.",

            "llm_invocado":
                False,
        }

    nombre = _texto(
        objetivo.get(
            "nombre"
        )
    )

    if not nombre:
        return {
            "ok":
                True,

            "resuelto":
                False,

            "modelo":
                modelo_django._meta.label,

            "objetivo":
                objetivo,

            "tipo_representacion":
                None,

            "razon":
                "El objetivo no contiene un nombre de campo o relación.",

            "llm_invocado":
                False,
        }

    campo = _resolver_campo(
        modelo_django,
        nombre,
    )

    if campo is None:
        return {
            "ok":
                True,

            "resuelto":
                False,

            "modelo":
                modelo_django._meta.label,

            "objetivo":
                objetivo,

            "tipo_representacion":
                None,

            "razon":
                (
                    f"Django._meta no pudo resolver "
                    f"el objetivo {nombre!r}."
                ),

            "llm_invocado":
                False,
        }

    # --------------------------------------------------------
    # RELACIÓN
    # --------------------------------------------------------

    if bool(
        getattr(
            campo,
            "is_relation",
            False,
        )
    ):

        tipo_relacion = _tipo_relacion(
            campo
        )

        multiple = bool(
            getattr(
                campo,
                "many_to_many",
                False,
            )
            or getattr(
                campo,
                "one_to_many",
                False,
            )
        )

        related_model = getattr(
            campo,
            "related_model",
            None,
        )

        return {
            "ok":
                True,

            "resuelto":
                True,

            "modelo":
                modelo_django._meta.label,

            "objetivo":
                objetivo,

            "nombre":
                nombre,

            "tipo_django":
                campo.__class__.__name__,

            "tipo_representacion":
                (
                    "relacion_multivaluada"
                    if multiple
                    else "relacion_escalar"
                ),

            "tipo_relacion":
                tipo_relacion,

            "multiple":
                multiple,

            "modelo_relacionado":
                (
                    related_model._meta.label
                    if related_model is not None
                    else None
                ),

            "contable_como_coleccion":
                multiple,

            "razon":
                (
                    "Django._meta declara una relación multivaluada."
                    if multiple
                    else
                    "Django._meta declara una relación escalar."
                ),

            "origen":
                "django_meta",

            "llm_invocado":
                False,
        }

    # --------------------------------------------------------
    # FILEFIELD
    # --------------------------------------------------------

    if isinstance(
        campo,
        models.FileField,
    ):

        return {
            "ok":
                True,

            "resuelto":
                True,

            "modelo":
                modelo_django._meta.label,

            "objetivo":
                objetivo,

            "nombre":
                nombre,

            "tipo_django":
                campo.__class__.__name__,

            "tipo_representacion":
                "archivo_escalar",

            "multiple":
                False,

            "contable_como_coleccion":
                False,

            "razon":
                (
                    "El objetivo es un FileField individual; "
                    "no representa por sí mismo una colección."
                ),

            "origen":
                "django_meta",

            "llm_invocado":
                False,
        }

    # --------------------------------------------------------
    # TEXTO SERIALIZADO DECLARADO
    # --------------------------------------------------------

    serializacion = (
        _detectar_serializacion_declarada(
            campo
        )
    )

    if serializacion is not None:

        return {
            "ok":
                True,

            "resuelto":
                True,

            "modelo":
                modelo_django._meta.label,

            "objetivo":
                objetivo,

            "nombre":
                nombre,

            "tipo_django":
                campo.__class__.__name__,

            "tipo_representacion":
                serializacion[
                    "tipo_representacion"
                ],

            "formato":
                serializacion[
                    "formato"
                ],

            "separador":
                serializacion[
                    "separador"
                ],

            "nombre_separador":
                serializacion[
                    "nombre_separador"
                ],

            "multiple":
                True,

            "contable_como_coleccion":
                True,

            "evidencia":
                serializacion[
                    "evidencia"
                ],

            "confianza":
                serializacion[
                    "confianza"
                ],

            "requiere_validacion_codigo":
                serializacion[
                    "requiere_validacion_codigo"
                ],

            "razon":
                (
                    "El propio metadato declarativo del campo "
                    "describe una colección textual delimitada."
                ),

            "origen":
                "django_meta_help_text",

            "llm_invocado":
                False,
        }

    # --------------------------------------------------------
    # ESCALAR ORDINARIO
    # --------------------------------------------------------

    return {
        "ok":
            True,

        "resuelto":
            True,

        "modelo":
            modelo_django._meta.label,

        "objetivo":
            objetivo,

        "nombre":
            nombre,

        "tipo_django":
            campo.__class__.__name__,

        "tipo_representacion":
            "campo_escalar",

        "multiple":
            False,

        "contable_como_coleccion":
            False,

        "razon":
            (
                "No existe evidencia estructural o declarativa "
                "suficiente para tratar el campo como colección."
            ),

        "origen":
            "django_meta",

        "llm_invocado":
            False,
    }


# ============================================================
# ENTRADA DIRECTA DESDE HOST023
# ============================================================

def resolver_representacion_coleccion(
    *,
    modelo: str,
    objetivo_host: dict[str, Any],
) -> dict[str, Any]:
    """
    Consume la salida de HOST023.
    """

    if not isinstance(
        objetivo_host,
        dict,
    ):
        return {
            "ok":
                False,

            "resuelto":
                False,

            "modelo":
                modelo,

            "tipo_representacion":
                None,

            "razon":
                "El resultado HOST023 no tiene formato válido.",

            "llm_invocado":
                False,
        }

    if not bool(
        objetivo_host.get(
            "resuelto"
        )
    ):
        return {
            "ok":
                True,

            "resuelto":
                False,

            "modelo":
                _texto(
                    objetivo_host.get(
                        "modelo",
                        modelo,
                    )
                ),

            "tipo_representacion":
                None,

            "razon":
                "HOST023 no resolvió un objetivo inequívoco.",

            "llm_invocado":
                False,
        }

    objetivo = objetivo_host.get(
        "objetivo"
    )

    return describir_representacion_objetivo(
        modelo=_texto(
            objetivo_host.get(
                "modelo",
                modelo,
            )
        ),
        objetivo=objetivo,
    )
