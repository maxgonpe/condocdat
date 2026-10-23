from unittest import TestCase

from ia_local.services.llm.cobertura_semantica import (
    evaluar_cobertura_semantica,
)


class TestARC002B03Negacion(TestCase):

    def evaluar(self, pregunta, restricciones=None):
        return evaluar_cobertura_semantica(
            pregunta,
            {
                "ok": True,
                "pregunta": pregunta,
                "operacion": "contar",
                "restricciones": (
                    restricciones
                    if restricciones is not None
                    else []
                ),
                "requiere_revision": True,
            },
        )

    def test_01_negacion_estado_no_cerrada(self):
        resultado = self.evaluar(
            "¿Hay alguna RDI de civil que no esté cerrada?"
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
            "alcance_negacion_no_certificado",
            resultado["componentes_pendientes"],
        )
        self.assertFalse(resultado["cobertura_verificada"])
        self.assertFalse(resultado["ejecutable"])

    def test_02_negacion_relacional(self):
        resultado = self.evaluar(
            "Muéstrame los equipos sin mantenimiento"
        )

        self.assertIn(
            "posible_negacion",
            resultado["senales_detectadas"],
        )

    def test_03_filtro_no_certifica_negacion(self):
        resultado = self.evaluar(
            "¿Hay alguna RDI que no esté cerrada?",
            [
                {
                    "tipo": "filtro",
                    "evidencia_textual": "cerrada",
                }
            ],
        )

        self.assertIn(
            "negacion_no_certificada",
            resultado["componentes_pendientes"],
        )
        self.assertFalse(resultado["ejecutable"])

    def test_04_pregunta_positiva_sin_senal_negativa(self):
        resultado = self.evaluar(
            "¿Cuántas RDI de civil están abiertas?"
        )

        self.assertNotIn(
            "posible_negacion",
            resultado["senales_detectadas"],
        )

    def test_05_no_confunde_palabras_con_negacion(self):
        resultado = self.evaluar(
            "¿Cuántos documentos del notario hay?"
        )

        self.assertNotIn(
            "posible_negacion",
            resultado["senales_detectadas"],
        )
