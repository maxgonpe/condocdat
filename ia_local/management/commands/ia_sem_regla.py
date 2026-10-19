from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from ia_local.services.semantica.reglas_declarativas import (
    buscar_regla_declarativa,
    guardar_regla_declarativa,
    validar_regla_declarativa,
)


class Command(BaseCommand):

    help = (
        "IA-SEM005 - Valida, registra y consulta "
        "reglas semánticas declarativas."
    )


    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "--validar",
            type=str,
            default="",
        )

        parser.add_argument(
            "--crear",
            type=str,
            default="",
        )

        parser.add_argument(
            "--buscar",
            type=str,
            default="",
        )

        parser.add_argument(
            "--modelo",
            type=str,
            default="",
        )

        parser.add_argument(
            "--operacion",
            type=str,
            default="listar",
        )

        parser.add_argument(
            "--condiciones",
            type=str,
            default="[]",
            help=(
                "JSON con condiciones, por ejemplo: "
                '[{"campo":"status",'
                '"operador":"exact",'
                '"valor":"PENDING"}]'
            ),
        )


    def handle(
        self,
        *args,
        **options,
    ):

        validar = (
            options.get(
                "validar"
            )
            or ""
        ).strip()

        crear = (
            options.get(
                "crear"
            )
            or ""
        ).strip()

        buscar = (
            options.get(
                "buscar"
            )
            or ""
        ).strip()

        modelo = (
            options.get(
                "modelo"
            )
            or ""
        ).strip()

        operacion = (
            options.get(
                "operacion"
            )
            or "listar"
        ).strip()

        if buscar:

            salida = buscar_regla_declarativa(
                buscar
            )

        elif validar or crear:

            if not modelo:

                raise CommandError(
                    "--modelo es obligatorio."
                )

            try:

                condiciones = json.loads(
                    options.get(
                        "condiciones"
                    )
                    or "[]"
                )

            except json.JSONDecodeError as exc:

                raise CommandError(
                    (
                        "JSON inválido en "
                        "--condiciones: "
                        f"{exc}"
                    )
                )

            if validar:

                salida = (
                    validar_regla_declarativa(
                        expresion=validar,
                        modelo=modelo,
                        operacion=operacion,
                        condiciones=condiciones,
                    )
                )

            else:

                salida = (
                    guardar_regla_declarativa(
                        expresion=crear,
                        modelo=modelo,
                        operacion=operacion,
                        condiciones=condiciones,
                    )
                )

        else:

            raise CommandError(
                "Use --validar, --crear o --buscar."
            )

        self.stdout.write(
            json.dumps(
                salida,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )