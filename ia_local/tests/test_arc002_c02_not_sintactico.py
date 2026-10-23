from unittest import TestCase
from unittest.mock import patch

from ia_local.services.query import grupos_logicos


class TestARC002C02NOT(TestCase):

    def test_01_not_unario(self):
        arbol = grupos_logicos._construir_ast_sintactico(
            "NOT (cerrado)"
        )

        self.assertEqual(arbol["tipo"], "GRUPO")
        self.assertEqual(arbol["operador"], "NOT")
        self.assertEqual(len(arbol["hijos"]), 1)
        self.assertEqual(
            arbol["hijos"][0]["texto"],
            "cerrado",
        )

    def test_02_and_con_not(self):
        arbol = grupos_logicos._construir_ast_sintactico(
            "activo y NOT (cerrado)"
        )

        self.assertEqual(arbol["operador"], "AND")
        self.assertEqual(
            arbol["hijos"][1]["operador"],
            "NOT",
        )

    def test_03_not_anidado(self):
        arbol = grupos_logicos._construir_ast_sintactico(
            "NOT (NOT (cerrado))"
        )

        self.assertEqual(arbol["operador"], "NOT")
        self.assertEqual(
            arbol["hijos"][0]["operador"],
            "NOT",
        )

    def test_04_not_no_llega_a_bridge(self):
        arbol = grupos_logicos._construir_ast_sintactico(
            "NOT (cerrado)"
        )

        contexto = {
            "modelo": None,
            "operacion": None,
            "siguiente_indice": 0,
            "resoluciones": [],
        }

        with patch.object(
            grupos_logicos,
            "componer_campo_operador_valor",
        ) as bridge:
            with self.assertRaises(
                grupos_logicos.ErrorSintaxisLogica
            ) as capturado:
                grupos_logicos._resolver_ast(
                    arbol,
                    prefijo="listar RDI",
                    limite=10,
                    contexto=contexto,
                )

            bridge.assert_not_called()

        self.assertEqual(
            capturado.exception.estado,
            "operador_no_resuelto",
        )

    def test_05_and_or_historicos(self):
        arbol = grupos_logicos._construir_ast_sintactico(
            "(activo y vigente) o suspendido"
        )

        self.assertEqual(arbol["operador"], "OR")
        self.assertEqual(
            arbol["hijos"][0]["operador"],
            "AND",
        )
