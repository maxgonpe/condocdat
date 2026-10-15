from django.core.management.base import BaseCommand

from ia_local.services.host.inspector_modelos_codigo import (
    construir_grafo_modelos,
)


class Command(BaseCommand):
    help = (
        "Relaciona funciones del proyecto anfitrion "
        "con modelos Django y operaciones ORM."
    )

    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "simbolo",
            nargs="?",
            default="ia_local.views.consulta_ia_json",
        )

        parser.add_argument(
            "--profundidad",
            type=int,
            default=3,
        )

    def handle(
        self,
        *args,
        **options,
    ):

        simbolo = options[
            "simbolo"
        ]

        profundidad = options[
            "profundidad"
        ]

        resultado = (
            construir_grafo_modelos(
                simbolo,
                profundidad=profundidad,
            )
        )

        self.stdout.write("")
        self.stdout.write(
            "=" * 100
        )

        self.stdout.write(
            "IA-HOST007 - FUNCION -> MODELO -> ORM"
        )

        self.stdout.write(
            "=" * 100
        )

        self.stdout.write(
            f"Raiz:             "
            f"{resultado['simbolo_raiz']}"
        )

        self.stdout.write(
            f"Profundidad:      "
            f"{resultado['profundidad']}"
        )

        self.stdout.write(
            f"Nodos codigo:     "
            f"{resultado['total_nodos_codigo']}"
        )

        self.stdout.write(
            f"Modelos:          "
            f"{resultado['total_modelos']}"
        )

        self.stdout.write("")
        self.stdout.write(
            "MODELOS DETECTADOS"
        )

        self.stdout.write(
            "-" * 100
        )

        if not resultado[
            "modelos"
        ]:

            self.stdout.write(
                "No se detectaron modelos Django "
                "en el recorrido."
            )

        for modelo in resultado[
            "modelos"
        ]:

            self.stdout.write(
                f"{modelo['label']:<45} "
                f"tabla={modelo['tabla']}"
            )

        self.stdout.write("")
        self.stdout.write(
            "RECORRIDO"
        )

        self.stdout.write(
            "-" * 100
        )

        for nodo in resultado[
            "nodos"
        ]:

            self.stdout.write("")
            self.stdout.write(
                nodo[
                    "qualname"
                ]
            )

            self.stdout.write(
                f"  archivo: "
                f"{nodo['archivo']}"
            )

            self.stdout.write(
                f"  lineas: "
                f"{nodo['linea_inicio']}"
                "-"
                f"{nodo['linea_fin']}"
            )

            if not (
                nodo[
                    "modelos"
                ]
                or nodo[
                    "get_model"
                ]
            ):

                self.stdout.write(
                    "  modelos: ninguno"
                )

                continue

            for modelo in nodo[
                "modelos"
            ]:

                self.stdout.write(
                    f"  MODELO: "
                    f"{modelo['label']}"
                )

            for operacion in nodo[
                "operaciones"
            ]:

                modelo = operacion[
                    "modelo"
                ]

                self.stdout.write(
                    f"    L{operacion['linea']} "
                    f"[{operacion['modo'].upper()}] "
                    f"{modelo['label']} "
                    f"-> {operacion['operacion']} "
                    f"({operacion['expresion']})"
                )

            for uso in nodo[
                "get_model"
            ]:

                self.stdout.write(
                    f"    L{uso['linea']} "
                    f"[GET_MODEL] "
                    f"{uso['modelo']['label']} "
                    f"({uso['expresion']})"
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "IA-HOST007 completado."
            )
        )