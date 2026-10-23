from copy import deepcopy
from unittest import TestCase

from ia_local.services.llm.trazabilidad_compuesta import (
    preparar_coleccion_restricciones,
)
from ia_local.services.llm.vinculo_semantico import (
    vincular_contexto_semantico,
    verificar_vinculo_semantico,
)


class TestARC003B03Verificacion(TestCase):

    PREGUNTA = "Cuantos documentos no estan cerrados"

    def contexto(self):
        coleccion = preparar_coleccion_restricciones({
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

        plan = {
            "modelo": "ejemplo.Documento",
            "operacion": "count",
            "filtros": [{
                "campo": "estado",
                "operador": "exact",
                "valor": "ABIERTO",
            }],
        }

        vinculo = vincular_contexto_semantico(
            self.PREGUNTA,
            coleccion,
            plan,
        )
        self.assertTrue(vinculo["ok"])

        return coleccion, plan, vinculo

    def test_01_vinculo_original_coincide(self):
        coleccion, plan, vinculo = self.contexto()

        resultado = verificar_vinculo_semantico(
            self.PREGUNTA, coleccion, plan, vinculo
        )

        self.assertTrue(resultado["ok"])
        self.assertTrue(resultado["coincidencia_verificada"])
        self.assertFalse(resultado["certificacion_semantica"])
        self.assertFalse(resultado["ejecutable"])

    def test_02_plan_modificado_rechazado(self):
        coleccion, plan, vinculo = self.contexto()
        modificado = deepcopy(plan)
        modificado["filtros"][0]["valor"] = "CERRADO"

        resultado = verificar_vinculo_semantico(
            self.PREGUNTA, coleccion, modificado, vinculo
        )

        self.assertFalse(resultado["ok"])
        self.assertEqual(
            resultado["estado"],
            "contexto_modificado",
        )

    def test_03_coleccion_modificada_rechazada(self):
        coleccion, plan, vinculo = self.contexto()
        modificada = deepcopy(coleccion)
        modificada["restricciones"][0]["tipo"] = "estado"

        resultado = verificar_vinculo_semantico(
            self.PREGUNTA, modificada, plan, vinculo
        )

        self.assertFalse(resultado["ok"])
        self.assertFalse(resultado["ejecutable"])

    def test_04_vinculo_autorizado_artificialmente_rechazado(self):
        coleccion, plan, vinculo = self.contexto()
        alterado = deepcopy(vinculo)
        alterado["certificacion_semantica"] = True

        resultado = verificar_vinculo_semantico(
            self.PREGUNTA, coleccion, plan, alterado
        )

        self.assertFalse(resultado["ok"])
        self.assertFalse(resultado["coincidencia_verificada"])
