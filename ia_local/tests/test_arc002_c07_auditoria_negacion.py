from unittest import TestCase
from unittest.mock import patch

from ia_local.services.llm.auditoria_negacion import (
    auditar_correspondencia_negativa,
)


class TestARC002C07AuditoriaNegacion(TestCase):

    def test_01_negacion_natural_sin_ast(self):
        r = auditar_correspondencia_negativa(
            "Cuantas RDI no estan cerradas"
        )

        self.assertTrue(r["ok"])
        self.assertEqual(r["cantidad_evidencias"], 1)
        self.assertIn(
            "negacion_original_sin_arbol_diagnostico",
            r["discrepancias"],
        )
        self.assertFalse(r["ejecutable"])

    def test_02_sem_neg_001(self):
        r = auditar_correspondencia_negativa(
            "Hay alguna RDI de civil que no este cerrada",
            "estado abierta",
        )

        self.assertTrue(r["ok"])
        self.assertIn(
            "correspondencia_entre_textos_no_demostrada",
            r["discrepancias"],
        )
        self.assertFalse(
            r["equivalencia_semantica_certificada"]
        )

    def test_03_ast_not_explicito(self):
        r = auditar_correspondencia_negativa(
            "NOT (cerrado)",
            "NOT (cerrado)",
        )

        self.assertTrue(r["ok"])
        self.assertEqual(r["cantidad_nodos_not"], 1)
        self.assertFalse(r["alcance_certificado"])
        self.assertFalse(r["ejecutable"])

    def test_04_textos_distintos_con_not(self):
        r = auditar_correspondencia_negativa(
            "documentos que no estan cerrados",
            "NOT (cerrado)",
        )

        self.assertTrue(r["ok"])
        self.assertEqual(r["cantidad_evidencias"], 1)
        self.assertEqual(r["cantidad_nodos_not"], 1)
        self.assertIn(
            "correspondencia_entre_textos_no_demostrada",
            r["discrepancias"],
        )

    def test_05_ast_invalido(self):
        r = auditar_correspondencia_negativa(
            "documentos no cerrados",
            "NOT cerrado",
        )

        self.assertFalse(r["ok"])
        self.assertEqual(
            r["estado"],
            "ast_diagnostico_invalido",
        )
        self.assertFalse(r["ejecutado"])

    def test_06_sin_bridge(self):
        with patch(
            "ia_local.services.query.grupos_logicos."
            "componer_campo_operador_valor"
        ) as bridge:
            r = auditar_correspondencia_negativa(
                "no cerrado",
                "NOT (cerrado)",
            )

        bridge.assert_not_called()
        self.assertTrue(r["ok"])
        self.assertFalse(r["llm_invocado"])
        self.assertFalse(r["cobertura_verificada"])
        self.assertFalse(r["integridad_completa"])
        self.assertFalse(r["ejecutable"])
        self.assertFalse(r["ejecutado"])
