from __future__ import annotations

import calendar
import re
import unicodedata
from datetime import date, timedelta
from typing import Any

from django.utils import timezone

from ia_local.services.query.fechas_absolutas import (
    componer_fechas_absolutas,
)


VERSION = "IA-QUERY006-v1"


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
            "fechas_relativas",

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
# CALENDARIO
# ============================================================


def _inicio_semana(
    fecha: date,
) -> date:
    """
    Semana calendario ISO:
    lunes = primer día.
    """

    return (
        fecha
        - timedelta(
            days=fecha.weekday()
        )
    )


def _fin_semana(
    fecha: date,
) -> date:

    return (
        _inicio_semana(
            fecha
        )
        + timedelta(
            days=6
        )
    )


def _inicio_mes(
    fecha: date,
) -> date:

    return fecha.replace(
        day=1
    )


def _fin_mes(
    fecha: date,
) -> date:

    ultimo_dia = calendar.monthrange(
        fecha.year,
        fecha.month,
    )[1]

    return fecha.replace(
        day=ultimo_dia
    )


def _mes_anterior(
    fecha: date,
) -> date:

    primer_dia_actual = fecha.replace(
        day=1
    )

    return (
        primer_dia_actual
        - timedelta(
            days=1
        )
    )


# ============================================================
# RESOLUCIÓN TEMPORAL
# ============================================================


def _resolver_expresion_relativa(
    expresion: str,
    *,
    hoy: date,
) -> dict[str, Any] | None:

    expresion = _normalizar_texto(
        expresion
    )

    # --------------------------------------------------------
    # HOY
    # --------------------------------------------------------

    if expresion == "hoy":

        return {
            "tipo":
                "exacta",

            "expresion":
                "hoy",

            "fecha":
                hoy,
        }

    # --------------------------------------------------------
    # AYER
    # --------------------------------------------------------

    if expresion == "ayer":

        return {
            "tipo":
                "exacta",

            "expresion":
                "ayer",

            "fecha":
                hoy
                - timedelta(
                    days=1
                ),
        }

    # --------------------------------------------------------
    # MAÑANA
    # --------------------------------------------------------

    if expresion == "manana":

        return {
            "tipo":
                "exacta",

            "expresion":
                "mañana",

            "fecha":
                hoy
                + timedelta(
                    days=1
                ),
        }

    # --------------------------------------------------------
    # ESTA SEMANA
    # --------------------------------------------------------

    if expresion == "esta semana":

        return {
            "tipo":
                "rango",

            "expresion":
                "esta semana",

            "fecha_desde":
                _inicio_semana(
                    hoy
                ),

            "fecha_hasta":
                _fin_semana(
                    hoy
                ),
        }

    # --------------------------------------------------------
    # SEMANA PASADA
    # --------------------------------------------------------

    if expresion in {
        "semana pasada",
        "semana anterior",
        "la semana pasada",
        "la semana anterior",
    }:

        referencia = (
            hoy
            - timedelta(
                days=7
            )
        )

        return {
            "tipo":
                "rango",

            "expresion":
                "semana pasada",

            "fecha_desde":
                _inicio_semana(
                    referencia
                ),

            "fecha_hasta":
                _fin_semana(
                    referencia
                ),
        }

    # --------------------------------------------------------
    # ESTE MES
    # --------------------------------------------------------

    if expresion == "este mes":

        return {
            "tipo":
                "rango",

            "expresion":
                "este mes",

            "fecha_desde":
                _inicio_mes(
                    hoy
                ),

            "fecha_hasta":
                _fin_mes(
                    hoy
                ),
        }

    # --------------------------------------------------------
    # MES PASADO
    # --------------------------------------------------------

    if expresion in {
        "mes pasado",
        "mes anterior",
        "el mes pasado",
        "el mes anterior",
    }:

        referencia = _mes_anterior(
            hoy
        )

        return {
            "tipo":
                "rango",

            "expresion":
                "mes pasado",

            "fecha_desde":
                _inicio_mes(
                    referencia
                ),

            "fecha_hasta":
                _fin_mes(
                    referencia
                ),
        }

    # --------------------------------------------------------
    # ÚLTIMOS N DÍAS
    # --------------------------------------------------------

    coincidencia = re.fullmatch(
        r"(?:los\s+)?ultimos\s+(\d+)\s+dias?",
        expresion,
    )

    if coincidencia:

        cantidad = int(
            coincidencia.group(
                1
            )
        )

        if cantidad < 1:

            return {
                "tipo":
                    "error",

                "estado":
                    "cantidad_dias_invalida",

                "razon":
                    (
                        "La cantidad de días debe "
                        "ser mayor que cero."
                    ),
            }

        if cantidad > 3660:

            return {
                "tipo":
                    "error",

                "estado":
                    "cantidad_dias_excesiva",

                "razon":
                    (
                        "El rango relativo solicitado "
                        "es excesivamente grande."
                    ),
            }

        fecha_desde = (
            hoy
            - timedelta(
                days=cantidad - 1
            )
        )

        return {
            "tipo":
                "rango",

            "expresion":
                f"últimos {cantidad} días",

            "cantidad_dias":
                cantidad,

            "fecha_desde":
                fecha_desde,

            "fecha_hasta":
                hoy,
        }

    return None


# ============================================================
# PARSER DE CONSULTA
# ============================================================


EXPRESION_RELATIVA = r"""
(?:
    hoy
    |
    ayer
    |
    ma[nñ]ana
    |
    esta\s+semana
    |
    (?:la\s+)?semana\s+(?:pasada|anterior)
    |
    este\s+mes
    |
    (?:el\s+)?mes\s+(?:pasado|anterior)
    |
    (?:los\s+)?[uú]ltimos\s+\d+\s+d[ií]as?
)
"""


def _extraer_componentes(
    pregunta: str,
) -> dict[str, Any] | None:

    # --------------------------------------------------------
    # FORMA EXPLÍCITA
    #
    # listar documentos cuya fecha es hoy
    # listar documentos con fecha de ayer
    # listar documentos cuya fecha es este mes
    # --------------------------------------------------------

    patron_explicito = re.compile(
        rf"""
        ^\s*
        (?P<operacion>
            listar
            |
            mostrar
            |
            muestrame
            |
            mu[eé]strame
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
            de
            |
            del
            |
            en
            |
            durante
        )
        \s+
        (?P<relativa>
            {EXPRESION_RELATIVA}
        )
        \s*$
        """,
        flags=(
            re.IGNORECASE
            | re.VERBOSE
        ),
    )

    coincidencia = patron_explicito.match(
        pregunta
    )

    if coincidencia:

        return {
            "operacion":
                "listar",

            "forma":
                "explicita",

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

            "campo_inferido":
                False,

            "expresion_relativa":
                _texto(
                    coincidencia.group(
                        "relativa"
                    )
                ),
        }

    # --------------------------------------------------------
    # FORMA RÁPIDA
    #
    # listar documentos de hoy
    # listar documentos de ayer
    # listar documentos de esta semana
    # listar documentos del mes pasado
    # listar documentos de los últimos 7 días
    #
    # No se adivina un campo Django.
    # Se utiliza el concepto semántico "fecha".
    # SEM/QUERY005 debe resolverlo inequívocamente.
    # --------------------------------------------------------

    patron_rapido = re.compile(
        rf"""
        ^\s*
        (?P<operacion>
            listar
            |
            mostrar
            |
            muestrame
            |
            mu[eé]strame
        )
        \s+
        (?P<entidad>.+?)
        \s+
        (?:
            de
            |
            del
            |
            durante
        )
        \s+
        (?P<relativa>
            {EXPRESION_RELATIVA}
        )
        \s*$
        """,
        flags=(
            re.IGNORECASE
            | re.VERBOSE
        ),
    )

    coincidencia = patron_rapido.match(
        pregunta
    )

    if coincidencia:

        return {
            "operacion":
                "listar",

            "forma":
                "rapida",

            "entidad":
                _texto(
                    coincidencia.group(
                        "entidad"
                    )
                ),

            "campo":
                "fecha",

            "campo_inferido":
                True,

            "expresion_relativa":
                _texto(
                    coincidencia.group(
                        "relativa"
                    )
                ),
        }

    return None


# ============================================================
# API PÚBLICA
# ============================================================


def componer_fechas_relativas(
    pregunta: str,
    *,
    limite: int = 20,
    fecha_referencia: date | None = None,
) -> dict[str, Any]:
    """
    IA-QUERY006.

    Convierte expresiones temporales relativas en fechas
    absolutas y delega la certificación a QUERY005/HOST.

    No ejecuta ORM.
    No utiliza LLM.

    fecha_referencia existe para pruebas deterministas.
    En uso normal se utiliza timezone.localdate().
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

    componentes = _extraer_componentes(
        pregunta
    )

    if componentes is None:

        return _error(
            "fecha_relativa_no_detectada",
            pregunta,
            (
                "No se encontró una expresión temporal "
                "relativa soportada por QUERY006."
            ),
        )

    hoy = (
        fecha_referencia
        if fecha_referencia is not None
        else timezone.localdate()
    )

    resolucion_temporal = (
        _resolver_expresion_relativa(
            componentes[
                "expresion_relativa"
            ],
            hoy=hoy,
        )
    )

    if resolucion_temporal is None:

        return _error(
            "fecha_relativa_no_resuelta",
            pregunta,
            (
                "La expresión relativa fue detectada, "
                "pero no pudo resolverse."
            ),
            componentes=componentes,
            fecha_referencia=hoy.isoformat(),
        )

    if (
        resolucion_temporal.get(
            "tipo"
        )
        == "error"
    ):

        return _error(
            resolucion_temporal.get(
                "estado",
                "fecha_relativa_invalida",
            ),
            pregunta,
            resolucion_temporal.get(
                "razon",
                "Expresión temporal inválida.",
            ),
            componentes=componentes,
            fecha_referencia=hoy.isoformat(),
        )

    entidad = componentes[
        "entidad"
    ]

    campo = componentes[
        "campo"
    ]

    # --------------------------------------------------------
    # TRADUCCIÓN A QUERY005
    # --------------------------------------------------------

    if (
        resolucion_temporal[
            "tipo"
        ]
        == "exacta"
    ):

        fecha = resolucion_temporal[
            "fecha"
        ].isoformat()

        pregunta_absoluta = (
            f"listar {entidad} "
            f"cuya {campo} es {fecha}"
        )

        fecha_desde = None
        fecha_hasta = None

    else:

        fecha = None

        fecha_desde = (
            resolucion_temporal[
                "fecha_desde"
            ].isoformat()
        )

        fecha_hasta = (
            resolucion_temporal[
                "fecha_hasta"
            ].isoformat()
        )

        pregunta_absoluta = (
            f"listar {entidad} "
            f"cuya {campo} entre "
            f"{fecha_desde} y "
            f"{fecha_hasta}"
        )

    # --------------------------------------------------------
    # QUERY005 + HOST
    # --------------------------------------------------------

    resultado_query005 = (
        componer_fechas_absolutas(
            pregunta_absoluta,
            limite=limite,
        )
    )

    if (
        not isinstance(
            resultado_query005,
            dict,
        )
        or resultado_query005.get(
            "ok"
        )
        is not True
    ):

        return _error(
            "rechazado_por_query005",
            pregunta,
            (
                "QUERY006 resolvió la fecha relativa, "
                "pero QUERY005/HOST rechazó el plan "
                "absoluto resultante."
            ),
            componentes=componentes,
            fecha_referencia=hoy.isoformat(),
            resolucion_temporal=(
                resolucion_temporal
            ),
            pregunta_absoluta=(
                pregunta_absoluta
            ),
            resultado_query005=(
                resultado_query005
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
            "fecha_relativa_validada",

        "modo":
            "fechas_relativas",

        "pregunta":
            pregunta,

        "forma":
            componentes[
                "forma"
            ],

        "entidad":
            entidad,

        "campo_solicitado":
            campo,

        "campo_inferido":
            componentes[
                "campo_inferido"
            ],

        "expresion_relativa":
            resolucion_temporal.get(
                "expresion"
            ),

        "fecha_referencia":
            hoy.isoformat(),

        "tipo_temporal":
            resolucion_temporal[
                "tipo"
            ],

        "fecha":
            fecha,

        "fecha_desde":
            fecha_desde,

        "fecha_hasta":
            fecha_hasta,

        "pregunta_absoluta":
            pregunta_absoluta,

        "modelo":
            resultado_query005.get(
                "modelo"
            ),

        "campo_resuelto":
            resultado_query005.get(
                "campo_resuelto"
            ),

        "tipo_campo":
            resultado_query005.get(
                "tipo_campo"
            ),

        "plan":
            resultado_query005.get(
                "plan"
            ),

        "resultado_query005":
            resultado_query005,

        "llm_invocado":
            False,

        "razon":
            (
                "QUERY006 convirtió la expresión relativa "
                "en una fecha absoluta y QUERY005/HOST "
                "certificaron el plan."
            ),
    }