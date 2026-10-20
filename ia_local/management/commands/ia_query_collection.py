from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.query.colecciones_estructuras import (
    describir_coleccion_natural,
)


class Command(BaseCommand):

    help = (
        "IA-QUERY008: clasifica colecciones y "
        "estructuras sin ejecutar ORM."
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
            describir_coleccion_natural(
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