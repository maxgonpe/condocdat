from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from ia_local.services.semantica.aprendizaje_controlado import (
    confirmar_propuesta,
    listar_propuestas,
    obtener_propuesta,
    proponer_aprendizaje,
    rechazar_propuesta,
)


class Command(BaseCommand):

    help = (
        "IA-SEM007 - Aprendizaje semántico "
        "controlado mediante propuestas."
    )


    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "--proponer",
            action="store_true",
        )

        parser.add_argument(
            "--confirmar",
            type=int,
        )

        parser.add_argument(
            "--rechazar",
            type=int,
        )

        parser.add_argument(
            "--ver",
            type=int,
        )

        parser.add_argument(
            "--listar",
            action="store_true",
        )

        parser.add_argument(
            "--estado",
            type=str,
            default="",
        )

        parser.add_argument(
            "--tipo",
            type=str,
            default="",
        )

        parser.add_argument(
            "--expresion",
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

        parser.add_argument(
            "--operacion",
            type=str,
            default="listar",
        )

        parser.add_argument(
            "--condiciones",
            type=str,
            default="[]",
        )

        parser.add_argument(
            "--motivo",
            type=str,
            default="",
        )


    def handle(
        self,
        *args,
        **options,
    ):

        if options.get(
            "confirmar"
        ) is not None:

            salida = confirmar_propuesta(
                options[
                    "confirmar"
                ]
            )

        elif options.get(
            "rechazar"
        ) is not None:

            salida = rechazar_propuesta(
                options[
                    "rechazar"
                ],
                motivo=options.get(
                    "motivo"
                )
                or "",
            )

        elif options.get(
            "ver"
        ) is not None:

            salida = obtener_propuesta(
                options[
                    "ver"
                ]
            )

        elif options.get(
            "listar"
        ):

            salida = {
                "ok":
                    True,

                "propuestas":
                    listar_propuestas(
                        estado=(
                            options.get(
                                "estado"
                            )
                            or None
                        )
                    ),

                "llm_invocado":
                    False,
            }

        elif options.get(
            "proponer"
        ):

            tipo = (
                options.get(
                    "tipo"
                )
                or ""
            ).strip().upper()

            expresion = (
                options.get(
                    "expresion"
                )
                or ""
            ).strip()

            if not tipo:

                raise CommandError(
                    "--tipo es obligatorio."
                )

            if not expresion:

                raise CommandError(
                    "--expresion es obligatoria."
                )

            datos = {}

            if tipo == "ENTIDAD":

                datos = {
                    "modelo":
                        options.get(
                            "modelo"
                        ),
                }

            elif tipo == "CAMPO":

                datos = {
                    "modelo":
                        options.get(
                            "modelo"
                        ),

                    "campo":
                        options.get(
                            "campo"
                        ),
                }

            elif tipo == "VALOR":

                datos = {
                    "modelo":
                        options.get(
                            "modelo"
                        ),

                    "campo":
                        options.get(
                            "campo"
                        ),

                    "valor":
                        options.get(
                            "valor"
                        ),
                }

            elif tipo == "REGLA":

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

                datos = {
                    "modelo":
                        options.get(
                            "modelo"
                        ),

                    "operacion":
                        options.get(
                            "operacion"
                        )
                        or "listar",

                    "condiciones":
                        condiciones,
                }

            else:

                datos = {}

            salida = proponer_aprendizaje(
                tipo=tipo,
                expresion=expresion,
                datos=datos,
                motivo=(
                    options.get(
                        "motivo"
                    )
                    or ""
                ),
            )

        else:

            raise CommandError(
                "Use --proponer, --confirmar, "
                "--rechazar, --ver o --listar."
            )

        self.stdout.write(
            json.dumps(
                salida,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )