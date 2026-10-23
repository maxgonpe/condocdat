from unittest import TestCase
from unittest.mock import patch

from ia_local.services.final import ejecutor_consultas


class TestARC002C08B04Bloqueo(TestCase):

    def test_01_negacion_omitida_no_despacha(self):
        pregunta = "Cuantas RDI de civil no estan cerradas"

        contrato = {
            "ok": True,
            "estado": "contrato_normalizado",
            "pregunta": pregunta,
            "tipo_contrato": "plan_host",
            "ejecutor_sugerido": "ejecutor_datos",
            "ejecutable": True,
            "ejecutado": False,
            "contrato": {
                "modelo": "rdi.RDIRecord",
                "operacion": "count",
                "filtros": [
                    {
                        "campo": "status",
                        "operador": "exact",
                        "valor": "ABIERTA",
                    },
                    {
                        "campo": "discipline",
                        "operador": "icontains",
                        "valor": "civil",
                    },
                ],
            },
        }

        with patch.object(
            ejecutor_consultas,
            "construir_contrato_respuesta",
            return_value=contrato,
        ), patch.object(
            ejecutor_consultas,
            "_ejecutar_contrato",
        ) as despacho:

            resultado = ejecutor_consultas.ejecutar_consulta(
                pregunta
            )

        self.assertFalse(resultado["ejecutado"])
        self.assertFalse(resultado["ok"])
        despacho.assert_not_called()

    def test_02_auditoria_detecta_la_omision(self):
        from ia_local.services.llm.auditoria_sustituciones import (
            auditar_sustituciones_semanticas,
        )

        resultado = auditar_sustituciones_semanticas(
            "Cuantas RDI de civil no estan cerradas",
            {
                "filtros": [
                    {
                        "campo": "status",
                        "operador": "exact",
                        "valor": "ABIERTA",
                    },
                ],
            },
        )

        self.assertTrue(resultado["ok"])
        self.assertIn(
            "negacion_original_sin_representacion_explicita",
            resultado["discrepancias"],
        )
        self.assertFalse(
            resultado["equivalencia_semantica_certificada"]
        )
