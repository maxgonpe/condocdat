from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.semantica.inventario_vocabulario import (
    buscar_vocabulario_modelo,
    construir_inventario_vocabulario,
)


class Command(BaseCommand):

    help = (
        "IA-SEM001 - Construye el inventario automático "
        "del vocabulario del host Django."
    )


    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "--modelo",
            type=str,
            default="",
            help=(
                "Muestra únicamente el vocabulario de un modelo. "
                "Acepta label, nombre, tabla o verbose_name."
            ),
        )

        parser.add_argument(
            "--json",
            action="store_true",
            help="Imprime la salida completa como JSON.",
        )


    def handle(
        self,
        *args,
        **options,
    ):

        referencia = (
            options.get(
                "modelo"
            )
            or ""
        ).strip()

        mostrar_json = bool(
            options.get(
                "json"
            )
        )

        if referencia:

            modelos = (
                buscar_vocabulario_modelo(
                    referencia
                )
            )

            salida = {
                "ok":
                    bool(
                        modelos
                    ),

                "version":
                    "IA-SEM001-v1",

                "referencia":
                    referencia,

                "total":
                    len(
                        modelos
                    ),

                "modelos":
                    modelos,

                "llm_invocado":
                    False,
            }

        else:

            salida = (
                construir_inventario_vocabulario()
            )

        if mostrar_json:

            self.stdout.write(
                json.dumps(
                    salida,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )

            return

        self.stdout.write("")
        self.stdout.write(
            "=" * 68
        )

        self.stdout.write(
            "IA-SEM001 - INVENTARIO AUTOMÁTICO DEL VOCABULARIO"
        )

        self.stdout.write(
            "=" * 68
        )

        self.stdout.write(
            f"OK: {salida.get('ok')}"
        )

        self.stdout.write(
            f"Versión: {salida.get('version')}"
        )

        self.stdout.write(
            f"LLM invocado: {salida.get('llm_invocado')}"
        )

        modelos = salida.get(
            "modelos",
            [],
        )

        self.stdout.write(
            f"Modelos: {len(modelos)}"
        )

        if not referencia:

            self.stdout.write(
                f"Campos: {salida.get('total_campos')}"
            )

            self.stdout.write(
                f"Relaciones: {salida.get('total_relaciones')}"
            )

            self.stdout.write(
                "Términos de entidades: "
                f"{salida.get('total_terminos_entidad')}"
            )

        self.stdout.write("")

        for modelo in modelos:

            self.stdout.write(
                f"{modelo['label']}"
            )

            self.stdout.write(
                "  entidad:"
            )

            for termino in modelo.get(
                "vocabulario_entidad",
                [],
            ):

                self.stdout.write(
                    "    - "
                    f"{termino['texto']} "
                    f"=> {termino['normalizado']} "
                    f"[{', '.join(termino['origenes'])}]"
                )

            self.stdout.write(
                f"  campos: {len(modelo.get('campos', []))}"
            )

            self.stdout.write(
                f"  relaciones: {len(modelo.get('relaciones', []))}"
            )

            self.stdout.write("")

        self.stdout.write(
            "=" * 68
        )