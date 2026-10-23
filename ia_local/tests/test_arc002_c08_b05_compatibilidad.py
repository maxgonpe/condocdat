from unittest import TestCase
from unittest.mock import patch

from ia_local.services.final import ejecutor_consultas


class TestARC002C08B05Compatibilidad(TestCase):

    def contrato(self, pregunta, filtros):
        return {
            "ok": True,
            "estado": "contrato_normalizado",
            "pregunta": pregunta,
            "tipo_contrato": "plan_host",
            "ejecutor_sugerido": "ejecutor_datos",
            "ejecutable": True,
            "ejecutado": False,
            "contrato": {
                "modelo": "ejemplo.Documento",
                "operacion": "count",
                "filtros": filtros,
            },
        }

    def ejecutar_simulado(self, pregunta, contrato):
        with patch.object(
            ejecutor_consultas,
            "construir_contrato_respuesta",
            return_value=contrato,
        ), patch.object(
            ejecutor_consultas,
            "_ejecutar_contrato",
            return_value={
                "ok": True,
                "ejecutado": True,
            },
        ) as despacho:

            resultado = ejecutor_consultas.ejecutar_consulta(
                pregunta
            )

        return resultado, despacho

    def test_01_consulta_positiva_conserva_despacho(self):
        pregunta = "Cuantos documentos estan activos"

        contrato = self.contrato(
            pregunta,
            [{
                "campo": "estado",
                "operador": "exact",
                "valor": "ACTIVO",
            }],
        )

        resultado, despacho = self.ejecutar_simulado(
            pregunta, contrato
        )

        despacho.assert_called_once_with(contrato)
        self.assertTrue(resultado["ejecutado"])

    def test_02_negacion_representada_sin_certificacion(self):
        pregunta = "Cuantos documentos no estan cerrados"

        contrato = self.contrato(
            pregunta,
            [{
                "campo": "estado",
                "operador": "exact",
                "valor": "CERRADO",
                "negado": True,
            }],
        )

        resultado, despacho = self.ejecutar_simulado(
            pregunta, contrato
        )

        # Representar NOT no prueba su alcance ni
        # certifica equivalencia semantica.
        despacho.assert_not_called()
        self.assertFalse(resultado["ejecutado"])

    def test_03_plan_unificado_sin_contrato_auditable(self):
        pregunta = "Cuantos documentos no estan cerrados"

        contrato = {
            "ok": True,
            "estado": "contrato_normalizado",
            "pregunta": pregunta,
            "tipo_contrato": "plan_unificado",
            "ejecutor_sugerido": "orquestador_plan_unificado",
            "ejecutable": True,
            "ejecutado": False,
            "contrato": {
                "modelo_base": {
                    "label": "ejemplo.Documento",
                },
                "ejecucion": {
                    "permitida": True,
                },
            },
        }

        resultado, despacho = self.ejecutar_simulado(
            pregunta, contrato
        )

        despacho.assert_not_called()
        self.assertFalse(resultado["ejecutado"])
