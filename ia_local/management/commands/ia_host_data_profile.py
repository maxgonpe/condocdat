from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.host.perfilador_datos import (
    campos_perfilables_modelo,
    perfilar_campo,
    perfilar_modelo,
)


class Command(BaseCommand):

    help = (
        "IA-HOST015: perfila valores reales de "
        "campos categóricos del proyecto anfitrión."
    )

    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "modelo",
        )

        parser.add_argument(
            "campo",
            nargs="?",
            default=None,
        )

        parser.add_argument(
            "--max-valores",
            type=int,
            default=25,
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

        modelo = options[
            "modelo"
        ]

        campo = options[
            "campo"
        ]

        max_valores = options[
            "max_valores"
        ]

        if campo:

            resultado = perfilar_campo(
                modelo,
                campo,
                max_valores=max_valores,
            )

        else:

            resultado = perfilar_modelo(
                modelo,
                max_valores=max_valores,
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
            "IA-HOST015 - PERFIL DE DATOS"
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

        if campo:

            self.stdout.write(
                f"Campo: {resultado.get('campo')}"
            )

            self.stdout.write("")
            self.stdout.write(
                json.dumps(
                    resultado,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )

        else:

            self.stdout.write(
                (
                    "Campos perfilables: "
                    + ", ".join(
                        campos_perfilables_modelo(
                            modelo
                        )
                    )
                )
            )

            self.stdout.write("")

            for perfil in resultado.get(
                "perfiles",
                [],
            ):

                self.stdout.write(
                    "-" * 100
                )

                self.stdout.write(
                    (
                        f"{perfil.get('campo')} "
                        f"({perfil.get('tipo')})"
                    )
                )

                for item in perfil.get(
                    "valores",
                    [],
                ):

                    self.stdout.write(
                        (
                            f"  {item.get('valor')!r}"
                            f" -> "
                            f"{item.get('frecuencia')}"
                        )
                    )

        self.stdout.write("")
        self.stdout.write(
            "=" * 100
        )
