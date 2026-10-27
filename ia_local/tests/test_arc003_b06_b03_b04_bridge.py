"""
ARC003-B06-B03-B04-A.

Integracion HTTP del bridge con el selector certificado.
No ejecuta ORM de negocio ni LLM.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings


PREGUNTA = (
    "¿Cuántos Documentos tienen status igual a DRAFT?"
)

BRIDGE = "ia_local.views_bridge"
SELECTOR = (
    "ia_local.services.final.entrada_web_compartida"
)


class TestARC003B06B03B04Bridge(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="arc003_b04_bridge",
            password="clave_solo_pruebas",
            is_staff=True,
            is_active=True,
        )

    def setUp(self):
        self.client.force_login(self.usuario)
        self.url = "/ia/bridge/consultar/"

    @staticmethod
    def respuesta(ok=True):
        return {
            "ok": ok,
            "estado": (
                "respuesta_formateada"
                if ok else "ejecucion_no_autorizada"
            ),
            "respuesta": (
                "Se encontraron 3 registros."
                if ok else "Consulta rechazada."
            ),
            "ejecutado": bool(ok),
            "total": 3 if ok else None,
            "registros": [],
            "campos": [],
        }

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=False
    )
    def test_01_bridge_tradicional(self):
        resultado = self.respuesta()

        with (
            patch(
                BRIDGE + ".responder_consulta",
                return_value=resultado,
            ) as legado,
            patch(
                SELECTOR + ".responder_consulta_web"
            ) as certificado,
            patch(
                BRIDGE + ".aplicar_politica_respuesta",
                side_effect=lambda **kw: kw["respuesta"],
            ),
            patch(
                BRIDGE + ".registrar_traza_consulta",
                return_value={"ok": True},
            ),
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": PREGUNTA},
            )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.json()["estado"],
            "respuesta_formateada",
        )
        legado.assert_called_once_with(PREGUNTA)
        certificado.assert_not_called()

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
    )
    def test_02_bridge_certificado(self):
        resultado = self.respuesta()

        with (
            patch(
                BRIDGE + ".responder_consulta"
            ) as legado,
            patch(
                SELECTOR + ".responder_consulta_web",
                return_value=resultado,
            ) as certificado,
            patch(
                BRIDGE + ".aplicar_politica_respuesta",
                side_effect=lambda **kw: kw["respuesta"],
            ),
            patch(
                BRIDGE + ".registrar_traza_consulta",
                return_value={"ok": True},
            ),
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": PREGUNTA},
            )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.json()["estado"],
            "respuesta_formateada",
        )

        certificado.assert_called_once()
        legado.assert_not_called()

        argumentos = certificado.call_args.args
        self.assertEqual(argumentos[1], PREGUNTA)
        self.assertEqual(
            argumentos[0].user.pk,
            self.usuario.pk,
        )

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
    )
    def test_03_rechazo_sin_fallback(self):
        rechazado = self.respuesta(ok=False)

        with (
            patch(
                BRIDGE + ".responder_consulta"
            ) as legado,
            patch(
                SELECTOR + ".responder_consulta_web",
                return_value=rechazado,
            ) as certificado,
            patch(
                BRIDGE + ".aplicar_politica_respuesta",
                side_effect=lambda **kw: kw["respuesta"],
            ),
            patch(
                BRIDGE + ".registrar_traza_consulta",
                return_value={"ok": True},
            ),
        ):
            respuesta = self.client.post(
                self.url,
                {"pregunta": PREGUNTA},
            )

        self.assertEqual(respuesta.status_code, 200)

        datos = respuesta.json()

        self.assertFalse(datos["ok"])
        self.assertFalse(datos["ejecutado"])
        self.assertIsNone(datos["total"])

        certificado.assert_called_once()
        legado.assert_not_called()
