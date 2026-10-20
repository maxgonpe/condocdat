from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.query.condiciones_and import (
    construir_plan_and,
)


class Command(BaseCommand):

    help = (
        "IA-QUERY001 - Construye y valida "
        "consultas con múltiples condiciones AND."
    )


    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "pregunta",
            type=str,
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

        resultado = construir_plan_and(
            options[
                "pregunta"
            ],
            limite=options.get(
                "limite",
                20,
            ),
        )

        self.stdout.write(
            json.dumps(
                resultado,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )