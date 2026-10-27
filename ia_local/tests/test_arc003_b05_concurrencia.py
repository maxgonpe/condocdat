"""
ARC003-B05-E03-B03
Concurrencia real PostgreSQL: consumo unico.

Dos hilos, conexiones independientes y mismo expediente.
HOST es simulado para controlar el punto de concurrencia.

No modifica registros de negocio ni publica HTTP.
"""

import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.backends.db import SessionStore
from django.db import connections
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


PREGUNTA = (
    "¿Cuántos Documentos tienen status igual a DRAFT?"
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
class TestARC003B05Concurrencia(TransactionTestCase):

    def setUp(self):
        if connections["default"].vendor != "postgresql":
            self.skipTest(
                "La prueba requiere PostgreSQL"
            )

        Usuario = get_user_model()

        self.usuario = Usuario.objects.create_user(
            username="arc003_concurrencia"
        )

        tipo = ContentType.objects.get(
            app_label="documents",
            model="document",
        )

        permiso = Permission.objects.get(
            content_type=tipo,
            codename="view_document",
        )

        self.usuario.user_permissions.add(permiso)

        sesion = SessionStore()
        sesion.create()

        self.session_key = sesion.session_key

        request = SimpleNamespace(
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
                    "status igual a DRAFT",
                "origen": "gramatica_determinista_b04",
            }],
            "ejecutable": False,
            "ejecutado": False,
        })

        self.assertTrue(coleccion["ok"])

        creado = crear_expediente(
            request,
            coleccion,
            "documents.Document",
        )

        self.assertTrue(creado["ok"], creado)

        self.identificador = creado["identificador"]
        self.version = creado["version"]

    def _solicitud_independiente(self, iniciado=None):
        """
        Cada hilo obtiene su propia conexion Django,
        usuario ORM y objeto de sesion.
        """
        connections.close_all()

        try:
            Usuario = get_user_model()

            usuario = Usuario.objects.get(
                pk=self.usuario.pk
            )

            sesion = SessionStore(
                session_key=self.session_key
            )

            request = SimpleNamespace(
                user=usuario,
                session=sesion,
            )

            if iniciado is not None:
                iniciado.set()

            return ejecutar_conteo_filtrado_certificado(
                request,
                self.identificador,
                self.version,
            )
        finally:
            connections.close_all()

    def test_01_dos_solicitudes_un_solo_despacho(self):

        host_entrado = threading.Event()
        liberar_host = threading.Event()
        segunda_iniciada = threading.Event()

        llamadas = []
        mutex = threading.Lock()

        def host_controlado(plan):
            with mutex:
                llamadas.append(plan)

            # El primer hilo retiene el bloqueo del
            # expediente mientras permanece en HOST.
            host_entrado.set()

            if not liberar_host.wait(timeout=10):
                raise RuntimeError(
                    "Timeout de sincronizacion HOST"
                )

            return {
                "ok": True,
                "ejecutado": True,
                "operacion": "contar",
                "modelo": "documents.Document",
                "total": 5,
            }

        with patch(
            EJECUTOR,
            side_effect=host_controlado,
        ):
            with ThreadPoolExecutor(
                max_workers=2
            ) as pool:

                primero = pool.submit(
                    self._solicitud_independiente
                )

                try:
                    self.assertTrue(
                        host_entrado.wait(timeout=10),
                        "Primera solicitud no alcanzo HOST",
                    )

                    segundo = pool.submit(
                        self._solicitud_independiente,
                        segunda_iniciada,
                    )

                    self.assertTrue(
                        segunda_iniciada.wait(timeout=10),
                        "Segunda solicitud no inicio",
                    )

                    # El primer hilo mantiene la
                    # transaccion y el bloqueo de fila.
                    # La segunda solicitud no deberia
                    # completar mientras esto ocurra.
                    with self.assertRaises(TimeoutError):
                        segundo.result(timeout=0.3)

                    with mutex:
                        self.assertEqual(
                            len(llamadas), 1
                        )

                finally:
                    # Liberar siempre al primer hilo,
                    # incluso si una asercion falla.
                    liberar_host.set()

                resultado_1 = primero.result(timeout=10)
                resultado_2 = segundo.result(timeout=10)

        exitosos = [
            r for r in (resultado_1, resultado_2)
            if r.get("ok") is True
        ]

        rechazados = [
            r for r in (resultado_1, resultado_2)
            if r.get("ok") is False
        ]

        self.assertEqual(len(exitosos), 1)
        self.assertEqual(len(rechazados), 1)

        self.assertTrue(exitosos[0]["ejecutado"])
        self.assertEqual(exitosos[0]["total"], 5)

        self.assertFalse(rechazados[0]["ejecutado"])

        with mutex:
            self.assertEqual(len(llamadas), 1)

        expediente = IAExpedienteConsulta.objects.get(
            pk=self.identificador
        )

        self.assertEqual(
            expediente.estado,
            "COMPLETADO",
        )

        self.assertEqual(
            expediente.version,
            self.version + 1,
        )
