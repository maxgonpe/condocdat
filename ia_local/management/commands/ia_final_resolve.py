from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.final.orquestador_consultas import (
    resolver_consulta,
)


class Command(BaseCommand):

    help = (
        "IA-FINAL001 - "
        "Orquestador único de interpretación."
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

        resultado = resolver_consulta(
            options[
                "pregunta"
            ]
        )

        self.stdout.write(
            json.dumps(
                resultado,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )