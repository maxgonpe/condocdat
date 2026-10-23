"""
ARC002-C05 — Diagnóstico sintáctico de expresiones lógicas.

Reutiliza el parser QUERY003.
No resuelve campos ni invoca BRIDGE, HOST, Qwen o FINAL.
No certifica ni ejecuta consultas.
"""

from copy import deepcopy

from ia_local.services.query.grupos_logicos import (
    ErrorSintaxisLogica,
    _construir_ast_sintactico,
    _validar_balance_general,
)

VERSION = "IA-ARC002-C05-v1"
MAX_PROFUNDIDAD = 64
MAX_NODOS = 128


def diagnosticar_ast_logico(expresion):
    base = {
        "ok": False,
        "version": VERSION,
        "estado": "expresion_invalida",
        "expresion_original": None,
        "arbol_sintactico": None,
        "operadores_detectados": [],
        "cantidad_condiciones": 0,
        "pendientes": ["certificacion_semantica_integral"],
        "cobertura_verificada": False,
        "integridad_completa": False,
        "ejecutable": False,
        "ejecutado": False,
        "llm_invocado": False,
    }

    if (
        not isinstance(expresion, str)
        or not expresion.strip()
        or len(expresion) > 1000
    ):
        return base

    texto = expresion.strip()

    try:
        _validar_balance_general(texto)
        arbol = _construir_ast_sintactico(texto)

        operadores = []
        cantidad_condiciones = 0
        total_nodos = 0

        def revisar(nodo, profundidad=0):
            nonlocal cantidad_condiciones, total_nodos

            total_nodos += 1

            if (
                profundidad > MAX_PROFUNDIDAD
                or total_nodos > MAX_NODOS
                or not isinstance(nodo, dict)
            ):
                raise ValueError("estructura_excesiva_o_invalida")

            tipo = nodo.get("tipo")

            if tipo == "CONDICION":
                if (
                    not isinstance(nodo.get("texto"), str)
                    or not nodo["texto"].strip()
                ):
                    raise ValueError("condicion_invalida")

                cantidad_condiciones += 1
                return

            if tipo != "GRUPO":
                raise ValueError("nodo_desconocido")

            operador = nodo.get("operador")
            hijos = nodo.get("hijos")

            if not isinstance(hijos, list):
                raise ValueError("hijos_invalidos")

            if operador == "NOT":
                if len(hijos) != 1:
                    raise ValueError("not_aridad_invalida")
            elif operador in ("AND", "OR"):
                if len(hijos) < 2:
                    raise ValueError("grupo_aridad_invalida")
            else:
                raise ValueError("operador_desconocido")

            operadores.append(operador)

            for hijo in hijos:
                revisar(hijo, profundidad + 1)

        revisar(arbol)

    except ErrorSintaxisLogica as exc:
        return {
            **base,
            "estado": exc.estado,
            "expresion_original": texto,
        }

    except (ValueError, RecursionError, TypeError):
        return {
            **base,
            "estado": "estructura_sintactica_invalida",
            "expresion_original": texto,
        }

    return {
        **base,
        "ok": True,
        "estado": "ast_sintactico_diagnostico",
        "expresion_original": texto,
        "arbol_sintactico": deepcopy(arbol),
        "operadores_detectados": operadores,
        "cantidad_condiciones": cantidad_condiciones,
        "pendientes": [
            "correspondencia_con_pregunta_original_pendiente",
            "asociacion_evidencias_pendiente",
            "resolucion_host_pendiente",
            "certificacion_semantica_integral",
        ],
    }
