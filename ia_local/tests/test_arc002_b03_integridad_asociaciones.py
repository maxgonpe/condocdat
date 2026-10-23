from copy import deepcopy
from unittest import TestCase

from ia_local.services.llm.asociacion_evidencias import (
    asociar_evidencias_requisitos,
)
from ia_local.services.llm.evidencia_negacion import (
    localizar_evidencias_negacion,
)
from ia_local.services.llm.trazabilidad_compuesta import (
    preparar_coleccion_restricciones,
)


PREGUNTA = "RDI que no esté cerrada"


def entradas():
    coleccion = preparar_coleccion_restricciones({
        "ok": True,
        "estado": "consolidacion_diagnostica",
        "pregunta": PREGUNTA,
        "restricciones": [
            {
                "tipo": "filtro",
                "evidencia_textual": "no esté cerrada",
            }
        ],
        "ejecutable": False,
        "ejecutado": False,
    })

    evidencias = localizar_evidencias_negacion(PREGUNTA)
    return coleccion, evidencias


class TestARC002B03IntegridadAsociaciones(TestCase):

    def test_01_entradas_originales_validas(self):
        coleccion, evidencias = entradas()
        resultado = asociar_evidencias_requisitos(
            coleccion, evidencias
        )

        self.assertTrue(resultado["ok"])
        self.assertFalse(resultado["ejecutable"])
        self.assertFalse(resultado["integridad_completa"])

    def test_02_rechaza_identificador_alterado(self):
        coleccion, evidencias = entradas()
        coleccion["restricciones"][0]["id"] = "r0001-falso"

        resultado = asociar_evidencias_requisitos(
            coleccion, evidencias
        )
        self.assertFalse(resultado["ok"])

    def test_03_rechaza_contenido_alterado(self):
        coleccion, evidencias = entradas()
        coleccion["restricciones"][0][
            "evidencia_textual"
        ] = "RDI"

        resultado = asociar_evidencias_requisitos(
            coleccion, evidencias
        )
        self.assertFalse(resultado["ok"])

    def test_04_rechaza_huella_alterada(self):
        coleccion, evidencias = entradas()
        coleccion["identificador_coleccion"] = "f" * 64

        resultado = asociar_evidencias_requisitos(
            coleccion, evidencias
        )
        self.assertFalse(resultado["ok"])

    def test_05_rechaza_posiciones_alteradas(self):
        coleccion, evidencias = entradas()
        evidencias["evidencias"][0]["inicio"] += 1
        evidencias["evidencias"][0]["fin"] += 1

        resultado = asociar_evidencias_requisitos(
            coleccion, evidencias
        )
        self.assertFalse(resultado["ok"])

    def test_06_rechaza_evidencia_duplicada(self):
        coleccion, evidencias = entradas()
        evidencias["evidencias"].append(
            deepcopy(evidencias["evidencias"][0])
        )

        resultado = asociar_evidencias_requisitos(
            coleccion, evidencias
        )
        self.assertFalse(resultado["ok"])

    def test_07_rechaza_certificacion_prematura(self):
        coleccion, evidencias = entradas()
        coleccion["restricciones"][0][
            "certificada_host"
        ] = True

        resultado = asociar_evidencias_requisitos(
            coleccion, evidencias
        )
        self.assertFalse(resultado["ok"])
