from unittest import TestCase
from unittest.mock import patch

from ia_local.services.llm.auditoria_sustituciones import (
    auditar_sustituciones_semanticas,
)


class TestARC002C07Sustituciones(TestCase):

    def test_01_sem_neg_001(self):
        pregunta = (
            "Hay alguna RDI de civil que no este cerrada"
        )
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

        r = auditar_sustituciones_semanticas(
            pregunta, plan
        )

        self.assertTrue(r["ok"])
        self.assertEqual(
            r["estado"],
            "sustitucion_negativa_potencial",
        )
        self.assertIn(
            "negacion_original_sin_representacion_explicita",
            r["discrepancias"],
        )
        self.assertFalse(
            r["equivalencia_semantica_certificada"]
        )
        self.assertFalse(r["ejecutable"])

    def test_02_negacion_explicita_pendiente(self):
        r = auditar_sustituciones_semanticas(
            "documentos no cerrados",
            {
                "filtros": [
                    {
                        "campo": "estado",
                        "operador": "exact",
                        "valor": "CERRADO",
                        "negado": True,
                    },
                ],
            },
        )

        self.assertTrue(r["ok"])
        self.assertTrue(
            r["negacion_representada_en_plan"]
        )
        self.assertIn(
            "representacion_negativa_sin_certificacion",
            r["pendientes"],
        )
        self.assertFalse(
            r["equivalencia_semantica_certificada"]
        )

    def test_03_operador_negativo_pendiente(self):
        r = auditar_sustituciones_semanticas(
            "equipos sin mantenimiento",
            {
                "filtros": [
                    {
                        "campo": "mantenimiento",
                        "operador": "ne",
                        "valor": "REALIZADO",
                    },
                ],
            },
        )

        self.assertTrue(r["ok"])
        self.assertTrue(
            r["negacion_representada_en_plan"]
        )
        self.assertFalse(r["cobertura_verificada"])

    def test_04_negacion_inventada_en_plan(self):
        r = auditar_sustituciones_semanticas(
            "listar documentos activos",
            {
                "filtros": [
                    {
                        "campo": "estado",
                        "operador": "exclude",
                        "valor": "CERRADO",
                    },
                ],
            },
        )

        self.assertTrue(r["ok"])
        self.assertIn(
            "negacion_plan_sin_respaldo_textual_detectado",
            r["discrepancias"],
        )

    def test_05_excepcion_textual(self):
        r = auditar_sustituciones_semanticas(
            "listar equipos excepto los retirados",
            {
                "filtros": [
                    {
                        "campo": "estado",
                        "operador": "exact",
                        "valor": "ACTIVO",
                    },
                ],
            },
        )

        self.assertTrue(r["ok"])
        self.assertTrue(
            r["negacion_original_detectada"]
        )
        self.assertIn(
            "negacion_original_sin_representacion_explicita",
            r["discrepancias"],
        )

    def test_06_entrada_invalida(self):
        r = auditar_sustituciones_semanticas(
            "documentos no cerrados",
            {"filtros": "valor_invalido"},
        )

        self.assertFalse(r["ok"])
        self.assertFalse(r["ejecutable"])
        self.assertFalse(r["ejecutado"])

    def test_07_no_invoca_bridge(self):
        with patch(
            "ia_local.services.query.grupos_logicos."
            "componer_campo_operador_valor"
        ) as bridge:
            r = auditar_sustituciones_semanticas(
                "documentos no cerrados",
                {
                    "filtros": [
                        {
                            "campo": "estado",
                            "operador": "exact",
                            "valor": "ABIERTO",
                        },
                    ],
                },
            )

        bridge.assert_not_called()
        self.assertTrue(r["ok"])
        self.assertFalse(r["llm_invocado"])
        self.assertFalse(r["ejecutable"])
        self.assertFalse(r["ejecutado"])
