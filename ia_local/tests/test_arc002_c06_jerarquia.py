from unittest import TestCase

from ia_local.services.query.trazabilidad_not import (
    localizar_nodos_not,
    _verificar_jerarquia_not,
)


class TestARC002C06Jerarquia(TestCase):

    def test_01_dos_not_independientes(self):
        texto = "NOT (activo) y NOT (cerrado)"
        resultado = localizar_nodos_not(texto)

        self.assertTrue(resultado["ok"])
        self.assertTrue(
            _verificar_jerarquia_not(
                resultado["nodos_not"], texto
            )
        )

    def test_02_not_anidados(self):
        texto = "NOT (NOT (cerrado))"
        resultado = localizar_nodos_not(texto)

        self.assertTrue(resultado["ok"])
        self.assertTrue(
            _verificar_jerarquia_not(
                resultado["nodos_not"], texto
            )
        )

    def test_03_rutas_adulteradas(self):
        texto = "NOT (NOT (cerrado))"
        resultado = localizar_nodos_not(texto)

        self.assertTrue(resultado["ok"])

        asociaciones = [
            dict(nodo)
            for nodo in resultado["nodos_not"]
        ]

        asociaciones[1]["ruta_ast"] = [1]

        with self.assertRaises(ValueError):
            from ia_local.services.query.diagnostico_ast import (
                diagnosticar_ast_logico,
            )

            arbol = diagnosticar_ast_logico(
                texto
            )["arbol_sintactico"]

            _verificar_jerarquia_not(
                asociaciones,
                texto,
                arbol,
            )

    def test_04_intervalos_intercambiados(self):
        texto = "NOT (activo) y NOT (cerrado)"
        resultado = localizar_nodos_not(texto)

        self.assertTrue(resultado["ok"])

        asociaciones = [
            dict(nodo)
            for nodo in resultado["nodos_not"]
        ]

        asociaciones[0]["inicio"] = (
            asociaciones[1]["inicio"]
        )
        asociaciones[0]["fin"] = (
            asociaciones[1]["fin"]
        )
        asociaciones[0]["fragmento_original"] = (
            asociaciones[1]["fragmento_original"]
        )

        with self.assertRaises(ValueError):
            _verificar_jerarquia_not(
                asociaciones, texto
            )
