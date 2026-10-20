from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.query.agregaciones import (
    componer_agregacion,
)


class Command(BaseCommand):

    help = (
        "IA-QUERY009: compone agregaciones naturales "
        "sin ejecutar ORM."
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
            componer_agregacion(
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