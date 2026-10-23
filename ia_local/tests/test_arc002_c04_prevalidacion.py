from unittest import TestCase
from unittest.mock import patch

from ia_local.services.query import grupos_logicos


class TestARC002C04Prevalidacion(TestCase):

    def test_01_not_posterior_no_invoca_bridge(self):
        expresion = "activo y NOT (cerrado)"

        ast_logico = (
            grupos_logicos._construir_ast_sintactico(
                expresion
            )
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
            ):
                grupos_logicos._resolver_ast(
                    ast_logico,
                    prefijo="listar RDI",
                    limite=10,
                    contexto=contexto,
                )

            bridge.assert_not_called()
            self.assertEqual(
                contexto["resoluciones"], []
            )
            self.assertEqual(
                contexto["siguiente_indice"], 0
            )
