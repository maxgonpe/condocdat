from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.semantica.politica_prioridad import (
    describir_politica,
    resolver_con_politica,
)


class Command(BaseCommand):

    help = (
        "IA-SEM008 - Aplica y expone la política "
        "formal de prioridad semántica."
    )


    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "expresion",
            nargs="?",
            default="",
        )

        parser.add_argument(
            "--modelo",
            type=str,
            default="",
        )

        parser.add_argument(
            "--campo",
            type=str,
            default="",
        )

        parser.add_argument(
            "--politica",
            action="store_true",
        )

        parser.add_argument(
            "--sin-reglas",
            action="store_true",
        )


    def handle(
        self,
        *args,
        **options,
    ):

        if options.get(
            "politica"
        ):

            salida = describir_politica()

        else:

            expresion = (
                options.get(
                    "expresion"
                )
                or ""
            ).strip()

            salida = resolver_con_politica(
                expresion,
                modelo_contexto=(
                    options.get(
                        "modelo"
                    )
                    or None
                ),
                campo_contexto=(
                    options.get(
                        "campo"
                    )
                    or None
                ),
                incluir_reglas=(
                    not bool(
                        options.get(
                            "sin_reglas"
                        )
                    )
                ),
            )

        self.stdout.write(
            json.dumps(
                salida,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )