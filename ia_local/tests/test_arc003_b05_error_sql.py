"""
ARC003-B05-E03-B02-A
Caracterizacion de fallo SQL real durante despacho.

Usa TransactionTestCase y PostgreSQL temporal.
NO es una prueba de garantia de consumo unico.
"""

from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.backends.db import SessionStore
from django.db import connection, DatabaseError
from django.test import TransactionTestCase, override_settings

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


EJECUTOR = (
    "ia_local.services.final."
    "ejecucion_conteo_filtrado.ejecutar_plan_datos"
)


@override_settings(
    IA_LOCAL_POLITICA_LECTURA=(
        "documents.ia_politica_lectura."
        "autorizar_lectura_documentos"
    ),
    IA_LOCAL_DOCUMENTOS_CONTEO_GLOBAL_HABILITADO=True,
)
class TestARC003B05ErrorSQL(TransactionTestCase):

    def setUp(self):
        Usuario = get_user_model()

        self.usuario = Usuario.objects.create_user(
            username="arc003_error_sql"
        )

        ct = ContentType.objects.get(
            app_label="documents",
            model="document",
        )
        permiso = Permission.objects.get(
            content_type=ct,
            codename="view_document",
        )
        self.usuario.user_permissions.add(permiso)

        sesion = SessionStore()
        sesion.create()

        self.request = SimpleNamespace(
            user=self.usuario,
            session=sesion,
        )

        self.pregunta = (
            "¿Cuántos Documentos tienen "
            "status igual a DRAFT?"
        )

        coleccion = preparar_coleccion_restricciones({
            "ok": True,
            "estado": "consolidacion_diagnostica",
            "pregunta": self.pregunta,
            "restricciones": [{
                "tipo": "filtro",
                "evidencia_textual":
                    "status igual a DRAFT",
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

    def test_01_rollback_ante_error_postgresql(self):

        def ejecutar_con_error(_plan):
            # SQL deliberadamente invalido: produce un
            # error real del motor PostgreSQL.
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM "
                    "arc003_tabla_inexistente_b02"
                )

        with patch(
            EJECUTOR,
            side_effect=ejecutar_con_error,
        ) as ejecutor:

            resultado = ejecutar_conteo_filtrado_certificado(
                self.request,
                self.identificador,
                self.version,
            )

        ejecutor.assert_called_once()

        self.assertFalse(resultado["ok"])
        self.assertFalse(resultado["ejecutado"])

        expediente = IAExpedienteConsulta.objects.get(
            pk=self.identificador
        )

        print(
            "\nESTADO DESPUES DEL ERROR SQL:",
            expediente.estado,
        )
        print(
            "VERSION DESPUES DEL ERROR:",
            expediente.version,
        )
        print(
            "RESPUESTA:",
            resultado["estado"],
        )

        # La falla SQL se revierte mediante savepoint.
        # El consumo del expediente debe persistir.
        self.assertEqual(
            expediente.estado,
            "COMPLETADO",
        )
        self.assertEqual(
            expediente.version,
            self.version + 1,
        )

        # Una segunda solicitud no puede llegar a HOST.
        with patch(EJECUTOR) as segundo_ejecutor:
            segundo = ejecutar_conteo_filtrado_certificado(
                self.request,
                self.identificador,
                self.version,
            )

        self.assertFalse(segundo["ok"])
        self.assertFalse(segundo["ejecutado"])
        segundo_ejecutor.assert_not_called()
