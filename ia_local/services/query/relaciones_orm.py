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

from ia_local.services.host.resolvedor_ruta_datos import (
    validar_ruta_orm_relacional,
)


VERSION = "IA-QUERY007-v1"


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

    texto = _texto(texto).lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
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
        "ok": False,
        "version": VERSION,
        "ejecutado": False,
        "estado": estado,
        "modo": "relaciones_orm",
        "pregunta": pregunta,
        "razon": razon,
        "llm_invocado": False,
    }

    salida.update(extra)

    return salida


# ============================================================
# PARSER
# ============================================================


def _extraer_cadena_relacional(
    pregunta: str,
) -> dict[str, Any] | None:
    """
    Ejemplos:

    listar documentos de correos enviados

        destino = documentos
        origen = correos enviados

    listar proyectos de documentos de correos enviados

        cadena natural:
        proyectos <- documentos <- correos enviados

        origen:
        correos enviados

        objetivos secuenciales:
        documentos
        proyectos
    """

    pregunta = _texto(pregunta)

    patron = re.compile(
        r"""
        ^\s*
        (?P<operacion>
            listar
            |
            mostrar
            |
            obtener
            |
            muestrame
            |
            mu[eé]strame
        )
        \s+
        (?P<cadena>.+?)
        \s*$
        """,
        flags=(
            re.IGNORECASE
            | re.VERBOSE
        ),
    )

    coincidencia = patron.match(
        pregunta
    )

    if not coincidencia:
        return None

    cadena = _texto(
        coincidencia.group("cadena")
    )

    partes = [
        _texto(parte)
        for parte
        in re.split(
            r"\s+de\s+",
            cadena,
            flags=re.IGNORECASE,
        )
        if _texto(parte)
    ]

    if len(partes) < 2:
        return None

    # Natural:
    #
    # proyectos de documentos de correos enviados
    #
    # partes:
    # [
    #   proyectos,
    #   documentos,
    #   correos enviados
    # ]
    #
    # El último elemento es el modelo origen.
    # Los anteriores se recorren desde derecha a izquierda.

    origen = partes[-1]

    objetivos = list(
        reversed(
            partes[:-1]
        )
    )

    return {
        "operacion": "listar",
        "cadena": cadena,
        "origen": origen,
        "objetivos": objetivos,
    }


# ============================================================
# ENTIDAD ORIGEN
# ============================================================


def _resolver_entidad_origen(
    expresion: str,
) -> dict[str, Any]:

    resolucion = (
        resolver_expresion_semantica(
            expresion,
            incluir_reglas=False,
        )
    )

    if (
        not isinstance(
            resolucion,
            dict,
        )
        or resolucion.get("ok") is not True
        or resolucion.get("estado") != "resuelto"
    ):
        return {
            "ok": False,
            "resolucion": resolucion,
        }

    resultado = resolucion.get(
        "resultado"
    )

    if not isinstance(
        resultado,
        dict,
    ):
        return {
            "ok": False,
            "resolucion": resolucion,
        }

    if resultado.get(
        "tipo"
    ) != "entidad":
        return {
            "ok": False,
            "resolucion": resolucion,
        }

    modelo = _texto(
        resultado.get("modelo")
    )

    if not modelo:
        return {
            "ok": False,
            "resolucion": resolucion,
        }

    return {
        "ok": True,
        "modelo": modelo,
        "resolucion": resolucion,
    }


# ============================================================
# API PÚBLICA
# ============================================================


def componer_relacion_orm(
    pregunta: str,
) -> dict[str, Any]:
    """
    IA-QUERY007.

    Resuelve navegación relacional natural mediante:

    SEM
      -> modelo origen

    HOST023 / resolver_objetivo_datos
      -> relación de cada salto

    HOST / validar_ruta_orm_relacional
      -> certificación final de ruta ORM

    No ejecuta ORM.
    No invoca LLM.
    No inventa relaciones.
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

    componentes = (
        _extraer_cadena_relacional(
            pregunta
        )
    )

    if componentes is None:
        return _error(
            "estructura_relacional_no_detectada",
            pregunta,
            (
                "No se encontró una estructura relacional "
                "del tipo 'destino de origen'."
            ),
        )

    # --------------------------------------------------------
    # MODELO ORIGEN
    # --------------------------------------------------------

    origen_resuelto = (
        _resolver_entidad_origen(
            componentes["origen"]
        )
    )

    if origen_resuelto.get(
        "ok"
    ) is not True:

        return _error(
            "entidad_origen_no_resuelta",
            pregunta,
            (
                "La entidad origen no pudo resolverse "
                "de forma inequívoca."
            ),
            componentes=componentes,
            resolucion_origen=(
                origen_resuelto.get(
                    "resolucion"
                )
            ),
        )

    modelo_origen = (
        origen_resuelto[
            "modelo"
        ]
    )

    modelo_actual = modelo_origen

    segmentos_orm: list[str] = []
    saltos: list[dict[str, Any]] = []

    # --------------------------------------------------------
    # RESOLUCIÓN DE SALTOS
    # --------------------------------------------------------

    for indice, expresion_objetivo in enumerate(
        componentes["objetivos"],
        start=1,
    ):

        resolucion_objetivo = (
            resolver_objetivo_datos(
                expresion_objetivo,
                modelo=modelo_actual,
            )
        )

        if (
            not isinstance(
                resolucion_objetivo,
                dict,
            )
            or resolucion_objetivo.get(
                "ok"
            )
            is not True
            or resolucion_objetivo.get(
                "resuelto"
            )
            is not True
        ):

            return _error(
                "relacion_no_resuelta",
                pregunta,
                (
                    "Uno de los saltos relacionales "
                    "no pudo resolverse de forma segura."
                ),
                indice_salto=indice,
                expresion_objetivo=(
                    expresion_objetivo
                ),
                modelo_actual=modelo_actual,
                resolucion_objetivo=(
                    resolucion_objetivo
                ),
                saltos=saltos,
            )

        objetivo = (
            resolucion_objetivo.get(
                "objetivo"
            )
        )

        if not isinstance(
            objetivo,
            dict,
        ):

            return _error(
                "objetivo_relacional_invalido",
                pregunta,
                (
                    "HOST resolvió el objetivo pero no "
                    "entregó una descripción válida."
                ),
                indice_salto=indice,
                resolucion_objetivo=(
                    resolucion_objetivo
                ),
            )

        if objetivo.get(
            "relacion"
        ) is not True:

            return _error(
                "objetivo_no_es_relacion",
                pregunta,
                (
                    "La expresión fue resuelta como un "
                    "campo escalar y no como una relación."
                ),
                indice_salto=indice,
                expresion_objetivo=(
                    expresion_objetivo
                ),
                objetivo=objetivo,
            )

        ruta_segmento = _texto(
            objetivo.get(
                "ruta_orm"
            )
        )

        modelo_destino = _texto(
            objetivo.get(
                "modelo_relacionado"
            )
        )

        if (
            not ruta_segmento
            or not modelo_destino
        ):

            return _error(
                "relacion_incompleta",
                pregunta,
                (
                    "La relación resuelta no contiene "
                    "ruta ORM o modelo destino."
                ),
                indice_salto=indice,
                objetivo=objetivo,
            )

        # ----------------------------------------------------
        # CERTIFICACIÓN DEL SALTO INDIVIDUAL
        # ----------------------------------------------------

        validacion_salto = (
            validar_ruta_orm_relacional(
                modelo=modelo_actual,
                ruta_orm=ruta_segmento,
            )
        )

        if (
            not isinstance(
                validacion_salto,
                dict,
            )
            or validacion_salto.get(
                "ok"
            )
            is not True
            or validacion_salto.get(
                "valida"
            )
            is not True
        ):

            return _error(
                "salto_rechazado_por_host",
                pregunta,
                (
                    "HOST rechazó la relación propuesta "
                    "por el resolvedor de objetivos."
                ),
                indice_salto=indice,
                expresion_objetivo=(
                    expresion_objetivo
                ),
                modelo_actual=modelo_actual,
                ruta_segmento=(
                    ruta_segmento
                ),
                validacion_salto=(
                    validacion_salto
                ),
            )

        segmentos_orm.append(
            ruta_segmento
        )

        saltos.append(
            {
                "indice":
                    indice,

                "expresion":
                    expresion_objetivo,

                "modelo_origen":
                    modelo_actual,

                "ruta_orm":
                    ruta_segmento,

                "modelo_destino":
                    modelo_destino,

                "tipo_django":
                    objetivo.get(
                        "tipo_django"
                    ),

                "tipo_relacion":
                    objetivo.get(
                        "tipo_relacion"
                    ),

                "validacion_host":
                    validacion_salto,
            }
        )

        modelo_actual = (
            modelo_destino
        )

    # --------------------------------------------------------
    # RUTA COMPLETA
    # --------------------------------------------------------

    ruta_orm = "__".join(
        segmentos_orm
    )

    validacion_ruta = (
        validar_ruta_orm_relacional(
            modelo=modelo_origen,
            ruta_orm=ruta_orm,
        )
    )

    if (
        not isinstance(
            validacion_ruta,
            dict,
        )
        or validacion_ruta.get(
            "ok"
        )
        is not True
        or validacion_ruta.get(
            "valida"
        )
        is not True
    ):

        return _error(
            "ruta_relacional_rechazada",
            pregunta,
            (
                "Los saltos individuales fueron resueltos, "
                "pero HOST rechazó la ruta relacional completa."
            ),
            modelo_origen=modelo_origen,
            ruta_orm=ruta_orm,
            saltos=saltos,
            validacion_ruta=(
                validacion_ruta
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
            "ruta_relacional_validada",

        "modo":
            "relaciones_orm",

        "pregunta":
            pregunta,

        "operacion":
            componentes["operacion"],

        "origen_solicitado":
            componentes["origen"],

        "objetivos_solicitados":
            componentes["objetivos"],

        "modelo_origen":
            modelo_origen,

        "modelo_destino":
            validacion_ruta.get(
                "modelo_destino"
            ),

        "ruta_orm":
            validacion_ruta.get(
                "ruta_orm"
            ),

        "profundidad":
            validacion_ruta.get(
                "profundidad"
            ),

        "contiene_relacion_multiple":
            validacion_ruta.get(
                "contiene_relacion_multiple"
            ),

        "saltos":
            saltos,

        "validacion_ruta":
            validacion_ruta,

        "resolucion_origen":
            origen_resuelto[
                "resolucion"
            ],

        "llm_invocado":
            False,

        "razon":
            (
                "QUERY007 resolvió una cadena relacional "
                "natural y HOST certificó cada salto y "
                "la ruta ORM completa mediante Django._meta."
            ),
    }