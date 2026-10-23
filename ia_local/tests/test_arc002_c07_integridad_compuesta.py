from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from ia_local.services.llm.trazabilidad_compuesta import (
    preparar_coleccion_restricciones,
)
from ia_local.services.llm.evidencia_negacion import (
    localizar_evidencias_negacion,
)
from ia_local.services.llm.asociacion_evidencias import (
    asociar_evidencias_requisitos,
)
from ia_local.services.llm.integridad_negacion_compuesta import (
    auditar_integridad_negativa_compuesta,
)


class TestARC002C07IntegridadCompuesta(TestCase):

    def coleccion(self, pregunta, fragmentos):
        originales = [
            {
                "tipo": "restriccion_textual",
                "evidencia_textual": fragmento,
            }
            for fragmento in fragmentos
        ]

        resultado = preparar_coleccion_restricciones({
            "ok": True,
            "estado": "consolidacion_diagnostica",
            "pregunta": pregunta,
            "restricciones": originales,
            "ejecutable": False,
            "ejecutado": False,
        })

        self.assertTrue(resultado["ok"])
        return resultado

    def test_01_integridad_textual_pendiente(self):
        c = self.coleccion(
            "RDI que no estan cerradas",
            ["no estan cerradas"],
        )

        r = auditar_integridad_negativa_compuesta(c)

        self.assertTrue(r["ok"])
        self.assertEqual(
            r["estado"],
            "integridad_textual_pendiente",
        )
        self.assertEqual(len(r["asociaciones"]), 1)
        self.assertEqual(
            r["asociaciones"][0]["estado"],
            "asociacion_textual",
        )
        self.assertFalse(r["integridad_completa"])
        self.assertFalse(r["ejecutable"])

    def test_02_evidencia_sin_requisito(self):
        c = self.coleccion(
            "RDI de civil que no estan cerradas",
            ["civil"],
        )

        r = auditar_integridad_negativa_compuesta(c)

        self.assertTrue(r["ok"])
        self.assertEqual(
            r["estado"],
            "integridad_con_discrepancias_pendientes",
        )
        self.assertEqual(
            r["discrepancias"][0]["motivo"],
            "evidencia_sin_requisito",
        )

    def test_03_asociacion_ambigua(self):
        c = self.coleccion(
            "RDI que no estan cerradas",
            ["no estan cerradas", "no estan cerradas"],
        )

        r = auditar_integridad_negativa_compuesta(c)

        self.assertTrue(r["ok"])
        self.assertEqual(
            r["discrepancias"][0]["motivo"],
            "asociacion_ambigua",
        )

    def test_04_restriccion_adulterada(self):
        c = self.coleccion(
            "RDI que no estan cerradas",
            ["no estan cerradas"],
        )

        alterada = deepcopy(c)
        alterada["restricciones"][0][
            "evidencia_textual"
        ] = "cerradas"

        r = auditar_integridad_negativa_compuesta(
            alterada
        )

        self.assertFalse(r["ok"])
        self.assertEqual(
            r["estado"],
            "coleccion_inconsistente",
        )

    def test_05_evidencias_adulteradas(self):
        c = self.coleccion(
            "RDI que no estan cerradas",
            ["no estan cerradas"],
        )

        evidencias = localizar_evidencias_negacion(
            c["pregunta_original"]
        )

        alteradas = deepcopy(evidencias)
        alteradas["evidencias"][0]["inicio"] = 0

        r = auditar_integridad_negativa_compuesta(
            c,
            evidencias_recibidas=alteradas,
        )

        self.assertFalse(r["ok"])
        self.assertEqual(
            r["estado"],
            "evidencias_adulteradas",
        )

    def test_06_asociaciones_adulteradas(self):
        c = self.coleccion(
            "RDI que no estan cerradas",
            ["no estan cerradas"],
        )

        evidencias = localizar_evidencias_negacion(
            c["pregunta_original"]
        )

        asociaciones = asociar_evidencias_requisitos(
            c, evidencias
        )

        alteradas = deepcopy(asociaciones)
        alteradas["asociaciones"][0][
            "requisitos_candidatos"
        ] = ["inventado"]

        r = auditar_integridad_negativa_compuesta(
            c,
            asociaciones_recibidas=alteradas,
        )

        self.assertFalse(r["ok"])
        self.assertEqual(
            r["estado"],
            "asociaciones_adulteradas",
        )

    def test_07_no_invoca_resolvedor(self):
        c = self.coleccion(
            "RDI que no estan cerradas",
            ["no estan cerradas"],
        )

        with patch(
            "ia_local.services.query.grupos_logicos."
            "componer_campo_operador_valor"
        ) as bridge:
            r = auditar_integridad_negativa_compuesta(c)

        bridge.assert_not_called()
        self.assertTrue(r["ok"])
        self.assertFalse(
            r["equivalencia_semantica_certificada"]
        )
        self.assertFalse(r["cobertura_verificada"])
        self.assertFalse(r["ejecutable"])
        self.assertFalse(r["ejecutado"])
