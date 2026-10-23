from unittest import TestCase
from unittest.mock import patch

from ia_local.services.final import ejecutor_consultas


class TestARC002C08Despacho(TestCase):

    PREGUNTA = "Cuantas RDI de civil no estan cerradas"

    def contrato(self, ejecutable):
        return {
            "ok": True,
            "estado": "contrato_normalizado",
            "pregunta": self.PREGUNTA,
            "intencion": "consulta_datos",
            "tipo_contrato": "plan_host",
            "ejecutor_sugerido": "ejecutor_datos",
            "ejecutable": ejecutable,
            "ejecutado": False,
            "certificacion_semantica": False,
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

    def test_01_contrato_no_ejecutable_no_despacha(self):
        with patch.object(
            ejecutor_consultas,
            "construir_contrato_respuesta",
            return_value=self.contrato(False),
        ), patch.object(
            ejecutor_consultas,
            "_ejecutar_contrato",
        ) as despacho:

            resultado = ejecutor_consultas.ejecutar_consulta(
                self.PREGUNTA
            )

        self.assertFalse(resultado["ok"])
        self.assertFalse(resultado["ejecutado"])
        self.assertEqual(
            resultado["estado"],
            "contrato_no_ejecutable",
        )
        despacho.assert_not_called()

    def test_02_caracterizar_contrato_sin_certificacion(self):
        contrato = self.contrato(True)

        with patch.object(
            ejecutor_consultas,
            "construir_contrato_respuesta",
            return_value=contrato,
        ), patch.object(
            ejecutor_consultas,
            "_ejecutar_contrato",
            return_value={
                "ok": False,
                "ejecutado": False,
            },
        ) as despacho:

            resultado = ejecutor_consultas.ejecutar_consulta(
                self.PREGUNTA
            )

        # Caracterizacion del comportamiento actual:
        # no constituye aprobacion de la politica.
        despacho.assert_called_once_with(contrato)
        self.assertFalse(resultado["ejecutado"])
        self.assertFalse(
            contrato["certificacion_semantica"]
        )
