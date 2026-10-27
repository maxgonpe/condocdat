"""
ARC003-B06-B02 — Integracion real del adaptador.

Prueba el circuito sin Mock, usando la base temporal
de Django y autorizacion explicita del anfitrion.
"""

from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.backends.db import SessionStore
from django.test import TestCase, override_settings

from ia_local.models import IAExpedienteConsulta
from ia_local.services.final.entrada_http_certificada import (
    responder_consulta_http,
)


PREGUNTA = (
    "¿Cuántos Documentos tienen status igual a DRAFT?"
)

POLITICA = (
    "documents.ia_politica_lectura."
    "autorizar_lectura_documentos"
)


@override_settings(
    IA_LOCAL_POLITICA_LECTURA=POLITICA,
    IA_LOCAL_DOCUMENTOS_CONTEO_GLOBAL_HABILITADO=True,
)
class TestARC003B06EntradaPersistente(TestCase):

    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()

        cls.usuario = Usuario.objects.create_user(
            username="arc003_b06_usuario"
        )

        tipo = ContentType.objects.get(
            app_label="documents",
            model="document",
        )

        permiso = Permission.objects.get(
            content_type=tipo,
            codename="view_document",
        )

        cls.usuario.user_permissions.add(permiso)

    def setUp(self):
        sesion = SessionStore()
        sesion.create()

        self.request = SimpleNamespace(
            user=self.usuario,
            session=sesion,
        )

    def test_01_circuito_real_completo(self):
        from documents.models import Document

        esperado = Document.objects.filter(
            status="DRAFT"
        ).count()

        resultado = responder_consulta_http(
            self.request,
            PREGUNTA,
        )

        self.assertTrue(resultado["ok"], resultado)
        self.assertTrue(resultado["ejecutado"])
        self.assertEqual(resultado["total"], esperado)
        self.assertEqual(
            resultado["estado"],
            "respuesta_formateada",
        )

        expedientes = IAExpedienteConsulta.objects.filter(
            pregunta_original=PREGUNTA,
            usuario_id=str(self.usuario.pk),
        )

        self.assertEqual(expedientes.count(), 1)

        expediente = expedientes.get()

        self.assertEqual(
            expediente.estado,
            "COMPLETADO",
        )

        self.assertEqual(expediente.version, 2)

    @override_settings(
        IA_LOCAL_DOCUMENTOS_CONTEO_GLOBAL_HABILITADO=False
    )
    def test_02_sin_autorizacion_global(self):

        resultado = responder_consulta_http(
            self.request,
            PREGUNTA,
        )

        self.assertFalse(resultado["ok"])
        self.assertFalse(resultado["ejecutado"])
        self.assertIsNone(resultado["total"])

    def test_03_pregunta_fuera_de_gramatica(self):

        resultado = responder_consulta_http(
            self.request,
            "Muestra todos los Documentos",
        )

        self.assertFalse(resultado["ok"])
        self.assertEqual(
            resultado["estado"],
            "gramatica_no_certificable",
        )

        self.assertFalse(
            IAExpedienteConsulta.objects.exists()
        )
