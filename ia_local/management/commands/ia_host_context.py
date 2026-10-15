from django.core.management.base import BaseCommand

from ia_local.services.host.contexto_semantico import (
    construir_contexto_llm,
)


class Command(BaseCommand):
    help = (
        "Construye contexto semantico estructural "
        "para una futura consulta al LLM."
    )

    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "pregunta",
        )

        parser.add_argument(
            "--profundidad",
            type=int,
            default=3,
        )

    def handle(
        self,
        *args,
        **options,
    ):

        pregunta = options[
            "pregunta"
        ]

        profundidad = options[
            "profundidad"
        ]

        resultado = (
            construir_contexto_llm(
                pregunta,
                profundidad=profundidad,
            )
        )

        self.stdout.write("")
        self.stdout.write(
            "=" * 100
        )

        self.stdout.write(
            "IA-HOST011 - CONTEXTO SEMANTICO PARA LLM"
        )

        self.stdout.write(
            "=" * 100
        )

        self.stdout.write(
            f"Pregunta:       "
            f"{pregunta}"
        )

        self.stdout.write(
            f"Profundidad:    "
            f"{profundidad}"
        )

        self.stdout.write(
            f"Hay evidencia:  "
            f"{resultado['hay_evidencia']}"
        )

        self.stdout.write(
            f"Modelos:        "
            f"{resultado['deteccion']['modelos']}"
        )

        self.stdout.write(
            f"Simbolos:       "
            f"{resultado['deteccion']['simbolos']}"
        )

        self.stdout.write(
            f"URLs:           "
            f"{resultado['deteccion']['urls']}"
        )

        self.stdout.write(
            f"Caracteres:     "
            f"{resultado['caracteres']}"
        )

        self.stdout.write("")
        self.stdout.write(
            "CONTEXTO PARA LLM"
        )

        self.stdout.write(
            "-" * 100
        )

        self.stdout.write(
            resultado[
                "contexto_texto"
            ]
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "IA-HOST011 completado."
            )
        )