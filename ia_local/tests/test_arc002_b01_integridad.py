from unittest import TestCase
from unittest.mock import patch

from ia_local.services.llm.consolidacion_semantica import (
    consolidar_interpretacion_semantica,
)

AUDITOR = (
    "ia_local.services.llm.consolidacion_semantica."
    "auditar_restricciones_semanticas"
)


def auditoria_simulada(restricciones, *, ok=True):
    return {
        "ok": ok,
        "ejecutado": False,
        "omisiones_auditoria": [],
        "extraccion_inicial": {
            "ok": True,
            "ejecutado": False,
            "operacion": "contar",
            "restricciones": restricciones,
            "capacidades_omitidas": [],
        },
    }


class TestARC002B01Integridad(TestCase):

    @patch(AUDITOR)
    def test_01_vacio_no_demuestra_integridad(self, auditar):
        auditar.return_value = auditoria_simulada([])

        resultado = consolidar_interpretacion_semantica(
            "¿Cuántas RDI de civil están abiertas?"
        )

        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["cantidad_restricciones"], 0)
        self.assertTrue(resultado["restricciones_vacias_pendientes"])
        self.assertTrue(resultado["requiere_revision"])
        self.assertFalse(resultado["ejecutable"])
        self.assertFalse(resultado["ejecutado"])

    @patch(AUDITOR)
    def test_02_consulta_general_vacia_tambien_pendiente(
        self, auditar
    ):
        auditar.return_value = auditoria_simulada([])

        resultado = consolidar_interpretacion_semantica(
            "¿Cuántos documentos hay?"
        )

        self.assertTrue(resultado["requiere_revision"])
        self.assertTrue(resultado["restricciones_vacias_pendientes"])
        self.assertFalse(resultado["ejecutable"])

    @patch(AUDITOR)
    def test_03_conserva_restricciones_extraidas(self, auditar):
        auditar.return_value = auditoria_simulada([
            {
                "tipo": "filtro",
                "evidencia_textual": "de civil",
            },
        ])

        resultado = consolidar_interpretacion_semantica(
            "¿Cuántas RDI de civil están abiertas?"
        )

        self.assertEqual(resultado["cantidad_restricciones"], 1)
        self.assertFalse(resultado["restricciones_vacias_pendientes"])
        self.assertTrue(resultado["requiere_revision"])
        self.assertFalse(
            resultado["restricciones"][0]["certificada_host"]
        )

    @patch(AUDITOR)
    def test_04_auditoria_rechazada_no_consolida(self, auditar):
        auditar.return_value = {"ok": False}

        resultado = consolidar_interpretacion_semantica(
            "¿Hay alguna RDI que no esté cerrada?"
        )

        self.assertFalse(resultado["ok"])
        self.assertEqual(
            resultado["estado"],
            "auditoria_no_validada"
        )
        self.assertFalse(resultado["ejecutable"])
