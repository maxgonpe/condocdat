from unittest import TestCase
from unittest.mock import patch

from ia_local.services.query import grupos_logicos


class TestARC002C04Estructura(TestCase):

    def comprobar_rechazo(self, arbol):
        contexto = {
            "modelo": None,
            "operacion": None,
            "siguiente_indice": 0,
            "resoluciones": [],
        }

        with patch.object(
            grupos_logicos,
            "componer_campo_operador_valor",
        ) as bridge:
            with self.assertRaises(
                grupos_logicos.ErrorSintaxisLogica
            ):
                grupos_logicos._resolver_ast(
                    arbol,
                    prefijo="listar elementos",
                    limite=10,
                    contexto=contexto,
                )

            bridge.assert_not_called()

        self.assertEqual(contexto["resoluciones"], [])
        self.assertEqual(contexto["siguiente_indice"], 0)

    def test_01_not_en_grupo_anidado(self):
        arbol = grupos_logicos._construir_ast_sintactico(
            "activo y (vigente o NOT (cerrado))"
        )
        self.comprobar_rechazo(arbol)

    def test_02_operador_desconocido(self):
        self.comprobar_rechazo({
            "tipo": "GRUPO",
            "operador": "XOR",
            "hijos": [
                {"tipo": "CONDICION", "texto": "activo"},
                {"tipo": "CONDICION", "texto": "cerrado"},
            ],
        })

    def test_03_and_con_un_solo_hijo(self):
        self.comprobar_rechazo({
            "tipo": "GRUPO",
            "operador": "AND",
            "hijos": [
                {"tipo": "CONDICION", "texto": "activo"},
            ],
        })

    def test_04_arbol_ciclico(self):
        arbol = {
            "tipo": "GRUPO",
            "operador": "AND",
            "hijos": [
                {"tipo": "CONDICION", "texto": "activo"},
            ],
        }
        arbol["hijos"].append(arbol)
        self.comprobar_rechazo(arbol)

    def test_05_profundidad_excesiva(self):
        arbol = {"tipo": "CONDICION", "texto": "activo"}

        for _ in range(66):
            arbol = {
                "tipo": "GRUPO",
                "operador": "AND",
                "hijos": [
                    {"tipo": "CONDICION", "texto": "vigente"},
                    arbol,
                ],
            }

        self.comprobar_rechazo(arbol)
