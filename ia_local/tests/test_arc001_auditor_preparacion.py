from unittest import TestCase
from unittest.mock import patch

from ia_local.services.llm.auditor_preparacion import (
    auditar_plan_preparado,
)

BASE = "ia_local.services.llm.auditor_preparacion"


def plan(filtros):
    return {
        "modelo": "pruebas.Elemento",
        "operacion": "contar",
        "filtros": filtros,
    }


def filtro_estado(negado=False):
    return {
        "campo": "estado",
        "operador": "exact",
        "valor": "CERRADA" if negado else "ABIERTA",
        "negado": negado,
    }


class TestARC001AuditorPreparacion(TestCase):

    def _auditores_controlados(self):
        return (
            patch(
                BASE + ".auditar_restricciones_semanticas",
                return_value={
                    "ok": True,
                    "omisiones_auditoria": [],
                    "requiere_revision": False,
                },
            ),
            patch(
                BASE + ".consolidar_interpretacion_semantica",
                return_value={
                    "ok": True,
                    "requiere_revision": False,
                    "omisiones_conocidas": [],
                },
            ),
            patch(
                BASE + ".evaluar_cobertura_semantica",
                return_value={
                    "ok": True,
                    "componentes_pendientes": [],
                    "cobertura_verificada": False,
                    "ejecutable": False,
                },
            ),
        )

    def test_01_abierta_sin_omision_demostrada(self):
        a, b, c = self._auditores_controlados()

        with a, b, c:
            resultado = auditar_plan_preparado(
                "¿Cuántas RDI están abiertas?",
                plan([filtro_estado()]),
            )

        self.assertEqual(
            resultado["estado"],
            "sin_omision_demostrada",
        )
        self.assertFalse(resultado["ejecutable"])

    def test_02_no_cerrada_exige_revision(self):
        a, b, c = self._auditores_controlados()

        with a, b, c:
            resultado = auditar_plan_preparado(
                "¿Hay alguna RDI que no esté cerrada?",
                plan([filtro_estado()]),
            )

        self.assertEqual(
            resultado["estado"],
            "revision_pendiente",
        )
        self.assertIn(
            "negacion_textual_sin_representacion_explica",
            resultado["pendientes"],
        )

    def test_03_negacion_representada_no_certifica(self):
        a, b, c = self._auditores_controlados()

        with a, b, c:
            resultado = auditar_plan_preparado(
                "¿Hay alguna RDI que no esté cerrada?",
                plan([filtro_estado(negado=True)]),
            )

        self.assertEqual(
            resultado["estado"],
            "sin_omision_demostrada",
        )
        self.assertFalse(
            resultado["cobertura_certificada"]
        )

    def test_04_omision_reportada_por_auditor(self):
        with (
            patch(
                BASE + ".auditar_restricciones_semanticas",
                return_value={
                    "omisiones_auditoria": ["filtro_omitido"],
                    "requiere_revision": True,
                },
            ),
            patch(
                BASE + ".consolidar_interpretacion_semantica",
                return_value={"requiere_revision": False},
            ),
            patch(
                BASE + ".evaluar_cobertura_semantica",
                return_value={"componentes_pendientes": []},
            ),
        ):
            resultado = auditar_plan_preparado(
                "Pregunta compuesta",
                plan([]),
            )

        self.assertEqual(
            resultado["estado"],
            "revision_pendiente",
        )

    def test_05_auditoria_falla_cerrado(self):
        with patch(
            BASE + ".auditar_restricciones_semanticas",
            side_effect=RuntimeError("error"),
        ):
            resultado = auditar_plan_preparado(
                "Pregunta",
                plan([]),
            )

        self.assertEqual(
            resultado["estado"],
            "revision_pendiente",
        )
        self.assertFalse(resultado["ejecutable"])

    def test_06_plan_invalido(self):
        resultado = auditar_plan_preparado(
            "Pregunta",
            {"filtros": "incorrecto"},
        )

        self.assertEqual(resultado["estado"], "plan_invalido")
        self.assertFalse(resultado["ejecutado"])
