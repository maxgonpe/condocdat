from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.host.interprete_datos import (
    interpretar_consulta_datos,
)
from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)


class Command(BaseCommand):

    help = (
        "IA-HOST015: interpreta y valida un plan "
        "de consulta de datos sin ejecutar ORM."
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

        interpretacion = (
            interpretar_consulta_datos(
                options[
                    "pregunta"
                ],
                modelo=options[
                    "modelo"
                ],
            )
        )

        if not interpretacion.get(
            "ok"
        ):

            resultado = {
                "ok":
                    False,

                "fase":
                    "interpretacion",

                "interpretacion":
                    interpretacion,
            }

        else:

            validacion = validar_plan_datos(
                interpretacion[
                    "propuesta"
                ]
            )

            resultado = {
                "ok":
                    validacion.get(
                        "ok"
                    ),

                "fase":
                    "validacion",

                "interpretacion":
                    interpretacion,

                "validacion":
                    validacion,
            }

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
            "IA-HOST015 - VALIDACION DE PLAN"
        )

        self.stdout.write(
            "=" * 100
        )

        self.stdout.write(
            f"OK: {resultado.get('ok')}"
        )

        self.stdout.write(
            f"Fase: {resultado.get('fase')}"
        )

        validacion = resultado.get(
            "validacion"
        )

        if validacion:

            self.stdout.write(
                (
                    "Plan validado: "
                    f"{validacion.get('plan_validado')}"
                )
            )

            self.stdout.write("")
            self.stdout.write(
                "PLAN"
            )

            self.stdout.write(
                json.dumps(
                    validacion.get(
                        "plan"
                    ),
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )

            self.stdout.write("")
            self.stdout.write(
                "ERRORES"
            )

            self.stdout.write(
                json.dumps(
                    validacion.get(
                        "errores"
                    ),
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )

        self.stdout.write("")
        self.stdout.write(
            "=" * 100
        )
