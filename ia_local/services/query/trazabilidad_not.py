"""
ARC002-C06-B01: trazabilidad sintactica de NOT.

No invoca HOST, BRIDGE, Qwen ni ORM.
No certifica equivalencia semantica con lenguaje natural.
"""

import re

from ia_local.services.query.diagnostico_ast import (
    diagnosticar_ast_logico,
)
from ia_local.services.query.grupos_logicos import (
    _construir_ast_sintactico,
)


PATRON_NOT = re.compile(r"\bNOT\b", re.IGNORECASE)


def _nodos_not(arbol, ruta=()):
    resultado = []

    if arbol.get("tipo") != "GRUPO":
        return resultado

    if arbol.get("operador") == "NOT":
        resultado.append((list(ruta), arbol))

    for indice, hijo in enumerate(arbol.get("hijos", [])):
        resultado.extend(
            _nodos_not(hijo, ruta + (indice,))
        )

    return resultado


def _cerrar_parentesis(texto, apertura):
    nivel = 0
    comilla = None
    escape = False

    for posicion in range(apertura, len(texto)):
        caracter = texto[posicion]

        if comilla:
            if escape:
                escape = False
            elif caracter == "\\":
                escape = True
            elif caracter == comilla:
                comilla = None
            continue

        if caracter in ("'", '"'):
            comilla = caracter
        elif caracter == "(":
            nivel += 1
        elif caracter == ")":
            nivel -= 1
            if nivel == 0:
                return posicion

    return None


def _ocurrencias(texto):
    resultado = []
    comilla = None
    escape = False
    posicion = 0

    while posicion < len(texto):
        caracter = texto[posicion]

        if comilla is not None:
            if escape:
                escape = False
            elif caracter == "\\":
                escape = True
            elif caracter == comilla:
                comilla = None

            posicion += 1
            continue

        if caracter in ("'", '"'):
            comilla = caracter
            posicion += 1
            continue

        coincidencia = PATRON_NOT.match(texto, posicion)

        if coincidencia is None:
            posicion += 1
            continue

        inicio = coincidencia.start()
        apertura = coincidencia.end()

        while (
            apertura < len(texto)
            and texto[apertura].isspace()
        ):
            apertura += 1

        if (
            apertura >= len(texto)
            or texto[apertura] != "("
        ):
            raise ValueError("not_sin_parentesis")

        cierre = _cerrar_parentesis(texto, apertura)

        if cierre is None:
            raise ValueError("not_parentesis_incompleto")

        resultado.append({
            "inicio": inicio,
            "fin": cierre + 1,
            "inicio_contenido": apertura + 1,
            "fin_contenido": cierre,
        })

        # Avanzamos solamente sobre la palabra NOT.
        # El contenido interior puede tener otros NOT.
        posicion = coincidencia.end()

    if comilla is not None:
        raise ValueError("comillas_sin_cerrar")

    return resultado


def _verificar_jerarquia_not(asociaciones, texto, arbol=None):
    """
    Verifica que el anidamiento de intervalos NOT
    coincida con las rutas del AST.

    No certifica equivalencia semantica.
    """

    rutas = set()
    intervalos = set()

    def obtener_nodo(ruta):
        actual = arbol

        for indice in ruta:
            if (
                not isinstance(actual, dict)
                or actual.get("tipo") != "GRUPO"
                or not isinstance(indice, int)
                or isinstance(indice, bool)
                or indice < 0
            ):
                raise ValueError("ruta_ast_invalida")

            hijos = actual.get("hijos")

            if (
                not isinstance(hijos, list)
                or indice >= len(hijos)
            ):
                raise ValueError("ruta_ast_inexistente")

            actual = hijos[indice]

        if (
            not isinstance(actual, dict)
            or actual.get("tipo") != "GRUPO"
            or actual.get("operador") != "NOT"
            or not isinstance(actual.get("hijos"), list)
            or len(actual["hijos"]) != 1
        ):
            raise ValueError("ruta_no_apunta_a_not")

        return actual

    for asociacion in asociaciones:
        ruta = tuple(asociacion["ruta_ast"])
        inicio = asociacion["inicio"]
        fin = asociacion["fin"]

        if (
            ruta in rutas
            or (inicio, fin) in intervalos
            or not isinstance(inicio, int)
            or not isinstance(fin, int)
            or isinstance(inicio, bool)
            or isinstance(fin, bool)
            or inicio < 0
            or fin > len(texto)
            or inicio >= fin
            or texto[inicio:fin] != asociacion["fragmento_original"]
        ):
            raise ValueError("asociacion_not_invalida")

        if arbol is not None:
            nodo_real = obtener_nodo(ruta)

            if nodo_real["hijos"][0] != asociacion["arbol_afectado"]:
                raise ValueError("subarbol_not_no_coincide")

        rutas.add(ruta)
        intervalos.add((inicio, fin))

    for indice, actual in enumerate(asociaciones):
        ruta_actual = tuple(actual["ruta_ast"])
        inicio_actual = actual["inicio"]
        fin_actual = actual["fin"]

        for anterior in asociaciones[:indice]:
            ruta_anterior = tuple(anterior["ruta_ast"])
            inicio_anterior = anterior["inicio"]
            fin_anterior = anterior["fin"]

            # Un NOT anterior es ancestro de otro si su
            # ruta es prefijo estricto de la ruta posterior.
            ancestro = (
                len(ruta_anterior) < len(ruta_actual)
                and ruta_actual[:len(ruta_anterior)]
                == ruta_anterior
            )

            contenido = (
                inicio_anterior < inicio_actual
                and fin_actual < fin_anterior
            )

            if ancestro != contenido:
                raise ValueError(
                    "jerarquia_not_no_coincide"
                )

            if not ancestro:
                # Los NOT independientes no deben
                # compartir caracteres del texto.
                if (
                    inicio_actual < fin_anterior
                    and inicio_anterior < fin_actual
                ):
                    raise ValueError(
                        "intervalos_not_superpuestos"
                    )

    return True


def localizar_nodos_not(expresion):
    salida = {
        "ok": False,
        "estado": "trazabilidad_no_establecida",
        "expresion_original": expresion if isinstance(
            expresion, str
        ) else None,
        "nodos_not": [],
        "asociacion_certificada": False,
        "cobertura_verificada": False,
        "integridad_completa": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }

    diagnostico = diagnosticar_ast_logico(expresion)

    if not diagnostico["ok"]:
        return {
            **salida,
            "estado": "ast_diagnostico_invalido",
        }

    texto = diagnostico["expresion_original"]
    nodos = _nodos_not(diagnostico["arbol_sintactico"])

    try:
        ocurrencias = _ocurrencias(texto)

        if len(nodos) != len(ocurrencias):
            raise ValueError("cantidad_not_no_coincide")

        asociaciones = []

        for (ruta, nodo), ocurrencia in zip(
            nodos, ocurrencias
        ):
            contenido = texto[
                ocurrencia["inicio_contenido"]:
                ocurrencia["fin_contenido"]
            ].strip()

            if not contenido:
                raise ValueError("not_vacio")

            arbol_interior = _construir_ast_sintactico(
                contenido
            )

            if arbol_interior != nodo["hijos"][0]:
                raise ValueError("alcance_not_no_coincide")

            asociaciones.append({
                "ruta_ast": ruta,
                "operador": "NOT",
                "inicio": ocurrencia["inicio"],
                "fin": ocurrencia["fin"],
                "fragmento_original": texto[
                    ocurrencia["inicio"]:
                    ocurrencia["fin"]
                ],
                "arbol_afectado": nodo["hijos"][0],
                "asociacion_certificada": False,
            })

        _verificar_jerarquia_not(
            asociaciones,
            texto,
            diagnostico["arbol_sintactico"],
        )

    except (ValueError, TypeError, KeyError, IndexError):
        return salida

    return {
        **salida,
        "ok": True,
        "estado": "not_localizado_sintacticamente",
        "nodos_not": asociaciones,
    }
