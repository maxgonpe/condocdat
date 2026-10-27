"""
ARC003-B05-E02
Integracion de expediente persistente.

Utiliza la base de datos temporal de pruebas Django.
No consulta registros de negocio mediante ia_local.
No habilita endpoints ni ejecucion HOST.
"""

from datetime import timedelta
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.backends.db import SessionStore
from django.test import TestCase, override_settings
from django.utils import timezone

from ia_local.models import IAExpedienteConsulta

from ia_local.services.host.expediente_consulta import (
    crear_expediente,
)
from ia_local.services.llm.trazabilidad_compuesta import (
    preparar_coleccion_restricciones,
)
from ia_local.services.final.preparacion_conteo_filtrado import (
    preparar_conteo_filtrado_certificado,
)


PREGUNTA = (
    "¿Cuántos Documentos tienen status igual a ACTIVO?"
)

RUTA_POLITICA = (
    "documents.ia_politica_lectura."
    "autorizar_lectura_documentos"
)


@override_settings(
    IA_LOCAL_POLITICA_LECTURA=RUTA_POLITICA,
    IA_LOCAL_DOCUMENTOS_CONTEO_GLOBAL_HABILITADO=True,
)
class TestARC003B05ExpedientePersistente(TestCase):

    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()

        cls.usuario = Usuario.objects.create_user(
            username="arc003_e02_usuario",
            password="prueba_no_productiva",
        )
        cls.otro_usuario = Usuario.objects.create_user(
            username="arc003_e02_otro",
            password="prueba_no_productiva",
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

        coleccion = preparar_coleccion_restricciones({
            "ok": True,
            "estado": "consolidacion_diagnostica",
            "pregunta": PREGUNTA,
            "restricciones": [{
                "tipo": "filtro",
                "evidencia_textual":
                    "status igual a ACTIVO",
                "origen": "gramatica_determinista_b04",
            }],
            "ejecutable": False,
            "ejecutado": False,
        })

        self.assertTrue(coleccion["ok"])

        creado = crear_expediente(
            self.request,
            coleccion,
            "documents.Document",
        )

        self.assertTrue(creado["ok"], creado)

        self.identificador = creado["identificador"]
        self.version = creado["version"]

    def preparar(self, request=None, version=None):
        return preparar_conteo_filtrado_certificado(
            request if request is not None
                else self.request,
            self.identificador,
            version if version is not None
                else self.version,
        )

    def expediente(self):
        return IAExpedienteConsulta.objects.get(
            pk=self.identificador
        )

    def test_01_preparacion_persistida_autorizada(self):
        resultado = self.preparar()

        self.assertTrue(resultado["ok"], resultado)
        self.assertTrue(resultado["contrato_preparado"])
        self.assertFalse(resultado["ejecutable"])
        self.assertFalse(resultado["ejecutado"])

        plan = resultado["contrato"]
        self.assertEqual(
            plan["modelo"],
            "documents.Document",
        )
        self.assertEqual(
            plan["filtros"][0]["valor"],
            "ACTIVO",
        )

    def test_02_otro_usuario_no_recupera_expediente(self):
        solicitud_ajena = SimpleNamespace(
            user=self.otro_usuario,
            session=self.request.session,
        )

        resultado = self.preparar(
            request=solicitud_ajena
        )

        self.assertFalse(resultado["ok"])
        self.assertEqual(
            resultado["estado"],
            "expediente_no_disponible",
        )

    def test_03_otra_sesion_no_recupera_expediente(self):
        otra_sesion = SessionStore()
        otra_sesion.create()

        solicitud = SimpleNamespace(
            user=self.usuario,
            session=otra_sesion,
        )

        resultado = self.preparar(request=solicitud)

        self.assertFalse(resultado["ok"])
        self.assertEqual(
            resultado["estado"],
            "expediente_no_disponible",
        )

    def test_04_version_obsoleta(self):
        resultado = self.preparar(
            version=self.version + 1
        )

        self.assertFalse(resultado["ok"])
        self.assertEqual(
            resultado["estado"],
            "version_obsoleta",
        )

    def test_05_expediente_vencido(self):
        expediente = self.expediente()
        expediente.fecha_expiracion = (
            timezone.now() - timedelta(seconds=1)
        )
        expediente.save(
            update_fields=["fecha_expiracion"]
        )

        resultado = self.preparar()

        self.assertFalse(resultado["ok"])
        self.assertEqual(
            resultado["estado"],
            "expediente_no_vigente",
        )

    def test_06_expediente_completado(self):
        expediente = self.expediente()
        expediente.estado = "COMPLETADO"
        expediente.save(update_fields=["estado"])

        resultado = self.preparar()

        self.assertFalse(resultado["ok"])

    def test_07_preparacion_no_consume_expediente(self):
        anterior = self.expediente()

        estado_inicial = anterior.estado
        version_inicial = anterior.version

        primero = self.preparar()
        segundo = self.preparar()

        self.assertTrue(primero["ok"], primero)
        self.assertTrue(segundo["ok"], segundo)

        posterior = self.expediente()

        self.assertEqual(
            posterior.estado,
            estado_inicial,
        )
        self.assertEqual(
            posterior.version,
            version_inicial,
        )

    @override_settings(
        IA_LOCAL_DOCUMENTOS_CONTEO_GLOBAL_HABILITADO=False
    )
    def test_08_politica_global_desactivada(self):
        resultado = self.preparar()

        self.assertFalse(resultado["ok"])
        self.assertEqual(
            resultado["estado"],
            "lectura_no_autorizada",
        )
