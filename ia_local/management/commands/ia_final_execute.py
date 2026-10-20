from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.final.ejecutor_consultas import (
    ejecutar_consulta,
)


class Command(BaseCommand):

    help = (
        "IA-FINAL003 - "
        "Ejecuta de forma segura contratos FINAL "
        "mediante HOST."
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

        resultado = ejecutar_consulta(
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