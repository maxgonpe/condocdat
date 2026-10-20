from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.final.contrato_respuesta import (
    construir_contrato_respuesta,
)


class Command(BaseCommand):

    help = (
        "IA-FINAL002 - "
        "Normaliza una consulta al contrato FINAL."
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
            construir_contrato_respuesta(
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