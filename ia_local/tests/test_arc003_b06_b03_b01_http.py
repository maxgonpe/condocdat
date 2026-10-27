"""
ARC003-B06-B03-B01
Integracion HTTP de /ia/consultar/.

Comprueba selector, autorizacion de acceso, metodo
HTTP, CSRF y ausencia de fallback.

No ejecuta ORM de negocio.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse


SELECTOR = (
    "ia_local.services.final.entrada_web_compartida"
)


class TestARC003B06B03B01HTTP(TestCase):

    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.usuario = Usuario.objects.create_user(
            username="arc003_b03_http",
            password="clave_solo_pruebas",
            is_staff=True,
            is_active=True,
        )

    def setUp(self):
        self.url = reverse("ia_local:consultar")
        self.client.force_login(self.usuario)
        self.pregunta = (
            "¿Cuántos Documentos tienen "
            "status igual a DRAFT?"
        )

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=False
    )
    def test_01_modo_legado(self):
        esperado = {
            "ok": True,
            "estado": "respuesta_formateada",
            "respuesta": "Resultado legado",
            "ejecutado": True,
        }

        with (
            patch(
                "ia_local.views.responder_consulta",
                return_value=esperado,
            ) as legado,
            patch(
                SELECTOR + ".responder_consulta_http"
            ) as certificado,
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": self.pregunta},
            )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), esperado)
        legado.assert_called_once_with(self.pregunta)
        certificado.assert_not_called()

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
    )
    def test_02_modo_certificado(self):
        esperado = {
            "ok": True,
            "estado": "respuesta_formateada",
            "respuesta": "Se encontraron 3 registros.",
            "total": 3,
            "ejecutado": True,
        }

        with (
            patch(
                SELECTOR + ".responder_consulta"
            ) as legado,
            patch(
                SELECTOR + ".responder_consulta_http",
                return_value=esperado,
            ) as certificado,
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": self.pregunta},
            )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), esperado)
        legado.assert_not_called()
        certificado.assert_called_once()

        argumentos = certificado.call_args.args
        self.assertEqual(len(argumentos), 2)
        self.assertEqual(argumentos[1], self.pregunta)
        self.assertEqual(
            argumentos[0].user.pk,
            self.usuario.pk,
        )

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
    )
    def test_03_rechazo_sin_fallback(self):
        rechazado = {
            "ok": False,
            "estado": "ejecucion_no_autorizada",
            "respuesta": "Consulta rechazada",
            "total": None,
            "ejecutado": False,
        }

        with (
            patch(
                SELECTOR + ".responder_consulta"
            ) as legado,
            patch(
                SELECTOR + ".responder_consulta_http",
                return_value=rechazado,
            ) as certificado,
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": self.pregunta},
            )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), rechazado)
        certificado.assert_called_once()
        legado.assert_not_called()

    def test_04_usuario_anonimo_no_ingresa(self):
        self.client.logout()

        with patch(
            SELECTOR + ".responder_consulta_http"
        ) as certificado:
            respuesta = self.client.post(
                self.url,
                {"pregunta": self.pregunta},
            )

        self.assertNotEqual(respuesta.status_code, 200)
        certificado.assert_not_called()

    def test_05_metodo_get_rechazado(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 405)

    def test_06_csrf_sin_token_rechazado(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)

        respuesta = cliente.post(
            self.url,
            {"pregunta": self.pregunta},
        )

        self.assertEqual(respuesta.status_code, 403)

    def test_07_usuario_no_staff_rechazado(self):
        Usuario = get_user_model()
        normal = Usuario.objects.create_user(
            username="arc003_b03_no_staff",
            password="clave_solo_pruebas",
            is_staff=False,
        )

        self.client.force_login(normal)

        with patch(
            SELECTOR + ".responder_consulta_http"
        ) as certificado:
            respuesta = self.client.post(
                self.url,
                {"pregunta": self.pregunta},
            )

        self.assertNotEqual(respuesta.status_code, 200)
        certificado.assert_not_called()
