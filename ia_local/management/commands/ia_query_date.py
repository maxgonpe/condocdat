from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.query.fechas_absolutas import (
    componer_fechas_absolutas,
)


class Command(BaseCommand):

    help = (
        "IA-QUERY005: interpreta fechas absolutas "
        "y rangos temporales sin ejecutar ORM."
    )


    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "pregunta",
            type=str,
            help=(
                "Consulta con fecha absoluta o rango."
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
            componer_fechas_absolutas(
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