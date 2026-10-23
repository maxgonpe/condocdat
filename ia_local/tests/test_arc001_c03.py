from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ia_local.services.entrada_canonica import (
    procesar_consulta_canonica,
)

PREPARADOR = (
    "ia_local.services.host.preparador_consulta_datos."
    "preparar_consulta_datos"
)

AUDITOR = (
    "ia_local.services.llm.auditor_preparacion."
    "auditar_plan_preparado"
)


def request_prueba():
    return SimpleNamespace(
        user=SimpleNamespace(
            is_authenticated=True,
            pk=123,
        ),
        session=SimpleNamespace(
            session_key="arc001_c03",
        ),
    )


def preparacion_prueba():
    return {
        "ok": True,
        "estado": "plan_host_preparado",
        "modelo": "pruebas.Elemento",
        "plan": {
            "modelo": "pruebas.Elemento",
            "operacion": "contar",
            "filtros": [],
        },
        "interpretacion": {
            "ok": True,
            "llm_invocado": True,
        },
        "certificacion_semantica": False,
        "ejecutable": False,
        "ejecutado": False,
    }


class TestARC001C03(TestCase):

    @patch(AUDITOR)
    @patch(PREPARADOR)
    def test_01_sin_omision_no_autoriza(
        self, preparar, auditar
    ):
        preparar.return_value = preparacion_prueba()
        auditar.return_value = {
            "estado": "sin_omision_demostrada",
            "pendientes": [],
        }

        resultado = procesar_consulta_canonica(
            request_prueba(),
            "Consulta de prueba",
            modo="preparar",
        )

        self.assertEqual(
            resultado["estado"],
            "pendiente_certificacion_semantica",
        )
        self.assertFalse(resultado["ejecutable"])
        self.assertFalse(resultado["ejecutado"])
        auditar.assert_called_once_with(
            "Consulta de prueba",
            preparar.return_value["plan"],
        )

    @patch(AUDITOR)
    @patch(PREPARADOR)
    def test_02_omision_exige_revision(
        self, preparar, auditar
    ):
        preparar.return_value = preparacion_prueba()
        auditar.return_value = {
            "estado": "revision_pendiente",
            "pendientes": ["negacion_no_conservada"],
        }

        resultado = procesar_consulta_canonica(
            request_prueba(),
            "Consulta con negacion",
            modo="preparar",
        )

        self.assertEqual(
            resultado["estado"],
            "revision_semantica_pendiente",
        )
        self.assertIn(
            "negacion_no_conservada",
            resultado["auditoria_semantica"]["pendientes"],
        )
        self.assertFalse(resultado["ejecutable"])

    @patch(AUDITOR)
    @patch(PREPARADOR)
    def test_03_fallo_auditoria_bloqueado(
        self, preparar, auditar
    ):
        preparar.return_value = preparacion_prueba()
        auditar.side_effect = RuntimeError("fallo")

        resultado = procesar_consulta_canonica(
            request_prueba(),
            "Consulta",
            modo="preparar",
        )

        self.assertEqual(
            resultado["estado"],
            "revision_semantica_pendiente",
        )
        self.assertFalse(resultado["ejecutado"])

    @patch(AUDITOR)
    @patch(PREPARADOR)
    def test_04_sin_identidad_no_audita(
        self, preparar, auditar
    ):
        request = request_prueba()
        request.user.is_authenticated = False

        resultado = procesar_consulta_canonica(
            request,
            "Consulta",
            modo="preparar",
        )

        self.assertEqual(
            resultado["estado"],
            "identidad_no_autenticada",
        )
        preparar.assert_not_called()
        auditar.assert_not_called()
