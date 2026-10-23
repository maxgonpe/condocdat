from copy import deepcopy
from unittest import TestCase

from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)
from ia_local.services.llm.certificador_limitado import (
    certificar_consulta_limitada,
)


class TestARC003B04Certificador(TestCase):

    PREGUNTA = (
        "¿Cuántos Documentos tienen status igual a ACTIVO?"
    )

    def plan(self):
        resultado = validar_plan_datos({
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

        self.assertTrue(resultado["ok"])
        return resultado["plan"]

    def test_01_primera_certificacion_limitada(self):
        resultado = certificar_consulta_limitada(
            self.PREGUNTA, self.plan()
        )

        self.assertTrue(resultado["ok"])
        self.assertEqual(
            resultado["estado"], "certificado_limitado"
        )
        self.assertTrue(resultado["certificacion_limitada"])
        self.assertFalse(
            resultado["certificacion_semantica_integral"]
        )
        self.assertFalse(resultado["ejecutable"])
        self.assertFalse(resultado["ejecutado"])

    def test_02_valor_cambiado(self):
        plan = deepcopy(self.plan())
        plan["filtros"][0]["valor"] = "CERRADO"

        resultado = certificar_consulta_limitada(
            self.PREGUNTA, plan
        )
        self.assertFalse(resultado["ok"])

    def test_03_filtro_adicional(self):
        plan = deepcopy(self.plan())
        plan["filtros"].append(
            deepcopy(plan["filtros"][0])
        )

        resultado = certificar_consulta_limitada(
            self.PREGUNTA, plan
        )
        self.assertFalse(resultado["ok"])

    def test_04_negacion_no_certificable(self):
        pregunta = (
            "¿Cuántos Documentos no tienen "
            "status igual a ACTIVO?"
        )
        resultado = certificar_consulta_limitada(
            pregunta, self.plan()
        )
        self.assertFalse(resultado["ok"])

    def test_05_disyuncion_no_certificable(self):
        pregunta = (
            "¿Cuántos Documentos tienen status "
            "igual a ACTIVO o CERRADO?"
        )
        resultado = certificar_consulta_limitada(
            pregunta, self.plan()
        )
        self.assertFalse(resultado["ok"])

    def test_06_autocertificacion_no_admitida(self):
        plan = deepcopy(self.plan())
        plan["certificacion_semantica"] = True

        resultado = certificar_consulta_limitada(
            self.PREGUNTA, plan
        )
        self.assertFalse(resultado["ok"])

    def test_07_operacion_modificada(self):
        plan = deepcopy(self.plan())
        plan["operacion"] = "listar"

        resultado = certificar_consulta_limitada(
            self.PREGUNTA, plan
        )
        self.assertFalse(resultado["ok"])
