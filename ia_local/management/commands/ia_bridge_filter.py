from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.bridge.campo_operador_valor import (
    componer_campo_operador_valor,
)


class Command(BaseCommand):

    help = (
        "IA-BRIDGE003 - Resuelve campo + operador "
        "+ valor libre y genera un plan HOST validado "
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

        salida = (
            componer_campo_operador_valor(
                options[
                    "expresion"
                ],
                limite=options.get(
                    "limite"
                ),
            )
        )

        self.stdout.write(
            json.dumps(
                salida,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )