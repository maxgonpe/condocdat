"""
ARC003-B06-B03-B05-A

Bridge con politica FINAL009 y trazabilidad FINAL007 reales.

Solo se simula la frontera funcional E03.
La politica, el bridge y el ORM de auditoria son reales.
"""

from unittest.mock import patch

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings


PREGUNTA = (
    "¿Cuántos Documentos tienen status igual a DRAFT?"
)

SELECTOR = (
    "ia_local.services.final.entrada_web_compartida."
    "responder_consulta_web"
)

TRAZADOR = "ia_local.views_bridge.registrar_traza_consulta"


@override_settings(
    IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True
)
class TestARC003B05ABridgeReal(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="arc003_b05_bridge_real",
            password="clave_solo_pruebas",
            is_staff=True,
            is_active=True,
        )

    def setUp(self):
        self.client.force_login(self.usuario)
        self.url = "/ia/bridge/consultar/"
        self.Historial = apps.get_model(
            "ia_local",
            "IAHistorialConsulta",
        )

    def consultar(self, respuesta_e03):
        with patch(
            SELECTOR,
            return_value=respuesta_e03,
        ) as certificado:
            respuesta = self.client.post(
                self.url,
                {
                    "pregunta": PREGUNTA,
                    "diagnostico": "1",
                },
            )

        certificado.assert_called_once()
        self.assertEqual(
            certificado.call_args.args[1],
            PREGUNTA,
        )

        return respuesta

    def test_01_conteo_certificado_preservado(self):
        contrato = {
            "ok": True,
            "version": "IA-ARC003-B06-B01-v1",
            "estado": "respuesta_formateada",
            "pregunta": PREGUNTA,
            "respuesta": "Se encontraron 3 registros.",
            "tipo": "conteo",
            "modelo": "documents.Document",
            "total": 3,
            "registros": [],
            "campos": [],
            "ejecutado": True,
            "llm_invocado": False,
        }

        antes = self.Historial.objects.count()
        respuesta = self.consultar(contrato)

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()

        for campo in (
            "ok",
            "estado",
            "version",
            "total",
            "ejecutado",
            "respuesta",
        ):
            self.assertEqual(
                datos[campo],
                contrato[campo],
            )

        self.assertEqual(
            datos["clasificacion"],
            "resuelta_ejecutada",
        )
        self.assertEqual(
            datos["mensaje"],
            contrato["respuesta"],
        )
        self.assertEqual(datos["resultados"], [])

        self.assertEqual(
            datos["trazabilidad"]["registrado"],
            True,
        )
        self.assertEqual(
            self.Historial.objects.count(),
            antes + 1,
        )

        traza = self.Historial.objects.latest("pk")
        self.assertTrue(traza.ok)
        self.assertTrue(traza.ejecutado)
        self.assertEqual(traza.total, 3)
        self.assertEqual(
            traza.estado,
            "respuesta_formateada",
        )

    def test_02_rechazo_conservado_y_auditado(self):
        contrato = {
            "ok": False,
            "version": "IA-ARC003-B06-B01-v1",
            "estado": "ejecucion_no_autorizada",
            "pregunta": PREGUNTA,
            "respuesta": "Consulta rechazada.",
            "tipo": "resultado",
            "modelo": None,
            "total": None,
            "registros": [],
            "campos": [],
            "ejecutado": False,
            "llm_invocado": False,
        }

        antes = self.Historial.objects.count()
        respuesta = self.consultar(contrato)

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()

        self.assertFalse(datos["ok"])
        self.assertFalse(datos["ejecutado"])
        self.assertEqual(
            datos["estado"],
            contrato["estado"],
        )
        self.assertIsNone(datos["total"])
        self.assertEqual(
            datos["respuesta"],
            contrato["respuesta"],
        )
        self.assertEqual(
            datos["clasificacion"],
            "error_controlado",
        )

        self.assertEqual(
            self.Historial.objects.count(),
            antes + 1,
        )

        traza = self.Historial.objects.latest("pk")
        self.assertFalse(traza.ok)
        self.assertFalse(traza.ejecutado)
        self.assertEqual(
            traza.estado,
            contrato["estado"],
        )

    def test_03_cero_es_un_total_valido(self):
        contrato = {
            "ok": True,
            "version": "IA-ARC003-B06-B01-v1",
            "estado": "respuesta_formateada",
            "respuesta": "Se encontraron 0 registros.",
            "tipo": "conteo",
            "modelo": "documents.Document",
            "total": 0,
            "registros": [],
            "campos": [],
            "ejecutado": True,
            "llm_invocado": False,
        }

        respuesta = self.consultar(contrato)
        datos = respuesta.json()

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(datos["ok"])
        self.assertTrue(datos["ejecutado"])
        self.assertEqual(datos["total"], 0)

        traza = self.Historial.objects.latest("pk")
        self.assertEqual(traza.total, 0)
        self.assertTrue(traza.ejecutado)

    def test_04_error_de_auditoria_no_reejecuta(self):
        contrato = {
            "ok": False,
            "estado": "ejecucion_no_autorizada",
            "respuesta": "Consulta rechazada.",
            "total": None,
            "registros": [],
            "campos": [],
            "ejecutado": False,
            "llm_invocado": False,
        }

        with (
            patch(
                SELECTOR,
                return_value=contrato,
            ) as certificado,
            patch(
                TRAZADOR,
                side_effect=RuntimeError(
                    "Fallo simulado de auditoria"
                ),
            ) as registrar,
            patch(
                "ia_local.views_bridge.responder_consulta"
            ) as legado,
        ):
            respuesta = self.client.post(
                self.url,
                {
                    "pregunta": PREGUNTA,
                    "diagnostico": "1",
                },
            )

        self.assertEqual(respuesta.status_code, 200)

        datos = respuesta.json()

        self.assertFalse(datos["ok"])
        self.assertFalse(datos["ejecutado"])
        self.assertEqual(
            datos["estado"],
            "ejecucion_no_autorizada",
        )
        self.assertEqual(
            datos["trazabilidad"]["estado"],
            "error_registro_traza",
        )

        certificado.assert_called_once()
        registrar.assert_called_once()
        legado.assert_not_called()
