from contextlib import nullcontext
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

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
class TestARC003B05PreparacionConteo(SimpleTestCase):

    def setUp(self):
        self.usuario = Mock()
        self.usuario.pk = 1
        self.usuario.is_authenticated = True
        self.usuario.is_active = True
        self.usuario.has_perm.return_value = True

        self.request = Mock()
        self.request.user = self.usuario

        self.coleccion = preparar_coleccion_restricciones({
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

        self.assertTrue(self.coleccion["ok"])

        self.expediente = SimpleNamespace(
            pk="expediente-prueba",
            pregunta_original=PREGUNTA,
            modelo_contexto="documents.Document",
            coleccion=deepcopy(self.coleccion),
            arbol_logico={},
            asociaciones={},
            estado="ABIERTO",
            version=1,
        )

    def preparar(self, expediente=None, version=1):
        if expediente is None:
            expediente = self.expediente

        with (
            patch(
                "ia_local.services.final."
                "preparacion_conteo_filtrado.transaction.atomic",
                return_value=nullcontext(),
            ),
            patch(
                "ia_local.services.final."
                "preparacion_conteo_filtrado._obtener_bloqueado",
                return_value=expediente,
            ),
            patch(
                "ia_local.services.final."
                "preparacion_conteo_filtrado._vigente",
                return_value=True,
            ),
        ):
            return preparar_conteo_filtrado_certificado(
                self.request,
                "expediente-prueba",
                version,
            )

    def test_01_preparacion_certificada(self):
        resultado = self.preparar()

        self.assertTrue(resultado["ok"], resultado)
        self.assertEqual(
            resultado["estado"],
            "conteo_filtrado_preparado",
        )
        self.assertTrue(resultado["contrato_preparado"])
        self.assertFalse(resultado["ejecutable"])
        self.assertFalse(resultado["ejecutado"])

    def test_02_plan_reconstruido(self):
        resultado = self.preparar()

        self.assertTrue(resultado["ok"], resultado)

        plan = resultado["contrato"]

        self.assertEqual(
            plan["modelo"],
            "documents.Document",
        )
        self.assertEqual(
            plan["operacion"],
            "contar",
        )
        self.assertEqual(
            plan["filtros"][0]["campo"],
            "status",
        )
        self.assertEqual(
            plan["filtros"][0]["valor"],
            "ACTIVO",
        )

    def test_03_version_obsoleta(self):
        resultado = self.preparar(version=2)

        self.assertFalse(resultado["ok"])
        self.assertEqual(
            resultado["estado"],
            "version_obsoleta",
        )

    def test_04_expediente_completado(self):
        expediente = deepcopy(self.expediente)
        expediente.estado = "COMPLETADO"

        resultado = self.preparar(expediente)

        self.assertFalse(resultado["ok"])

    def test_05_modelo_contexto_alterado(self):
        expediente = deepcopy(self.expediente)
        expediente.modelo_contexto = "documents.Project"

        resultado = self.preparar(expediente)

        self.assertFalse(resultado["ok"])
        self.assertEqual(
            resultado["estado"],
            "modelo_contexto_no_equivalente",
        )

    def test_06_pregunta_modificada(self):
        expediente = deepcopy(self.expediente)
        expediente.pregunta_original = (
            "¿Cuántos Documentos tienen "
            "status igual a CERRADO?"
        )

        resultado = self.preparar(expediente)

        self.assertFalse(resultado["ok"])

    @override_settings(
        IA_LOCAL_DOCUMENTOS_CONTEO_GLOBAL_HABILITADO=False,
    )
    def test_07_sin_autorizacion_global(self):
        resultado = self.preparar()

        self.assertFalse(resultado["ok"])
        self.assertEqual(
            resultado["estado"],
            "lectura_no_autorizada",
        )

    def test_08_sin_permiso_documentos(self):
        self.usuario.has_perm.return_value = False

        resultado = self.preparar()

        self.assertFalse(resultado["ok"])

    def test_09_restriccion_adicional(self):
        expediente = deepcopy(self.expediente)
        expediente.coleccion["restricciones"].append(
            deepcopy(
                expediente.coleccion["restricciones"][0]
            )
        )

        resultado = self.preparar(expediente)

        self.assertFalse(resultado["ok"])

    def test_10_expediente_ajeno(self):
        with (
            patch(
                "ia_local.services.final."
                "preparacion_conteo_filtrado.transaction.atomic",
                return_value=nullcontext(),
            ),
            patch(
                "ia_local.services.final."
                "preparacion_conteo_filtrado._obtener_bloqueado",
                return_value=None,
            ),
        ):
            resultado = preparar_conteo_filtrado_certificado(
                self.request,
                "expediente-ajeno",
                1,
            )

        self.assertFalse(resultado["ok"])
        self.assertEqual(
            resultado["estado"],
            "expediente_no_disponible",
        )

    def test_11_identificador_pendiente_alterado(self):
        expediente = deepcopy(self.expediente)

        expediente.coleccion["pendientes"] = [
            "r0001-identificador-falso"
        ]

        resultado = self.preparar(expediente)

        self.assertFalse(resultado["ok"])
        self.assertFalse(resultado["contrato_preparado"])
        self.assertFalse(resultado["ejecutable"])
        self.assertFalse(resultado["ejecutado"])
