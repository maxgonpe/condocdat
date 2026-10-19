from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.semantica.resolvedor_ambiguedades import (
    resolver_expresion_semantica,
)


class Command(BaseCommand):

    help = (
        "IA-SEM006 - Resuelve expresiones y detecta "
        "ambigüedades usando SEM001-SEM005."
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
            "--modelo",
            type=str,
            default="",
        )

        parser.add_argument(
            "--campo",
            type=str,
            default="",
        )

        parser.add_argument(
            "--sin-reglas",
            action="store_true",
        )


    def handle(
        self,
        *args,
        **options,
    ):

        salida = resolver_expresion_semantica(
            options[
                "expresion"
            ],
            modelo_contexto=(
                options.get(
                    "modelo"
                )
                or None
            ),
            campo_contexto=(
                options.get(
                    "campo"
                )
                or None
            ),
            incluir_reglas=(
                not bool(
                    options.get(
                        "sin_reglas"
                    )
                )
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