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


def solicitud_valida():
    return SimpleNamespace(
        user=SimpleNamespace(
            is_authenticated=True,
            pk=123,
        ),
        session=SimpleNamespace(
            session_key="arc001_b03",
        ),
    )


def plan_simulado():
    return {
        "ok": True,
        "estado": "plan_host_preparado",
        "modelo": "pruebas.Elemento",
        "plan": {
            "modelo": "pruebas.Elemento",
            "operacion": "contar",
            "filtros": [],
            "orden": [],
            "limite": None,
            "condiciones_no_resueltas": [],
        },
        "interpretacion": {
            "ok": True,
            "llm_invocado": True,
        },
        "certificacion_semantica": False,
        "ejecutable": False,
        "ejecutado": False,
    }


class TestARC001B03(TestCase):

    @patch(PREPARADOR)
    def test_01_prepara_sin_autorizar(self, preparar):
        preparar.return_value = plan_simulado()
        pregunta = "¿Cuántas RDI de civil están abiertas?"

        respuesta = procesar_consulta_canonica(
            solicitud_valida(),
            pregunta,
            modo="preparar",
        )

        preparar.assert_called_once_with(pregunta)
        self.assertIn(
            respuesta["estado"],
            (
                "pendiente_certificacion_semantica",
                "revision_semantica_pendiente",
            ),
        )
        self.assertEqual(
            respuesta["pregunta_original"],
            pregunta,
        )
        self.assertTrue(respuesta["contexto_valido"])
        self.assertTrue(respuesta["llm_invocado"])
        self.assertFalse(respuesta["ok"])
        self.assertFalse(respuesta["ejecutable"])
        self.assertFalse(respuesta["ejecutado"])

    @patch(PREPARADOR)
    def test_02_inspeccionar_no_invoca_llm(self, preparar):
        respuesta = procesar_consulta_canonica(
            solicitud_valida(),
            "¿Cuántos documentos hay?",
            modo="inspeccionar",
        )

        preparar.assert_not_called()
        self.assertEqual(
            respuesta["estado"],
            "pendiente_integracion",
        )

    @patch(PREPARADOR)
    def test_03_anonimo_no_invoca_llm(self, preparar):
        request = solicitud_valida()
        request.user.is_authenticated = False

        respuesta = procesar_consulta_canonica(
            request,
            "¿Cuántos documentos hay?",
            modo="preparar",
        )

        preparar.assert_not_called()
        self.assertEqual(
            respuesta["estado"],
            "identidad_no_autenticada",
        )

    @patch(PREPARADOR)
    def test_04_ejecucion_no_habilitada(self, preparar):
        respuesta = procesar_consulta_canonica(
            solicitud_valida(),
            "¿Cuántos documentos hay?",
            modo="ejecutar",
        )

        preparar.assert_not_called()
        self.assertEqual(
            respuesta["estado"],
            "modo_no_habilitado",
        )

    @patch(PREPARADOR)
    def test_05_preparador_rechazado(self, preparar):
        preparar.return_value = {
            "ok": False,
            "estado": "entidad_no_resuelta",
            "ejecutable": False,
            "ejecutado": False,
        }

        respuesta = procesar_consulta_canonica(
            solicitud_valida(),
            "Consulta ambigua",
            modo="preparar",
        )

        self.assertEqual(
            respuesta["estado"],
            "preparacion_no_disponible",
        )
        self.assertFalse(respuesta["ejecutado"])

    @patch(PREPARADOR)
    def test_06_rechaza_autorizacion_falsa(self, preparar):
        falso = plan_simulado()
        falso["ejecutable"] = True
        preparar.return_value = falso

        respuesta = procesar_consulta_canonica(
            solicitud_valida(),
            "¿Cuántos documentos hay?",
            modo="preparar",
        )

        self.assertEqual(
            respuesta["estado"],
            "preparacion_no_disponible",
        )
        self.assertFalse(respuesta["ejecutable"])

    @patch(PREPARADOR)
    def test_07_fallo_controlado(self, preparar):
        preparar.side_effect = RuntimeError("fallo simulado")

        respuesta = procesar_consulta_canonica(
            solicitud_valida(),
            "¿Cuántos documentos hay?",
            modo="preparar",
        )

        self.assertEqual(
            respuesta["estado"],
            "error_preparacion",
        )
        self.assertFalse(respuesta["ejecutado"])

    @patch(PREPARADOR)
    def test_08_modelo_inconsistente(self, preparar):
        falso = plan_simulado()
        falso["plan"]["modelo"] = "otra.Entidad"
        preparar.return_value = falso

        respuesta = procesar_consulta_canonica(
            solicitud_valida(),
            "¿Cuántos documentos hay?",
            modo="preparar",
        )

        self.assertEqual(
            respuesta["estado"],
            "plan_preparado_invalido",
        )
        self.assertFalse(respuesta["ejecutado"])
