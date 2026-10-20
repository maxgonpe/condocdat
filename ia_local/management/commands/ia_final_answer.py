from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.final.formateador_respuesta import (
    responder_consulta,
)


class Command(BaseCommand):

    help = (
        "IA-FINAL004 - "
        "Entrega la respuesta pública formateada."
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

        resultado = responder_consulta(
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