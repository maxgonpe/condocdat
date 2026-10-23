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


class TestARC002B03Unicode(TestCase):

    def comprobar(self, pregunta):
        coleccion = preparar_coleccion_restricciones({
            "ok": True,
            "estado": "consolidacion_diagnostica",
            "pregunta": pregunta,
            "restricciones": [{
                "tipo": "filtro",
                "evidencia_textual": "no cerrada",
            }],
            "ejecutable": False,
            "ejecutado": False,
        })

        resultado = asociar_evidencias_requisitos(
            coleccion,
            localizar_evidencias_negacion(pregunta),
        )

        self.assertTrue(resultado["ok"])
        self.assertEqual(
            resultado["asociaciones"][0]["estado"],
            "asociacion_textual",
        )
        self.assertFalse(resultado["ejecutable"])
        self.assertFalse(resultado["integridad_completa"])

    def test_01_casefold_expande_eszett(self):
        self.comprobar("Straße RDI no cerrada")

    def test_02_casefold_expande_i_unicode(self):
        self.comprobar("İ RDI no cerrada")
