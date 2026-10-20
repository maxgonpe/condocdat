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
from ia_local.services.host.validador_agrupamiento_datos import (
    validar_agrupamiento_datos,
)


# ============================================================
# IA-QUERY010
# AGRUPAMIENTOS
# ============================================================
#
# Responsabilidad:
#
#   convertir expresiones naturales explícitas de agrupamiento
#   en componentes certificados por HOST.
#
# QUERY010:
#   - NO ejecuta ORM;
#   - NO usa LLM;
#   - NO genera SQL;
#   - NO usa annotate();
#   - NO usa values();
#   - NO inventa campos;
#   - NO inventa relaciones.
#
# Flujo:
#
#   lenguaje natural
#       -> QUERY010
#       -> SEM006 / HOST023
#       -> HOST024
#       -> HOST035
#
# ============================================================


VERSION = "IA-QUERY010-v1"


def _texto(
    valor: Any,
) -> str:

    return str(
        valor or ""
    ).strip()


def _normalizar(
    valor: Any,
) -> str:

    texto = _texto(
        valor
    ).lower()

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
        "modo": "agrupamientos",
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
            "expresion_original":
                expresion,
            "expresion_limpia":
                expresion_limpia,
            "resolucion":
                resolucion,
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
            "expresion_original":
                expresion,
            "expresion_limpia":
                expresion_limpia,
            "resolucion":
                resolucion,
        }

    modelo = _texto(
        resultado.get(
            "modelo"
        )
    )

    if not modelo:

        return {
            "ok": False,
            "expresion_original":
                expresion,
            "expresion_limpia":
                expresion_limpia,
            "resolucion":
                resolucion,
        }

    return {
        "ok": True,
        "modelo": modelo,
        "expresion_original":
            expresion,
        "expresion_limpia":
            expresion_limpia,
        "resolucion":
            resolucion,
    }


# ============================================================
# OBJETIVOS
# ============================================================


def _resolver_objetivo(
    *,
    expresion: str,
    modelo: str,
) -> dict[str, Any]:

    # --------------------------------------------------------
    # 1. HOST023
    #
    # Prioridad para nombres canónicos, relaciones y aliases
    # estructurales de Django.
    # --------------------------------------------------------

    objetivo_host_inicial = (
        resolver_objetivo_datos(
            expresion,
            modelo=modelo,
        )
    )

    if (
        isinstance(
            objetivo_host_inicial,
            dict,
        )
        and objetivo_host_inicial.get(
            "ok"
        )
        is True
        and objetivo_host_inicial.get(
            "resuelto"
        )
        is True
    ):

        return {
            "ok": True,
            "objetivo_host":
                objetivo_host_inicial,
            "resolucion_semantica":
                None,
            "via":
                "HOST023",
        }

    # --------------------------------------------------------
    # 2. SEM006
    #
    # Ejemplos:
    #
    # estado   -> status
    # fecha    -> date
    # tema     -> title
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
            "ok": False,
            "objetivo_host":
                objetivo_host_inicial,
            "resolucion_semantica":
                resolucion_semantica,
            "via":
                None,
        }

    resultado = resolucion_semantica.get(
        "resultado"
    )

    if not isinstance(
        resultado,
        dict,
    ):

        return {
            "ok": False,
            "objetivo_host":
                objetivo_host_inicial,
            "resolucion_semantica":
                resolucion_semantica,
            "via":
                None,
        }

    tipo = _texto(
        resultado.get(
            "tipo"
        )
    )

    if tipo == "campo":

        nombre_canonico = _texto(
            resultado.get(
                "campo"
            )
        )

    elif tipo == "relacion":

        nombre_canonico = _texto(
            resultado.get(
                "campo",
                resultado.get(
                    "relacion"
                ),
            )
        )

    else:

        nombre_canonico = ""

    if not nombre_canonico:

        return {
            "ok": False,
            "objetivo_host":
                objetivo_host_inicial,
            "resolucion_semantica":
                resolucion_semantica,
            "via":
                None,
        }

    objetivo_host = (
        resolver_objetivo_datos(
            nombre_canonico,
            modelo=modelo,
        )
    )

    if (
        not isinstance(
            objetivo_host,
            dict,
        )
        or objetivo_host.get(
            "ok"
        )
        is not True
        or objetivo_host.get(
            "resuelto"
        )
        is not True
    ):

        return {
            "ok": False,
            "objetivo_host":
                objetivo_host,
            "objetivo_host_inicial":
                objetivo_host_inicial,
            "resolucion_semantica":
                resolucion_semantica,
            "via":
                None,
        }

    return {
        "ok": True,
        "objetivo_host":
            objetivo_host,
        "objetivo_host_inicial":
            objetivo_host_inicial,
        "resolucion_semantica":
            resolucion_semantica,
        "via":
            "SEM006->HOST023",
    }


# ============================================================
# PARSER
# ============================================================


def _extraer_consulta(
    pregunta: str,
) -> dict[str, Any] | None:

    texto = _normalizar(
        pregunta
    )

    # --------------------------------------------------------
    # CONTEO DE REGISTROS AGRUPADO
    #
    # cuantos documentos por estado
    # cantidad de documentos por estado
    # numero de documentos por estado
    # total de documentos por estado
    # --------------------------------------------------------

    patrones_conteo = (
        r"^cuantos?\s+"
        r"(?P<entidad>.+?)\s+"
        r"por\s+"
        r"(?P<grupo>.+?)$",

        r"^cuantas?\s+"
        r"(?P<entidad>.+?)\s+"
        r"por\s+"
        r"(?P<grupo>.+?)$",

        r"^(?:cantidad|numero|nro|total)\s+de\s+"
        r"(?P<entidad>.+?)\s+"
        r"por\s+"
        r"(?P<grupo>.+?)$",
    )

    for patron in patrones_conteo:

        coincidencia = re.match(
            patron,
            texto,
        )

        if coincidencia:

            return {
                "tipo":
                    "conteo_agrupado",

                "entidad":
                    _limpiar_entidad_natural(
                        coincidencia.group(
                            "entidad"
                        )
                    ),

                "grupo":
                    _texto(
                        coincidencia.group(
                            "grupo"
                        )
                    ),

                "objetivo":
                    None,

                "operacion":
                    "contar",
            }

    # --------------------------------------------------------
    # AGREGACIÓN SOBRE OBJETIVO AGRUPADA
    #
    # suma de number por estado de documentos
    # promedio de number por estado de documentos
    # maximo de fecha por proyecto de documentos
    # minimo de fecha por estado de documentos
    # --------------------------------------------------------

    patron_agregado = re.compile(
        r"^(?P<operacion>"
        r"suma|sumar|sumatoria|"
        r"promedio|media|"
        r"maximo|mayor|"
        r"minimo|menor"
        r")"
        r"(?:\s+de)?\s+"
        r"(?P<objetivo>.+?)\s+"
        r"por\s+"
        r"(?P<grupo>.+?)\s+"
        r"de\s+"
        r"(?P<entidad>.+?)$"
    )

    coincidencia = patron_agregado.match(
        texto
    )

    if coincidencia:

        return {
            "tipo":
                "agregacion_agrupada",

            "entidad":
                _limpiar_entidad_natural(
                    coincidencia.group(
                        "entidad"
                    )
                ),

            "grupo":
                _texto(
                    coincidencia.group(
                        "grupo"
                    )
                ),

            "objetivo":
                _texto(
                    coincidencia.group(
                        "objetivo"
                    )
                ),

            "operacion":
                _texto(
                    coincidencia.group(
                        "operacion"
                    )
                ),
        }

    return None


# ============================================================
# API PÚBLICA
# ============================================================


def componer_agrupamiento(
    pregunta: str,
) -> dict[str, Any]:

    pregunta = _texto(
        pregunta
    )

    if not pregunta:

        return _error(
            pregunta=pregunta,
            estado="pregunta_vacia",
            razon=(
                "La pregunta no contiene texto."
            ),
        )

    componentes = (
        _extraer_consulta(
            pregunta
        )
    )

    if componentes is None:

        return _error(
            pregunta=pregunta,
            estado=(
                "estructura_agrupamiento_"
                "no_detectada"
            ),
            razon=(
                "QUERY010 no detectó una estructura "
                "explícita de agrupamiento."
            ),
        )

    # --------------------------------------------------------
    # ENTIDAD
    # --------------------------------------------------------

    resolucion_entidad = (
        _resolver_entidad(
            componentes[
                "entidad"
            ]
        )
    )

    if (
        resolucion_entidad.get(
            "ok"
        )
        is not True
    ):

        return _error(
            pregunta=pregunta,
            estado="entidad_no_resuelta",
            razon=(
                "La entidad principal no pudo "
                "resolverse de forma inequívoca."
            ),
            entidad_solicitada=(
                componentes[
                    "entidad"
                ]
            ),
            resolucion_entidad=(
                resolucion_entidad
            ),
        )

    modelo = resolucion_entidad[
        "modelo"
    ]

    # --------------------------------------------------------
    # CAMPO AGRUPADOR
    # --------------------------------------------------------

    resolucion_grupo = (
        _resolver_objetivo(
            expresion=componentes[
                "grupo"
            ],
            modelo=modelo,
        )
    )

    if (
        resolucion_grupo.get(
            "ok"
        )
        is not True
    ):

        return _error(
            pregunta=pregunta,
            estado=(
                "campo_agrupacion_"
                "no_resuelto"
            ),
            razon=(
                "El campo solicitado para agrupación "
                "no pudo resolverse de forma "
                "inequívoca."
            ),
            modelo=modelo,
            grupo_solicitado=(
                componentes[
                    "grupo"
                ]
            ),
            resolucion_grupo=(
                resolucion_grupo
            ),
        )

    grupo_host = (
        resolucion_grupo[
            "objetivo_host"
        ]
    )

    campo_agrupacion = (
        grupo_host.get(
            "objetivo"
        )
    )

    # --------------------------------------------------------
    # CONTEO AGRUPADO
    # --------------------------------------------------------

    if (
        componentes[
            "tipo"
        ]
        == "conteo_agrupado"
    ):

        objetivo_vacio = {
            "ok": True,
            "resuelto": False,
            "modelo": modelo,
            "objetivo": None,
            "candidatos": [],
            "razon": (
                "QUERY010 determinó un conteo "
                "de registros por grupo."
            ),
            "llm_invocado": False,
        }

        operacion_host = (
            resolver_operacion_datos(
                "cuantos registros",
                modelo=modelo,
                objetivo_host=(
                    objetivo_vacio
                ),
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
                estado=(
                    "operacion_no_resuelta"
                ),
                razon=(
                    "HOST024 no certificó el "
                    "conteo de registros."
                ),
                modelo=modelo,
                operacion_host=(
                    operacion_host
                ),
            )

        agrupamiento_host = (
            validar_agrupamiento_datos(
                modelo=modelo,
                campo_agrupacion=(
                    campo_agrupacion
                ),
                operacion_semantica=(
                    operacion_host
                ),
                objetivo_agregado=None,
            )
        )

        if (
            agrupamiento_host.get(
                "ok"
            )
            is not True
        ):

            return _error(
                pregunta=pregunta,
                estado=(
                    "agrupamiento_rechazado_"
                    "por_host"
                ),
                razon=(
                    agrupamiento_host.get(
                        "razon"
                    )
                    or
                    "HOST035 rechazó el agrupamiento."
                ),
                modelo=modelo,
                grupo_solicitado=(
                    componentes[
                        "grupo"
                    ]
                ),
                agrupamiento_host=(
                    agrupamiento_host
                ),
            )

        return {
            "ok": True,
            "version": VERSION,
            "ejecutado": False,
            "estado":
                "agrupamiento_validado",
            "modo":
                "agrupamientos",
            "pregunta":
                pregunta,
            "modelo":
                modelo,
            "entidad_solicitada":
                componentes[
                    "entidad"
                ],
            "grupo_solicitado":
                componentes[
                    "grupo"
                ],
            "campo_agrupacion":
                campo_agrupacion,
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
            "resolucion_entidad":
                resolucion_entidad.get(
                    "resolucion"
                ),
            "resolucion_grupo":
                resolucion_grupo,
            "operacion_host":
                operacion_host,
            "agrupamiento_host":
                agrupamiento_host,
            "llm_invocado":
                False,
            "razon": (
                "QUERY010 compuso un conteo "
                "agrupado y HOST035 certificó "
                "el contrato."
            ),
        }

    # --------------------------------------------------------
    # AGREGACIÓN AGRUPADA
    # --------------------------------------------------------

    resolucion_objetivo = (
        _resolver_objetivo(
            expresion=componentes[
                "objetivo"
            ],
            modelo=modelo,
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
            estado=(
                "objetivo_agregado_"
                "no_resuelto"
            ),
            razon=(
                "El objetivo de la agregación "
                "no pudo resolverse."
            ),
            modelo=modelo,
            objetivo_solicitado=(
                componentes[
                    "objetivo"
                ]
            ),
            resolucion_objetivo=(
                resolucion_objetivo
            ),
        )

    objetivo_host = (
        resolucion_objetivo[
            "objetivo_host"
        ]
    )

    objetivo_agregado = (
        objetivo_host.get(
            "objetivo"
        )
    )

    texto_operacion = (
        f"{componentes['operacion']} "
        f"de {componentes['objetivo']}"
    )

    operacion_host = (
        resolver_operacion_datos(
            texto_operacion,
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
                "HOST024 no pudo resolver "
                "la operación agregada."
            ),
            modelo=modelo,
            operacion_host=(
                operacion_host
            ),
        )

    if (
        operacion_host.get(
            "compatible"
        )
        is not True
    ):

        return _error(
            pregunta=pregunta,
            estado=(
                "agregacion_incompatible"
            ),
            razon=(
                operacion_host.get(
                    "razon"
                )
                or
                "HOST024 rechazó la operación."
            ),
            modelo=modelo,
            objetivo_solicitado=(
                componentes[
                    "objetivo"
                ]
            ),
            operacion_host=(
                operacion_host
            ),
        )

    agrupamiento_host = (
        validar_agrupamiento_datos(
            modelo=modelo,
            campo_agrupacion=(
                campo_agrupacion
            ),
            operacion_semantica=(
                operacion_host
            ),
            objetivo_agregado=(
                objetivo_agregado
            ),
        )
    )

    if (
        agrupamiento_host.get(
            "ok"
        )
        is not True
    ):

        return _error(
            pregunta=pregunta,
            estado=(
                "agrupamiento_rechazado_"
                "por_host"
            ),
            razon=(
                agrupamiento_host.get(
                    "razon"
                )
                or
                "HOST035 rechazó el agrupamiento."
            ),
            modelo=modelo,
            agrupamiento_host=(
                agrupamiento_host
            ),
        )

    return {
        "ok": True,
        "version": VERSION,
        "ejecutado": False,
        "estado":
            "agrupamiento_validado",
        "modo":
            "agrupamientos",
        "pregunta":
            pregunta,
        "modelo":
            modelo,
        "entidad_solicitada":
            componentes[
                "entidad"
            ],
        "grupo_solicitado":
            componentes[
                "grupo"
            ],
        "objetivo_solicitado":
            componentes[
                "objetivo"
            ],
        "campo_agrupacion":
            campo_agrupacion,
        "objetivo_agregado":
            objetivo_agregado,
        "operacion_semantica":
            operacion_host.get(
                "operacion_semantica"
            ),
        "accion_plan":
            operacion_host.get(
                "accion_plan"
            ),
        "resolucion_entidad":
            resolucion_entidad.get(
                "resolucion"
            ),
        "resolucion_grupo":
            resolucion_grupo,
        "resolucion_objetivo":
            resolucion_objetivo,
        "operacion_host":
            operacion_host,
        "agrupamiento_host":
            agrupamiento_host,
        "llm_invocado":
            False,
        "razon": (
            "QUERY010 compuso una agregación "
            "agrupada y HOST035 certificó "
            "el contrato."
        ),
    }