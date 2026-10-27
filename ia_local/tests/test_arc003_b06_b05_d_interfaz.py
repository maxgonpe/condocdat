"""
ARC003-B06-B03-B05-D

Regresiones estructurales de index.html.
No simulan la ejecucion del navegador.
"""

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class TestARC003B05DInterfaz(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.archivo = (
            Path(settings.BASE_DIR)
            / "ia_local"
            / "templates"
            / "ia_local"
            / "index.html"
        )

        cls.html = cls.archivo.read_text(
            encoding="utf-8"
        )

    def test_01_rechazo_antes_de_exportar(self):
        html = self.html

        rechazo = html.index(
            "const respuestaRechazada = ("
        )

        control = html.index(
            "if (respuestaRechazada)"
        )

        exportacion = html.index(
            "ultimaSalida = construirSalidaExportable(data);"
        )

        self.assertLess(rechazo, control)
        self.assertLess(control, exportacion)

        bloque = html[control:exportacion]

        self.assertIn(
            "desactivarExportaciones();",
            bloque,
        )

        self.assertIn(
            "ultimaSalida = null;",
            bloque,
        )

        self.assertIn(
            'mostrarEstado(',
            bloque,
        )

        self.assertIn(
            "return;",
            bloque,
        )

    def test_02_e03_exige_ejecucion(self):
        html = self.html

        self.assertIn(
            'data.version.startsWith("IA-ARC003-B06-B01")',
            html,
        )

        self.assertIn(
            "data.ok !== true || data.ejecutado !== true",
            html,
        )

        self.assertIn(
            'esContratoE03 ? "E03 certificado" : "FINAL004"',
            html,
        )

    def test_03_ruta_contextual_y_csrf(self):
        html = self.html

        self.assertIn(
            "{% url 'ia_local:consultar_contextual' %}",
            html,
        )

        self.assertIn(
            '"csrfmiddlewaretoken"',
            html,
        )

        self.assertIn(
            'data.estado === "requiere_aclaracion"',
            html,
        )
