from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.bridge.compositor_sem_host import (
    componer_sem_a_host,
)


class Command(BaseCommand):

    help = (
        "IA-BRIDGE002 - Compone componentes SEM "
        "parciales y genera un plan HOST validado "
        "sin ejecutar ORM."
    )


    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "expresion",
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

        salida = componer_sem_a_host(
            options[
                "expresion"
            ],
            limite=options.get(
                "limite"
            ),
        )

        self.stdout.write(
            json.dumps(
                salida,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )