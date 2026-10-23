from unittest import TestCase

from ia_local.services.query.trazabilidad_not import (
    localizar_nodos_not,
)


class TestARC002C06Correspondencia(TestCase):

    def comprobar_intervalos(self, expresion, resultado):
        self.assertTrue(resultado["ok"])

        for nodo in resultado["nodos_not"]:
            self.assertEqual(
                expresion[nodo["inicio"]:nodo["fin"]],
                nodo["fragmento_original"],
            )
            self.assertFalse(nodo["asociacion_certificada"])

        self.assertFalse(resultado["ejecutable"])
        self.assertFalse(resultado["ejecutado"])

    def test_01_not_repetidos_identicos(self):
        expresion = "NOT (activo) y NOT (activo)"
        r = localizar_nodos_not(expresion)

        self.comprobar_intervalos(expresion, r)
        self.assertEqual(
            [n["ruta_ast"] for n in r["nodos_not"]],
            [[0], [1]],
        )
        self.assertNotEqual(
            r["nodos_not"][0]["inicio"],
            r["nodos_not"][1]["inicio"],
        )

    def test_02_not_anidado_con_literal(self):
        expresion = 'NOT ("NOT (cerrado)")'
        r = localizar_nodos_not(expresion)

        self.comprobar_intervalos(expresion, r)
        self.assertEqual(len(r["nodos_not"]), 1)
        self.assertEqual(
            r["nodos_not"][0]["ruta_ast"], []
        )

    def test_03_literal_con_parentesis(self):
        expresion = (
            'NOT ("texto con ) y NOT (interno)") '
            'o NOT (activo)'
        )
        r = localizar_nodos_not(expresion)

        self.comprobar_intervalos(expresion, r)
        self.assertEqual(len(r["nodos_not"]), 2)
        self.assertEqual(
            [n["ruta_ast"] for n in r["nodos_not"]],
            [[0], [1]],
        )

    def test_04_anidamiento_y_repeticion(self):
        expresion = (
            "NOT (NOT (activo)) "
            "y NOT (activo)"
        )
        r = localizar_nodos_not(expresion)

        self.comprobar_intervalos(expresion, r)
        self.assertEqual(len(r["nodos_not"]), 3)
        self.assertEqual(
            [n["ruta_ast"] for n in r["nodos_not"]],
            [[0], [0, 0], [1]],
        )
