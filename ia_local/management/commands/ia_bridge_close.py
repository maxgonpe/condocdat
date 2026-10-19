from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from ia_local.services.bridge.auditoria_cierre import (
    auditar_cierre_bridge,
)


class Command(BaseCommand):

    help = (
        "IA-BRIDGE010 - Auditoría final de "
        "regresión, seguridad y portabilidad."
    )


    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "--pregunta",
            type=str,
            default=None,
            help=(
                "Pregunta runtime opcional "
                "que BRIDGE debe resolver."
            ),
        )

        parser.add_argument(
            "--limite",
            type=int,
            default=1,
        )

        parser.add_argument(
            "--json",
            action="store_true",
            help=(
                "Muestra solamente el resultado "
                "JSON completo."
            ),
        )


    def handle(
        self,
        *args,
        **options,
    ):

        resultado = (
            auditar_cierre_bridge(
                pregunta_runtime=(
                    options.get(
                        "pregunta"
                    )
                ),
                limite_runtime=(
                    options.get(
                        "limite",
                        1,
                    )
                ),
            )
        )

        if options.get(
            "json"
        ):

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
                ""
            )

            self.stdout.write(
                "=" * 80
            )

            self.stdout.write(
                "IA-BRIDGE010 - AUDITORÍA FINAL"
            )

            self.stdout.write(
                "=" * 80
            )

            self.stdout.write(
                ""
            )

            self.stdout.write(
                (
                    f"Estado:        "
                    f"{resultado['estado']}"
                )
            )

            self.stdout.write(
                (
                    f"Pruebas:       "
                    f"{resultado['total_pruebas']}"
                )
            )

            self.stdout.write(
                (
                    f"Correctas:     "
                    f"{resultado['total_ok']}"
                )
            )

            self.stdout.write(
                (
                    f"Fallos:        "
                    f"{resultado['total_fallos']}"
                )
            )

            self.stdout.write(
                ""
            )

            self.stdout.write(
                "RESULTADOS"
            )

            self.stdout.write(
                "-" * 80
            )

            for prueba in resultado[
                "pruebas"
            ]:

                marca = (
                    "OK"
                    if prueba.get(
                        "ok"
                    )
                    else "ERROR"
                )

                self.stdout.write(
                    (
                        f"[{marca}] "
                        f"{prueba['nombre']}: "
                        f"{prueba['detalle']}"
                    )
                )

            self.stdout.write(
                ""
            )

            self.stdout.write(
                "APPS HOST DETECTADAS"
            )

            self.stdout.write(
                "-" * 80
            )

            for app in resultado[
                "apps_host"
            ]:

                self.stdout.write(
                    app
                )

            self.stdout.write(
                ""
            )

        if not resultado.get(
            "ok",
            False,
        ):

            raise CommandError(
                (
                    "IA-BRIDGE010 detectó "
                    f"{resultado['total_fallos']} "
                    "invariante(s) incumplida(s)."
                )
            )