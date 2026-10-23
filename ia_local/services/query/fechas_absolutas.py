from __future__ import annotations

from ia_local.config.cardinalidad import LIMITE_MUESTRA_PREDETERMINADO

import re
import unicodedata
from datetime import date
from typing import Any

from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)
from ia_local.services.semantica.resolvedor_ambiguedades import (
    resolver_expresion_semantica,
)


VERSION = "IA-QUERY005-v1"


# ============================================================
# UTILIDADES
# ============================================================


def _texto(
    valor: Any,
) -> str:

    if valor is None:
        return ""

    return str(
        valor
    ).strip()


def _normalizar_texto(
    texto: str,
) -> str:
    """
    Normalización destinada solamente al reconocimiento
    estructural del lenguaje.

    No modifica expresiones enviadas posteriormente a SEM.
    """

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


def _error(
    estado: str,
    pregunta: str,
    razon: str,
    **extra: Any,
) -> dict[str, Any]:

    salida = {
        "ok":
            False,

        "version":
            VERSION,

        "ejecutado":
            False,

        "estado":
            estado,

        "modo":
            "fechas_absolutas",

        "pregunta":
            pregunta,

        "razon":
            razon,

        "llm_invocado":
            False,
    }

    salida.update(
        extra
    )

    return salida


# ============================================================
# FECHAS
# ============================================================


def _normalizar_fecha_absoluta(
    expresion: str,
) -> str:
    """
    Formatos aceptados:

        YYYY-MM-DD
        YYYY/MM/DD
        DD/MM/YYYY
        DD-MM-YYYY

    Siempre retorna:

        YYYY-MM-DD

    La validez calendario se comprueba con datetime.date.
    """

    expresion = _texto(
        expresion
    )

    if not expresion:

        raise ValueError(
            "La fecha está vacía."
        )

    # --------------------------------------------------------
    # YYYY-MM-DD
    # --------------------------------------------------------

    coincidencia = re.fullmatch(
        r"(\d{4})-(\d{1,2})-(\d{1,2})",
        expresion,
    )

    if coincidencia:

        anio = int(
            coincidencia.group(
                1
            )
        )

        mes = int(
            coincidencia.group(
                2
            )
        )

        dia = int(
            coincidencia.group(
                3
            )
        )

        return date(
            anio,
            mes,
            dia,
        ).isoformat()

    # --------------------------------------------------------
    # YYYY/MM/DD
    # --------------------------------------------------------

    coincidencia = re.fullmatch(
        r"(\d{4})/(\d{1,2})/(\d{1,2})",
        expresion,
    )

    if coincidencia:

        anio = int(
            coincidencia.group(
                1
            )
        )

        mes = int(
            coincidencia.group(
                2
            )
        )

        dia = int(
            coincidencia.group(
                3
            )
        )

        return date(
            anio,
            mes,
            dia,
        ).isoformat()

    # --------------------------------------------------------
    # DD/MM/YYYY o DD-MM-YYYY
    # --------------------------------------------------------

    coincidencia = re.fullmatch(
        r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})",
        expresion,
    )

    if coincidencia:

        dia = int(
            coincidencia.group(
                1
            )
        )

        mes = int(
            coincidencia.group(
                2
            )
        )

        anio = int(
            coincidencia.group(
                3
            )
        )

        return date(
            anio,
            mes,
            dia,
        ).isoformat()

    raise ValueError(
        (
            "Formato de fecha no reconocido. "
            "Use YYYY-MM-DD, YYYY/MM/DD, "
            "DD/MM/YYYY o DD-MM-YYYY."
        )
    )


# ============================================================
# EXPRESIONES RELATIVAS
# ============================================================


EXPRESIONES_RELATIVAS = (
    r"\bhoy\b",
    r"\bayer\b",
    r"\banteayer\b",
    r"\bmanana\b",
    r"\besta semana\b",
    r"\bsemana pasada\b",
    r"\bsemana anterior\b",
    r"\beste mes\b",
    r"\bmes pasado\b",
    r"\bmes anterior\b",
    r"\beste ano\b",
    r"\bano pasado\b",
    r"\bultimos?\s+\d+\s+dias?\b",
    r"\bultimas?\s+\d+\s+semanas?\b",
    r"\bultimos?\s+\d+\s+meses?\b",
)


def _contiene_fecha_relativa(
    pregunta: str,
) -> bool:

    normalizada = _normalizar_texto(
        pregunta
    )

    return any(
        re.search(
            patron,
            normalizada,
        )
        for patron
        in EXPRESIONES_RELATIVAS
    )


# ============================================================
# PARSER
# ============================================================


TOKEN_FECHA = (
    r"\d{1,4}[/-]\d{1,2}[/-]\d{1,4}"
)


def _extraer_componentes(
    pregunta: str,
) -> dict[str, Any] | None:
    """
    Formas soportadas:

    FECHA EXACTA
        listar documentos cuya fecha es 2026-09-15
        listar documentos con fecha 15/09/2026

    RANGO DESDE/HASTA
        listar documentos cuya fecha desde
        2026-09-01 hasta 2026-09-30

    RANGO ENTRE/Y
        listar documentos cuya fecha entre
        01/09/2026 y 30/09/2026
    """

    # --------------------------------------------------------
    # RANGO: DESDE / HASTA
    # --------------------------------------------------------

    patron_rango_desde = re.compile(
        rf"""
        ^\s*
        (?P<operacion>
            listar
            | mostrar
            | muestrame
            | mu[eé]strame
        )
        \s+
        (?P<entidad>.+?)
        \s+
        (?:
            cuy[oa]
            |
            con
        )
        \s+
        (?P<campo>.+?)
        \s+
        desde
        \s+
        (?P<fecha_desde>{TOKEN_FECHA})
        \s+
        hasta
        \s+
        (?P<fecha_hasta>{TOKEN_FECHA})
        \s*$
        """,
        flags=(
            re.IGNORECASE
            | re.VERBOSE
        ),
    )

    coincidencia = patron_rango_desde.match(
        pregunta
    )

    if coincidencia is not None:

        return {
            "operacion":
                "listar",

            "tipo_consulta":
                "rango",

            "forma":
                "desde_hasta",

            "entidad":
                _texto(
                    coincidencia.group(
                        "entidad"
                    )
                ),

            "campo":
                _texto(
                    coincidencia.group(
                        "campo"
                    )
                ),

            "fecha_desde":
                _texto(
                    coincidencia.group(
                        "fecha_desde"
                    )
                ),

            "fecha_hasta":
                _texto(
                    coincidencia.group(
                        "fecha_hasta"
                    )
                ),
        }

    # --------------------------------------------------------
    # RANGO: ENTRE / Y
    # --------------------------------------------------------

    patron_rango_entre = re.compile(
        rf"""
        ^\s*
        (?P<operacion>
            listar
            | mostrar
            | muestrame
            | mu[eé]strame
        )
        \s+
        (?P<entidad>.+?)
        \s+
        (?:
            cuy[oa]
            |
            con
        )
        \s+
        (?P<campo>.+?)
        \s+
        (?:esta\s+)?
        entre
        \s+
        (?P<fecha_desde>{TOKEN_FECHA})
        \s+
        y
        \s+
        (?P<fecha_hasta>{TOKEN_FECHA})
        \s*$
        """,
        flags=(
            re.IGNORECASE
            | re.VERBOSE
        ),
    )

    coincidencia = patron_rango_entre.match(
        pregunta
    )

    if coincidencia is not None:

        return {
            "operacion":
                "listar",

            "tipo_consulta":
                "rango",

            "forma":
                "entre_y",

            "entidad":
                _texto(
                    coincidencia.group(
                        "entidad"
                    )
                ),

            "campo":
                _texto(
                    coincidencia.group(
                        "campo"
                    )
                ),

            "fecha_desde":
                _texto(
                    coincidencia.group(
                        "fecha_desde"
                    )
                ),

            "fecha_hasta":
                _texto(
                    coincidencia.group(
                        "fecha_hasta"
                    )
                ),
        }

    # --------------------------------------------------------
    # FECHA EXACTA
    # --------------------------------------------------------

    patron_exacta = re.compile(
        rf"""
        ^\s*
        (?P<operacion>
            listar
            | mostrar
            | muestrame
            | mu[eé]strame
        )
        \s+
        (?P<entidad>.+?)
        \s+
        (?:
            cuy[oa]
            |
            con
        )
        \s+
        (?P<campo>.+?)
        \s+
        (?:
            es
            |
            igual\s+a
            |
            del
            |
            de
        )
        \s+
        (?P<fecha>{TOKEN_FECHA})
        \s*$
        """,
        flags=(
            re.IGNORECASE
            | re.VERBOSE
        ),
    )

    coincidencia = patron_exacta.match(
        pregunta
    )

    if coincidencia is not None:

        return {
            "operacion":
                "listar",

            "tipo_consulta":
                "exacta",

            "forma":
                "fecha_exacta",

            "entidad":
                _texto(
                    coincidencia.group(
                        "entidad"
                    )
                ),

            "campo":
                _texto(
                    coincidencia.group(
                        "campo"
                    )
                ),

            "fecha":
                _texto(
                    coincidencia.group(
                        "fecha"
                    )
                ),
        }

    return None


# ============================================================
# SEM006
# ============================================================


def _extraer_entidad_sem(
    resolucion: dict[str, Any],
) -> str | None:

    if not isinstance(
        resolucion,
        dict,
    ):
        return None

    if (
        resolucion.get(
            "ok"
        )
        is not True
    ):
        return None

    if (
        resolucion.get(
            "estado"
        )
        != "resuelto"
    ):
        return None

    resultado = resolucion.get(
        "resultado"
    )

    if not isinstance(
        resultado,
        dict,
    ):
        return None

    if (
        resultado.get(
            "tipo"
        )
        != "entidad"
    ):
        return None

    modelo = _texto(
        resultado.get(
            "modelo"
        )
    )

    return (
        modelo
        or None
    )


def _extraer_campo_sem(
    resolucion: dict[str, Any],
    modelo: str,
) -> str | None:

    if not isinstance(
        resolucion,
        dict,
    ):
        return None

    if (
        resolucion.get(
            "ok"
        )
        is not True
    ):
        return None

    if (
        resolucion.get(
            "estado"
        )
        != "resuelto"
    ):
        return None

    resultado = resolucion.get(
        "resultado"
    )

    if not isinstance(
        resultado,
        dict,
    ):
        return None

    if (
        resultado.get(
            "tipo"
        )
        != "campo"
    ):
        return None

    modelo_resultado = _texto(
        resultado.get(
            "modelo"
        )
    )

    if (
        modelo_resultado
        and modelo_resultado
        != modelo
    ):
        return None

    campo = _texto(
        resultado.get(
            "campo"
        )
    )

    return (
        campo
        or None
    )


# ============================================================
# TIPO DE CAMPO CERTIFICADO POR HOST
# ============================================================


def _tipos_filtros_host(
    validacion_host: dict[str, Any],
) -> set[str]:

    if not isinstance(
        validacion_host,
        dict,
    ):
        return set()

    plan = validacion_host.get(
        "plan"
    )

    if not isinstance(
        plan,
        dict,
    ):
        return set()

    filtros = plan.get(
        "filtros"
    )

    if not isinstance(
        filtros,
        list,
    ):
        return set()

    tipos = set()

    for filtro in filtros:

        if not isinstance(
            filtro,
            dict,
        ):
            continue

        tipo = _texto(
            filtro.get(
                "tipo"
            )
        )

        if tipo:
            tipos.add(
                tipo
            )

    return tipos


# ============================================================
# API PÚBLICA
# ============================================================


def componer_fechas_absolutas(
    pregunta: str,
    *,
    limite: int = LIMITE_MUESTRA_PREDETERMINADO,
) -> dict[str, Any]:
    """
    IA-QUERY005.

    Compone filtros de fecha absoluta y rangos inclusivos.

    No ejecuta ORM.
    No utiliza LLM.
    SEM resuelve entidad/campo.
    HOST certifica tipo, operador y valor.
    """

    pregunta = _texto(
        pregunta
    )

    if not pregunta:

        return _error(
            "pregunta_vacia",
            pregunta,
            "La consulta está vacía.",
        )

    # --------------------------------------------------------
    # QUERY006, NO QUERY005
    # --------------------------------------------------------

    if _contiene_fecha_relativa(
        pregunta
    ):

        return _error(
            "fecha_relativa_no_permitida",
            pregunta,
            (
                "QUERY005 sólo procesa fechas absolutas. "
                "Las expresiones relativas corresponden "
                "a IA-QUERY006."
            ),
        )

    # --------------------------------------------------------
    # PARSER
    # --------------------------------------------------------

    componentes = _extraer_componentes(
        pregunta
    )

    if componentes is None:

        return _error(
            "fecha_absoluta_no_detectada",
            pregunta,
            (
                "No se encontró una expresión segura de "
                "fecha absoluta o rango."
            ),
        )

    # --------------------------------------------------------
    # NORMALIZAR FECHAS
    # --------------------------------------------------------

    tipo_consulta = componentes[
        "tipo_consulta"
    ]

    try:

        if tipo_consulta == "exacta":

            fecha = _normalizar_fecha_absoluta(
                componentes[
                    "fecha"
                ]
            )

            fecha_desde = None
            fecha_hasta = None

        else:

            fecha = None

            fecha_desde = (
                _normalizar_fecha_absoluta(
                    componentes[
                        "fecha_desde"
                    ]
                )
            )

            fecha_hasta = (
                _normalizar_fecha_absoluta(
                    componentes[
                        "fecha_hasta"
                    ]
                )
            )

    except ValueError as exc:

        return _error(
            "fecha_invalida",
            pregunta,
            str(
                exc
            ),
            componentes=componentes,
        )

    # --------------------------------------------------------
    # COHERENCIA DEL RANGO
    # --------------------------------------------------------

    if (
        tipo_consulta == "rango"
        and fecha_desde is not None
        and fecha_hasta is not None
        and date.fromisoformat(
            fecha_desde
        )
        > date.fromisoformat(
            fecha_hasta
        )
    ):

        return _error(
            "rango_fecha_invertido",
            pregunta,
            (
                "La fecha inicial es posterior "
                "a la fecha final."
            ),
            componentes=componentes,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )

    # --------------------------------------------------------
    # SEM006 - ENTIDAD
    # --------------------------------------------------------

    resolucion_entidad = (
        resolver_expresion_semantica(
            componentes[
                "entidad"
            ],
        )
    )

    modelo = _extraer_entidad_sem(
        resolucion_entidad
    )

    if modelo is None:

        return _error(
            "entidad_no_resuelta",
            pregunta,
            (
                "SEM006 no resolvió de forma inequívoca "
                "la entidad solicitada."
            ),
            componentes=componentes,
            resolucion_entidad=(
                resolucion_entidad
            ),
        )

    # --------------------------------------------------------
    # SEM006 - CAMPO
    # --------------------------------------------------------

    resolucion_campo = (
        resolver_expresion_semantica(
            componentes[
                "campo"
            ],
            modelo_contexto=modelo,
        )
    )

    campo = _extraer_campo_sem(
        resolucion_campo,
        modelo,
    )

    if campo is None:

        return _error(
            "campo_fecha_no_resuelto",
            pregunta,
            (
                "SEM006 no resolvió de forma inequívoca "
                "el campo temporal solicitado."
            ),
            componentes=componentes,
            modelo=modelo,
            resolucion_entidad=(
                resolucion_entidad
            ),
            resolucion_campo=(
                resolucion_campo
            ),
        )

    # --------------------------------------------------------
    # FILTROS DECLARATIVOS
    # --------------------------------------------------------

    if tipo_consulta == "exacta":

        filtros = [
            {
                "campo":
                    campo,

                "operador":
                    "exact",

                "valor":
                    fecha,
            }
        ]

    else:

        filtros = [
            {
                "campo":
                    campo,

                "operador":
                    "gte",

                "valor":
                    fecha_desde,
            },
            {
                "campo":
                    campo,

                "operador":
                    "lte",

                "valor":
                    fecha_hasta,
            },
        ]

    propuesta_host = {
        "modelo":
            modelo,

        "operacion":
            "listar",

        "filtros":
            filtros,

        "orden":
            [],

        "limite":
            limite,

        "condiciones_no_resueltas":
            [],
    }

    # --------------------------------------------------------
    # HOST
    # --------------------------------------------------------

    validacion_host = validar_plan_datos(
        propuesta_host
    )

    if (
        not isinstance(
            validacion_host,
            dict,
        )
        or validacion_host.get(
            "ok"
        )
        is not True
        or validacion_host.get(
            "plan_validado"
        )
        is not True
    ):

        return _error(
            "rechazado_por_host",
            pregunta,
            (
                "QUERY005 resolvió la expresión temporal, "
                "pero HOST rechazó el plan."
            ),
            componentes=componentes,
            modelo=modelo,
            campo=campo,
            propuesta_host=(
                propuesta_host
            ),
            validacion_host=(
                validacion_host
            ),
            resolucion_entidad=(
                resolucion_entidad
            ),
            resolucion_campo=(
                resolucion_campo
            ),
        )

    # --------------------------------------------------------
    # CERTIFICAR QUE REALMENTE ES CAMPO TEMPORAL
    # --------------------------------------------------------

    tipos_host = _tipos_filtros_host(
        validacion_host
    )

    tipos_temporales = {
        "DateField",
        "DateTimeField",
    }

    if (
        not tipos_host
        or not tipos_host.issubset(
            tipos_temporales
        )
    ):

        return _error(
            "campo_no_temporal",
            pregunta,
            (
                "El campo fue resuelto, pero HOST no lo "
                "identificó como DateField o DateTimeField."
            ),
            componentes=componentes,
            modelo=modelo,
            campo=campo,
            tipos_host=sorted(
                tipos_host
            ),
            validacion_host=(
                validacion_host
            ),
        )

    # --------------------------------------------------------
    # RESPUESTA
    # --------------------------------------------------------

    return {
        "ok":
            True,

        "version":
            VERSION,

        "ejecutado":
            False,

        "estado":
            (
                "fecha_exacta_validada"
                if tipo_consulta == "exacta"
                else "rango_fecha_validado"
            ),

        "modo":
            "fechas_absolutas",

        "pregunta":
            pregunta,

        "tipo_consulta":
            tipo_consulta,

        "forma":
            componentes.get(
                "forma"
            ),

        "modelo":
            modelo,

        "campo_solicitado":
            componentes[
                "campo"
            ],

        "campo_resuelto":
            campo,

        "tipo_campo":
            sorted(
                tipos_host
            )[0],

        "fecha":
            fecha,

        "fecha_desde":
            fecha_desde,

        "fecha_hasta":
            fecha_hasta,

        "propuesta_host":
            propuesta_host,

        "validacion_host":
            validacion_host,

        "plan":
            validacion_host.get(
                "plan"
            ),

        "resolucion_entidad":
            resolucion_entidad,

        "resolucion_campo":
            resolucion_campo,

        "llm_invocado":
            False,

        "razon":
            (
                "QUERY005 normalizó una expresión temporal "
                "absoluta y HOST certificó el plan sin "
                "ejecutar ORM."
            ),
    }