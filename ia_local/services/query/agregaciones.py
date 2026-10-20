from __future__ import annotations

import re
import unicodedata
from typing import Any

from ia_local.services.semantica.resolvedor_ambiguedades import (
    resolver_expresion_semantica,
)

from ia_local.services.host.resolvedor_objetivo_datos import (
    resolver_objetivo_datos,
)

from ia_local.services.host.resolvedor_operacion_datos import (
    resolver_operacion_datos,
)


VERSION = "IA-QUERY009-v1"


# ============================================================
# UTILIDADES
# ============================================================


def _texto(
    valor: Any,
) -> str:

    if valor is None:
        return ""

    return str(valor).strip()


def _normalizar(
    texto: str,
) -> str:

    texto = _texto(
        texto
    ).lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(
            caracter
        )
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()



def _limpiar_entidad_natural(
    expresion: str,
) -> str:

    texto = _texto(
        expresion
    )

    texto = re.sub(
        r"^\s*(?:el|la|los|las|un|una|unos|unas)\s+",
        "",
        texto,
        flags=re.IGNORECASE,
    )

    return texto.strip()



def _error(
    *,
    pregunta: str,
    estado: str,
    razon: str,
    **extra: Any,
) -> dict[str, Any]:

    salida = {
        "ok": False,
        "version": VERSION,
        "ejecutado": False,
        "estado": estado,
        "modo": "agregaciones",
        "pregunta": pregunta,
        "razon": razon,
        "llm_invocado": False,
    }

    salida.update(
        extra
    )

    return salida


# ============================================================
# ENTIDAD
# ============================================================


def _resolver_entidad(
    expresion: str,
) -> dict[str, Any]:

    expresion_limpia = (
        _limpiar_entidad_natural(
            expresion
        )
    )

    resolucion = (
        resolver_expresion_semantica(
            expresion_limpia,
            incluir_reglas=False,
        )
    )

    if (
        not isinstance(
            resolucion,
            dict,
        )
        or resolucion.get(
            "ok"
        )
        is not True
        or resolucion.get(
            "estado"
        )
        != "resuelto"
    ):

        return {
            "ok": False,
            "expresion_original": expresion,
            "expresion_limpia": expresion_limpia,
            "resolucion": resolucion,
        }

    resultado = resolucion.get(
        "resultado"
    )

    if (
        not isinstance(
            resultado,
            dict,
        )
        or resultado.get(
            "tipo"
        )
        != "entidad"
    ):

        return {
            "ok": False,
            "expresion_original": expresion,
            "expresion_limpia": expresion_limpia,
            "resolucion": resolucion,
        }

    modelo = _texto(
        resultado.get(
            "modelo"
        )
    )

    if not modelo:

        return {
            "ok": False,
            "expresion_original": expresion,
            "expresion_limpia": expresion_limpia,
            "resolucion": resolucion,
        }

    return {
        "ok": True,
        "modelo": modelo,
        "expresion_original": expresion,
        "expresion_limpia": expresion_limpia,
        "resolucion": resolucion,
    }


# ============================================================
# PARSER
# ============================================================


def _extraer_consulta(
    pregunta: str,
) -> dict[str, Any] | None:

    texto = _texto(
        pregunta
    )

    normalizado = _normalizar(
        texto
    )

    # --------------------------------------------------------
    # CONTEO DE REGISTROS
    #
    # cuantos documentos hay
    # cantidad de documentos
    # numero de documentos
    # --------------------------------------------------------

    patrones_conteo_registros = (
        r"^cuantos?\s+(?P<entidad>.+?)\s+hay$",
        r"^cuantas?\s+(?P<entidad>.+?)\s+hay$",
        r"^cantidad\s+de\s+(?P<entidad>.+?)$",
        r"^numero\s+de\s+(?P<entidad>.+?)$",
        r"^nro\s+de\s+(?P<entidad>.+?)$",
        r"^total\s+de\s+(?P<entidad>.+?)$",
    )

    for patron in patrones_conteo_registros:

        coincidencia = re.match(
            patron,
            normalizado,
        )

        if coincidencia:

            return {
                "tipo":
                    "contar_registros",

                "entidad":
                    _texto(
                        coincidencia.group(
                            "entidad"
                        )
                    ),

                "objetivo":
                    None,
            }

    # --------------------------------------------------------
    # CONTEO DE OBJETIVO RELACIONAL
    #
    # cuantos correos enviados tienen los documentos
    # cuantas attachments tienen los documentos
    # --------------------------------------------------------

    coincidencia = re.match(
        r"""
        ^cuant(?:os|as)
        \s+
        (?P<objetivo>.+?)
        \s+
        (?:tienen|tiene)
        \s+
        (?P<entidad>.+?)
        $
        """,
        normalizado,
        flags=re.VERBOSE,
    )

    if coincidencia:

        return {
            "tipo":
                "agregacion_objetivo",

            "entidad":
                _texto(
                    coincidencia.group(
                        "entidad"
                    )
                ),

            "objetivo":
                _texto(
                    coincidencia.group(
                        "objetivo"
                    )
                ),
        }

    # --------------------------------------------------------
    # SUMA / PROMEDIO / MIN / MAX
    #
    # suma de campo de entidad
    # promedio de campo de entidad
    # maximo de fecha de documentos
    # minimo de fecha de documentos
    # --------------------------------------------------------

    coincidencia = re.match(
        r"""
        ^
        (?P<operacion>
            suma
            |
            sumar
            |
            sumatoria
            |
            promedio
            |
            media
            |
            maximo
            |
            mayor
            |
            minimo
            |
            menor
        )
        \s+
        (?:de\s+)?
        (?P<objetivo>.+?)
        \s+
        de
        \s+
        (?P<entidad>.+?)
        $
        """,
        normalizado,
        flags=re.VERBOSE,
    )

    if coincidencia:

                        return {
            "tipo":
                "agregacion_objetivo",

            "entidad":
                _limpiar_entidad_natural(
                    coincidencia.group(
                        "entidad"
                    )
                ),

            "objetivo":
                _texto(
                    coincidencia.group(
                        "objetivo"
                    )
                ),
        }

    return None


def _resolver_objetivo_agregacion(
    *,
    expresion: str,
    modelo: str,
) -> dict[str, Any]:

    # --------------------------------------------------------
    # 1. HOST023 primero
    #
    # Es especialmente bueno resolviendo relaciones reales:
    #
    # correos enviados -> correos_enviados
    # documentos       -> document
    # --------------------------------------------------------

    objetivo_host = (
        resolver_objetivo_datos(
            expresion,
            modelo=modelo,
        )
    )

    if (
        isinstance(
            objetivo_host,
            dict,
        )
        and objetivo_host.get(
            "ok"
        )
        is True
        and objetivo_host.get(
            "resuelto"
        )
        is True
    ):

        return {
            "ok":
                True,

            "objetivo_host":
                objetivo_host,

            "resolucion_semantica":
                None,

            "via":
                "HOST023",
        }

    # --------------------------------------------------------
    # 2. SEM006
    #
    # Necesario para aliases semánticos:
    #
    # fecha -> date
    # tema  -> title
    # --------------------------------------------------------

    resolucion_semantica = (
        resolver_expresion_semantica(
            expresion,
            modelo_contexto=modelo,
            incluir_reglas=False,
        )
    )

    if (
        not isinstance(
            resolucion_semantica,
            dict,
        )
        or resolucion_semantica.get(
            "ok"
        )
        is not True
        or resolucion_semantica.get(
            "estado"
        )
        != "resuelto"
    ):

        return {
            "ok":
                False,

            "objetivo_host":
                objetivo_host,

            "resolucion_semantica":
                resolucion_semantica,

            "via":
                None,
        }

    resultado = (
        resolucion_semantica.get(
            "resultado"
        )
    )

    if not isinstance(
        resultado,
        dict,
    ):

        return {
            "ok":
                False,

            "objetivo_host":
                objetivo_host,

            "resolucion_semantica":
                resolucion_semantica,

            "via":
                None,
        }

    if (
        resultado.get(
            "tipo"
        )
        != "campo"
    ):

        return {
            "ok":
                False,

            "objetivo_host":
                objetivo_host,

            "resolucion_semantica":
                resolucion_semantica,

            "via":
                None,
        }

    campo = _texto(
        resultado.get(
            "campo"
        )
    )

    if not campo:

        return {
            "ok":
                False,

            "objetivo_host":
                objetivo_host,

            "resolucion_semantica":
                resolucion_semantica,

            "via":
                None,
        }

    # --------------------------------------------------------
    # SEM propone el nombre canónico.
    # HOST023 vuelve a certificar contra Django._meta.
    # --------------------------------------------------------

    objetivo_canonico = (
        resolver_objetivo_datos(
            campo,
            modelo=modelo,
        )
    )

    if (
        not isinstance(
            objetivo_canonico,
            dict,
        )
        or objetivo_canonico.get(
            "ok"
        )
        is not True
        or objetivo_canonico.get(
            "resuelto"
        )
        is not True
    ):

        return {
            "ok":
                False,

            "objetivo_host":
                objetivo_canonico,

            "objetivo_host_inicial":
                objetivo_host,

            "resolucion_semantica":
                resolucion_semantica,

            "via":
                None,
        }

    return {
        "ok":
            True,

        "objetivo_host":
            objetivo_canonico,

        "objetivo_host_inicial":
            objetivo_host,

        "resolucion_semantica":
            resolucion_semantica,

        "via":
            "SEM006->HOST023",
    }



# ============================================================
# API PÚBLICA
# ============================================================


def componer_agregacion(
    pregunta: str,
) -> dict[str, Any]:

    pregunta = _texto(
        pregunta
    )

    if not pregunta:

        return _error(
            pregunta=pregunta,
            estado="pregunta_vacia",
            razon="La consulta está vacía.",
        )

    componentes = (
        _extraer_consulta(
            pregunta
        )
    )

    if componentes is None:

        return _error(
            pregunta=pregunta,
            estado="estructura_agregacion_no_detectada",
            razon=(
                "No se encontró una estructura de agregación "
                "soportada de forma inequívoca."
            ),
        )

    # --------------------------------------------------------
    # ENTIDAD PRINCIPAL
    # --------------------------------------------------------

    entidad = (
        _resolver_entidad(
            componentes[
                "entidad"
            ]
        )
    )

    if entidad.get(
        "ok"
    ) is not True:

        return _error(
            pregunta=pregunta,
            estado="entidad_no_resuelta",
            razon=(
                "La entidad principal no pudo resolverse "
                "de forma inequívoca."
            ),
            entidad_solicitada=(
                componentes[
                    "entidad"
                ]
            ),
            resolucion_entidad=(
                entidad.get(
                    "resolucion"
                )
            ),
        )

    modelo = entidad[
        "modelo"
    ]

    # --------------------------------------------------------
    # CONTAR REGISTROS
    # --------------------------------------------------------

    if (
        componentes[
            "tipo"
        ]
        == "contar_registros"
    ):

        objetivo_host = {
            "ok": True,
            "resuelto": False,
            "modelo": modelo,
            "objetivo": None,
            "candidatos": [],
            "razon": (
                "QUERY009 determinó que la consulta solicita "
                "conteo del modelo principal y no de un objetivo."
            ),
            "llm_invocado": False,
        }

        operacion_host = (
            resolver_operacion_datos(
                pregunta,
                modelo=modelo,
                objetivo_host=objetivo_host,
            )
        )

        if (
            not isinstance(
                operacion_host,
                dict,
            )
            or operacion_host.get(
                "ok"
            )
            is not True
            or operacion_host.get(
                "resuelto"
            )
            is not True
            or operacion_host.get(
                "compatible"
            )
            is not True
        ):

            return _error(
                pregunta=pregunta,
                estado="agregacion_rechazada_por_host",
                razon=(
                    "HOST no aceptó el conteo de registros."
                ),
                modelo=modelo,
                operacion_host=operacion_host,
            )

        return {
            "ok":
                True,

            "version":
                VERSION,

            "ejecutado":
                False,

            "estado":
                "agregacion_validada",

            "modo":
                "agregaciones",

            "pregunta":
                pregunta,

            "modelo":
                modelo,

            "entidad_solicitada":
                componentes[
                    "entidad"
                ],

            "objetivo_solicitado":
                None,

            "operacion_semantica":
                operacion_host.get(
                    "operacion_semantica"
                ),

            "accion_plan":
                operacion_host.get(
                    "accion_plan"
                ),

            "compatible":
                True,

            "objetivo_host":
                objetivo_host,

            "operacion_host":
                operacion_host,

            "resolucion_entidad":
                entidad[
                    "resolucion"
                ],

            "llm_invocado":
                False,

            "razon":
                (
                    "QUERY009 resolvió un conteo del modelo "
                    "principal y HOST certificó la operación."
                ),
        }

    # --------------------------------------------------------
    # AGREGACIÓN SOBRE OBJETIVO
    # --------------------------------------------------------

    resolucion_objetivo = (
        _resolver_objetivo_agregacion(
            expresion=componentes[
                "objetivo"
            ],
            modelo=modelo,
        )
    )

    objetivo_host = (
        resolucion_objetivo.get(
            "objetivo_host"
        )
    )

    if (
        resolucion_objetivo.get(
            "ok"
        )
        is not True
    ):

        return _error(
            pregunta=pregunta,
            estado="objetivo_no_resuelto",
            razon=(
                "El objetivo de la agregación no pudo "
                "resolverse de forma inequívoca."
            ),
            modelo=modelo,
            objetivo_solicitado=(
                componentes[
                    "objetivo"
                ]
            ),
            objetivo_host=objetivo_host,
            resolucion_objetivo=(
                resolucion_objetivo
            ),
        )

    operacion_host = (
        resolver_operacion_datos(
            pregunta,
            modelo=modelo,
            objetivo_host=objetivo_host,
        )
    )

    if (
        not isinstance(
            operacion_host,
            dict,
        )
        or operacion_host.get(
            "ok"
        )
        is not True
        or operacion_host.get(
            "resuelto"
        )
        is not True
    ):

        return _error(
            pregunta=pregunta,
            estado="operacion_no_resuelta",
            razon=(
                "HOST no pudo resolver una operación "
                "semántica inequívoca."
            ),
            modelo=modelo,
            objetivo_host=objetivo_host,
            resolucion_objetivo=(
                resolucion_objetivo
            ),
            operacion_host=operacion_host,
        )

    if (
        operacion_host.get(
            "compatible"
        )
        is not True
    ):

        return _error(
            pregunta=pregunta,
            estado="agregacion_incompatible",
            razon=(
                operacion_host.get(
                    "razon"
                )
                or
                "HOST rechazó la agregación solicitada."
            ),
            modelo=modelo,
            objetivo_solicitado=(
                componentes[
                    "objetivo"
                ]
            ),
            objetivo_host=objetivo_host,
            resolucion_objetivo=(
                resolucion_objetivo
            ),
            operacion_host=operacion_host,
        )

    if (
        operacion_host.get(
            "compatible"
        )
        is not True
    ):

        return _error(
            pregunta=pregunta,
            estado="agregacion_incompatible",
            razon=(
                operacion_host.get(
                    "razon"
                )
                or
                "HOST rechazó la agregación solicitada."
            ),
            modelo=modelo,
            objetivo_solicitado=(
                componentes[
                    "objetivo"
                ]
            ),
            objetivo_host=objetivo_host,
            operacion_host=operacion_host,
        )

    return {
        "ok":
            True,

        "version":
            VERSION,

        "ejecutado":
            False,

        "estado":
            "agregacion_validada",

        "modo":
            "agregaciones",

        "pregunta":
            pregunta,

        "modelo":
            modelo,

        "entidad_solicitada":
            componentes[
                "entidad"
            ],

        "objetivo_solicitado":
            componentes[
                "objetivo"
            ],

        "operacion_semantica":
            operacion_host.get(
                "operacion_semantica"
            ),

        "accion_plan":
            operacion_host.get(
                "accion_plan"
            ),

        "compatible":
            True,

        "tipo_django_objetivo":
            operacion_host.get(
                "tipo_django_objetivo"
            ),

        "objetivo_host":
            objetivo_host,

        "operacion_host":
            operacion_host,

        "resolucion_entidad":
            entidad[
                "resolucion"
            ],

        "llm_invocado":
            False,

        "razon":
            (
                "QUERY009 resolvió una agregación natural y "
                "HOST certificó su compatibilidad con el "
                "tipo Django real."
            ),
    }