"""
ARC003-B06-B03-B05-C
Integracion HTTP completa con PostgreSQL.

Sin mocks del certificador, HOST, expediente o ejecutor E03.
Solo se vigila que FINAL tradicional no sea invocado.
"""

from unittest.mock import patch

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings


PREGUNTA = (
    "¿Cuántos Documentos tienen status igual a DRAFT?"
)

POLITICA = (
    "documents.ia_politica_lectura."
    "autorizar_lectura_documentos"
)


@override_settings(
    IA_LOCAL_HTTP_CERTIFICADO_HABILITADO=True,
    IA_LOCAL_POLITICA_LECTURA=POLITICA,
    IA_LOCAL_DOCUMENTOS_CONTEO_GLOBAL_HABILITADO=True,
)
class TestARC003B05CHTTPPostgreSQL(TestCase):

    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()

        cls.autorizado = Usuario.objects.create_user(
            username="arc003_b05c_autorizado",
            password="clave_solo_pruebas",
            is_staff=True,
            is_active=True,
        )

        cls.sin_permiso = Usuario.objects.create_user(
            username="arc003_b05c_sin_permiso",
            password="clave_solo_pruebas",
            is_staff=True,
            is_active=True,
        )

        permiso = Permission.objects.get(
            content_type__app_label="documents",
            codename="view_document",
        )

        cls.autorizado.user_permissions.add(permiso)

    def setUp(self):
        self.url = "/ia/consultar/"

        self.Documento = apps.get_model(
            "documents", "Document"
        )

        self.Expediente = apps.get_model(
            "ia_local", "IAExpedienteConsulta"
        )

        self.client.force_login(self.autorizado)

    def consultar(self, pregunta=PREGUNTA):
        with patch(
            "ia_local.views.responder_consulta"
        ) as legado:
            respuesta = self.client.post(
                self.url,
                {"pregunta": pregunta},
            )

        legado.assert_not_called()

        self.assertEqual(
            respuesta.status_code, 200
        )

        return respuesta.json()

    def test_01_conteo_real_autorizado(self):
        esperado = self.Documento.objects.filter(
            status="DRAFT"
        ).count()

        self.assertEqual(
            self.Expediente.objects.count(), 0
        )

        datos = self.consultar()

        self.assertTrue(datos["ok"], datos)
        self.assertTrue(datos["ejecutado"], datos)
        self.assertEqual(
            datos["estado"], "respuesta_formateada"
        )
        self.assertEqual(
            datos["modelo"], "documents.Document"
        )
        self.assertEqual(datos["total"], esperado)
        self.assertFalse(datos["llm_invocado"])

        self.assertEqual(
            self.Expediente.objects.count(), 1
        )

        expediente = self.Expediente.objects.get()

        self.assertEqual(
            expediente.estado, "COMPLETADO"
        )
        self.assertEqual(expediente.version, 2)
        self.assertEqual(
            expediente.modelo_contexto,
            "documents.Document",
        )
        self.assertEqual(
            expediente.pregunta_original, PREGUNTA
        )

    def test_02_usuario_sin_permiso_rechazado(self):
        self.client.force_login(self.sin_permiso)

        datos = self.consultar()

        self.assertFalse(datos["ok"], datos)
        self.assertFalse(datos["ejecutado"], datos)
        self.assertIsNone(datos["total"])
        self.assertEqual(
            datos["estado"],
            "ejecucion_no_autorizada",
        )

        self.assertFalse(
            self.Expediente.objects.filter(
                estado="COMPLETADO"
            ).exists()
        )

    @override_settings(
        IA_LOCAL_DOCUMENTOS_CONTEO_GLOBAL_HABILITADO=False
    )
    def test_03_conteo_global_desactivado(self):
        datos = self.consultar()

        self.assertFalse(datos["ok"], datos)
        self.assertFalse(datos["ejecutado"], datos)
        self.assertIsNone(datos["total"])
        self.assertEqual(
            datos["estado"],
            "ejecucion_no_autorizada",
        )

        self.assertFalse(
            self.Expediente.objects.filter(
                estado="COMPLETADO"
            ).exists()
        )

    def test_04_gramatica_invalida(self):
        datos = self.consultar(
            "Elimina todos los Documentos"
        )

        self.assertFalse(datos["ok"], datos)
        self.assertFalse(datos["ejecutado"], datos)
        self.assertEqual(
            datos["estado"],
            "gramatica_no_certificable",
        )
        self.assertEqual(
            self.Expediente.objects.count(), 0
        )

    @override_settings(
        IA_LOCAL_POLITICA_LECTURA=None
    )
    def test_05_sin_politica_host(self):
        datos = self.consultar()

        self.assertFalse(datos["ok"], datos)
        self.assertFalse(datos["ejecutado"], datos)
        self.assertIsNone(datos["total"])
        self.assertEqual(
            datos["estado"],
            "ejecucion_no_autorizada",
        )

        self.assertFalse(
            self.Expediente.objects.filter(
                estado="COMPLETADO"
            ).exists()
        )
