"""
ARC003-B05-D03-A
Integracion del registro portable con una politica
del anfitrion Condocdat.

No concede acceso ni ejecuta ORM.
"""

from unittest.mock import Mock

from django.test import SimpleTestCase, override_settings

from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)
from ia_local.services.host.registro_politicas import (
    autorizar_lectura_configurada,
    resolver_politica_lectura,
)


RUTA_POLITICA = (
    "documents.ia_politica_lectura."
    "autorizar_lectura_documentos"
)


@override_settings(
    IA_LOCAL_POLITICA_LECTURA=RUTA_POLITICA
)
class TestARC003B05PoliticaCondocdat(SimpleTestCase):

    def setUp(self):
        self.usuario = Mock()
        self.usuario.pk = 1
        self.usuario.is_authenticated = True
        self.usuario.is_active = True
        self.usuario.is_staff = True

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

    def test_01_politica_anfitrion_resuelta(self):
        politica = resolver_politica_lectura()
        self.assertTrue(callable(politica))

    def test_02_staff_no_equivale_a_autorizacion(self):
        resultado = autorizar_lectura_configurada(
            self.usuario,
            self.plan,
        )

        self.assertFalse(resultado["ok"])
        self.assertFalse(resultado["autorizado"])
        self.assertFalse(resultado["ejecutable"])

    def test_03_denegacion_no_ejecuta(self):
        resultado = autorizar_lectura_configurada(
            self.usuario,
            self.plan,
        )

        self.assertFalse(resultado["ejecutado"])
        self.assertEqual(
            resultado["estado"],
            "lectura_no_autorizada",
        )
