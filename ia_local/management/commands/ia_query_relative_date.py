from __future__ import annotations

import json
from datetime import date

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from ia_local.services.query.fechas_relativas import (
    componer_fechas_relativas,
)


class Command(BaseCommand):

    help = (
        "IA-QUERY006: interpreta fechas relativas "
        "sin ejecutar ORM."
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
            "--fecha-referencia",
            type=str,
            default=None,
            help=(
                "Fecha YYYY-MM-DD para pruebas "
                "deterministas."
            ),
        )


    def handle(
        self,
        *args,
        **options,
    ):

        fecha_referencia = None

        if options[
            "fecha_referencia"
        ]:

            try:

                fecha_referencia = (
                    date.fromisoformat(
                        options[
                            "fecha_referencia"
                        ]
                    )
                )

            except ValueError as exc:

                raise CommandError(
                    (
                        "--fecha-referencia debe "
                        "usar YYYY-MM-DD."
                    )
                ) from exc

        resultado = (
            componer_fechas_relativas(
                options[
                    "pregunta"
                ],
                limite=options[
                    "limite"
                ],
                fecha_referencia=(
                    fecha_referencia
                ),
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