import json
from unittest import TestCase
from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory

from ia_local import views, views_bridge, views_desambiguacion


class UsuarioStaff:
    is_authenticated = True
    is_active = True
    is_staff = True
    pk = 123

    def get_username(self):
        return "usuario_arc001"


class SesionPrueba(dict):
    session_key = "sesion_arc001_c04"
    modified = False


class TestARC001C04Paridad(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.usuario = UsuarioStaff()

    def solicitud(self, ruta, datos=None):
        request = self.factory.post(
            ruta,
            datos or {"pregunta": "¿Cuántos documentos hay?"},
        )
        request.user = self.usuario
        request.session = SesionPrueba()
        return request

    def resultado_final(self):
        return {
            "ok": False,
            "estado": "respuesta_no_ejecutable",
            "respuesta": "Certificación pendiente.",
            "ejecutado": False,
            "llm_invocado": True,
            "registros": [],
            "campos": [],
            "diagnostico": {},
        }

    def test_01_html_usa_final(self):
        with (
            patch.object(views, "responder_consulta") as final,
            patch.object(views, "_ejecutar_consulta_ia") as host,
            patch.object(views, "render") as render,
        ):
            final.return_value = self.resultado_final()
            render.return_value = HttpResponse("OK")

            respuesta = views.consulta_ia(
                self.solicitud("/ia/")
            )

            self.assertEqual(respuesta.status_code, 200)
            final.assert_called_once()
            host.assert_not_called()

    def test_02_json_usa_final(self):
        with patch.object(
            views, "responder_consulta"
        ) as final:
            final.return_value = self.resultado_final()

            respuesta = views.consulta_ia_json(
                self.solicitud("/ia/consultar/")
            )

            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(
                json.loads(respuesta.content)["estado"],
                "respuesta_no_ejecutable",
            )
            final.assert_called_once()

    def test_03_diagnostico_usa_final(self):
        with (
            patch.object(views, "responder_consulta") as final,
            patch.object(views, "render") as render,
        ):
            final.return_value = self.resultado_final()
            render.return_value = HttpResponse("OK")

            respuesta = views.diagnostico_ia(
                self.solicitud("/ia/diagnostico/")
            )

            self.assertEqual(respuesta.status_code, 200)
            final.assert_called_once()

            contexto = render.call_args.args[2]
            self.assertEqual(
                contexto["resultado_final"]["estado"],
                "respuesta_no_ejecutable",
            )

    def test_04_aclaracion_legitima(self):
        pregunta = "¿Cuántos elementos hay?"

        primera = self.solicitud(
            "/ia/consultar-contextual/",
            {"pregunta": pregunta},
        )

        with (
            patch.object(
                views_desambiguacion,
                "_identidad",
                return_value="identidad_prueba",
            ),
            patch.object(
                views_desambiguacion,
                "preparar_aclaracion",
            ) as preparar,
            patch.object(
                views_desambiguacion,
                "verificar_eleccion",
            ) as verificar,
            patch.object(
                views_desambiguacion,
                "responder_consulta",
            ) as final,
        ):
            preparar.return_value = {
                "estado": "requiere_aclaracion",
                "opciones": [
                    {"id": "opcion_1", "etiqueta": "Entidad A"},
                    {"id": "opcion_2", "etiqueta": "Entidad B"},
                ],
            }

            respuesta_1 = (
                views_desambiguacion.consultar_con_aclaracion(
                    primera
                )
            )

            self.assertEqual(respuesta_1.status_code, 200)

            datos_1 = json.loads(respuesta_1.content)
            self.assertEqual(
                datos_1["estado"],
                "requiere_aclaracion",
            )

            token = datos_1["token_aclaracion"]

            segunda = self.solicitud(
                "/ia/consultar-contextual/",
                {
                    "pregunta": pregunta,
                    "opcion_id": "opcion_1",
                    "token_aclaracion": token,
                },
            )

            segunda.session = primera.session

            verificar.return_value = {
                "ok": True,
                "estado": "eleccion_certificada",
            }

            final.return_value = self.resultado_final()

            respuesta_2 = (
                views_desambiguacion.consultar_con_aclaracion(
                    segunda
                )
            )

            self.assertEqual(respuesta_2.status_code, 200)
            self.assertTrue(
                json.loads(respuesta_2.content)["aclaracion_completada"]
            )

            verificar.assert_called_once_with(
                pregunta, "opcion_1"
            )

            final.assert_called_once_with(
                pregunta,
                entidad_aclarada="opcion_1",
            )

    def test_05_aclaracion_token_invalido(self):
        pregunta = "¿Cuántos elementos hay?"

        request = self.solicitud(
            "/ia/consultar-contextual/",
            {
                "pregunta": pregunta,
                "opcion_id": "opcion_1",
                "token_aclaracion": "token_invalido",
            },
        )

        request.session[
            views_desambiguacion.SESSION_KEY
        ] = {
            "pregunta": pregunta,
            "token": "token_correcto",
            "identidad": "identidad_prueba",
            "creado": __import__("time").time(),
        }

        with (
            patch.object(
                views_desambiguacion,
                "_identidad",
                return_value="identidad_prueba",
            ),
            patch.object(
                views_desambiguacion,
                "verificar_eleccion",
            ) as verificar,
            patch.object(
                views_desambiguacion,
                "responder_consulta",
            ) as final,
        ):
            respuesta = (
                views_desambiguacion.consultar_con_aclaracion(
                    request
                )
            )

            self.assertEqual(
                json.loads(respuesta.content)["estado"],
                "aclaracion_token_invalido",
            )

            self.assertNotIn(
                views_desambiguacion.SESSION_KEY,
                request.session,
            )

            verificar.assert_not_called()
            final.assert_not_called()
