from __future__ import annotations

import re
from typing import Any

from ia_local.services.bridge.campo_operador_valor import (
    componer_campo_operador_valor,
)


VERSION = "IA-QUERY003-v1"


# ============================================================
# IA-QUERY003
# AGRUPACION LOGICA EXPLICITA AND / OR
# ============================================================
#
# Responsabilidad:
#   - interpretar agrupaciones lógicas explícitas;
#   - respetar paréntesis y comillas;
#   - construir un árbol declarativo AND/OR;
#   - resolver cada condición atómica mediante BRIDGE003;
#   - aceptar únicamente hojas certificadas por HOST.
#
# NO:
#   - ejecuta ORM;
#   - importa Q;
#   - modifica HOST;
#   - modifica BRIDGE;
#   - modifica SEM;
#   - inventa precedencia AND/OR.
#
# Regla crítica:
#
#   A y B o C
#
# es ambiguo y se rechaza.
#
# Debe escribirse:
#
#   (A y B) o C
#
# o:
#
#   A y (B o C)
#
# ============================================================


OPERADORES_AND = {
    "y",
    "and",
    "ademas",
    "además",
}

OPERADORES_OR = {
    "o",
    "or",
}


class ErrorSintaxisLogica(Exception):
    def __init__(
        self,
        estado: str,
        razon: str,
    ):
        super().__init__(razon)
        self.estado = estado
        self.razon = razon


def _error(
    *,
    estado: str,
    pregunta: str,
    razon: str,
    **extra: Any,
) -> dict[str, Any]:
    salida: dict[str, Any] = {
        "ok": False,
        "version": VERSION,
        "ejecutado": False,
        "estado": estado,
        "pregunta": pregunta,
        "razon": razon,
        "llm_invocado": False,
    }

    salida.update(extra)

    return salida


def _extraer_plan_bridge003(
    resultado: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Sólo acepta planes realmente certificados por HOST.
    """

    if not isinstance(resultado, dict):
        return None

    validacion = resultado.get(
        "validacion_host"
    )

    if isinstance(validacion, dict):
        if (
            validacion.get("ok") is True
            and validacion.get(
                "plan_validado"
            ) is True
        ):
            plan = validacion.get("plan")

            if isinstance(plan, dict):
                return plan

    plan_host = resultado.get(
        "plan_host"
    )

    if (
        resultado.get("ok") is True
        and isinstance(plan_host, dict)
    ):
        return plan_host

    return None


def _separar_prefijo_expresion(
    pregunta: str,
) -> tuple[str, str] | None:
    """
    Separa el prefijo operación/entidad de la expresión lógica.

    Debe preservar como parte de la expresión cualquier inicio
    lógico previo al primer 'cuyo', por ejemplo:

        listar documentos (cuyo ...)
        listar documentos (o cuyo ...)
        listar documentos (y cuyo ...)

    El prefijo resultante debe quedar únicamente como:

        listar documentos
    """

    coincidencia = re.search(
        r"\b(cuyo|cuya|cuyos|cuyas)\b",
        pregunta,
        flags=re.IGNORECASE,
    )

    if coincidencia is None:
        return None

    indice_expresion = coincidencia.start()

    prefijo_previo = pregunta[
        :indice_expresion
    ]

    # Detectamos si inmediatamente antes del primer "cuyo"
    # existe el comienzo de una expresión lógica:
    #
    #   (
    #   (o
    #   (or
    #   (y
    #   (and
    #
    # En ese caso todo ese segmento pertenece a la expresión,
    # no al prefijo operación/entidad.
    coincidencia_inicio_logico = re.search(
        r"""
        (
            \(
            \s*
            (?:
                o
                | or
                | y
                | and
                | ademas
                | además
            )?
            \s*
        )
        $
        """,
        prefijo_previo,
        flags=re.IGNORECASE | re.VERBOSE,
    )

    if coincidencia_inicio_logico is not None:
        indice_expresion = (
            coincidencia_inicio_logico.start()
        )

    prefijo = pregunta[
        :indice_expresion
    ].strip()

    expresion = pregunta[
        indice_expresion:
    ].strip()

    if not prefijo or not expresion:
        return None

    return prefijo, expresion


def _normalizar_condicion(
    condicion: str,
) -> str:
    condicion = condicion.strip()

    if re.match(
        r"^(cuyo|cuya|cuyos|cuyas)\b",
        condicion,
        flags=re.IGNORECASE,
    ):
        return condicion

    return f"cuyo {condicion}"


def _validar_balance_general(
    texto: str,
) -> None:
    """
    Verifica:
      - paréntesis;
      - comillas simples/dobles;
      - escapes dentro de comillas.
    """

    profundidad = 0
    comilla: str | None = None
    escape = False

    for caracter in texto:
        if escape:
            escape = False
            continue

        if (
            caracter == "\\"
            and comilla is not None
        ):
            escape = True
            continue

        if comilla is not None:
            if caracter == comilla:
                comilla = None

            continue

        if caracter in {'"', "'"}:
            comilla = caracter
            continue

        if caracter == "(":
            profundidad += 1

        elif caracter == ")":
            profundidad -= 1

            if profundidad < 0:
                raise ErrorSintaxisLogica(
                    "parentesis_no_balanceados",
                    (
                        "Se encontró un paréntesis de cierre "
                        "sin apertura correspondiente."
                    ),
                )

    if comilla is not None:
        raise ErrorSintaxisLogica(
            "comillas_no_balanceadas",
            (
                "La consulta contiene una cadena entre "
                "comillas sin cierre."
            ),
        )

    if profundidad != 0:
        raise ErrorSintaxisLogica(
            "parentesis_no_balanceados",
            (
                "La consulta contiene paréntesis "
                "sin cierre."
            ),
        )


def _parentesis_externos_completos(
    texto: str,
) -> bool:
    """
    Determina si todo el texto está envuelto por
    un único par de paréntesis externos.

    Ejemplo:
        (A y B)       -> True
        (A) o (B)     -> False
    """

    texto = texto.strip()

    if (
        len(texto) < 2
        or texto[0] != "("
        or texto[-1] != ")"
    ):
        return False

    profundidad = 0
    comilla: str | None = None
    escape = False

    for indice, caracter in enumerate(
        texto
    ):
        if escape:
            escape = False
            continue

        if (
            caracter == "\\"
            and comilla is not None
        ):
            escape = True
            continue

        if comilla is not None:
            if caracter == comilla:
                comilla = None

            continue

        if caracter in {'"', "'"}:
            comilla = caracter
            continue

        if caracter == "(":
            profundidad += 1

        elif caracter == ")":
            profundidad -= 1

            if (
                profundidad == 0
                and indice != len(texto) - 1
            ):
                return False

    return profundidad == 0


def _quitar_parentesis_externos(
    texto: str,
) -> str:
    texto = texto.strip()

    while _parentesis_externos_completos(
        texto
    ):
        texto = texto[1:-1].strip()

    return texto


def _es_limite_palabra(
    texto: str,
    indice: int,
) -> bool:
    if indice < 0 or indice >= len(texto):
        return True

    caracter = texto[indice]

    return (
        caracter.isspace()
        or caracter in "()"
    )


def _operador_en_posicion(
    texto: str,
    indice: int,
) -> tuple[str, int] | None:
    """
    Reconoce únicamente operadores lógicos como palabras
    completas.

    Retorna:
        ("AND", largo)
        ("OR", largo)
    """

    resto = texto[indice:]

    candidatos = [
        ("además", "AND"),
        ("ademas", "AND"),
        ("and", "AND"),
        ("or", "OR"),
        ("y", "AND"),
        ("o", "OR"),
    ]

    resto_casefold = resto.casefold()

    for palabra, operador in candidatos:
        if not resto_casefold.startswith(
            palabra.casefold()
        ):
            continue

        fin = indice + len(palabra)

        inicio_valido = _es_limite_palabra(
            texto,
            indice - 1,
        )

        fin_valido = _es_limite_palabra(
            texto,
            fin,
        )

        if inicio_valido and fin_valido:
            return operador, len(palabra)

    return None


def _dividir_nivel_superior(
    texto: str,
) -> tuple[
    list[str],
    list[str],
]:
    """
    Divide operadores AND/OR únicamente cuando aparecen
    en profundidad 0 y fuera de comillas.

    No entra dentro de paréntesis.
    """

    partes: list[str] = []
    operadores: list[str] = []

    buffer: list[str] = []

    profundidad = 0
    comilla: str | None = None
    escape = False

    indice = 0

    while indice < len(texto):
        caracter = texto[indice]

        if escape:
            buffer.append(caracter)
            escape = False
            indice += 1
            continue

        if (
            caracter == "\\"
            and comilla is not None
        ):
            buffer.append(caracter)
            escape = True
            indice += 1
            continue

        if comilla is not None:
            buffer.append(caracter)

            if caracter == comilla:
                comilla = None

            indice += 1
            continue

        if caracter in {'"', "'"}:
            buffer.append(caracter)
            comilla = caracter
            indice += 1
            continue

        if caracter == "(":
            profundidad += 1
            buffer.append(caracter)
            indice += 1
            continue

        if caracter == ")":
            profundidad -= 1
            buffer.append(caracter)
            indice += 1
            continue

        if profundidad == 0:
            encontrado = _operador_en_posicion(
                texto,
                indice,
            )

            if encontrado is not None:
                operador, largo = encontrado

                parte = "".join(
                    buffer
                ).strip()

                if not parte:
                    raise ErrorSintaxisLogica(
                        "operador_logico_mal_formado",
                        (
                            "Se encontró un operador lógico "
                            "sin condición previa."
                        ),
                    )

                partes.append(parte)
                operadores.append(
                    operador
                )

                buffer = []

                indice += largo

                while (
                    indice < len(texto)
                    and texto[indice].isspace()
                ):
                    indice += 1

                continue

        buffer.append(caracter)
        indice += 1

    ultima = "".join(buffer).strip()

    if not ultima:
        if operadores:
            raise ErrorSintaxisLogica(
                "operador_logico_mal_formado",
                (
                    "La expresión termina con un operador "
                    "lógico sin condición posterior."
                ),
            )

        return [], []

    partes.append(ultima)

    return partes, operadores


def _construir_ast_sintactico(
    expresion: str,
) -> dict[str, Any]:
    """
    Construye AST sin resolver todavía campos ni valores.

    Regla:
      en un mismo nivel sólo puede existir AND o OR,
      nunca ambos.
    """

    expresion = _quitar_parentesis_externos(
        expresion
    )

    if not expresion:
        raise ErrorSintaxisLogica(
            "condicion_vacia",
            "Se encontró una condición vacía.",
        )

    partes, operadores = (
        _dividir_nivel_superior(
            expresion
        )
    )

    if not operadores:
        return {
            "tipo": "CONDICION",
            "texto": expresion.strip(),
        }

    tipos = set(operadores)

    if len(tipos) > 1:
        raise ErrorSintaxisLogica(
            "precedencia_ambigua",
            (
                "Se detectaron AND y OR en el mismo nivel "
                "sin agrupación explícita. Use paréntesis "
                "para indicar la precedencia deseada."
            ),
        )

    operador = operadores[0]

    hijos = [
        _construir_ast_sintactico(
            parte
        )
        for parte in partes
    ]

    return {
        "tipo": "GRUPO",
        "operador": operador,
        "hijos": hijos,
    }


def _resolver_ast(
    nodo: dict[str, Any],
    *,
    prefijo: str,
    limite: int,
    contexto: dict[str, Any],
) -> dict[str, Any]:
    """
    Convierte las hojas sintácticas en condiciones
    certificadas por BRIDGE003/HOST.
    """

    tipo = nodo.get("tipo")

    if tipo == "GRUPO":
        operador = nodo.get("operador")

        hijos_resueltos = []

        for hijo in nodo.get(
            "hijos",
            [],
        ):
            hijos_resueltos.append(
                _resolver_ast(
                    hijo,
                    prefijo=prefijo,
                    limite=limite,
                    contexto=contexto,
                )
            )

        return {
            "tipo": "GRUPO",
            "operador": operador,
            "hijos": hijos_resueltos,
        }

    if tipo != "CONDICION":
        raise ErrorSintaxisLogica(
            "nodo_logico_invalido",
            "Se encontró un nodo lógico desconocido.",
        )

    condicion_original = str(
        nodo.get("texto") or ""
    ).strip()

    condicion = _normalizar_condicion(
        condicion_original
    )

    pregunta_condicion = (
        f"{prefijo} {condicion}"
    ).strip()

    resultado_bridge = (
        componer_campo_operador_valor(
            pregunta_condicion,
            limite=limite,
        )
    )

    plan = _extraer_plan_bridge003(
        resultado_bridge
    )

    indice = contexto[
        "siguiente_indice"
    ]

    contexto[
        "siguiente_indice"
    ] += 1

    if plan is None:
        raise ErrorSintaxisLogica(
            "condicion_no_resuelta",
            (
                "BRIDGE003 no produjo un plan HOST "
                f"validado para la condición {indice}."
            ),
        )

    filtros = plan.get("filtros")

    if (
        not isinstance(filtros, list)
        or len(filtros) != 1
    ):
        raise ErrorSintaxisLogica(
            "condicion_atomica_invalida",
            (
                "Cada hoja de QUERY003 debe resolver "
                "exactamente un filtro HOST."
            ),
        )

    modelo = plan.get("modelo")
    operacion = plan.get("operacion")

    if contexto["modelo"] is None:
        contexto["modelo"] = modelo
        contexto["operacion"] = operacion

    else:
        if modelo != contexto["modelo"]:
            raise ErrorSintaxisLogica(
                "modelos_incompatibles",
                (
                    "Todas las condiciones del árbol "
                    "deben pertenecer al mismo modelo."
                ),
            )

        if operacion != contexto[
            "operacion"
        ]:
            raise ErrorSintaxisLogica(
                "operaciones_incompatibles",
                (
                    "Todas las condiciones del árbol "
                    "deben utilizar la misma operación."
                ),
            )

    filtro = dict(
        filtros[0]
    )

    resolucion = {
        "indice": indice,
        "condicion": condicion,
        "pregunta_condicion": (
            pregunta_condicion
        ),
        "modelo": modelo,
        "operacion": operacion,
        "filtro": filtro,
    }

    contexto[
        "resoluciones"
    ].append(
        resolucion
    )

    return {
        "tipo": "CONDICION",
        "indice": indice,
        "campo": filtro.get("campo"),
        "operador": filtro.get(
            "operador"
        ),
        "lookup": filtro.get(
            "lookup"
        ),
        "valor": filtro.get("valor"),
        "tipo_django": filtro.get(
            "tipo"
        ),
    }


def componer_grupos_logicos(
    pregunta: str,
    limite: int = 20,
) -> dict[str, Any]:
    """
    Punto público IA-QUERY003.
    """

    pregunta = str(
        pregunta or ""
    ).strip()

    if not pregunta:
        return _error(
            estado="pregunta_vacia",
            pregunta=pregunta,
            razon="La pregunta está vacía.",
        )

    separado = (
        _separar_prefijo_expresion(
            pregunta
        )
    )

    if separado is None:
        return _error(
            estado="prefijo_consulta_no_resuelto",
            pregunta=pregunta,
            razon=(
                "No fue posible separar la operación/entidad "
                "de la expresión lógica."
            ),
        )

    prefijo, expresion = separado

    try:
        _validar_balance_general(
            expresion
        )

        ast_sintactico = (
            _construir_ast_sintactico(
                expresion
            )
        )

    except ErrorSintaxisLogica as exc:
        return _error(
            estado=exc.estado,
            pregunta=pregunta,
            razon=exc.razon,
        )

    contexto: dict[str, Any] = {
        "modelo": None,
        "operacion": None,
        "siguiente_indice": 0,
        "resoluciones": [],
    }

    try:
        arbol = _resolver_ast(
            ast_sintactico,
            prefijo=prefijo,
            limite=limite,
            contexto=contexto,
        )

    except ErrorSintaxisLogica as exc:
        return _error(
            estado=exc.estado,
            pregunta=pregunta,
            razon=exc.razon,
            resoluciones=contexto[
                "resoluciones"
            ],
        )

    cantidad = contexto[
        "siguiente_indice"
    ]

    if cantidad < 2:
        return _error(
            estado="sin_agrupacion_logica",
            pregunta=pregunta,
            razon=(
                "QUERY003 requiere al menos dos "
                "condiciones lógicas."
            ),
            resoluciones=contexto[
                "resoluciones"
            ],
        )

    contrato = {
        "modelo": contexto["modelo"],
        "operacion": contexto[
            "operacion"
        ],
        "arbol_logico": arbol,
        "limite": limite,
    }

    return {
        "ok": True,
        "version": VERSION,
        "ejecutado": False,
        "estado": "arbol_logico_validado",
        "modo": "agrupacion_logica",
        "pregunta": pregunta,
        "cantidad_condiciones": cantidad,
        "contrato_logico": contrato,
        "resoluciones": contexto[
            "resoluciones"
        ],
        "llm_invocado": False,
        "razon": (
            "QUERY003 construyó un árbol lógico explícito "
            "y cada condición atómica fue certificada "
            "individualmente por HOST. El árbol no fue "
            "ejecutado."
        ),
    }