from copy import deepcopy
from unittest import TestCase

from ia_local.services.llm.trazabilidad_compuesta import (
    preparar_coleccion_restricciones,
)
from ia_local.services.llm.vinculo_semantico import (
    vincular_contexto_semantico,
)


class TestARC003B02Vinculo(TestCase):

    PREGUNTA = "Cuantos documentos no estan cerrados"

    def coleccion(self):
        return preparar_coleccion_restricciones({
            "ok": True,
            "estado": "consolidacion_diagnostica",
            "pregunta": self.PREGUNTA,
            "restricciones": [{
                "tipo": "negacion",
                "evidencia_textual": "no estan cerrados",
            }],
            "ejecutable": False,
            "ejecutado": False,
        })

    def plan(self):
        return {
            "modelo": "ejemplo.Documento",
            "operacion": "count",
            "filtros": [{
                "campo": "estado",
                "operador": "exact",
                "valor": "ABIERTO",
            }],
        }

    def test_01_identidad_determinista(self):
        a = vincular_contexto_semantico(
            self.PREGUNTA, self.coleccion(), self.plan()
        )
        b = vincular_contexto_semantico(
            self.PREGUNTA, self.coleccion(), self.plan()
        )

        self.assertTrue(a["ok"])
        self.assertEqual(
            a["identificador_vinculo"],
            b["identificador_vinculo"],
        )
        self.assertFalse(a["ejecutable"])
        self.assertFalse(a["certificacion_semantica"])

    def test_02_cambio_plan_invalida_identidad(self):
        plan_b = deepcopy(self.plan())
        plan_b["filtros"][0]["valor"] = "CERRADO"

        a = vincular_contexto_semantico(
            self.PREGUNTA, self.coleccion(), self.plan()
        )
        b = vincular_contexto_semantico(
            self.PREGUNTA, self.coleccion(), plan_b
        )

        self.assertNotEqual(
            a["identificador_vinculo"],
            b["identificador_vinculo"],
        )

    def test_03_cambio_pregunta_rechazado(self):
        resultado = vincular_contexto_semantico(
            self.PREGUNTA + " hoy",
            self.coleccion(),
            self.plan(),
        )
        self.assertFalse(resultado["ok"])

    def test_04_coleccion_alterada_rechazada(self):
        coleccion = self.coleccion()
        coleccion["restricciones"][0]["tipo"] = "estado"

        resultado = vincular_contexto_semantico(
            self.PREGUNTA,
            coleccion,
            self.plan(),
        )
        self.assertFalse(resultado["ok"])

    def test_05_plan_autocertificado_rechazado(self):
        plan = self.plan()
        plan["certificacion_semantica"] = True

        resultado = vincular_contexto_semantico(
            self.PREGUNTA,
            self.coleccion(),
            plan,
        )
        self.assertFalse(resultado["ok"])
