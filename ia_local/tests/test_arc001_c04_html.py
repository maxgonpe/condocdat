from unittest import TestCase
from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory

from ia_local.views import consulta_ia


class StaffPrueba:
    is_authenticated = True
    is_active = True
    is_staff = True


class TestARC001C04HTML(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def solicitud(self, metodo="post", pregunta="Consulta"):
        if metodo == "post":
            request = self.factory.post(
                "/ia/", {"pregunta": pregunta}
            )
        else:
            request = self.factory.get("/ia/")

        request.user = StaffPrueba()
        return request

    def test_01_post_usa_solo_final(self):
        with (
            patch("ia_local.views.responder_consulta") as final,
            patch("ia_local.views._ejecutar_consulta_ia") as host,
            patch("ia_local.views.render") as render,
        ):
            final.return_value = {
                "ok": True,
                "estado": "respuesta_formateada",
                "respuesta": "Cinco resultados",
                "registros": [],
                "ejecutado": True,
                "diagnostico": {},
            }
            render.return_value = HttpResponse("OK")

            respuesta = consulta_ia(
                self.solicitud(pregunta="¿Cuántas RDI hay?")
            )

            self.assertEqual(respuesta.status_code, 200)
            final.assert_called_once_with("¿Cuántas RDI hay?")
            host.assert_not_called()

            contexto = render.call_args.args[2]
            self.assertEqual(
                contexto["respuesta"], "Cinco resultados"
            )

    def test_02_rechazo_final_no_reintenta_host(self):
        with (
            patch("ia_local.views.responder_consulta") as final,
            patch("ia_local.views._ejecutar_consulta_ia") as host,
            patch("ia_local.views.render") as render,
        ):
            final.return_value = {
                "ok": False,
                "estado": "respuesta_no_ejecutable",
                "respuesta": "Certificación pendiente.",
                "ejecutado": False,
                "registros": [],
                "diagnostico": {},
            }
            render.return_value = HttpResponse("OK")

            consulta_ia(self.solicitud())

            final.assert_called_once()
            host.assert_not_called()

            contexto = render.call_args.args[2]
            self.assertEqual(
                contexto["respuesta"],
                "Certificación pendiente.",
            )

    def test_03_get_no_invoca_motores(self):
        with (
            patch("ia_local.views.responder_consulta") as final,
            patch("ia_local.views._ejecutar_consulta_ia") as host,
            patch("ia_local.views.render") as render,
        ):
            render.return_value = HttpResponse("OK")

            respuesta = consulta_ia(self.solicitud("get"))

            self.assertEqual(respuesta.status_code, 200)
            final.assert_not_called()
            host.assert_not_called()

    def test_04_pregunta_vacia_no_invoca_motores(self):
        with (
            patch("ia_local.views.responder_consulta") as final,
            patch("ia_local.views._ejecutar_consulta_ia") as host,
            patch("ia_local.views.render") as render,
        ):
            render.return_value = HttpResponse("OK")

            consulta_ia(self.solicitud(pregunta=""))

            final.assert_not_called()
            host.assert_not_called()
            contexto = render.call_args.args[2]
            self.assertEqual(
                contexto["error"], "Escribe una pregunta."
            )
