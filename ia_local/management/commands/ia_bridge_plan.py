from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.bridge.sem_a_host import (
    adaptar_sem_a_host,
)


class Command(BaseCommand):

    help = (
        "IA-BRIDGE001 - Traduce una resolución SEM "
        "a un plan HOST validado sin ejecutar ORM."
    )


    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "expresion",
            type=str,
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
            "--limite",
            type=int,
            default=20,
        )


    def handle(
        self,
        *args,
        **options,
    ):

        salida = adaptar_sem_a_host(
            options[
                "expresion"
            ],
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
            limite=options.get(
                "limite"
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