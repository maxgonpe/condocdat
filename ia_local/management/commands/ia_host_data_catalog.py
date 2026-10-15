from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.host.catalogo_datos import (
    buscar_modelo_datos,
    construir_catalogo_datos,
)


class Command(BaseCommand):

    help = (
        "IA-HOST015: inspecciona el catálogo "
        "portable de modelos y campos de datos."
    )

    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "modelo",
            nargs="?",
            default=None,
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

        referencia = options[
            "modelo"
        ]

        if referencia:

            resultado = buscar_modelo_datos(
                referencia
            )

        else:

            resultado = (
                construir_catalogo_datos()
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
            "IA-HOST015 - CATALOGO DE DATOS"
        )
        self.stdout.write(
            "=" * 100
        )

        self.stdout.write(
            f"Modelos: {len(resultado)}"
        )

        for modelo in resultado:

            self.stdout.write("")
            self.stdout.write(
                (
                    f"{modelo['label']} "
                    f"-> {modelo['tabla']}"
                )
            )

            self.stdout.write(
                (
                    "  campos consultables: "
                    + ", ".join(
                        modelo[
                            "campos_consultables"
                        ]
                    )
                )
            )

        self.stdout.write("")
        self.stdout.write(
            "=" * 100
        )
