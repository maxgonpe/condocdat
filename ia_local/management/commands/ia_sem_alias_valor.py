from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from ia_local.services.semantica.aliases_valor import (
    buscar_alias_valor,
    guardar_alias_valor,
    inspeccionar_campo_valores,
    validar_alias_valor,
)


class Command(BaseCommand):

    help = (
        "IA-SEM004 - Inspecciona, valida y registra "
        "interpretaciones locales de valores."
    )


    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "--inspeccionar",
            action="store_true",
        )

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
            "--campo",
            type=str,
            default="",
        )

        parser.add_argument(
            "--valor",
            type=str,
            default="",
        )


    def handle(
        self,
        *args,
        **options,
    ):

        modelo = (
            options.get(
                "modelo"
            )
            or ""
        ).strip()

        campo = (
            options.get(
                "campo"
            )
            or ""
        ).strip()

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

        valor = (
            options.get(
                "valor"
            )
            or ""
        ).strip()

        if not modelo or not campo:

            raise CommandError(
                "--modelo y --campo son obligatorios."
            )

        if options.get(
            "inspeccionar"
        ):

            salida = inspeccionar_campo_valores(
                modelo=modelo,
                campo=campo,
            )

        elif validar:

            salida = validar_alias_valor(
                modelo=modelo,
                campo=campo,
                expresion=validar,
                valor_destino=valor,
            )

        elif crear:

            salida = guardar_alias_valor(
                modelo=modelo,
                campo=campo,
                expresion=crear,
                valor_destino=valor,
            )

        elif buscar:

            salida = buscar_alias_valor(
                modelo=modelo,
                campo=campo,
                expresion=buscar,
            )

        else:

            raise CommandError(
                "Use --inspeccionar, --validar, "
                "--crear o --buscar."
            )

        self.stdout.write(
            json.dumps(
                salida,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )