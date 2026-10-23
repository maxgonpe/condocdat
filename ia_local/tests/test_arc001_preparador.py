from unittest import TestCase
from unittest.mock import patch

from ia_local.services.host.preparador_consulta_datos import (
    preparar_consulta_datos,
)


MODULO = (
    "ia_local.services.host.preparador_consulta_datos"
)


class TestARC001Preparador(TestCase):

    def test_01_pregunta_vacia(self):
        resultado = preparar_consulta_datos(" ")

        self.assertFalse(resultado["ok"])
        self.assertFalse(resultado["ejecutado"])

    @patch(f"{MODULO}.validar_plan_datos")
    @patch(f"{MODULO}.interpretar_consulta_datos")
    @patch(f"{MODULO}.resolver_entidad_datos")
    def test_02_preparacion_sin_ejecucion(
        self, resolver, interpretar, validar
    ):
        resolver.return_value = {
            "resuelto": True,
            "entidad": "pruebas.Elemento",
        }

        interpretar.return_value = {
            "ok": True,
            "propuesta": {
                "modelo": "pruebas.Elemento",
                "operacion": "contar",
                "filtros": [],
                "orden": [],
                "limite": None,
                "condiciones_no_resueltas": [],
            },
        }

        validar.return_value = {
            "ok": True,
            "plan": interpretar.return_value["propuesta"],
        }

        resultado = preparar_consulta_datos(
            "¿Cuántos elementos hay?"
        )

        self.assertTrue(resultado["ok"])
        self.assertEqual(
            resultado["estado"],
            "plan_host_preparado",
        )
        self.assertFalse(resultado["ejecutable"])
        self.assertFalse(resultado["ejecutado"])
        self.assertFalse(
            resultado["certificacion_semantica"]
        )

        validar.assert_called_once()

    @patch(f"{MODULO}.resolver_entidad_datos")
    def test_03_entidad_no_resuelta(self, resolver):
        resolver.return_value = {
            "resuelto": False,
        }

        resultado = preparar_consulta_datos(
            "Consulta ambigua"
        )

        self.assertEqual(
            resultado["estado"],
            "entidad_no_resuelta",
        )

    @patch(f"{MODULO}.validar_plan_datos")
    @patch(f"{MODULO}.interpretar_consulta_datos")
    @patch(f"{MODULO}.resolver_entidad_datos")
    def test_04_modelo_llm_inconsistente(
        self, resolver, interpretar, validar
    ):
        resolver.return_value = {
            "resuelto": True,
            "entidad": "pruebas.Elemento",
        }

        interpretar.return_value = {
            "ok": True,
            "propuesta": {
                "modelo": "otra.Entidad",
                "operacion": "contar",
            },
        }

        resultado = preparar_consulta_datos(
            "¿Cuántos elementos hay?"
        )

        self.assertEqual(
            resultado["estado"],
            "modelo_inconsistente",
        )
        validar.assert_not_called()

    @patch(f"{MODULO}.validar_plan_datos")
    @patch(f"{MODULO}.interpretar_consulta_datos")
    @patch(f"{MODULO}.resolver_entidad_datos")
    def test_05_plan_rechazado(
        self, resolver, interpretar, validar
    ):
        resolver.return_value = {
            "resuelto": True,
            "entidad": "pruebas.Elemento",
        }

        interpretar.return_value = {
            "ok": True,
            "propuesta": {
                "modelo": "pruebas.Elemento",
                "operacion": "contar",
            },
        }

        validar.return_value = {
            "ok": False,
            "errores": ["Campo no permitido"],
        }

        resultado = preparar_consulta_datos(
            "¿Cuántos elementos hay?"
        )

        self.assertEqual(
            resultado["estado"],
            "plan_rechazado_host",
        )

    def test_06_no_importa_ejecutor_funcional(self):
        import ast
        import inspect
        from ia_local.services.host import preparador_consulta_datos

        fuente = inspect.getsource(
            preparador_consulta_datos
        )
        arbol = ast.parse(fuente)

        nombres = {
            nodo.id
            for nodo in ast.walk(arbol)
            if isinstance(nodo, ast.Name)
        }

        self.assertNotIn(
            "ejecutar_plan_datos",
            nombres,
        )
