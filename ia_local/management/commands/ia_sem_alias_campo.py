from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from ia_local.services.semantica.aliases_campo import (
    buscar_alias_campo,
    guardar_alias_campo,
    listar_aliases_campo,
    validar_alias_campo,
)


class Command(BaseCommand):

    help = (
        "IA-SEM003 - Administra y valida aliases "
        "locales de campos Django."
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
            "--campo",
            type=str,
            default="",
        )

        parser.add_argument(
            "--listar",
            action="store_true",
        )

        parser.add_argument(
            "--inactivos",
            action="store_true",
        )


    def handle(
        self,
        *args,
        **options,
    ):

        expresion_validar = (
            options.get(
                "validar"
            )
            or ""
        ).strip()

        expresion_crear = (
            options.get(
                "crear"
            )
            or ""
        ).strip()

        expresion_buscar = (
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

        campo = (
            options.get(
                "campo"
            )
            or ""
        ).strip()

        if expresion_validar:

            if (
                not modelo
                or not campo
            ):
                raise CommandError(
                    "--modelo y --campo son obligatorios "
                    "con --validar"
                )

            salida = validar_alias_campo(
                modelo=modelo,
                expresion=expresion_validar,
                campo_destino=campo,
            )

        elif expresion_crear:

            if (
                not modelo
                or not campo
            ):
                raise CommandError(
                    "--modelo y --campo son obligatorios "
                    "con --crear"
                )

            salida = guardar_alias_campo(
                modelo=modelo,
                expresion=expresion_crear,
                campo_destino=campo,
            )

        elif expresion_buscar:

            if not modelo:
                raise CommandError(
                    "--modelo es obligatorio "
                    "con --buscar"
                )

            salida = buscar_alias_campo(
                modelo=modelo,
                expresion=expresion_buscar,
            )

        elif options.get(
            "listar"
        ):

            salida = {
                "ok":
                    True,

                "aliases":
                    listar_aliases_campo(
                        modelo=(
                            modelo
                            or None
                        ),
                        incluir_inactivos=bool(
                            options.get(
                                "inactivos"
                            )
                        ),
                    ),

                "llm_invocado":
                    False,
            }

        else:

            raise CommandError(
                "Use --validar, --crear, --buscar o --listar."
            )

        self.stdout.write(
            json.dumps(
                salida,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )