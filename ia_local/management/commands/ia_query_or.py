from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from ia_local.services.query.condiciones_or import (
    componer_condiciones_or,
)


class Command(BaseCommand):
    help = (
        "IA-QUERY002: compone múltiples condiciones OR "
        "sin ejecutar ORM."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "pregunta",
            type=str,
            help="Consulta en lenguaje natural.",
        )

        parser.add_argument(
            "--limite",
            type=int,
            default=20,
            help="Límite solicitado para cada rama HOST.",
        )

    def handle(self, *args, **options):
        resultado = componer_condiciones_or(
            options["pregunta"],
            limite=options["limite"],
        )

        self.stdout.write(
            json.dumps(
                resultado,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )