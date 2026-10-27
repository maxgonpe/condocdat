"""
ARC003-B06-B03-B04-B.

Proteccion de desambiguacion contextual en modo E03.
No realiza consultas de negocio ni invoca el LLM.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.test import TestCase, override_settings

from ia_local.views_desambiguacion import SESSION_KEY


MODULO = "ia_local.views_desambiguacion"

PREGUNTA = (
    "¿Cuántos Documentos tienen status igual a DRAFT?"
)


class TestARC003B06B03B04Contextual(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="arc003_b04_contextual",
            password="clave_solo_pruebas",
            is_staff=True,
            is_active=True,
        )

    def setUp(self):
        self.client.force_login(self.usuario)
        self.url = "/ia/consultar-contextual/"

    def guardar_pendiente(self):
        sesion = self.client.session
        sesion[SESSION_KEY] = {
            "pregunta": PREGUNTA,
            "token": "token_prueba",
            "identidad": "user:" + str(self.usuario.pk),
            "creado": 1,
        }
        sesion.save()

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
    )
    def test_01_continuacion_rechazada_sin_final(self):
        self.guardar_pendiente()

        with (
            patch(MODULO + ".responder_consulta") as legado,
            patch(MODULO + ".verificar_eleccion") as verificar,
            patch(MODULO + ".preparar_aclaracion") as preparar,
            patch(MODULO + ".consulta_ia_json") as json_view,
        ):
            respuesta = self.client.post(
                self.url,
                {
                    "pregunta": PREGUNTA,
                    "opcion_id": "documents.Document",
                    "token_aclaracion": "token_prueba",
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
        preparar.assert_not_called()
        json_view.assert_not_called()

        self.assertNotIn(
            SESSION_KEY,
            self.client.session,
        )

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
    )
    def test_02_pregunta_normal_delega_a_json(self):
        esperado = {
            "ok": False,
            "estado": "gramatica_no_certificable",
            "ejecutado": False,
        }

        with (
            patch(
                MODULO + ".consulta_ia_json",
                return_value=JsonResponse(esperado),
            ) as json_view,
            patch(MODULO + ".preparar_aclaracion") as preparar,
            patch(MODULO + ".responder_consulta") as legado,
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": PREGUNTA},
            )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), esperado)

        json_view.assert_called_once()
        legado.assert_not_called()
        preparar.assert_not_called()

        solicitud = json_view.call_args.args[0]
        self.assertEqual(solicitud.user.pk, self.usuario.pk)

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
    )
    def test_03_pregunta_certificada_invalida(self):
        with (
            patch(MODULO + ".consulta_ia_json") as json_view,
            patch(MODULO + ".preparar_aclaracion") as preparar,
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": ""},
            )

        self.assertEqual(
            respuesta.json()["estado"],
            "pregunta_vacia",
        )
        json_view.assert_not_called()
        preparar.assert_not_called()

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=False
    )
    def test_04_legado_sigue_preparando_aclaracion(self):
        aclaracion = {
            "ok": True,
            "estado": "sin_aclaracion",
        }

        with (
            patch(
                MODULO + ".preparar_aclaracion",
                return_value=aclaracion,
            ) as preparar,
            patch(
                MODULO + ".consulta_ia_json",
                return_value=JsonResponse({"ok": True}),
            ) as json_view,
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": PREGUNTA},
            )

        self.assertEqual(respuesta.status_code, 200)
        preparar.assert_called_once_with(PREGUNTA)
        json_view.assert_called_once()

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
    )
    def test_05_no_staff_no_ingresa(self):
        normal = get_user_model().objects.create_user(
            username="arc003_b04_contextual_normal",
            password="clave_solo_pruebas",
            is_staff=False,
            is_active=True,
        )
        self.client.force_login(normal)

        with (
            patch(MODULO + ".consulta_ia_json") as json_view,
            patch(MODULO + ".responder_consulta") as legado,
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": PREGUNTA},
            )

        self.assertNotEqual(respuesta.status_code, 200)
        json_view.assert_not_called()
        legado.assert_not_called()
