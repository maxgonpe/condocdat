from unittest import TestCase
from unittest.mock import patch

from ia_local.services.query import grupos_logicos


class TestARC002C03NOTSeguridad(TestCase):

    def analizar(self, expresion):
        return grupos_logicos._construir_ast_sintactico(
            expresion
        )

    def test_01_not_sin_parentesis_rechazado(self):
        with self.assertRaises(
            grupos_logicos.ErrorSintaxisLogica
        ):
            self.analizar("NOT cerrado")

    def test_02_not_vacio_rechazado(self):
        with self.assertRaises(
            grupos_logicos.ErrorSintaxisLogica
        ):
            self.analizar("NOT ()")

    def test_03_not_parentesis_incompleto(self):
        with self.assertRaises(
            grupos_logicos.ErrorSintaxisLogica
        ):
            self.analizar("NOT (cerrado")

    def test_04_not_sobre_grupo_and(self):
        arbol = self.analizar(
            "NOT (activo y cerrado)"
        )

        self.assertEqual(arbol["operador"], "NOT")
        self.assertEqual(len(arbol["hijos"]), 1)
        self.assertEqual(
            arbol["hijos"][0]["operador"],
            "AND",
        )

    def test_05_and_con_not_incompleto(self):
        with self.assertRaises(
            grupos_logicos.ErrorSintaxisLogica
        ):
            self.analizar("activo y NOT cerrado")

    def test_06_no_enviar_not_incompleto_a_bridge(self):
        with patch.object(
            grupos_logicos,
            "componer_campo_operador_valor",
        ) as bridge:
            try:
                arbol = self.analizar(
                    "NOT cerrado"
                )

                contexto = {
                    "modelo": None,
                    "operacion": None,
                    "siguiente_indice": 0,
                    "resoluciones": [],
                }

                grupos_logicos._resolver_ast(
                    arbol,
                    prefijo="listar RDI",
                    limite=10,
                    contexto=contexto,
                )

            except grupos_logicos.ErrorSintaxisLogica:
                pass

            bridge.assert_not_called()

    def test_07_not_anidado_con_or(self):
        arbol = self.analizar(
            "activo y NOT (cerrado o suspendido)"
        )

        self.assertEqual(arbol["operador"], "AND")
        self.assertEqual(
            arbol["hijos"][1]["operador"],
            "NOT",
        )
        self.assertEqual(
            arbol["hijos"][1]["hijos"][0]["operador"],
            "OR",
        )
