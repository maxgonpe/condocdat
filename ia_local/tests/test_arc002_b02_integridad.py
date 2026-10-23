from unittest import TestCase

from ia_local.services.llm.integridad_requisitos import (
    diagnosticar_integridad_requisitos,
)
from ia_local.services.llm.trazabilidad_compuesta import (
    preparar_coleccion_restricciones,
)


def consolidacion(pregunta, restricciones):
    return {
        "ok": True,
        "estado": "consolidacion_diagnostica",
        "pregunta": pregunta,
        "restricciones": restricciones,
        "ejecutable": False,
        "ejecutado": False,
    }


class TestARC002B02Integridad(TestCase):

    def test_01_coleccion_vacia_no_demuestra_integridad(self):
        pregunta = "¿Cuántas RDI de civil están abiertas?"

        coleccion = preparar_coleccion_restricciones(
            consolidacion(pregunta, [])
        )

        resultado = diagnosticar_integridad_requisitos(
            coleccion
        )

        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["requisitos_identificados"], [])
        self.assertFalse(resultado["integridad_demostrada"])
        self.assertFalse(resultado["ejecutable"])

    def test_02_conserva_identificadores_originales(self):
        pregunta = "¿Cuántas RDI de civil están abiertas?"

        coleccion = preparar_coleccion_restricciones(
            consolidacion(
                pregunta,
                [
                    {
                        "tipo": "filtro",
                        "evidencia_textual": "de civil",
                    },
                    {
                        "tipo": "filtro",
                        "evidencia_textual": "están abiertas",
                    },
                ],
            )
        )

        resultado = diagnosticar_integridad_requisitos(
            coleccion
        )

        ids_originales = [
            r["id"] for r in coleccion["restricciones"]
        ]

        self.assertEqual(
            resultado["requisitos_identificados"],
            ids_originales,
        )
        self.assertEqual(
            resultado["requisitos_pendientes"],
            ids_originales,
        )
        self.assertFalse(resultado["integridad_demostrada"])

    def test_03_rechaza_coleccion_alterada(self):
        pregunta = "¿Cuántas RDI de civil están abiertas?"

        coleccion = preparar_coleccion_restricciones(
            consolidacion(
                pregunta,
                [
                    {
                        "tipo": "filtro",
                        "evidencia_textual": "de civil",
                    },
                ],
            )
        )

        coleccion["restricciones"][0][
            "certificada_host"
        ] = True

        resultado = diagnosticar_integridad_requisitos(
            coleccion
        )

        self.assertFalse(resultado["ok"])
        self.assertFalse(resultado["ejecutable"])

    def test_04_rechaza_pendientes_inconsistentes(self):
        pregunta = "¿Cuántas RDI hay?"

        coleccion = preparar_coleccion_restricciones(
            consolidacion(
                pregunta,
                [
                    {
                        "tipo": "entidad",
                        "evidencia_textual": "RDI",
                    },
                ],
            )
        )

        coleccion["pendientes"] = []

        resultado = diagnosticar_integridad_requisitos(
            coleccion
        )

        self.assertFalse(resultado["ok"])

    def test_05_identificadores_deterministas(self):
        pregunta = "¿Cuántas RDI de civil están abiertas?"

        datos = consolidacion(
            pregunta,
            [
                {
                    "tipo": "filtro",
                    "evidencia_textual": "de civil",
                },
            ],
        )

        primera = preparar_coleccion_restricciones(datos)
        segunda = preparar_coleccion_restricciones(datos)

        self.assertEqual(
            primera["identificador_coleccion"],
            segunda["identificador_coleccion"],
        )

        self.assertEqual(
            primera["restricciones"][0]["id"],
            segunda["restricciones"][0]["id"],
        )
