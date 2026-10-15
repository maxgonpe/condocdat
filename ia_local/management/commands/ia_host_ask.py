from django.core.management.base import BaseCommand

from ia_local.services.host.respuesta_llm import (
    responder_pregunta_host,
)


class Command(BaseCommand):
    help = (
        "Responde preguntas estructurales sobre el "
        "proyecto usando HOST011 + Ollama/Qwen."
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

        parser.add_argument(
            "--mostrar-contexto",
            action="store_true",
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

        mostrar_contexto = options[
            "mostrar_contexto"
        ]

        self.stdout.write("")
        self.stdout.write(
            "=" * 100
        )

        self.stdout.write(
            "IA-HOST012 - CONSULTA ESTRUCTURAL CON QWEN"
        )

        self.stdout.write(
            "=" * 100
        )

        self.stdout.write(
            f"Pregunta:    {pregunta}"
        )

        self.stdout.write(
            f"Profundidad: {profundidad}"
        )

        resultado = (
            responder_pregunta_host(
                pregunta,
                profundidad=profundidad,
            )
        )

        self.stdout.write(
            f"Evidencia:   "
            f"{resultado.get('hay_evidencia')}"
        )

        self.stdout.write(
            f"LLM usado:   "
            f"{resultado.get('llm_invocado')}"
        )

        deteccion = resultado.get(
            "deteccion",
            {},
        )

        self.stdout.write(
            f"Deteccion:   "
            f"modelos={deteccion.get('modelos', 0)} "
            f"simbolos={deteccion.get('simbolos', 0)} "
            f"urls={deteccion.get('urls', 0)}"
        )

        if not resultado[
            "ok"
        ]:

            self.stdout.write("")
            self.stdout.write(
                self.style.ERROR(
                    "ERROR"
                )
            )

            self.stdout.write(
                str(
                    resultado.get(
                        "error"
                    )
                )
            )

            return

        if resultado.get(
            "modelo"
        ):

            self.stdout.write(
                f"Modelo LLM:  "
                f"{resultado['modelo']}"
            )

        self.stdout.write("")
        self.stdout.write(
            "RESPUESTA"
        )

        self.stdout.write(
            "-" * 100
        )

        self.stdout.write(
            resultado[
                "respuesta"
            ]
        )

        metricas = resultado.get(
            "metricas"
        )

        if metricas:

            self.stdout.write("")
            self.stdout.write(
                "METRICAS"
            )

            self.stdout.write(
                "-" * 100
            )

            self.stdout.write(
                f"Prompt tokens: "
                f"{metricas.get('prompt_eval_count')}"
            )

            self.stdout.write(
                f"Output tokens: "
                f"{metricas.get('eval_count')}"
            )

            self.stdout.write(
                f"Duracion ns:   "
                f"{metricas.get('total_duration')}"
            )

        if mostrar_contexto:

            self.stdout.write("")
            self.stdout.write(
                "CONTEXTO ENTREGADO AL LLM"
            )

            self.stdout.write(
                "-" * 100
            )

            self.stdout.write(
                resultado[
                    "contexto"
                ]
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "IA-HOST012 completado."
            )
        )