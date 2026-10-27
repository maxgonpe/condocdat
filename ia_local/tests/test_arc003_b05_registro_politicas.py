"""
ARC003-B05-D02
Pruebas del registro confiable de politicas.

Las politicas permisivas son exclusivamente de prueba.
No realizan consultas ORM.
"""

from copy import deepcopy
from unittest.mock import Mock

from django.test import SimpleTestCase, override_settings

from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)
from ia_local.services.host.registro_politicas import (
    autorizar_lectura_configurada,
    resolver_politica_lectura,
)


RUTA_PRUEBAS = (
    "ia_local.tests.test_arc003_b05_registro_politicas"
)


def politica_permisiva_prueba(
    *, usuario, modelo, operacion, campos, plan
):
    return {
        "permitido": True,
        "modelo": modelo,
        "operacion": operacion,
        "campos": list(campos),
        "alcance": "universo_completo",
    }


def politica_denegada_prueba(
    *, usuario, modelo, operacion, campos, plan
):
    return {
        "permitido": False,
        "modelo": modelo,
        "operacion": operacion,
        "campos": list(campos),
        "alcance": "universo_completo",
    }


def politica_con_error_prueba(**kwargs):
    raise RuntimeError("fallo simulado")


class TestARC003B05RegistroPoliticas(SimpleTestCase):

    def setUp(self):
        self.usuario = Mock()
        self.usuario.pk = 1
        self.usuario.is_authenticated = True
        self.usuario.is_active = True

        validacion = validar_plan_datos({
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

        self.assertTrue(validacion["ok"])
        self.plan = validacion["plan"]

    @override_settings(IA_LOCAL_POLITICA_LECTURA=None)
    def test_01_sin_configuracion(self):
        self.assertIsNone(resolver_politica_lectura())

        resultado = autorizar_lectura_configurada(
            self.usuario, self.plan
        )
        self.assertFalse(resultado["autorizado"])
        self.assertFalse(resultado["ejecutable"])

    @override_settings(
        IA_LOCAL_POLITICA_LECTURA="modulo.inexistente.politica"
    )
    def test_02_ruta_inexistente(self):
        resultado = autorizar_lectura_configurada(
            self.usuario, self.plan
        )
        self.assertFalse(resultado["autorizado"])

    @override_settings(
        IA_LOCAL_POLITICA_LECTURA=123
    )
    def test_03_configuracion_no_textual(self):
        resultado = autorizar_lectura_configurada(
            self.usuario, self.plan
        )
        self.assertFalse(resultado["autorizado"])

    @override_settings(
        IA_LOCAL_POLITICA_LECTURA=(
            RUTA_PRUEBAS + ".politica_denegada_prueba"
        )
    )
    def test_04_denegacion_explicita(self):
        resultado = autorizar_lectura_configurada(
            self.usuario, self.plan
        )
        self.assertFalse(resultado["autorizado"])

    @override_settings(
        IA_LOCAL_POLITICA_LECTURA=(
            RUTA_PRUEBAS + ".politica_con_error_prueba"
        )
    )
    def test_05_error_politica(self):
        resultado = autorizar_lectura_configurada(
            self.usuario, self.plan
        )
        self.assertFalse(resultado["autorizado"])

    @override_settings(
        IA_LOCAL_POLITICA_LECTURA=(
            RUTA_PRUEBAS + ".politica_permisiva_prueba"
        )
    )
    def test_06_autorizacion_de_prueba(self):
        resultado = autorizar_lectura_configurada(
            self.usuario, self.plan
        )
        self.assertTrue(resultado["autorizado"])
        self.assertEqual(
            resultado["origen_politica"],
            "configuracion_django",
        )
        self.assertFalse(resultado["ejecutable"])

    @override_settings(
        IA_LOCAL_POLITICA_LECTURA=(
            RUTA_PRUEBAS + ".politica_permisiva_prueba"
        )
    )
    def test_07_plan_manipulado(self):
        plan = deepcopy(self.plan)
        plan["certificacion_limitada"] = True

        resultado = autorizar_lectura_configurada(
            self.usuario, plan
        )
        self.assertFalse(resultado["autorizado"])

    @override_settings(
        IA_LOCAL_POLITICA_LECTURA=(
            RUTA_PRUEBAS + ".politica_permisiva_prueba"
        )
    )
    def test_08_usuario_anonimo(self):
        usuario = Mock()
        usuario.pk = None
        usuario.is_authenticated = False
        usuario.is_active = False

        resultado = autorizar_lectura_configurada(
            usuario, self.plan
        )
        self.assertFalse(resultado["autorizado"])
