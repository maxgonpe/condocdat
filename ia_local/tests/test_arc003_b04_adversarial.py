from copy import deepcopy
from unittest import TestCase

from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)
from ia_local.services.llm.certificador_limitado import (
    certificar_consulta_limitada,
)


class TestARC003B04Adversarial(TestCase):

    PREGUNTA = (
        "¿Cuántos Documentos tienen status igual a ACTIVO?"
    )

    def plan(self):
        validacion = validar_plan_datos({
            "modelo": "documents.Document",
            "operacion": "contar",
            "filtros": [{
                "campo": "status",
                "operador": "exact",
                "valor": "ACTIVO",
            }],
            "orden": [],
            "limite": 10,
            "condiciones_no_resueltas": [],
        })
        self.assertTrue(validacion["ok"])
        return validacion["plan"]

    def test_01_entidad_diferente(self):
        resultado = certificar_consulta_limitada(
            "¿Cuántos Proyectos tienen status igual a ACTIVO?",
            self.plan(),
        )
        self.assertFalse(resultado["ok"])

    def test_02_campo_diferente(self):
        resultado = certificar_consulta_limitada(
            "¿Cuántos Documentos tienen revision igual a ACTIVO?",
            self.plan(),
        )
        self.assertFalse(resultado["ok"])

    def test_03_restriccion_adicional(self):
        resultado = certificar_consulta_limitada(
            "¿Cuántos Documentos tienen status igual a ACTIVO "
            "y revision igual a B?",
            self.plan(),
        )
        self.assertFalse(resultado["ok"])

    def test_04_texto_extra_al_final(self):
        resultado = certificar_consulta_limitada(
            self.PREGUNTA + " solamente los recientes",
            self.plan(),
        )
        self.assertFalse(resultado["ok"])

    def test_05_operador_negativo(self):
        plan = deepcopy(self.plan())
        plan["filtros"][0]["operador"] = "ne"
        plan["filtros"][0]["negado"] = True

        resultado = certificar_consulta_limitada(
            self.PREGUNTA, plan
        )
        self.assertFalse(resultado["ok"])

    def test_06_plan_no_normalizado(self):
        plan = deepcopy(self.plan())
        del plan["filtros"][0]["tipo"]

        resultado = certificar_consulta_limitada(
            self.PREGUNTA, plan
        )
        self.assertFalse(resultado["ok"])

    def test_07_puntuacion_alterada(self):
        resultado = certificar_consulta_limitada(
            "¿Cuántos Documentos tienen status igual a ACTIVO?"
            " ¿Y los cerrados?",
            self.plan(),
        )
        self.assertFalse(resultado["ok"])

    def test_08_certificacion_no_habilita_ejecucion(self):
        resultado = certificar_consulta_limitada(
            self.PREGUNTA, self.plan()
        )
        self.assertTrue(resultado["certificacion_limitada"])
        self.assertFalse(resultado["ejecutable"])
        self.assertFalse(resultado["ejecutado"])
