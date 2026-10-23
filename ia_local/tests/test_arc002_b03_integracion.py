from unittest import TestCase
from unittest.mock import patch

from ia_local.services.llm.cobertura_semantica import (
    evaluar_cobertura_semantica,
)


class TestARC002B03Integracion(TestCase):

    def evaluar(self, pregunta):
        return evaluar_cobertura_semantica(
            pregunta,
            {
                "ok": True,
                "pregunta": pregunta,
                "operacion": "contar",
                "restricciones": [],
                "requiere_revision": True,
            },
        )

    def test_01_posiciones_originales(self):
        pregunta = "¿Hay alguna RDI que no esté cerrada?"
        resultado = self.evaluar(pregunta)

        evidencias = resultado["evidencias_negacion"]
        self.assertEqual(len(evidencias), 1)

        evidencia = evidencias[0]
        self.assertEqual(
            pregunta[evidencia["inicio"]:evidencia["fin"]],
            "no",
        )
        self.assertIsNone(evidencia["alcance_semantico"])
        self.assertFalse(evidencia["certificada"])

    def test_02_varias_negaciones(self):
        resultado = self.evaluar(
            "Equipos sin mantenimiento y no entregados"
        )

        self.assertEqual(
            [
                e["marcador_textual"]
                for e in resultado["evidencias_negacion"]
            ],
            ["sin", "no"],
        )
        self.assertIn(
            "alcance_negacion_no_certificado",
            resultado["componentes_pendientes"],
        )

    def test_03_consulta_sin_negaciones(self):
        resultado = self.evaluar(
            "¿Cuántas RDI están abiertas?"
        )

        self.assertEqual(resultado["evidencias_negacion"], [])
        self.assertFalse(resultado["cobertura_verificada"])
        self.assertFalse(resultado["ejecutable"])

    def test_04_fallo_del_localizador(self):
        with patch(
            "ia_local.services.llm.evidencia_negacion."
            "localizar_evidencias_negacion",
            side_effect=RuntimeError("Fallo simulado"),
        ):
            resultado = self.evaluar(
                "¿Hay alguna RDI que no esté cerrada?"
            )

        self.assertIn(
            "evidencia_negacion_no_disponible",
            resultado["componentes_pendientes"],
        )
        self.assertEqual(resultado["evidencias_negacion"], [])
        self.assertFalse(resultado["ejecutable"])

    def test_05_preserva_contrato_historico(self):
        resultado = self.evaluar(
            "Facturas sin pagos"
        )

        self.assertIn(
            "posible_negacion",
            resultado["senales_detectadas"],
        )
        self.assertIn(
            "negacion_no_certificada",
            resultado["componentes_pendientes"],
        )
        self.assertIn(
            "certificacion_integral_no_disponible",
            resultado["componentes_pendientes"],
        )
        self.assertFalse(resultado["ejecutado"])
