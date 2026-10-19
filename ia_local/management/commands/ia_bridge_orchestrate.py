from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.bridge.orquestador_principal import (
    consultar_orquestado,
)


class Command(BaseCommand):

    help = (
        "IA-BRIDGE009 - Ejecuta el orquestador principal "
        "con fallback legado opcional."
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

        parser.add_argument(
            "--fallback-legado",
            action="store_true",
            help=(
                "Autoriza explícitamente el fallback "
                "al motor histórico cuando el fallo "
                "BRIDGE sea elegible."
            ),
        )


    def handle(
        self,
        *args,
        **options,
    ):

        resultado = consultar_orquestado(
            options[
                "pregunta"
            ],
            limite=options.get(
                "limite",
                20,
            ),
            diagnostico=options.get(
                "diagnostico",
                False,
            ),
            permitir_fallback_legado=options.get(
                "fallback_legado",
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