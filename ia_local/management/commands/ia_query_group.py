from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.query.grupos_logicos import (
    componer_grupos_logicos,
)


class Command(BaseCommand):
    help = (
        "IA-QUERY003: construye agrupaciones lógicas "
        "AND/OR explícitas sin ejecutar ORM."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "pregunta",
            type=str,
            help=(
                "Consulta con agrupación lógica "
                "explícita."
            ),
        )

        parser.add_argument(
            "--limite",
            type=int,
            default=20,
            help=(
                "Límite solicitado a HOST para "
                "cada condición."
            ),
        )

    def handle(
        self,
        *args,
        **options,
    ):
        resultado = (
            componer_grupos_logicos(
                options["pregunta"],
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