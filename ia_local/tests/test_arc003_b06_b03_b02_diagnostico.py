"""
ARC003-B06-B03-B02
Integracion HTTP del diagnostico certificado.

No ejecuta consultas reales de negocio.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


PREGUNTA = (
    "¿Cuántos Documentos tienen status igual a DRAFT?"
)


class TestARC003B06DiagnosticoHTTP(TestCase):

    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.usuario = Usuario.objects.create_user(
            username="arc003_b03_diagnostico",
            password="solo_pruebas",
            is_staff=True,
            is_active=True,
        )

    def setUp(self):
        self.client.force_login(self.usuario)
        self.url = reverse("ia_local:diagnostico")

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
    )
    def test_01_certificado_exitoso(self):
        respuesta_certificada = {
            "ok": True,
            "version": "IA-ARC003-B06-B01-v1",
            "estado": "respuesta_formateada",
            "modelo": "documents.Document",
            "tipo": "conteo",
            "total": 3,
            "respuesta": "Se encontraron 3 registros.",
            "ejecutado": True,
            "llm_invocado": False,
        }

        with (
            patch(
                "ia_local.views.responder_consulta_web",
                return_value=respuesta_certificada,
            ) as certificado,
            patch(
                "ia_local.views.responder_consulta"
            ) as legado,
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": PREGUNTA},
            )

        self.assertEqual(respuesta.status_code, 200)
        certificado.assert_called_once()
        legado.assert_not_called()

        diagnostico = respuesta.context[
            "diagnostico_certificado"
        ]

        self.assertEqual(diagnostico["circuito"], "E03")
        self.assertEqual(diagnostico["total"], 3)
        self.assertTrue(diagnostico["ejecutado"])
        self.assertIsNone(
            respuesta.context["diagnostico"]
        )

        self.assertContains(
            respuesta,
            "Circuito certificado E03",
        )

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
    )
    def test_02_rechazo_sin_fallback(self):
        rechazado = {
            "ok": False,
            "version": "IA-ARC003-B06-B01-v1",
            "estado": "ejecucion_no_autorizada",
            "respuesta": "Consulta rechazada",
            "total": None,
            "ejecutado": False,
            "llm_invocado": False,
        }

        with (
            patch(
                "ia_local.views.responder_consulta_web",
                return_value=rechazado,
            ) as certificado,
            patch(
                "ia_local.views.responder_consulta"
            ) as legado,
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": PREGUNTA},
            )

        self.assertEqual(respuesta.status_code, 200)
        certificado.assert_called_once()
        legado.assert_not_called()

        diagnostico = respuesta.context[
            "diagnostico_certificado"
        ]

        self.assertFalse(diagnostico["ok"])
        self.assertFalse(diagnostico["ejecutado"])
        self.assertIsNone(diagnostico["total"])
        self.assertEqual(
            diagnostico["estado"],
            "ejecucion_no_autorizada",
        )

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=False
    )
    def test_03_legado_conservado(self):
        resultado_final = {
            "ok": False,
            "version": "IA-FINAL004-v1",
            "estado": "respuesta_no_ejecutable",
            "tipo": "resultado",
            "modelo": None,
            "respuesta": "Consulta no ejecutable",
            "ejecutado": False,
            "llm_invocado": False,
            "diagnostico": {},
        }

        with (
            patch(
                "ia_local.views.responder_consulta",
                return_value=resultado_final,
            ) as legado,
            patch(
                "ia_local.views.responder_consulta_web"
            ) as certificado,
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": PREGUNTA},
            )

        self.assertEqual(respuesta.status_code, 200)
        legado.assert_called_once_with(PREGUNTA)
        certificado.assert_not_called()

        self.assertIsNone(
            respuesta.context.get(
                "diagnostico_certificado"
            )
        )
        self.assertIsNotNone(
            respuesta.context["diagnostico"]
        )

    def test_04_get_no_ejecuta(self):
        with (
            patch(
                "ia_local.views.responder_consulta"
            ) as legado,
            patch(
                "ia_local.views.responder_consulta_web"
            ) as certificado,
        ):
            respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        legado.assert_not_called()
        certificado.assert_not_called()

    def test_05_anonimo_rechazado(self):
        self.client.logout()

        respuesta = self.client.post(
            self.url,
            {"pregunta": PREGUNTA},
        )

        self.assertNotEqual(respuesta.status_code, 200)
