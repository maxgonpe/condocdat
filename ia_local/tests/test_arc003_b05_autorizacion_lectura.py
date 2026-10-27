"""
ARC003-B05-D01
Pruebas del contrato portable de autorizacion.

No ejecutan ORM ni acceden a registros de negocio.
"""

from copy import deepcopy
from unittest.mock import Mock

from django.test import SimpleTestCase

from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)
from ia_local.services.host.autorizacion_lectura import (
    autorizar_lectura,
)


class TestARC003B05Autorizacion(SimpleTestCase):

    def setUp(self):
        self.usuario = Mock()
        self.usuario.pk = 1
        self.usuario.is_authenticated = True
        self.usuario.is_active = True

        propuesta = {
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
        }

        validacion = validar_plan_datos(propuesta)
        self.assertTrue(validacion["ok"])
        self.assertTrue(validacion["plan_validado"])

        self.plan = validacion["plan"]

    def decision(self):
        return {
            "permitido": True,
            "modelo": "documents.Document",
            "operacion": "contar",
            "campos": ["status"],
            "alcance": "universo_completo",
        }

    def test_01_autorizacion_explicita(self):
        politica = Mock(return_value=self.decision())

        resultado = autorizar_lectura(
            self.usuario,
            self.plan,
            politica=politica,
        )

        self.assertTrue(resultado["ok"])
        self.assertTrue(resultado["autorizado"])
        self.assertFalse(resultado["ejecutable"])
        self.assertFalse(resultado["ejecutado"])
        politica.assert_called_once()

    def test_02_sin_politica(self):
        resultado = autorizar_lectura(
            self.usuario,
            self.plan,
        )

        self.assertFalse(resultado["ok"])
        self.assertFalse(resultado["autorizado"])

    def test_03_usuario_no_autenticado(self):
        usuario = Mock()
        usuario.pk = 1
        usuario.is_authenticated = False
        usuario.is_active = True

        politica = Mock(return_value=self.decision())

        resultado = autorizar_lectura(
            usuario,
            self.plan,
            politica=politica,
        )

        self.assertFalse(resultado["ok"])
        politica.assert_not_called()

    def test_04_politica_deniega(self):
        decision = self.decision()
        decision["permitido"] = False

        resultado = autorizar_lectura(
            self.usuario,
            self.plan,
            politica=Mock(return_value=decision),
        )

        self.assertFalse(resultado["ok"])

    def test_05_modelo_incorrecto(self):
        decision = self.decision()
        decision["modelo"] = "documents.Project"

        resultado = autorizar_lectura(
            self.usuario,
            self.plan,
            politica=Mock(return_value=decision),
        )

        self.assertFalse(resultado["ok"])

    def test_06_campo_incorrecto(self):
        decision = self.decision()
        decision["campos"] = ["revision"]

        resultado = autorizar_lectura(
            self.usuario,
            self.plan,
            politica=Mock(return_value=decision),
        )

        self.assertFalse(resultado["ok"])

    def test_07_alcance_parcial_no_admitido(self):
        decision = self.decision()
        decision["alcance"] = "solo_proyectos_del_usuario"

        resultado = autorizar_lectura(
            self.usuario,
            self.plan,
            politica=Mock(return_value=decision),
        )

        self.assertFalse(resultado["ok"])

    def test_08_politica_con_excepcion(self):
        politica = Mock(
            side_effect=RuntimeError("error interno")
        )

        resultado = autorizar_lectura(
            self.usuario,
            self.plan,
            politica=politica,
        )

        self.assertFalse(resultado["ok"])
        self.assertEqual(
            resultado["estado"],
            "error_politica",
        )

    def test_09_plan_alterado(self):
        plan = deepcopy(self.plan)
        plan["filtros"][0]["valor"] = "CERRADO"
        plan["certificacion_limitada"] = True

        politica = Mock(return_value=self.decision())

        resultado = autorizar_lectura(
            self.usuario,
            plan,
            politica=politica,
        )

        self.assertFalse(resultado["ok"])
        politica.assert_not_called()
