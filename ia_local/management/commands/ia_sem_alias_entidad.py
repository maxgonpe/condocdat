from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from ia_local.services.semantica.aliases_entidad import (
    buscar_alias_entidad,
    guardar_alias_entidad,
    listar_aliases_entidad,
    validar_alias_entidad,
)


class Command(BaseCommand):

    help = (
        "IA-SEM002 - Administra y valida aliases locales "
        "de entidades Django."
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

        if expresion_validar:

            if not modelo:
                raise CommandError(
                    "--modelo es obligatorio con --validar"
                )

            salida = validar_alias_entidad(
                expresion=expresion_validar,
                modelo_destino=modelo,
            )

        elif expresion_crear:

            if not modelo:
                raise CommandError(
                    "--modelo es obligatorio con --crear"
                )

            salida = guardar_alias_entidad(
                expresion=expresion_crear,
                modelo_destino=modelo,
            )

        elif expresion_buscar:

            salida = buscar_alias_entidad(
                expresion_buscar
            )

        elif options.get(
            "listar"
        ):

            salida = {
                "ok":
                    True,

                "aliases":
                    listar_aliases_entidad(
                        incluir_inactivos=bool(
                            options.get(
                                "inactivos"
                            )
                        )
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