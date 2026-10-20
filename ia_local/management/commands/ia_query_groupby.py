from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.query.agrupamientos import (
    componer_agrupamiento,
)


class Command(BaseCommand):

    help = (
        "Prueba IA-QUERY010: "
        "agrupamientos declarativos."
    )

    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "pregunta",
            type=str,
        )

    def handle(
        self,
        *args,
        **options,
    ):

        resultado = (
            componer_agrupamiento(
                options[
                    "pregunta"
                ]
            )
        )

        self.stdout.write(
            json.dumps(
                resultado,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )