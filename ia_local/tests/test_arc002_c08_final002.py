from unittest import TestCase
from unittest.mock import patch

from ia_local.services.final import contrato_respuesta


class TestARC002C08FINAL002(TestCase):

    PREGUNTA = "Cuantas RDI de civil no estan cerradas"

    def salida_final001(self):
        plan = {
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
        }

        return {
            "ok": True,
            "version": "IA-FINAL001-v1",
            "estado": "consulta_interpretada",
            "pregunta": self.PREGUNTA,
            "resuelto": True,
            "intencion": "consulta_datos",
            "componente": "HOST_SIMULADO",
            "tipo_plan": "plan_host",
            "plan_ejecutable": plan,
            "resultado_interpretacion": {
                "ok": True,
                "modelo": "rdi.RDIRecord",
                "plan": plan,
                "certificacion_semantica": False,
                "ejecutado": False,
            },
            "certificacion_semantica": False,
            "ejecutable": True,
            "ejecutado": False,
        }

    def test_01_caracterizar_contrato_final002(self):
        with patch.object(
            contrato_respuesta,
            "resolver_consulta",
            return_value=self.salida_final001(),
        ):
            resultado = (
                contrato_respuesta.construir_contrato_respuesta(
                    self.PREGUNTA
                )
            )

        self.assertTrue(resultado["ok"])
        self.assertEqual(
            resultado["tipo_contrato"],
            "plan_host",
        )
        self.assertEqual(
            resultado["ejecutor_sugerido"],
            "ejecutor_datos",
        )

        # Esta prueba caracteriza el comportamiento actual.
        # No interpreta ejecutable=True como autorizacion
        # semantica valida.
        self.assertTrue(resultado["ejecutable"])

    def test_02_fallback_llm_permanece_bloqueado(self):
        final001 = {
            "ok": False,
            "estado": "consulta_no_resuelta",
            "pregunta": self.PREGUNTA,
        }

        fallback = {
            "ok": True,
            "plan_validado": True,
            "modelo": "rdi.RDIRecord",
            "plan": self.salida_final001()[
                "plan_ejecutable"
            ],
            "llm_invocado": True,
            "ejecutado": False,
        }

        with patch.object(
            contrato_respuesta,
            "resolver_consulta",
            return_value=final001,
        ), patch.object(
            contrato_respuesta,
            "construir_plan_llm",
            return_value=fallback,
        ):
            resultado = (
                contrato_respuesta.construir_contrato_respuesta(
                    self.PREGUNTA
                )
            )

        self.assertFalse(resultado["ok"])
        self.assertFalse(resultado["ejecutable"])
        self.assertEqual(
            resultado["estado"],
            "consulta_llm_pendiente_cobertura",
        )
        self.assertIsNone(
            resultado["ejecutor_sugerido"]
        )
