from __future__ import annotations

import ast
from typing import Any

from .catalogo_datos import obtener_modelo_django
from .inspector_llamadas import construir_indice_simbolos


# ============================================================
# IA-HOST027-C01
# VALIDACIÓN ESTÁTICA DE COLECCIONES SERIALIZADAS
# ============================================================
#
# Corrección C01:
#   normaliza whitespace PERIFÉRICO de delimitadores que contienen
#   al menos un carácter no blanco.
#
# Ejemplo:
#       escritura: ", ".join(...)
#       lectura:    .split(",")
#       declarado:  ","
#
# Se consideran equivalentes porque el espacio es formato de salida
# alrededor del delimitador lógico ",".
#
# IMPORTANTE:
#   los delimitadores formados exclusivamente por whitespace
#   (por ejemplo "\n", "\t" o " ") NO se normalizan mediante strip(),
#   porque el whitespace es en ese caso el delimitador real.
#
# HOST027-C01:
#   - no ejecuta código del host;
#   - no ejecuta QuerySets;
#   - no toca BD;
#   - no usa LLM;
#   - usa AST;
#   - reutiliza el índice de símbolos de inspector_llamadas.py;
#   - no contiene nombres específicos de Condocdat.
#
# Para declarar contrato validado se exige:
#   1. al menos una evidencia de escritura;
#   2. al menos una evidencia de lectura;
#   3. ambas compatibles con el separador declarado por HOST026;
#   4. cero incompatibilidades detectadas.
#
# ============================================================


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _codigo(nodo: ast.AST) -> str:
    try:
        return ast.unparse(nodo)
    except Exception:
        return ""


def _nombre_llamada(nodo: ast.Call) -> str:
    return _codigo(nodo.func).strip()


def _nombre_simple_llamada(nodo: ast.Call) -> str:
    nombre = _nombre_llamada(nodo)
    if not nombre:
        return ""
    return nombre.split(".")[-1]


def _constante_texto(nodo: ast.AST | None) -> str | None:
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
        return nodo.value
    return None


def _normalizar_separador(separador: str) -> str:
    """
    Normalización conservadora del delimitador.

    Si contiene algún carácter no blanco:
        elimina sólo whitespace periférico.

    Si está formado exclusivamente por whitespace:
        lo conserva exactamente.

    Esto permite considerar equivalentes:
        ", "  y ","
        " ; " y ";"

    sin destruir delimitadores reales como:
        "\\n"
        "\\t"
        " "
    """
    if not isinstance(separador, str):
        return separador

    if separador == "":
        return separador

    if any(not caracter.isspace() for caracter in separador):
        return separador.strip()

    return separador


def _separadores_compatibles(
    detectado: str,
    esperado: str,
) -> bool:
    return (
        _normalizar_separador(detectado)
        == _normalizar_separador(esperado)
    )


def _separador_join(nodo: ast.AST) -> str | None:
    """
    Reconoce:
        ",".join(...)
        ", ".join(...)
    """
    if not isinstance(nodo, ast.Call):
        return None

    func = nodo.func

    if not isinstance(func, ast.Attribute):
        return None

    if func.attr != "join":
        return None

    return _constante_texto(func.value)


def _separador_split(nodo: ast.AST) -> str | None:
    """
    Reconoce:
        expresion.split(",")
    Exige separador explícito.
    """
    if not isinstance(nodo, ast.Call):
        return None

    func = nodo.func

    if not isinstance(func, ast.Attribute):
        return None

    if func.attr != "split":
        return None

    if not nodo.args:
        return None

    return _constante_texto(nodo.args[0])


def _expresion_menciona_campo(
    nodo: ast.AST,
    campo: str,
) -> bool:
    """
    Comprueba referencias AST reales al nombre del campo.

    Ejemplos válidos:
        correo.adjuntos_nombres
        obj.campo
    """
    for sub in ast.walk(nodo):

        if isinstance(sub, ast.Attribute):
            if sub.attr == campo:
                return True

        if isinstance(sub, ast.Name):
            if sub.id == campo:
                return True

    return False


def _target_es_campo(
    nodo: ast.AST,
    campo: str,
) -> bool:

    if isinstance(nodo, ast.Attribute):
        return nodo.attr == campo

    if isinstance(nodo, ast.Name):
        return nodo.id == campo

    return False


def _parsear_codigo_simbolo(
    codigo: str,
) -> ast.Module | None:

    if not codigo.strip():
        return None

    try:
        return ast.parse(codigo)
    except SyntaxError:
        return None


def _candidatos_helper(
    nombre_llamada: str,
    indice: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Resolución conservadora por nombre simple.

    Sólo se considera helper inequívoco si existe exactamente
    un símbolo con ese nombre en el índice.
    """
    nombre = _texto(nombre_llamada).split(".")[-1]

    if not nombre:
        return []

    candidatos = list(
        indice.get(
            "por_nombre",
            {},
        ).get(
            nombre,
            [],
        )
    )

    if len(candidatos) != 1:
        return []

    return candidatos


def _buscar_join_en_helper(
    simbolo_helper: dict[str, Any],
    separador_esperado: str,
) -> list[dict[str, Any]]:

    codigo = _texto(
        simbolo_helper.get(
            "codigo"
        )
    )

    arbol = _parsear_codigo_simbolo(
        codigo
    )

    if arbol is None:
        return []

    evidencias = []

    for nodo in ast.walk(arbol):

        if not isinstance(nodo, ast.Call):
            continue

        separador = _separador_join(
            nodo
        )

        if separador is None:
            continue

        evidencias.append(
            {
                "tipo":
                    "serializacion_join_helper",

                "simbolo":
                    simbolo_helper.get(
                        "qualname"
                    ),

                "archivo":
                    simbolo_helper.get(
                        "archivo"
                    ),

                "linea":
                    (
                        (
                            simbolo_helper.get(
                                "linea_inicio"
                            )
                            or 1
                        )
                        + (
                            getattr(
                                nodo,
                                "lineno",
                                1,
                            )
                            - 1
                        )
                    ),

                "separador_detectado":
                    separador,

                "separador_normalizado":
                    _normalizar_separador(
                        separador
                    ),

                "separador_esperado_normalizado":
                    _normalizar_separador(
                        separador_esperado
                    ),

                "separador_compatible":
                    _separadores_compatibles(
                        separador,
                        separador_esperado,
                    ),

                "codigo":
                    _codigo(
                        nodo
                    ),
            }
        )

    return evidencias


def _analizar_escrituras_simbolo(
    simbolo: dict[str, Any],
    *,
    campo: str,
    separador_esperado: str,
    indice: dict[str, Any],
) -> list[dict[str, Any]]:

    codigo = _texto(
        simbolo.get(
            "codigo"
        )
    )

    arbol = _parsear_codigo_simbolo(
        codigo
    )

    if arbol is None:
        return []

    resultado = []

    linea_base = (
        simbolo.get(
            "linea_inicio"
        )
        or 1
    )

    def agregar_evidencia(
        *,
        nodo: ast.AST,
        valor: ast.AST,
        tipo_contexto: str,
    ) -> None:

        separador_directo = (
            _separador_join(
                valor
            )
        )

        if separador_directo is not None:

            resultado.append(
                {
                    "tipo":
                        "serializacion_join_directa",

                    "contexto":
                        tipo_contexto,

                    "simbolo":
                        simbolo.get(
                            "qualname"
                        ),

                    "archivo":
                        simbolo.get(
                            "archivo"
                        ),

                    "linea":
                        linea_base
                        + (
                            getattr(
                                nodo,
                                "lineno",
                                1,
                            )
                            - 1
                        ),

                    "campo":
                        campo,

                    "separador_detectado":
                        separador_directo,

                    "separador_normalizado":
                        _normalizar_separador(
                            separador_directo
                        ),

                    "separador_esperado_normalizado":
                        _normalizar_separador(
                            separador_esperado
                        ),

                    "separador_compatible":
                        _separadores_compatibles(
                            separador_directo,
                            separador_esperado,
                        ),

                    "codigo":
                        _codigo(
                            valor
                        ),
                }
            )

            return

        if not isinstance(
            valor,
            ast.Call,
        ):
            return

        helper_nombre = (
            _nombre_simple_llamada(
                valor
            )
        )

        if not helper_nombre:
            return

        helpers = _candidatos_helper(
            helper_nombre,
            indice,
        )

        if len(helpers) != 1:
            return

        evidencias_helper = (
            _buscar_join_en_helper(
                helpers[0],
                separador_esperado,
            )
        )

        for evidencia in evidencias_helper:

            resultado.append(
                {
                    "tipo":
                        "serializacion_via_helper",

                    "contexto":
                        tipo_contexto,

                    "simbolo":
                        simbolo.get(
                            "qualname"
                        ),

                    "archivo":
                        simbolo.get(
                            "archivo"
                        ),

                    "linea":
                        linea_base
                        + (
                            getattr(
                                nodo,
                                "lineno",
                                1,
                            )
                            - 1
                        ),

                    "campo":
                        campo,

                    "helper":
                        helpers[0].get(
                            "qualname"
                        ),

                    "separador_detectado":
                        evidencia.get(
                            "separador_detectado"
                        ),

                    "separador_normalizado":
                        evidencia.get(
                            "separador_normalizado"
                        ),

                    "separador_esperado_normalizado":
                        evidencia.get(
                            "separador_esperado_normalizado"
                        ),

                    "separador_compatible":
                        evidencia.get(
                            "separador_compatible",
                            False,
                        ),

                    "codigo":
                        _codigo(
                            valor
                        ),

                    "evidencia_helper":
                        evidencia,
                }
            )

    for nodo in ast.walk(arbol):

        # ----------------------------------------------
        # keyword:
        #   Modelo(campo=...)
        #   objects.create(campo=...)
        #   objects.update(campo=...)
        # ----------------------------------------------

        if isinstance(
            nodo,
            ast.Call,
        ):

            for keyword in nodo.keywords:

                if (
                    keyword.arg
                    == campo
                ):
                    agregar_evidencia(
                        nodo=nodo,
                        valor=keyword.value,
                        tipo_contexto="keyword",
                    )

        # ----------------------------------------------
        # asignación:
        #   obj.campo = ...
        # ----------------------------------------------

        if isinstance(
            nodo,
            ast.Assign,
        ):

            if any(
                _target_es_campo(
                    target,
                    campo,
                )
                for target
                in nodo.targets
            ):
                agregar_evidencia(
                    nodo=nodo,
                    valor=nodo.value,
                    tipo_contexto="assign",
                )

        if isinstance(
            nodo,
            ast.AnnAssign,
        ):

            if (
                nodo.value is not None
                and _target_es_campo(
                    nodo.target,
                    campo,
                )
            ):
                agregar_evidencia(
                    nodo=nodo,
                    valor=nodo.value,
                    tipo_contexto="annassign",
                )

    return resultado


def _analizar_lecturas_simbolo(
    simbolo: dict[str, Any],
    *,
    campo: str,
    separador_esperado: str,
) -> list[dict[str, Any]]:

    codigo = _texto(
        simbolo.get(
            "codigo"
        )
    )

    arbol = _parsear_codigo_simbolo(
        codigo
    )

    if arbol is None:
        return []

    resultado = []

    linea_base = (
        simbolo.get(
            "linea_inicio"
        )
        or 1
    )

    for nodo in ast.walk(arbol):

        if not isinstance(
            nodo,
            ast.Call,
        ):
            continue

        separador = _separador_split(
            nodo
        )

        if separador is None:
            continue

        func = nodo.func

        if not isinstance(
            func,
            ast.Attribute,
        ):
            continue

        receptor = func.value

        if not _expresion_menciona_campo(
            receptor,
            campo,
        ):
            continue

        resultado.append(
            {
                "tipo":
                    "deserializacion_split",

                "simbolo":
                    simbolo.get(
                        "qualname"
                    ),

                "archivo":
                    simbolo.get(
                        "archivo"
                    ),

                "linea":
                    linea_base
                    + (
                        getattr(
                            nodo,
                            "lineno",
                            1,
                        )
                        - 1
                    ),

                "campo":
                    campo,

                "separador_detectado":
                    separador,

                "separador_normalizado":
                    _normalizar_separador(
                        separador
                    ),

                "separador_esperado_normalizado":
                    _normalizar_separador(
                        separador_esperado
                    ),

                "separador_compatible":
                    _separadores_compatibles(
                        separador,
                        separador_esperado,
                    ),

                "codigo":
                    _codigo(
                        nodo
                    ),
            }
        )

    return resultado


# ============================================================
# API PÚBLICA
# ============================================================

def validar_coleccion_serializada(
    *,
    modelo: str,
    representacion_host: dict[str, Any],
) -> dict[str, Any]:
    """
    Contrasta una colección serializada HOST026 contra código
    Python real del host.
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

            "validado":
                False,

            "modelo":
                modelo,

            "razon":
                "El modelo no pudo resolverse inequívocamente.",

            "llm_invocado":
                False,
        }

    if not isinstance(
        representacion_host,
        dict,
    ):
        return {
            "ok":
                False,

            "resuelto":
                False,

            "validado":
                False,

            "modelo":
                modelo_django._meta.label,

            "razon":
                "La representación HOST026 no tiene formato válido.",

            "llm_invocado":
                False,
        }

    tipo_representacion = _texto(
        representacion_host.get(
            "tipo_representacion"
        )
    )

    if (
        tipo_representacion
        != "coleccion_serializada"
    ):
        return {
            "ok":
                True,

            "resuelto":
                True,

            "validado":
                False,

            "aplica":
                False,

            "modelo":
                modelo_django._meta.label,

            "tipo_representacion":
                tipo_representacion
                or None,

            "razon":
                (
                    "HOST027 sólo valida representaciones "
                    "coleccion_serializada."
                ),

            "llm_invocado":
                False,
        }

    campo = _texto(
        representacion_host.get(
            "nombre"
        )
    )

    separador = representacion_host.get(
        "separador"
    )

    if (
        not campo
        or not isinstance(
            separador,
            str,
        )
        or separador == ""
    ):
        return {
            "ok":
                True,

            "resuelto":
                False,

            "validado":
                False,

            "aplica":
                True,

            "modelo":
                modelo_django._meta.label,

            "campo":
                campo
                or None,

            "razon":
                (
                    "HOST026 no entregó campo y separador "
                    "suficientes para validar el contrato."
                ),

            "llm_invocado":
                False,
        }

    try:
        modelo_django._meta.get_field(
            campo
        )
    except Exception:
        return {
            "ok":
                True,

            "resuelto":
                False,

            "validado":
                False,

            "aplica":
                True,

            "modelo":
                modelo_django._meta.label,

            "campo":
                campo,

            "razon":
                (
                    "El campo informado por HOST026 no existe "
                    "en Django._meta."
                ),

            "llm_invocado":
                False,
        }

    indice = construir_indice_simbolos()

    escrituras = []
    lecturas = []

    for simbolo in indice.get(
        "simbolos",
        [],
    ):

        escrituras.extend(
            _analizar_escrituras_simbolo(
                simbolo,
                campo=campo,
                separador_esperado=separador,
                indice=indice,
            )
        )

        lecturas.extend(
            _analizar_lecturas_simbolo(
                simbolo,
                campo=campo,
                separador_esperado=separador,
            )
        )

    escrituras_compatibles = [
        item
        for item in escrituras
        if bool(
            item.get(
                "separador_compatible"
            )
        )
    ]

    lecturas_compatibles = [
        item
        for item in lecturas
        if bool(
            item.get(
                "separador_compatible"
            )
        )
    ]

    escrituras_incompatibles = [
        item
        for item in escrituras
        if not bool(
            item.get(
                "separador_compatible"
            )
        )
    ]

    lecturas_incompatibles = [
        item
        for item in lecturas
        if not bool(
            item.get(
                "separador_compatible"
            )
        )
    ]

    existe_incompatibilidad = bool(
        escrituras_incompatibles
        or lecturas_incompatibles
    )

    validado = bool(
        escrituras_compatibles
        and lecturas_compatibles
        and not existe_incompatibilidad
    )

    if validado:
        razon = (
            "El código host contiene evidencia compatible "
            "de serialización y deserialización para el "
            "separador lógico declarado."
        )

    elif existe_incompatibilidad:
        razon = (
            "Se detectó evidencia de código con un separador "
            "lógicamente incompatible; el contrato no puede "
            "validarse."
        )

    elif not escrituras_compatibles:
        razon = (
            "No se encontró evidencia estática inequívoca "
            "de escritura compatible para el campo."
        )

    else:
        razon = (
            "No se encontró evidencia estática inequívoca "
            "de lectura compatible para el campo."
        )

    return {
        "ok":
            True,

        "resuelto":
            True,

        "aplica":
            True,

        "validado":
            validado,

        "modelo":
            modelo_django._meta.label,

        "campo":
            campo,

        "tipo_representacion":
            "coleccion_serializada",

        "separador":
            separador,

        "separador_normalizado":
            _normalizar_separador(
                separador
            ),

        "estrategia_conteo":
            (
                "elementos_no_vacios"
                if validado
                else None
            ),

        "evidencia_escritura":
            escrituras,

        "evidencia_lectura":
            lecturas,

        "total_escrituras_compatibles":
            len(
                escrituras_compatibles
            ),

        "total_lecturas_compatibles":
            len(
                lecturas_compatibles
            ),

        "total_incompatibilidades":
            len(
                escrituras_incompatibles
            )
            + len(
                lecturas_incompatibles
            ),

        "razon":
            razon,

        "origen":
            "ast_host",

        "llm_invocado":
            False,
    }
