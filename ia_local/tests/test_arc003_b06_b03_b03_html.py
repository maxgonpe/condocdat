"""
ARC003-B06-B03-B03
Integracion HTTP de la pagina principal /ia/.

Prueba compatibilidad, seleccion de circuito,
ausencia de fallback y restricciones HTTP.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse


PREGUNTA = (
    "¿Cuántos Documentos tienen status igual a DRAFT?"
)

ADAPTADOR = (
    "ia_local.services.final.adaptador_html_arc001."
    "adaptar_final_html"
)


def salida_html():
    return {
        "diagnostico": {},
        "respuesta_estructurada": {},
        "respuesta_texto": "Respuesta de prueba",
    }


class TestARC003B06B03B03HTML(TestCase):

    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()

        cls.usuario = Usuario.objects.create_user(
            username="arc003_b03_html",
            password="clave_solo_pruebas",
            is_staff=True,
            is_active=True,
        )

    def setUp(self):
        self.url = "/ia/"
        self.client.force_login(self.usuario)

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=False
    )
    def test_01_html_modo_legado(self):
        resultado = {
            "ok": True,
            "estado": "respuesta_formateada",
            "respuesta": "Legado",
        }

        with (
            patch(
                "ia_local.views.responder_consulta",
                return_value=resultado,
            ) as legado,
            patch(
                "ia_local.views.responder_consulta_web"
            ) as certificado,
            patch(
                ADAPTADOR,
                return_value=salida_html(),
            ) as adaptador,
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": PREGUNTA},
            )

        self.assertEqual(respuesta.status_code, 200)
        legado.assert_called_once_with(PREGUNTA)
        certificado.assert_not_called()
        adaptador.assert_called_once_with(resultado)

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
    )
    def test_02_html_modo_certificado(self):
        resultado = {
            "ok": True,
            "version": "IA-ARC003-B06-B01-v1",
            "estado": "respuesta_formateada",
            "respuesta": "Se encontraron 3 registros.",
            "tipo": "conteo",
            "total": 3,
            "ejecutado": True,
        }

        with (
            patch(
                "ia_local.views.responder_consulta_web",
                return_value=resultado,
            ) as certificado,
            patch(
                "ia_local.views.responder_consulta"
            ) as legado,
            patch(
                ADAPTADOR,
                return_value=salida_html(),
            ) as adaptador,
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": PREGUNTA},
            )

        self.assertEqual(respuesta.status_code, 200)
        certificado.assert_called_once()

        args = certificado.call_args.args

        self.assertEqual(len(args), 2)
        self.assertEqual(args[1], PREGUNTA)
        self.assertEqual(
            args[0].user.pk,
            self.usuario.pk,
        )

        legado.assert_not_called()
        adaptador.assert_called_once_with(resultado)

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
    )
    def test_03_rechazo_no_reintenta_final(self):
        rechazado = {
            "ok": False,
            "estado": "ejecucion_no_autorizada",
            "respuesta": "Consulta rechazada",
            "ejecutado": False,
            "total": None,
        }

        with (
            patch(
                "ia_local.views.responder_consulta_web",
                return_value=rechazado,
            ) as certificado,
            patch(
                "ia_local.views.responder_consulta"
            ) as legado,
            patch(
                ADAPTADOR,
                return_value=salida_html(),
            ) as adaptador,
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": PREGUNTA},
            )

        self.assertEqual(respuesta.status_code, 200)
        certificado.assert_called_once()
        legado.assert_not_called()
        adaptador.assert_called_once_with(rechazado)

    def test_04_get_no_ejecuta_consultas(self):
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

    def test_05_anonimo_no_ingresa(self):
        self.client.logout()

        with (
            patch(
                "ia_local.views.responder_consulta"
            ) as legado,
            patch(
                "ia_local.views.responder_consulta_web"
            ) as certificado,
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": PREGUNTA},
            )

        self.assertNotEqual(respuesta.status_code, 200)
        legado.assert_not_called()
        certificado.assert_not_called()

    def test_06_csrf_rechazado(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)

        with patch(
            "ia_local.views.responder_consulta_web"
        ) as certificado:
            respuesta = cliente.post(
                self.url,
                {"pregunta": PREGUNTA},
            )

        self.assertEqual(respuesta.status_code, 403)
        certificado.assert_not_called()

    def test_07_no_staff_no_ingresa(self):
        Usuario = get_user_model()

        normal = Usuario.objects.create_user(
            username="arc003_b03_html_no_staff",
            password="clave_solo_pruebas",
            is_staff=False,
            is_active=True,
        )

        self.client.force_login(normal)

        with (
            patch(
                "ia_local.views.responder_consulta"
            ) as legado,
            patch(
                "ia_local.views.responder_consulta_web"
            ) as certificado,
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": PREGUNTA},
            )

        self.assertNotEqual(respuesta.status_code, 200)
        legado.assert_not_called()
        certificado.assert_not_called()
