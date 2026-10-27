from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

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
from ia_local.services.final.ejecucion_conteo_filtrado import (
    ejecutar_conteo_filtrado_certificado,
)


PREGUNTA = (
    "¿Cuántos Documentos tienen status igual a ACTIVO?"
)

RUTA_POLITICA = (
    "documents.ia_politica_lectura."
    "autorizar_lectura_documentos"
)

EJECUTOR = (
    "ia_local.services.final."
    "ejecucion_conteo_filtrado.ejecutar_plan_datos"
)


@override_settings(
    IA_LOCAL_POLITICA_LECTURA=RUTA_POLITICA,
    IA_LOCAL_DOCUMENTOS_CONTEO_GLOBAL_HABILITADO=True,
)
class TestARC003B05EjecucionFiltrada(TestCase):

    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.usuario = Usuario.objects.create_user(
            username="arc003_e03_usuario"
        )
        cls.otro_usuario = Usuario.objects.create_user(
            username="arc003_e03_otro"
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

    def ejecutar(self, request=None, version=None):
        return ejecutar_conteo_filtrado_certificado(
            request or self.request,
            self.identificador,
            self.version if version is None else version,
        )

    def respuesta_host(self):
        return {
            "ok": True,
            "ejecutado": True,
            "operacion": "contar",
            "modelo": "documents.Document",
            "total": 7,
        }

    def expediente(self):
        return IAExpedienteConsulta.objects.get(
            pk=self.identificador
        )

    def test_01_despacho_y_consumo_unico(self):
        with patch(
            EJECUTOR, return_value=self.respuesta_host()
        ) as host:
            primero = self.ejecutar()
            segundo = self.ejecutar()

        self.assertTrue(primero["ok"], primero)
        self.assertEqual(primero["total"], 7)
        self.assertFalse(segundo["ok"])
        host.assert_called_once()

        plan = host.call_args.args[0]
        self.assertEqual(plan["operacion"], "contar")
        self.assertEqual(
            plan["filtros"][0]["valor"], "ACTIVO"
        )

        expediente = self.expediente()
        self.assertEqual(expediente.estado, "COMPLETADO")
        self.assertEqual(
            expediente.version, self.version + 1
        )

    def test_02_otro_usuario_rechazado(self):
        ajeno = SimpleNamespace(
            user=self.otro_usuario,
            session=self.request.session,
        )

        with patch(EJECUTOR) as host:
            resultado = self.ejecutar(request=ajeno)

        self.assertFalse(resultado["ok"])
        host.assert_not_called()

    def test_03_sin_autorizacion(self):
        with (
            override_settings(
                IA_LOCAL_DOCUMENTOS_CONTEO_GLOBAL_HABILITADO=False
            ),
            patch(EJECUTOR) as host,
        ):
            resultado = self.ejecutar()

        self.assertFalse(resultado["ok"])
        host.assert_not_called()
        self.assertEqual(
            self.expediente().estado, "ABIERTO"
        )

    def test_04_version_obsoleta(self):
        with patch(EJECUTOR) as host:
            resultado = self.ejecutar(
                version=self.version + 1
            )

        self.assertFalse(resultado["ok"])
        host.assert_not_called()

    def test_05_expediente_vencido(self):
        expediente = self.expediente()
        expediente.fecha_expiracion = (
            timezone.now() - timedelta(seconds=1)
        )
        expediente.save(
            update_fields=["fecha_expiracion"]
        )

        with patch(EJECUTOR) as host:
            resultado = self.ejecutar()

        self.assertFalse(resultado["ok"])
        host.assert_not_called()

    def test_06_rechazo_host_consume_expediente(self):
        with patch(
            EJECUTOR,
            return_value={
                "ok": False,
                "ejecutado": False,
            },
        ) as host:
            primero = self.ejecutar()
            segundo = self.ejecutar()

        self.assertFalse(primero["ok"])
        self.assertFalse(segundo["ok"])
        host.assert_called_once()
        self.assertEqual(
            self.expediente().estado,
            "COMPLETADO",
        )

    def test_07_excepcion_host_consume_expediente(self):
        with patch(
            EJECUTOR,
            side_effect=RuntimeError("fallo simulado"),
        ) as host:
            primero = self.ejecutar()
            segundo = self.ejecutar()

        self.assertFalse(primero["ok"])
        self.assertFalse(segundo["ok"])
        host.assert_called_once()
        self.assertEqual(
            self.expediente().estado,
            "COMPLETADO",
        )
