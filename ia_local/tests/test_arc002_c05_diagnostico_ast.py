from unittest import TestCase
from unittest.mock import patch

from ia_local.services.query.diagnostico_ast import (
    diagnosticar_ast_logico,
)


class TestARC002C05DiagnosticoAST(TestCase):

    def test_01_and_not_or(self):
        resultado = diagnosticar_ast_logico(
            "activo y NOT (cerrado o suspendido)"
        )

        self.assertTrue(resultado["ok"])
        self.assertEqual(
            resultado["estado"],
            "ast_sintactico_diagnostico",
        )
        self.assertEqual(
            resultado["cantidad_condiciones"], 3
        )

        arbol = resultado["arbol_sintactico"]

        self.assertEqual(arbol["operador"], "AND")
        self.assertEqual(
            arbol["hijos"][1]["operador"], "NOT"
        )
        self.assertEqual(
            arbol["hijos"][1]["hijos"][0]["operador"],
            "OR",
        )
        self.assertFalse(resultado["ejecutable"])
        self.assertFalse(resultado["ejecutado"])

    def test_02_and_or_historico(self):
        resultado = diagnosticar_ast_logico(
            "(activo y vigente) o suspendido"
        )

        self.assertTrue(resultado["ok"])
        self.assertEqual(
            resultado["arbol_sintactico"]["operador"],
            "OR",
        )
        self.assertEqual(
            resultado["cantidad_condiciones"], 3
        )

    def test_03_not_simple(self):
        resultado = diagnosticar_ast_logico(
            "NOT (cerrado)"
        )

        self.assertTrue(resultado["ok"])
        self.assertEqual(
            resultado["arbol_sintactico"]["operador"],
            "NOT",
        )
        self.assertEqual(
            resultado["cantidad_condiciones"], 1
        )
        self.assertFalse(
            resultado["cobertura_verificada"]
        )

    def test_04_not_mal_formado(self):
        resultado = diagnosticar_ast_logico(
            "activo y NOT cerrado"
        )

        self.assertFalse(resultado["ok"])
        self.assertIsNone(
            resultado["arbol_sintactico"]
        )
        self.assertFalse(resultado["ejecutable"])

    def test_05_sin_llamadas_a_bridge(self):
        with patch(
            "ia_local.services.query.grupos_logicos."
            "componer_campo_operador_valor"
        ) as bridge:
            resultado = diagnosticar_ast_logico(
                "activo y NOT (cerrado)"
            )

        self.assertTrue(resultado["ok"])
        bridge.assert_not_called()
        self.assertFalse(resultado["llm_invocado"])

    def test_06_profundidad_excesiva(self):
        expresion = "activo"

        for _ in range(66):
            expresion = f"NOT ({expresion})"

        resultado = diagnosticar_ast_logico(
            expresion
        )

        self.assertFalse(resultado["ok"])
        self.assertFalse(resultado["ejecutable"])
        self.assertFalse(resultado["ejecutado"])
