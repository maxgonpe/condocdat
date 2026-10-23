from types import SimpleNamespace
from unittest import TestCase

from ia_local.services.entrada_canonica import (
    procesar_consulta_canonica,
)


def request_valido():
    return SimpleNamespace(
        user=SimpleNamespace(
            is_authenticated=True,
            pk=123,
        ),
        session=SimpleNamespace(
            session_key="sesion_de_prueba",
        ),
    )


class TestARC001EntradaCanonica(TestCase):

    def test_01_pregunta_conservada(self):
        pregunta = "  ¿Cuántas RDI están abiertas?  "
        resultado = procesar_consulta_canonica(
            request_valido(),
            pregunta,
        )
        self.assertEqual(
            resultado["pregunta_original"],
            pregunta,
        )
        self.assertEqual(
            resultado["estado"],
            "pendiente_integracion",
        )

    def test_02_no_ejecuta(self):
        resultado = procesar_consulta_canonica(
            request_valido(),
            "lista los últimos correos",
        )
        self.assertFalse(resultado["ok"])
        self.assertFalse(resultado["ejecutable"])
        self.assertFalse(resultado["ejecutado"])
        self.assertFalse(resultado["llm_invocado"])

    def test_03_rechaza_anonimo(self):
        request = request_valido()
        request.user.is_authenticated = False

        resultado = procesar_consulta_canonica(
            request,
            "¿Cuántos documentos hay?",
        )
        self.assertEqual(
            resultado["estado"],
            "identidad_no_autenticada",
        )

    def test_04_rechaza_sesion_sin_clave(self):
        request = request_valido()
        request.session.session_key = None

        resultado = procesar_consulta_canonica(
            request,
            "¿Cuántos documentos hay?",
        )
        self.assertEqual(
            resultado["estado"],
            "sesion_no_identificada",
        )

    def test_05_rechaza_ejecucion(self):
        resultado = procesar_consulta_canonica(
            request_valido(),
            "¿Cuántos documentos hay?",
            modo="ejecutar",
        )
        self.assertEqual(
            resultado["estado"],
            "modo_no_habilitado",
        )

    def test_06_rechaza_contexto_externo(self):
        resultado = procesar_consulta_canonica(
            request_valido(),
            "¿Cuántos documentos hay?",
            contexto={
                "ejecutable": True,
                "plan": {"operacion": "contar"},
            },
        )
        self.assertEqual(
            resultado["estado"],
            "contexto_no_habilitado",
        )

    def test_07_rechaza_pregunta_vacia(self):
        resultado = procesar_consulta_canonica(
            request_valido(),
            "   ",
        )
        self.assertEqual(
            resultado["estado"],
            "pregunta_vacia",
        )

    def test_08_contrato_uniforme(self):
        resultado = procesar_consulta_canonica(
            request_valido(),
            "¿Cuántas RDI de civil están abiertas?",
        )

        for clave in (
            "version",
            "pregunta_original",
            "estado",
            "ok",
            "resuelto",
            "ejecutable",
            "ejecutado",
            "llm_invocado",
            "contexto_valido",
            "interpretacion",
            "certificacion",
            "resultado",
            "diagnostico",
        ):
            self.assertIn(clave, resultado)
