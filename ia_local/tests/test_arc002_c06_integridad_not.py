from unittest import TestCase
from unittest.mock import patch

from ia_local.services.query.trazabilidad_not import (
    localizar_nodos_not,
)


class TestARC002C06IntegridadNOT(TestCase):

    def test_01_not_dentro_de_comillas_no_es_operador(self):
        resultado = localizar_nodos_not(
            '"NOT (cerrado)"'
        )

        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["nodos_not"], [])
        self.assertFalse(resultado["ejecutable"])

    def test_02_not_literal_y_not_real(self):
        expresion = '"NOT (cerrado)" y NOT (activo)'
        resultado = localizar_nodos_not(expresion)

        self.assertTrue(resultado["ok"])
        self.assertEqual(len(resultado["nodos_not"]), 1)

        nodo = resultado["nodos_not"][0]
        self.assertEqual(nodo["ruta_ast"], [1])
        self.assertEqual(
            nodo["fragmento_original"],
            "NOT (activo)",
        )
        self.assertEqual(
            expresion[nodo["inicio"]:nodo["fin"]],
            nodo["fragmento_original"],
        )

    def test_03_not_como_parte_de_palabra(self):
        resultado = localizar_nodos_not(
            "notificacion y NOT (cerrado)"
        )

        self.assertTrue(resultado["ok"])
        self.assertEqual(len(resultado["nodos_not"]), 1)
        self.assertEqual(
            resultado["nodos_not"][0]["ruta_ast"],
            [1],
        )

    def test_04_sin_bridge_en_caso_adversarial(self):
        with patch(
            "ia_local.services.query.grupos_logicos."
            "componer_campo_operador_valor"
        ) as bridge:
            resultado = localizar_nodos_not(
                '"NOT (cerrado)" y NOT (activo)'
            )

        bridge.assert_not_called()
        self.assertFalse(resultado["ejecutable"])
        self.assertFalse(resultado["ejecutado"])
        self.assertFalse(resultado["asociacion_certificada"])
