from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.bridge.respuesta_compacta import (
    consultar_respuesta_compacta,
)


class Command(BaseCommand):

    help = (
        "IA-BRIDGE005 - Ejecuta una consulta y devuelve "
        "una respuesta compacta preparada para API/interfaz."
    )


    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "pregunta",
            type=str,
        )

        parser.add_argument(
            "--limite",
            type=int,
            default=20,
        )

        parser.add_argument(
            "--diagnostico",
            action="store_true",
        )


    def handle(
        self,
        *args,
        **options,
    ):

        resultado = consultar_respuesta_compacta(
            options[
                "pregunta"
            ],
            limite=options.get(
                "limite"
            ),
            incluir_diagnostico=options.get(
                "diagnostico",
                False,
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