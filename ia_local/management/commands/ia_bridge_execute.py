from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.bridge.ejecutor_controlado import (
    ejecutar_consulta_bridge,
)


class Command(BaseCommand):

    help = (
        "IA-BRIDGE004 - Ejecuta mediante HOST un plan "
        "SEM/BRIDGE previamente validado."
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

        resultado = ejecutar_consulta_bridge(
            options[
                "expresion"
            ],
            limite=options.get(
                "limite"
            ),
        )

        self.stdout.write(
            json.dumps(
                resultado,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )