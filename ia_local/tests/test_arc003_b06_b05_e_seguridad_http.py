"""
ARC003-B06-B03-B05-E.

Seguridad HTTP y conmutacion de circuitos.
No ejecuta E03 ni FINAL de negocio:
las funciones de entrada se simulan exclusivamente
para comprobar aislamiento y seleccion de ruta.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.test import Client, TestCase, override_settings
from django.urls import reverse


PREGUNTA = "¿Cuántos Documentos tienen status igual a DRAFT?"

RESPUESTA_E03 = {
    "ok": False,
    "estado": "gramatica_no_certificable",
    "respuesta": "Consulta no certificada.",
    "ejecutado": False,
    "total": None,
}

RESPUESTA_LEGADA = {
    "ok": True,
    "estado": "respuesta_formateada",
    "respuesta": "Respuesta tradicional.",
    "ejecutado": True,
    "total": 2,
}


class TestARC003B05ESeguridadHTTP(TestCase):

    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()

        cls.staff = Usuario.objects.create_user(
            username="arc003_b05e_staff",
            password="clave_solo_pruebas",
            is_staff=True,
            is_active=True,
        )

        cls.normal = Usuario.objects.create_user(
            username="arc003_b05e_normal",
            password="clave_solo_pruebas",
            is_staff=False,
            is_active=True,
        )

    def setUp(self):
        self.url = reverse("ia_local:consultar")
        self.contextual = reverse(
            "ia_local:consultar_contextual"
        )

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
    )
    def test_01_anonimo_no_ingresa(self):
        with (
            patch("ia_local.views.responder_consulta_web") as e03,
            patch("ia_local.views.responder_consulta") as legado,
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": PREGUNTA},
            )

        self.assertNotEqual(respuesta.status_code, 200)
        e03.assert_not_called()
        legado.assert_not_called()

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
    )
    def test_02_no_staff_no_ingresa(self):
        self.client.force_login(self.normal)

        with (
            patch("ia_local.views.responder_consulta_web") as e03,
            patch("ia_local.views.responder_consulta") as legado,
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": PREGUNTA},
            )

        self.assertNotEqual(respuesta.status_code, 200)
        e03.assert_not_called()
        legado.assert_not_called()

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
    )
    def test_03_post_sin_csrf_rechazado(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.staff)

        with (
            patch("ia_local.views.responder_consulta_web") as e03,
            patch("ia_local.views.responder_consulta") as legado,
        ):
            respuesta = cliente.post(
                self.url,
                {"pregunta": PREGUNTA},
            )

        self.assertEqual(respuesta.status_code, 403)
        e03.assert_not_called()
        legado.assert_not_called()

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
    )
    def test_04_certificado_selecciona_e03(self):
        self.client.force_login(self.staff)

        with (
            patch(
                "ia_local.views.responder_consulta_web",
                return_value=RESPUESTA_E03,
            ) as e03,
            patch("ia_local.views.responder_consulta") as legado,
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": PREGUNTA},
            )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.json()["estado"],
            "gramatica_no_certificable",
        )
        self.assertFalse(respuesta.json()["ejecutado"])
        e03.assert_called_once()
        legado.assert_not_called()

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=False
    )
    def test_05_tradicional_conserva_final(self):
        self.client.force_login(self.staff)

        with (
            patch(
                "ia_local.views.responder_consulta",
                return_value=RESPUESTA_LEGADA,
            ) as legado,
            patch("ia_local.views.responder_consulta_web") as e03,
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": PREGUNTA},
            )

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()["ok"])
        legado.assert_called_once()
        e03.assert_not_called()

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
    )
    def test_06_contextual_bloquea_continuacion(self):
        self.client.force_login(self.staff)

        with (
            patch(
                "ia_local.views_desambiguacion.responder_consulta"
            ) as legado,
            patch(
                "ia_local.views_desambiguacion.verificar_eleccion"
            ) as verificar,
            patch(
                "ia_local.views_desambiguacion.consulta_ia_json"
            ) as json_view,
        ):
            respuesta = self.client.post(
                self.contextual,
                {
                    "pregunta": PREGUNTA,
                    "opcion_id": "Document",
                    "token_aclaracion": "token_anterior",
                },
            )

        self.assertEqual(respuesta.status_code, 200)

        datos = respuesta.json()
        self.assertFalse(datos["ok"])
        self.assertFalse(datos["ejecutado"])
        self.assertEqual(
            datos["estado"],
            "aclaracion_no_certificada_en_http",
        )

        legado.assert_not_called()
        verificar.assert_not_called()
        json_view.assert_not_called()
