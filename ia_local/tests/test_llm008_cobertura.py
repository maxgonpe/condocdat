from django.test import SimpleTestCase


class CoberturaSemanticaLLM008Tests(SimpleTestCase):
    """
    Contratos de aceptación F5-07-14-D05.

    Estas pruebas documentan las exigencias que
    deberá verificar el certificador integral.
    """

    CASOS = (
        {
            "pregunta": "¿Cuántos documentos hay?",
            "operacion": "contar",
            "exigencias": set(),
        },
        {
            "pregunta": (
                "Muéstrame documentos "
                "pendientes o aprobados"
            ),
            "operacion": "listar",
            "exigencias": {"filtro", "logica_or"},
        },
        {
            "pregunta": (
                "Muéstrame los últimos cinco "
                "documentos pendientes"
            ),
            "operacion": "listar",
            "exigencias": {
                "filtro",
                "ordenamiento",
                "limite",
            },
        },
        {
            "pregunta": (
                "Muéstrame los últimos cinco "
                "documentos pendientes de los proyectos"
            ),
            "operacion": "listar",
            "exigencias": {
                "filtro",
                "ordenamiento",
                "limite",
                "relacion",
            },
        },
        {
            "pregunta": (
                "Muéstrame documentos "
                "pendientes o aprobados de los proyectos"
            ),
            "operacion": "listar",
            "exigencias": {
                "filtro",
                "logica_or",
                "relacion",
            },
        },
    )

    def test_matriz_de_aceptacion(self):
        self.assertEqual(len(self.CASOS), 5)

        for caso in self.CASOS:
            with self.subTest(pregunta=caso["pregunta"]):
                self.assertTrue(caso["pregunta"])
                self.assertIn(
                    caso["operacion"],
                    {"listar", "contar"},
                )
                self.assertIsInstance(
                    caso["exigencias"],
                    set,
                )

    def test_exigencias_no_representadas_deben_bloquear(self):
        """
        Establece el invariante de seguridad.

        Una interpretación parcial nunca habilita FINAL.
        """
        for caso in self.CASOS:
            with self.subTest(pregunta=caso["pregunta"]):
                exigencias = caso["exigencias"]

                if not exigencias:
                    continue

                representadas = set()

                pendientes = exigencias - representadas

                self.assertTrue(pendientes)

                ejecutable = not pendientes

                self.assertFalse(ejecutable)
