from unittest import TestCase

from ia_local.services.final.orquestador_consultas import (
    _es_ejecutable,
)


class TestARC002C08Frontera(TestCase):

    def test_01_plan_host_sin_certificacion(self):
        resultado = {
            "ok": True,
            "plan": {
                "modelo": "ejemplo.Documento",
                "operacion": "count",
                "filtros": [
                    {
                        "campo": "estado",
                        "operador": "exact",
                        "valor": "ABIERTO",
                    },
                ],
            },
            "certificacion_semantica": False,
            "ejecutado": False,
        }

        # Caracterizacion del comportamiento actual.
        # True NO constituye autorizacion semantica.
        self.assertTrue(
            _es_ejecutable(
                resultado=resultado,
                tipo_plan="plan",
            )
        )

    def test_02_plan_unificado_no_permitido(self):
        resultado = {
            "plan_unificado": {
                "ejecucion": {
                    "permitida": False,
                },
            },
        }

        self.assertFalse(
            _es_ejecutable(
                resultado=resultado,
                tipo_plan="plan_unificado",
            )
        )

    def test_03_plan_unificado_permitido(self):
        resultado = {
            "plan_unificado": {
                "ejecucion": {
                    "permitida": True,
                },
            },
        }

        self.assertTrue(
            _es_ejecutable(
                resultado=resultado,
                tipo_plan="plan_unificado",
            )
        )
