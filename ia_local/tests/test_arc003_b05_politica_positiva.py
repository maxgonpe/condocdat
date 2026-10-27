from copy import deepcopy
from unittest.mock import Mock

from django.test import SimpleTestCase, override_settings

from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)
from ia_local.services.host.registro_politicas import (
    autorizar_lectura_configurada,
)


RUTA = (
    "documents.ia_politica_lectura."
    "autorizar_lectura_documentos"
)


@override_settings(IA_LOCAL_POLITICA_LECTURA=RUTA)
class TestARC003B05PoliticaPositiva(SimpleTestCase):

    def setUp(self):
        self.usuario = Mock()
        self.usuario.pk = 1
        self.usuario.is_authenticated = True
        self.usuario.is_active = True
        self.usuario.is_staff = True
        self.usuario.has_perm.return_value = True

        resultado = validar_plan_datos({
            "modelo": "documents.Document",
            "operacion": "contar",
            "filtros": [{
                "campo": "status",
                "operador": "exact",
                "valor": "ACTIVO",
            }],
            "orden": [],
            "limite": 10,
            "condiciones_no_resueltas": [],
        })

        self.assertTrue(resultado["ok"])
        self.plan = resultado["plan"]

    def consultar(self, plan=None):
        return autorizar_lectura_configurada(
            self.usuario,
            self.plan if plan is None else plan,
        )

    @override_settings(
        IA_LOCAL_DOCUMENTOS_CONTEO_GLOBAL_HABILITADO=True
    )
    def test_01_permiso_explicito(self):
        resultado = self.consultar()

        self.assertTrue(resultado["autorizado"])
        self.assertFalse(resultado["ejecutable"])
        self.assertFalse(resultado["ejecutado"])

        self.usuario.has_perm.assert_called_with(
            "documents.view_document"
        )

    @override_settings(
        IA_LOCAL_DOCUMENTOS_CONTEO_GLOBAL_HABILITADO=False
    )
    def test_02_habilitacion_desactivada(self):
        self.assertFalse(self.consultar()["autorizado"])

    @override_settings(
        IA_LOCAL_DOCUMENTOS_CONTEO_GLOBAL_HABILITADO=True
    )
    def test_03_sin_permiso_documento(self):
        self.usuario.has_perm.return_value = False

        self.assertFalse(self.consultar()["autorizado"])

    @override_settings(
        IA_LOCAL_DOCUMENTOS_CONTEO_GLOBAL_HABILITADO=True
    )
    def test_04_usuario_inactivo(self):
        self.usuario.is_active = False

        self.assertFalse(self.consultar()["autorizado"])

    @override_settings(
        IA_LOCAL_DOCUMENTOS_CONTEO_GLOBAL_HABILITADO=True
    )
    def test_05_campo_diferente(self):
        plan = deepcopy(self.plan)
        plan["filtros"][0]["campo"] = "revision"
        plan["filtros"][0]["lookup"] = "revision"

        self.assertFalse(
            self.consultar(plan)["autorizado"]
        )

    @override_settings(
        IA_LOCAL_DOCUMENTOS_CONTEO_GLOBAL_HABILITADO=True
    )
    def test_06_filtro_negado(self):
        plan = deepcopy(self.plan)
        plan["filtros"][0]["negado"] = True

        self.assertFalse(
            self.consultar(plan)["autorizado"]
        )

    @override_settings(
        IA_LOCAL_DOCUMENTOS_CONTEO_GLOBAL_HABILITADO="True"
    )
    def test_07_cadena_no_habilita(self):
        self.assertFalse(self.consultar()["autorizado"])

    @override_settings(
        IA_LOCAL_DOCUMENTOS_CONTEO_GLOBAL_HABILITADO=True
    )
    def test_08_error_permiso(self):
        self.usuario.has_perm.side_effect = RuntimeError(
            "fallo simulado"
        )

        self.assertFalse(self.consultar()["autorizado"])
