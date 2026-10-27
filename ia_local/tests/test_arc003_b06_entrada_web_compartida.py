"""
ARC003-B06-B03-A — Pruebas del selector web.

Sin base de datos. Verifica seleccion de circuito,
compatibilidad y ausencia de fallback.
"""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from ia_local.services.final.entrada_web_compartida import (
    responder_consulta_web,
)


MODULO = (
    "ia_local.services.final.entrada_web_compartida"
)

PREGUNTA = (
    "¿Cuántos Documentos tienen status igual a DRAFT?"
)


class TestARC003B06EntradaWebCompartida(SimpleTestCase):

    def setUp(self):
        self.request = SimpleNamespace(
            user=SimpleNamespace(
                is_authenticated=True,
                is_active=True,
            )
        )

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=False
    )
    def test_01_modo_legado_conservado(self):
        esperado = {
            "ok": True,
            "estado": "respuesta_formateada",
        }

        with (
            patch(
                MODULO + ".responder_consulta",
                return_value=esperado,
            ) as legado,
            patch(
                MODULO + ".responder_consulta_http"
            ) as certificado,
        ):
            resultado = responder_consulta_web(
                self.request,
                PREGUNTA,
            )

        self.assertIs(resultado, esperado)
        legado.assert_called_once_with(PREGUNTA)
        certificado.assert_not_called()

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
    )
    def test_02_modo_certificado(self):
        esperado = {
            "ok": True,
            "estado": "respuesta_formateada",
            "total": 3,
        }

        with (
            patch(
                MODULO + ".responder_consulta"
            ) as legado,
            patch(
                MODULO + ".responder_consulta_http",
                return_value=esperado,
            ) as certificado,
        ):
            resultado = responder_consulta_web(
                self.request,
                PREGUNTA,
            )

        self.assertIs(resultado, esperado)

        certificado.assert_called_once_with(
            self.request,
            PREGUNTA,
        )
        legado.assert_not_called()

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
    )
    def test_03_rechazo_sin_fallback(self):
        rechazado = {
            "ok": False,
            "estado": "lectura_no_autorizada",
            "ejecutado": False,
        }

        with (
            patch(
                MODULO + ".responder_consulta"
            ) as legado,
            patch(
                MODULO + ".responder_consulta_http",
                return_value=rechazado,
            ) as certificado,
        ):
            resultado = responder_consulta_web(
                self.request,
                PREGUNTA,
            )

        self.assertIs(resultado, rechazado)
        certificado.assert_called_once()
        legado.assert_not_called()

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=False
    )
    def test_04_aclaracion_legada_conservada(self):
        esperado = {"ok": True}

        with (
            patch(
                MODULO + ".responder_consulta",
                return_value=esperado,
            ) as legado,
            patch(
                MODULO + ".responder_consulta_http"
            ) as certificado,
        ):
            resultado = responder_consulta_web(
                self.request,
                PREGUNTA,
                entidad_aclarada="documents.Document",
            )

        self.assertIs(resultado, esperado)

        legado.assert_called_once_with(
            PREGUNTA,
            entidad_aclarada="documents.Document",
        )
        certificado.assert_not_called()

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
    )
    def test_05_aclaracion_certificada_bloqueada(self):
        with (
            patch(
                MODULO + ".responder_consulta"
            ) as legado,
            patch(
                MODULO + ".responder_consulta_http"
            ) as certificado,
        ):
            resultado = responder_consulta_web(
                self.request,
                PREGUNTA,
                entidad_aclarada="documents.Document",
            )

        self.assertFalse(resultado["ok"])
        self.assertFalse(resultado["ejecutado"])
        self.assertEqual(
            resultado["estado"],
            "aclaracion_no_certificada_en_http",
        )

        legado.assert_not_called()
        certificado.assert_not_called()

    def test_06_configuracion_ausente_desactivada(self):
        # La ausencia del setting debe conservar FINAL.
        with (
            patch(
                MODULO + ".settings"
            ) as configuracion,
            patch(
                MODULO + ".responder_consulta",
                return_value={"ok": True},
            ) as legado,
            patch(
                MODULO + ".responder_consulta_http"
            ) as certificado,
        ):
            configuracion.configure_mock(
                **{
                    "IA_LOCAL_HTTP_CERTIFICADO_HABILITADO":
                        False
                }
            )

            resultado = responder_consulta_web(
                self.request,
                PREGUNTA,
            )

        self.assertTrue(resultado["ok"])
        legado.assert_called_once()
        certificado.assert_not_called()

    @override_settings(
        IA_LOCAL_HTTP_CERTIFICADO_HABILITADO="true"
    )
    def test_07_configuracion_no_booleana_no_activa(self):
        with (
            patch(
                MODULO + ".responder_consulta",
                return_value={"ok": True},
            ) as legado,
            patch(
                MODULO + ".responder_consulta_http"
            ) as certificado,
        ):
            resultado = responder_consulta_web(
                self.request,
                PREGUNTA,
            )

        self.assertTrue(resultado["ok"])
        legado.assert_called_once()
        certificado.assert_not_called()
