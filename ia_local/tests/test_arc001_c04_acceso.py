from unittest import TestCase

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.http import HttpResponse

from ia_local.views_desambiguacion import (
    consultar_con_aclaracion,
)


class UsuarioPrueba:
    is_authenticated = True
    is_active = True
    is_staff = False


class TestARC001C04Acceso(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_01_anonimo_rechazado(self):
        request = self.factory.post(
            "/ia/consultar-contextual/",
            {"pregunta": "Consulta de prueba"},
        )
        request.user = AnonymousUser()

        respuesta = consultar_con_aclaracion(request)

        self.assertEqual(respuesta.status_code, 302)

    def test_02_no_staff_rechazado(self):
        request = self.factory.post(
            "/ia/consultar-contextual/",
            {"pregunta": "Consulta de prueba"},
        )
        request.user = UsuarioPrueba()

        respuesta = consultar_con_aclaracion(request)

        self.assertEqual(respuesta.status_code, 302)

    def test_03_get_no_procesa(self):
        request = self.factory.get(
            "/ia/consultar-contextual/"
        )
        request.user = type(
            "StaffPrueba",
            (),
            {
                "is_authenticated": True,
                "is_active": True,
                "is_staff": True,
            },
        )()

        respuesta = consultar_con_aclaracion(request)

        self.assertEqual(respuesta.status_code, 405)
