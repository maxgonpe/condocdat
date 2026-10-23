from unittest import TestCase

from ia_local.services.llm.asociacion_evidencias import (
    asociar_evidencias_requisitos,
)
from ia_local.services.llm.evidencia_negacion import (
    localizar_evidencias_negacion,
)
from ia_local.services.llm.trazabilidad_compuesta import (
    preparar_coleccion_restricciones,
)


def coleccion(pregunta, fragmentos):
    return preparar_coleccion_restricciones({
        "ok": True,
        "estado": "consolidacion_diagnostica",
        "pregunta": pregunta,
        "restricciones": [
            {
                "tipo": "filtro",
                "evidencia_textual": fragmento,
            }
            for fragmento in fragmentos
        ],
        "ejecutable": False,
        "ejecutado": False,
    })


class TestARC002B03Asociacion(TestCase):

    def asociar(self, pregunta, fragmentos):
        return asociar_evidencias_requisitos(
            coleccion(pregunta, fragmentos),
            localizar_evidencias_negacion(pregunta),
        )

    def test_01_asociacion_textual_unica(self):
        resultado = self.asociar(
            "RDI que no esté cerrada",
            ["no esté cerrada"],
        )

        asociacion = resultado["asociaciones"][0]

        self.assertEqual(
            asociacion["estado"], "asociacion_textual"
        )
        self.assertEqual(
            len(asociacion["requisitos_candidatos"]), 1
        )
        self.assertFalse(asociacion["alcance_certificado"])
        self.assertFalse(resultado["ejecutable"])

    def test_02_evidencia_sin_asociacion(self):
        resultado = self.asociar(
            "RDI que no esté cerrada",
            ["RDI"],
        )

        self.assertEqual(
            resultado["asociaciones"][0]["estado"],
            "sin_asociacion",
        )

    def test_03_asociacion_ambigua(self):
        resultado = self.asociar(
            "RDI que no esté cerrada",
            ["no esté cerrada", "no esté"],
        )

        self.assertEqual(
            resultado["asociaciones"][0]["estado"],
            "asociacion_ambigua",
        )

    def test_04_preguntas_diferentes_rechazadas(self):
        pregunta = "RDI que no esté cerrada"

        resultado = asociar_evidencias_requisitos(
            coleccion(pregunta, ["no esté cerrada"]),
            localizar_evidencias_negacion(
                "Equipos sin mantenimiento"
            ),
        )

        self.assertFalse(resultado["ok"])
        self.assertFalse(resultado["ejecutable"])

    def test_05_no_certifica_negacion(self):
        resultado = self.asociar(
            "Equipos sin mantenimiento",
            ["sin mantenimiento"],
        )

        self.assertTrue(resultado["ok"])
        self.assertFalse(resultado["cobertura_verificada"])
        self.assertFalse(resultado["integridad_completa"])
        self.assertFalse(resultado["ejecutado"])
