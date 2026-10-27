from types import SimpleNamespace
from unittest.mock import patch, sentinel

from django.test import SimpleTestCase

from ia_local.services.final.entrada_http_certificada import (
    responder_consulta_http,
)


MODULO = (
    "ia_local.services.final.entrada_http_certificada"
)

PREGUNTA = (
    "¿Cuántos Documentos tienen status igual a DRAFT?"
)


class TestARC003B06EntradaHTTP(SimpleTestCase):

    def setUp(self):
        self.request = SimpleNamespace(
            user=SimpleNamespace(
                is_authenticated=True,
                is_active=True,
            ),
            session=sentinel.session,
        )

    def test_01_pregunta_vacia(self):
        with patch(
            MODULO + ".ejecutar_conteo_filtrado_certificado"
        ) as despacho:
            resultado = responder_consulta_http(
                self.request, ""
            )

        self.assertFalse(resultado["ok"])
        despacho.assert_not_called()

    def test_02_gramatica_no_admitida(self):
        with patch(
            MODULO + ".ejecutar_conteo_filtrado_certificado"
        ) as despacho:
            resultado = responder_consulta_http(
                self.request,
                "Dame todos los Documentos",
            )

        self.assertEqual(
            resultado["estado"],
            "gramatica_no_certificable",
        )
        despacho.assert_not_called()

    def test_03_usuario_no_autenticado(self):
        request = SimpleNamespace(
            user=SimpleNamespace(
                is_authenticated=False,
                is_active=True,
            ),
            session=sentinel.session,
        )

        with patch(
            MODULO + ".ejecutar_conteo_filtrado_certificado"
        ) as despacho:
            resultado = responder_consulta_http(
                request, PREGUNTA
            )

        self.assertFalse(resultado["ok"])
        despacho.assert_not_called()

    def test_04_entidad_ambigua(self):
        with (
            patch(
                MODULO + ".buscar_modelo_datos",
                return_value=[
                    {"label": "documents.Document"},
                    {"label": "documents.Project"},
                ],
            ),
            patch(
                MODULO + ".crear_expediente"
            ) as crear,
        ):
            resultado = responder_consulta_http(
                self.request, PREGUNTA
            )

        self.assertFalse(resultado["ok"])
        crear.assert_not_called()

    def test_05_recorrido_certificado(self):
        coleccion = {
            "ok": True,
            "ejecutable": False,
        }

        with (
            patch(
                MODULO + ".buscar_modelo_datos",
                return_value=[
                    {"label": "documents.Document"}
                ],
            ),
            patch(
                MODULO + ".preparar_coleccion_restricciones",
                return_value=coleccion,
            ) as normalizar,
            patch(
                MODULO + ".crear_expediente",
                return_value={
                    "ok": True,
                    "identificador": "expediente-servidor",
                    "version": 1,
                },
            ) as crear,
            patch(
                MODULO + ".ejecutar_conteo_filtrado_certificado",
                return_value={
                    "ok": True,
                    "estado": "conteo_filtrado_ejecutado",
                    "modelo": "documents.Document",
                    "total": 3,
                    "ejecutado": True,
                },
            ) as ejecutar,
        ):
            resultado = responder_consulta_http(
                self.request, PREGUNTA
            )

        self.assertTrue(resultado["ok"], resultado)
        self.assertEqual(resultado["total"], 3)
        self.assertTrue(resultado["ejecutado"])

        restricciones = normalizar.call_args.args[0][
            "restricciones"
        ]
        self.assertEqual(
            restricciones[0]["evidencia_textual"],
            "status igual a DRAFT",
        )

        crear.assert_called_once_with(
            self.request,
            coleccion,
            "documents.Document",
        )
        ejecutar.assert_called_once_with(
            self.request,
            "expediente-servidor",
            1,
        )

    def test_06_ejecucion_rechazada_sin_fallback(self):
        with (
            patch(
                MODULO + ".buscar_modelo_datos",
                return_value=[
                    {"label": "documents.Document"}
                ],
            ),
            patch(
                MODULO + ".preparar_coleccion_restricciones",
                return_value={
                    "ok": True,
                    "ejecutable": False,
                },
            ),
            patch(
                MODULO + ".crear_expediente",
                return_value={
                    "ok": True,
                    "identificador": "expediente-servidor",
                    "version": 1,
                },
            ),
            patch(
                MODULO + ".ejecutar_conteo_filtrado_certificado",
                return_value={
                    "ok": False,
                    "estado": "lectura_no_autorizada",
                    "ejecutado": False,
                },
            ) as ejecutar,
        ):
            resultado = responder_consulta_http(
                self.request, PREGUNTA
            )

        self.assertFalse(resultado["ok"])
        self.assertFalse(resultado["ejecutado"])
        self.assertIsNone(resultado["total"])
        ejecutar.assert_called_once()
