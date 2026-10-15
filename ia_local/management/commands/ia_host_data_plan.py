from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.host.interprete_datos import (
    interpretar_consulta_datos,
)


class Command(BaseCommand):

    help = (
        "IA-HOST015: genera un plan declarativo "
        "para una consulta de datos."
    )

    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "modelo",
        )

        parser.add_argument(
            "pregunta",
        )

        parser.add_argument(
            "--json",
            action="store_true",
            dest="salida_json",
        )

    def handle(
        self,
        *args,
        **options,
    ):

        resultado = interpretar_consulta_datos(
            options[
                "pregunta"
            ],
            modelo=options[
                "modelo"
            ],
        )

        if options[
            "salida_json"
        ]:

            self.stdout.write(
                json.dumps(
                    resultado,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )

            return

        self.stdout.write("")
        self.stdout.write(
            "=" * 100
        )
        self.stdout.write(
            "IA-HOST015 - PLAN DE DATOS"
        )
        self.stdout.write(
            "=" * 100
        )

        self.stdout.write(
            f"OK: {resultado.get('ok')}"
        )

        self.stdout.write(
            f"Modelo: {resultado.get('modelo')}"
        )

        self.stdout.write(
            (
                "LLM invocado: "
                f"{resultado.get('llm_invocado')}"
            )
        )

        propuesta = resultado.get(
            "propuesta"
        )

        if propuesta is not None:

            self.stdout.write("")
            self.stdout.write(
                "PROPUESTA"
            )

            self.stdout.write(
                json.dumps(
                    propuesta,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )

        error = resultado.get(
            "error"
        )

        if error is not None:

            self.stdout.write("")
            self.stdout.write(
                "ERROR"
            )

            self.stdout.write(
                json.dumps(
                    error,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )

        self.stdout.write("")
        self.stdout.write(
            "=" * 100
        )
