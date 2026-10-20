from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.query.ordenamiento_natural import (
    componer_ordenamiento_natural,
)


class Command(BaseCommand):

    help = (
        "IA-QUERY004: interpreta ordenamiento natural "
        "y solicita certificación a HOST sin ejecutar ORM."
    )


    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "pregunta",
            type=str,
            help=(
                "Consulta con ordenamiento explícito."
            ),
        )

        parser.add_argument(
            "--limite",
            type=int,
            default=20,
            help=(
                "Límite solicitado al plan HOST."
            ),
        )


    def handle(
        self,
        *args,
        **options,
    ):

        resultado = (
            componer_ordenamiento_natural(
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
