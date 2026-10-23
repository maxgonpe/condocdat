from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from ia_local.services.llm.trazabilidad_compuesta import (
    preparar_coleccion_restricciones,
)
from ia_local.services.llm.diagnostico_negacion_integral import (
    diagnosticar_negacion_integral,
)


class TestARC002C07DiagnosticoIntegral(TestCase):

    def coleccion(self, pregunta, fragmentos):
        resultado = preparar_coleccion_restricciones({
            "ok": True,
            "estado": "consolidacion_diagnostica",
            "pregunta": pregunta,
            "restricciones": [
                {
                    "tipo": "restriccion_textual",
                    "evidencia_textual": fragmento,
                }
                for fragmento in fragmentos
            ],
            "ejecutable": False,
            "ejecutado": False,
        })
        self.assertTrue(resultado["ok"])
        return resultado

    def plan_positivo(self):
        return {
            "modelo": "modelo.Ejemplo",
            "operacion": "count",
            "filtros": [
                {
                    "campo": "estado",
                    "operador": "exact",
                    "valor": "ABIERTO",
                },
            ],
        }

    def test_01_sem_neg_001_conservado(self):
        pregunta = "RDI de civil que no estan cerradas"
        coleccion = self.coleccion(
            pregunta,
            ["civil", "no estan cerradas"],
        )

        r = diagnosticar_negacion_integral(
            pregunta,
            coleccion,
            self.plan_positivo(),
        )

        self.assertTrue(r["ok"])
        self.assertEqual(
            r["estado"],
            "revision_con_discrepancias",
        )

        origenes = {
            d["origen"] for d in r["discrepancias"]
        }
        self.assertIn("sustituciones", origenes)
        self.assertIn("correspondencia", origenes)

        self.assertFalse(
            r["equivalencia_semantica_certificada"]
        )
        self.assertFalse(r["ejecutable"])

    def test_02_negacion_explicita_sigue_pendiente(self):
        pregunta = "documentos no cerrados"
        coleccion = self.coleccion(
            pregunta, ["no cerrados"]
        )

        plan = {
            "filtros": [{
                "campo": "estado",
                "operador": "exact",
                "valor": "CERRADO",
                "negado": True,
            }],
        }

        r = diagnosticar_negacion_integral(
            pregunta, coleccion, plan
        )

        self.assertTrue(r["ok"])
        self.assertFalse(r["cobertura_verificada"])
        self.assertFalse(r["integridad_completa"])
        self.assertFalse(r["ejecutable"])
        self.assertTrue(r["pendientes"])

    def test_03_asociacion_ambigua_conservada(self):
        pregunta = "documentos no cerrados"
        coleccion = self.coleccion(
            pregunta,
            ["no cerrados", "no cerrados"],
        )

        r = diagnosticar_negacion_integral(
            pregunta,
            coleccion,
            self.plan_positivo(),
        )

        self.assertTrue(r["ok"])

        motivos = [
            d["detalle"]
            for d in r["discrepancias"]
            if d["origen"] == "integridad"
        ]

        self.assertTrue(any(
            isinstance(m, dict)
            and m.get("motivo") == "asociacion_ambigua"
            for m in motivos
        ))

    def test_04_coleccion_adulterada_rechazada(self):
        pregunta = "documentos no cerrados"
        coleccion = self.coleccion(
            pregunta, ["no cerrados"]
        )

        alterada = deepcopy(coleccion)
        alterada["restricciones"][0][
            "evidencia_textual"
        ] = "cerrados"

        r = diagnosticar_negacion_integral(
            pregunta,
            alterada,
            self.plan_positivo(),
        )

        self.assertFalse(r["ok"])
        self.assertEqual(
            r["estado"], "diagnostico_invalido"
        )

    def test_05_pregunta_inconsistente(self):
        coleccion = self.coleccion(
            "documentos no cerrados",
            ["no cerrados"],
        )

        r = diagnosticar_negacion_integral(
            "documentos activos",
            coleccion,
            self.plan_positivo(),
        )

        self.assertFalse(r["ok"])
        self.assertEqual(r["estado"], "entrada_invalida")

    def test_06_ast_invalido_rechazado(self):
        pregunta = "documentos no cerrados"
        coleccion = self.coleccion(
            pregunta, ["no cerrados"]
        )

        r = diagnosticar_negacion_integral(
            pregunta,
            coleccion,
            self.plan_positivo(),
            expresion_logica="NOT cerrado",
        )

        self.assertFalse(r["ok"])
        self.assertEqual(
            r["estado"], "diagnostico_invalido"
        )

    def test_07_sin_bridge(self):
        pregunta = "documentos no cerrados"
        coleccion = self.coleccion(
            pregunta, ["no cerrados"]
        )

        with patch(
            "ia_local.services.query.grupos_logicos."
            "componer_campo_operador_valor"
        ) as bridge:
            r = diagnosticar_negacion_integral(
                pregunta,
                coleccion,
                self.plan_positivo(),
            )

        bridge.assert_not_called()
        self.assertTrue(r["ok"])
        self.assertFalse(r["llm_invocado"])
        self.assertFalse(r["ejecutable"])
        self.assertFalse(r["ejecutado"])
