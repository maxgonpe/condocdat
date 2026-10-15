from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.host.intencion import (
    detectar_intencion,
)


class Command(BaseCommand):

    help = (
        "IA-HOST014: detecta la intención portable "
        "de una pregunta."
    )

    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "pregunta",
        )

        parser.add_argument(
            "--json",
            action="store_true",
            dest="salida_json",
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

        resultado = detectar_intencion(
            pregunta,
            profundidad=profundidad,
        )

        if options[
            "salida_json"
        ]:

            self.stdout.write(
                json.dumps(
                    resultado,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )

            return

        self.stdout.write("")
        self.stdout.write(
            "=" * 100
        )
        self.stdout.write(
            "IA-HOST014 - INTENCION PORTABLE"
        )
        self.stdout.write(
            "=" * 100
        )

        campos = (
            (
                "Pregunta",
                resultado.get(
                    "pregunta"
                ),
            ),
            (
                "Tipo",
                resultado.get(
                    "tipo"
                ),
            ),
            (
                "Subtipo",
                resultado.get(
                    "subtipo"
                ),
            ),
            (
                "Acción",
                resultado.get(
                    "accion"
                ),
            ),
            (
                "Entidad",
                resultado.get(
                    "entidad"
                ),
            ),
            (
                "Confianza",
                resultado.get(
                    "confianza"
                ),
            ),
            (
                "Origen",
                resultado.get(
                    "origen"
                ),
            ),
            (
                "LLM invocado",
                resultado.get(
                    "llm_invocado",
                    False,
                ),
            ),
            (
                "Validado",
                resultado.get(
                    "validado"
                ),
            ),
            (
                "Razón",
                resultado.get(
                    "razon"
                ),
            ),
        )

        for titulo, valor in campos:

            self.stdout.write("")
            self.stdout.write(
                titulo.upper()
            )
            self.stdout.write(
                str(
                    valor
                )
            )

        deteccion = resultado.get(
            "contexto_deteccion"
        )

        if deteccion is not None:

            self.stdout.write("")
            self.stdout.write(
                "DETECCION HOST"
            )

            self.stdout.write(
                json.dumps(
                    deteccion,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )

        self.stdout.write("")
        self.stdout.write(
            "=" * 100
        )
