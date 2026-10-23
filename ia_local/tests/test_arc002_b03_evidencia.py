from unittest import TestCase

from ia_local.services.llm.evidencia_negacion import (
    localizar_evidencias_negacion,
)


class TestARC002B03Evidencia(TestCase):

    def test_01_negacion_estado(self):
        pregunta = (
            "¿Hay alguna RDI de civil que no esté cerrada?"
        )

        resultado = localizar_evidencias_negacion(pregunta)

        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["cantidad"], 1)

        evidencia = resultado["evidencias"][0]

        self.assertEqual(evidencia["marcador_textual"], "no")
        self.assertIn(
            "esté cerrada",
            evidencia["fragmento_contextual"],
        )
        self.assertIsNone(evidencia["alcance_semantico"])
        self.assertFalse(evidencia["certificada"])

    def test_02_negacion_relacional(self):
        resultado = localizar_evidencias_negacion(
            "Equipos sin mantenimiento"
        )

        self.assertEqual(resultado["cantidad"], 1)
        self.assertEqual(
            resultado["evidencias"][0]["marcador_textual"],
            "sin",
        )

    def test_03_varias_negaciones(self):
        resultado = localizar_evidencias_negacion(
            "Trabajos sin factura y no entregados"
        )

        self.assertEqual(resultado["cantidad"], 2)

        marcadores = [
            e["marcador_textual"]
            for e in resultado["evidencias"]
        ]

        self.assertEqual(marcadores, ["sin", "no"])

    def test_04_posiciones_exactas(self):
        pregunta = "Facturas que no tienen pagos"

        resultado = localizar_evidencias_negacion(pregunta)

        evidencia = resultado["evidencias"][0]

        self.assertEqual(
            pregunta[evidencia["inicio"]:evidencia["fin"]],
            evidencia["marcador_textual"],
        )

    def test_05_sin_negacion(self):
        resultado = localizar_evidencias_negacion(
            "¿Cuántos documentos del notario hay?"
        )

        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["cantidad"], 0)
        self.assertFalse(resultado["cobertura_verificada"])
        self.assertFalse(resultado["ejecutable"])
