from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.query.consultas_relacionales import (
    componer_consulta_relacional,
)


class Command(BaseCommand):

    help = (
        "Prueba IA-QUERY011: "
        "consultas relacionales compuestas."
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

        resultado = (
            componer_consulta_relacional(
                options[
                    "pregunta"
                ],
                limite=options[
                    "limite"
                ],
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