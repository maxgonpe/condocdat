from django.test import SimpleTestCase

from ia_local.services.llm.cobertura_semantica import (
    evaluar_cobertura_semantica,
)


class VerificadorCoberturaLLM008Tests(SimpleTestCase):

    def evaluar(self, pregunta, restricciones, **extras):
        consolidacion = {
            "ok": True,
            "pregunta": pregunta,
            "operacion": "listar",
            "restricciones": restricciones,
            "omisiones_conocidas": [],
            "restricciones_pendientes_host": [],
            "requiere_revision": False,
            **extras,
        }
        return evaluar_cobertura_semantica(
            pregunta, consolidacion
        )

    def test_or_comprimido(self):
        pregunta = "Muéstrame documentos pendientes o aprobados"

        resultado = self.evaluar(pregunta, [
            {
                "tipo": "filtro",
                "evidencia_textual": "pendientes o aprobados",
            }
        ])

        self.assertIn(
            "disyuncion_no_atomizada",
            resultado["componentes_pendientes"],
        )
        self.assertFalse(resultado["ejecutable"])

    def test_relacion_omitida(self):
        pregunta = (
            "Muéstrame documentos pendientes "
            "de los proyectos"
        )

        resultado = self.evaluar(pregunta, [
            {
                "tipo": "filtro",
                "evidencia_textual": "pendientes",
            }
        ])

        self.assertIn(
            "alcance_relacional_no_representado",
            resultado["componentes_pendientes"],
        )

    def test_orden_limite_relacion(self):
        pregunta = (
            "Muéstrame los últimos cinco documentos "
            "pendientes de los proyectos"
        )

        resultado = self.evaluar(pregunta, [
            {"tipo": "ordenamiento", "evidencia_textual": "últimos"},
            {"tipo": "limite", "evidencia_textual": "cinco"},
            {"tipo": "filtro", "evidencia_textual": "pendientes"},
        ])

        self.assertIn(
            "alcance_relacional_no_representado",
            resultado["componentes_pendientes"],
        )
        self.assertIn(
            "campo_orden_no_certificado",
            resultado["componentes_pendientes"],
        )
        self.assertIn(
            "valor_limite_no_certificado",
            resultado["componentes_pendientes"],
        )

    def test_no_acepta_certificacion_inyectada(self):
        pregunta = "Muéstrame documentos pendientes"

        resultado = self.evaluar(
            pregunta,
            [],
            cobertura_verificada=True,
            ejecutable=True,
            ejecutado=True,
        )

        self.assertFalse(resultado["cobertura_verificada"])
        self.assertFalse(resultado["ejecutable"])
        self.assertFalse(resultado["ejecutado"])

    def test_pregunta_alterada(self):
        resultado = evaluar_cobertura_semantica(
            "Muéstrame documentos pendientes",
            {
                "ok": True,
                "pregunta": "Muéstrame documentos aprobados",
                "restricciones": [],
            },
        )

        self.assertIn(
            "pregunta_original_no_coincidente",
            resultado["componentes_pendientes"],
        )

    def test_conteo_simple_no_autorizado_automaticamente(self):
        pregunta = "¿Cuántos documentos hay?"

        resultado = self.evaluar(
            pregunta,
            [],
            operacion="contar",
        )

        self.assertIn(
            "certificacion_integral_no_disponible",
            resultado["componentes_pendientes"],
        )
        self.assertFalse(resultado["ejecutable"])
