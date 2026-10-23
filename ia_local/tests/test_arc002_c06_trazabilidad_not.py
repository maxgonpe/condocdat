from unittest import TestCase
from unittest.mock import patch

from ia_local.services.query.trazabilidad_not import (
    localizar_nodos_not,
)


class TestARC002C06TrazabilidadNOT(TestCase):

    def test_01_not_sobre_or(self):
        texto = "activo y NOT (cerrado o suspendido)"
        r = localizar_nodos_not(texto)

        self.assertTrue(r["ok"])
        self.assertEqual(len(r["nodos_not"]), 1)

        nodo = r["nodos_not"][0]

        self.assertEqual(nodo["ruta_ast"], [1])
        self.assertEqual(
            nodo["fragmento_original"],
            "NOT (cerrado o suspendido)",
        )
        self.assertEqual(
            nodo["arbol_afectado"]["operador"],
            "OR",
        )
        self.assertEqual(
            texto[nodo["inicio"]:nodo["fin"]],
            nodo["fragmento_original"],
        )

    def test_02_dos_not_independientes(self):
        r = localizar_nodos_not(
            "NOT (activo) y NOT (cerrado)"
        )

        self.assertTrue(r["ok"])
        self.assertEqual(
            [n["ruta_ast"] for n in r["nodos_not"]],
            [[0], [1]],
        )

    def test_03_not_anidados(self):
        r = localizar_nodos_not(
            "NOT (NOT (cerrado))"
        )

        self.assertTrue(r["ok"])
        self.assertEqual(
            [n["ruta_ast"] for n in r["nodos_not"]],
            [[], [0]],
        )
        self.assertEqual(
            r["nodos_not"][0]["fragmento_original"],
            "NOT (NOT (cerrado))",
        )
        self.assertEqual(
            r["nodos_not"][1]["fragmento_original"],
            "NOT (cerrado)",
        )

    def test_04_not_profundo(self):
        r = localizar_nodos_not(
            "activo y (vigente o NOT (suspendido))"
        )

        self.assertTrue(r["ok"])
        self.assertEqual(
            r["nodos_not"][0]["ruta_ast"],
            [1, 1],
        )

    def test_05_not_sobre_and(self):
        r = localizar_nodos_not(
            "NOT (activo y cerrado)"
        )

        self.assertTrue(r["ok"])
        self.assertEqual(
            r["nodos_not"][0]["arbol_afectado"]["operador"],
            "AND",
        )

    def test_06_not_incompleto(self):
        r = localizar_nodos_not(
            "activo y NOT cerrado"
        )

        self.assertFalse(r["ok"])
        self.assertEqual(r["nodos_not"], [])

    def test_07_no_invoca_bridge(self):
        with patch(
            "ia_local.services.query.grupos_logicos."
            "componer_campo_operador_valor"
        ) as bridge:
            r = localizar_nodos_not(
                "activo y NOT (cerrado)"
            )

        self.assertTrue(r["ok"])
        bridge.assert_not_called()
        self.assertFalse(r["ejecutable"])
        self.assertFalse(r["ejecutado"])
        self.assertFalse(r["asociacion_certificada"])
