from ia_local.config.cardinalidad import LIMITE_MUESTRA_PREDETERMINADO

import re
import unicodedata
from typing import Any

from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)
from ia_local.services.semantica.resolvedor_ambiguedades import (
    resolver_expresion_semantica,
)


VERSION = "IA-QUERY004-v1"


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


def _normalizar(
    texto: str,
) -> str:
    """
    Normalización usada exclusivamente para reconocer
    vocabulario estructural.

    No modifica la expresión que posteriormente recibe SEM.
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
            "ordenamiento_natural",

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
# DIRECCIÓN
# ============================================================


DIRECCIONES_ASC = {
    "asc",
    "ascendente",
    "creciente",
}

DIRECCIONES_DESC = {
    "desc",
    "descendente",
    "decreciente",
}


def _resolver_direccion(
    expresion: str | None,
) -> str | None:

    if expresion is None:
        return "asc"

    normalizada = _normalizar(
        expresion
    )

    if normalizada in DIRECCIONES_ASC:
        return "asc"

    if normalizada in DIRECCIONES_DESC:
        return "desc"

    return None


# ============================================================
# DETECCIÓN DE EXPRESIONES TEMPORALES IMPLÍCITAS
# ============================================================


def _es_orden_temporal_implicito(
    pregunta: str,
) -> bool:

    normalizada = _normalizar(
        pregunta
    )

    patrones = (
        r"\bmas recientes primero\b",
        r"\bmas reciente primero\b",
        r"\bmas antiguos primero\b",
        r"\bmas antiguo primero\b",
        r"\bmas nuevas primero\b",
        r"\bmas nuevos primero\b",
        r"\bmas viejas primero\b",
        r"\bmas viejos primero\b",
    )

    return any(
        re.search(
            patron,
            normalizada,
        )
        for patron
        in patrones
    )


# ============================================================
# PARSER
# ============================================================


def _extraer_componentes(
    pregunta: str,
) -> dict[str, Any] | None:
    """
    Extrae:

        entidad
        campo
        direccion

    Formas soportadas inicialmente:

        listar documentos ordenados por fecha
        listar documentos ordenados por fecha descendente
        listar documentos ordenados por codigo ascendente
        listar documentos por codigo descendente

    La segunda forma exige dirección explícita para evitar
    interpretar cualquier "por ..." como ordenamiento.
    """

    # --------------------------------------------------------
    # FORMA EXPLÍCITA:
    #
    # listar documentos ordenados por fecha descendente
    # --------------------------------------------------------

    patron_explicito = re.compile(
        r"""
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
            ordenad[oa]s?
            \s+por
            |
            ordenar
            \s+por
        )
        \s+
        (?P<campo>.+?)
        (?:
            \s+
            (?P<direccion>
                ascendente
                | descendente
                | asc
                | desc
                | creciente
                | decreciente
            )
        )?
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

    if coincidencia is not None:

        return {
            "operacion":
                "listar",

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

            "direccion_texto":
                (
                    _texto(
                        coincidencia.group(
                            "direccion"
                        )
                    )
                    or None
                ),

            "forma":
                "orden_explicito",
        }

    # --------------------------------------------------------
    # FORMA CORTA:
    #
    # listar documentos por codigo descendente
    #
    # Aquí la dirección es obligatoria.
    # --------------------------------------------------------

    patron_corto = re.compile(
        r"""
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
        por
        \s+
        (?P<campo>.+?)
        \s+
        (?P<direccion>
            ascendente
            | descendente
            | asc
            | desc
            | creciente
            | decreciente
        )
        \s*$
        """,
        flags=(
            re.IGNORECASE
            | re.VERBOSE
        ),
    )

    coincidencia = patron_corto.match(
        pregunta
    )

    if coincidencia is not None:

        return {
            "operacion":
                "listar",

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

            "direccion_texto":
                _texto(
                    coincidencia.group(
                        "direccion"
                    )
                ),

            "forma":
                "orden_corto",
        }

    return None


# ============================================================
# EXTRACCIÓN SEGURA DE RESULTADOS SEM
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
# API PÚBLICA QUERY004
# ============================================================


def componer_ordenamiento_natural(
    pregunta: str,
    *,
    limite: int = LIMITE_MUESTRA_PREDETERMINADO,
) -> dict[str, Any]:
    """
    IA-QUERY004.

    Interpreta una petición de ordenamiento natural,
    resuelve entidad y campo mediante SEM006 y entrega
    la propuesta a HOST para certificación.

    No ejecuta ORM.
    No usa LLM.
    No construye order_by().
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
    # NO INFERIR CAMPOS TEMPORALES
    # --------------------------------------------------------

    if _es_orden_temporal_implicito(
        pregunta
    ):

        return _error(
            "campo_orden_no_explicito",
            pregunta,
            (
                "La consulta expresa orden temporal, pero no "
                "indica qué campo temporal debe utilizarse. "
                "QUERY004 no infiere automáticamente entre "
                "date, created_at, updated_at u otros campos."
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
            "orden_no_detectado",
            pregunta,
            (
                "No se encontró una expresión de ordenamiento "
                "segura y explícita."
            ),
        )

    entidad_texto = componentes[
        "entidad"
    ]

    campo_texto = componentes[
        "campo"
    ]

    direccion = _resolver_direccion(
        componentes.get(
            "direccion_texto"
        )
    )

    if direccion is None:

        return _error(
            "direccion_no_resuelta",
            pregunta,
            (
                "La dirección de ordenamiento no pudo "
                "normalizarse a asc o desc."
            ),
            componentes=componentes,
        )

    # --------------------------------------------------------
    # SEM006 - ENTIDAD
    # --------------------------------------------------------

    resolucion_entidad = (
        resolver_expresion_semantica(
            entidad_texto,
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
            campo_texto,
            modelo_contexto=modelo,
        )
    )

    campo = _extraer_campo_sem(
        resolucion_campo,
        modelo,
    )

    if campo is None:

        return _error(
            "campo_orden_no_resuelto",
            pregunta,
            (
                "SEM006 no resolvió de forma inequívoca "
                "el campo solicitado para ordenar."
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
    # PROPUESTA HOST
    # --------------------------------------------------------

    propuesta_host = {
        "modelo":
            modelo,

        "operacion":
            "listar",

        "filtros":
            [],

        "orden": [
            {
                "campo":
                    campo,

                "direccion":
                    direccion,
            }
        ],

        "limite":
            limite,

        "condiciones_no_resueltas":
            [],
    }

    # --------------------------------------------------------
    # HOST CERTIFICA
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
                "QUERY004 resolvió la intención de orden, "
                "pero HOST rechazó el plan propuesto."
            ),
            componentes=componentes,
            modelo=modelo,
            campo=campo,
            direccion=direccion,
            resolucion_entidad=(
                resolucion_entidad
            ),
            resolucion_campo=(
                resolucion_campo
            ),
            propuesta_host=(
                propuesta_host
            ),
            validacion_host=(
                validacion_host
            ),
        )

    plan = validacion_host.get(
        "plan"
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
            "plan_orden_validado",

        "modo":
            "ordenamiento_natural",

        "pregunta":
            pregunta,

        "forma":
            componentes.get(
                "forma"
            ),

        "modelo":
            modelo,

        "campo_solicitado":
            campo_texto,

        "campo_resuelto":
            campo,

        "direccion":
            direccion,

        "propuesta_host":
            propuesta_host,

        "validacion_host":
            validacion_host,

        "plan":
            plan,

        "resolucion_entidad":
            resolucion_entidad,

        "resolucion_campo":
            resolucion_campo,

        "llm_invocado":
            False,

        "razon":
            (
                "QUERY004 resolvió entidad, campo y dirección "
                "de ordenamiento; HOST certificó el plan sin "
                "ejecutar ORM."
            ),
    }
