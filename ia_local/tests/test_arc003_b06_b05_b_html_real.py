"""
ARC003-B06-B03-B05-B

Verifica la vista HTML con adaptar_final_html real.
Solo se simula el resultado funcional de E03.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from ia_local.services.final.adaptador_html_arc001 import (
    adaptar_final_html,
)


PREGUNTA = (
    "¿Cuántos Documentos tienen status igual a DRAFT?"
)


@override_settings(
    IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
)
class TestARC003B05BHTMLReal(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="arc003_b05_html_real",
            password="clave_solo_pruebas",
            is_staff=True,
            is_active=True,
        )

    def setUp(self):
        self.client.force_login(self.usuario)

    def contrato(self, *, total=None, ejecutado=False):
        correcto = ejecutado is True

        return {
            "ok": correcto,
            "version": "IA-ARC003-B06-B01-v1",
            "estado": (
                "respuesta_formateada"
                if correcto
                else "ejecucion_no_autorizada"
            ),
            "pregunta": PREGUNTA,
            "respuesta": (
                f"Se encontraron {total} registros."
                if correcto
                else "Consulta rechazada."
            ),
            "tipo": "conteo" if correcto else "resultado",
            "modelo": (
                "documents.Document" if correcto else None
            ),
            "total": total,
            "registros": [],
            "campos": [],
            "ejecutado": correcto,
            "llm_invocado": False,
        }

    def consultar(self, contrato):
        with (
            patch(
                "ia_local.views.responder_consulta_web",
                return_value=contrato,
            ) as certificado,
            patch(
                "ia_local.views.responder_consulta"
            ) as legado,
        ):
            respuesta = self.client.post(
                "/ia/",
                {"pregunta": PREGUNTA},
            )

        self.assertEqual(respuesta.status_code, 200)
        certificado.assert_called_once()
        legado.assert_not_called()

        self.assertEqual(
            certificado.call_args.args[1],
            PREGUNTA,
        )
        self.assertEqual(
            certificado.call_args.args[0].user.pk,
            self.usuario.pk,
        )

        return respuesta

    def test_01_conteo_positivo(self):
        contrato = self.contrato(
            total=3,
            ejecutado=True,
        )

        respuesta = self.consultar(contrato)
        contexto = respuesta.context

        self.assertEqual(
            contexto["respuesta_estructurada"],
            contrato,
        )
        self.assertEqual(
            contexto["respuesta"],
            "Se encontraron 3 registros.",
        )
        self.assertEqual(
            contexto["respuesta_estructurada"]["total"],
            3,
        )
        self.assertEqual(contexto["error"], "")

        adaptado = adaptar_final_html(contrato)
        self.assertTrue(adaptado["ok"])
        self.assertTrue(adaptado["ejecutado"])

    def test_02_total_cero_sigue_ejecutado(self):
        contrato = self.contrato(
            total=0,
            ejecutado=True,
        )

        respuesta = self.consultar(contrato)

        self.assertEqual(
            respuesta.context["respuesta_estructurada"]["total"],
            0,
        )
        self.assertEqual(
            respuesta.context["respuesta"],
            "Se encontraron 0 registros.",
        )

        adaptado = adaptar_final_html(contrato)
        self.assertTrue(adaptado["ok"])
        self.assertTrue(adaptado["ejecutado"])

    def test_03_rechazo_preservado(self):
        contrato = self.contrato(
            total=None,
            ejecutado=False,
        )

        respuesta = self.consultar(contrato)
        estructura = respuesta.context["respuesta_estructurada"]

        self.assertFalse(estructura["ok"])
        self.assertFalse(estructura["ejecutado"])
        self.assertIsNone(estructura["total"])
        self.assertEqual(
            estructura["estado"],
            "ejecucion_no_autorizada",
        )
        self.assertEqual(
            respuesta.context["respuesta"],
            "Consulta rechazada.",
        )

        adaptado = adaptar_final_html(contrato)
        self.assertFalse(adaptado["ok"])
        self.assertFalse(adaptado["ejecutado"])

    def test_04_contrato_invalido_rechazado(self):
        for invalido in (None, "", [], 123):
            with self.subTest(valor=invalido):
                with self.assertRaises(ValueError):
                    adaptar_final_html(invalido)
