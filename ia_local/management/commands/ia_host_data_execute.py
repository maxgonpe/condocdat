from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.host.ejecutor_datos import (
    ejecutar_plan_datos,
)
from ia_local.services.host.interprete_datos import (
    interpretar_consulta_datos,
)
from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)


class Command(BaseCommand):

    help = (
        "IA-HOST015: interpreta, valida y ejecuta "
        "una consulta ORM portable y segura."
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

        pregunta = options[
            "pregunta"
        ]

        modelo = options[
            "modelo"
        ]

        interpretacion = (
            interpretar_consulta_datos(
                pregunta,
                modelo=modelo,
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

            if not validacion.get(
                "plan_validado"
            ):

                resultado = {
                    "ok":
                        False,

                    "fase":
                        "validacion",

                    "interpretacion":
                        interpretacion,

                    "validacion":
                        validacion,
                }

            else:

                ejecucion = ejecutar_plan_datos(
                    validacion[
                        "plan"
                    ]
                )

                resultado = {
                    "ok":
                        ejecucion.get(
                            "ok"
                        ),

                    "fase":
                        "ejecucion",

                    "interpretacion":
                        interpretacion,

                    "validacion":
                        validacion,

                    "ejecucion":
                        ejecucion,
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
            "IA-HOST015 - EJECUCION DE DATOS"
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

        ejecucion = resultado.get(
            "ejecucion"
        )

        if ejecucion:

            self.stdout.write("")
            self.stdout.write(
                "EJECUCION"
            )

            self.stdout.write(
                json.dumps(
                    ejecucion,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )

        else:

            validacion = resultado.get(
                "validacion"
            )

            if validacion:

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
