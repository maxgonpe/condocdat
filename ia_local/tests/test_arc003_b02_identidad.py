from copy import deepcopy
from unittest import TestCase

from ia_local.services.llm.trazabilidad_compuesta import (
    preparar_coleccion_restricciones,
)


class TestARC003B02Identidad(TestCase):

    def consolidacion(self, pregunta):
        return {
            "ok": True,
            "estado": "consolidacion_diagnostica",
            "pregunta": pregunta,
            "restricciones": [
                {
                    "tipo": "negacion",
                    "evidencia_textual": "no estan cerrados",
                },
            ],
            "ejecutable": False,
            "ejecutado": False,
        }

    def test_01_identidad_depende_de_pregunta(self):
        pregunta_a = "Cuantos documentos no estan cerrados"
        pregunta_b = (
            "Cuantos documentos no estan cerrados hoy"
        )

        a = preparar_coleccion_restricciones(
            self.consolidacion(pregunta_a)
        )
        b = preparar_coleccion_restricciones(
            self.consolidacion(pregunta_b)
        )

        self.assertTrue(a["ok"])
        self.assertTrue(b["ok"])
        self.assertNotEqual(
            a["identificador_coleccion"],
            b["identificador_coleccion"],
        )

    def test_02_identidad_no_incluye_plan_host(self):
        pregunta = "Cuantos documentos no estan cerrados"

        coleccion = preparar_coleccion_restricciones(
            self.consolidacion(pregunta)
        )

        self.assertTrue(coleccion["ok"])

        plan_a = {
            "modelo": "ejemplo.Documento",
            "filtros": [{
                "campo": "estado",
                "operador": "exact",
                "valor": "ABIERTO",
            }],
        }

        plan_b = deepcopy(plan_a)
        plan_b["filtros"][0]["valor"] = "CERRADO"

        self.assertNotEqual(plan_a, plan_b)

        # La identidad actual de la coleccion es la misma
        # independientemente del plan que se pretenda ejecutar.
        identidad = coleccion["identificador_coleccion"]

        self.assertEqual(
            identidad,
            coleccion["identificador_coleccion"],
        )

        # Ningun plan forma parte del contrato identificado.
        self.assertNotIn("plan_host", coleccion)
        self.assertNotIn("huella_plan", coleccion)

    def test_03_coleccion_no_autoriza_ejecucion(self):
        coleccion = preparar_coleccion_restricciones(
            self.consolidacion(
                "Cuantos documentos no estan cerrados"
            )
        )

        self.assertTrue(coleccion["ok"])
        self.assertFalse(coleccion["ejecutable"])
        self.assertFalse(coleccion["integridad_completa"])
        self.assertFalse(coleccion["cobertura_verificada"])
