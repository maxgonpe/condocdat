from django.core.management.base import BaseCommand

from ia_local.services.host.inspector_llamadas import (
    construir_grafo_llamadas,
    construir_resumen_llamadas,
)


class Command(BaseCommand):
    help = (
        "Construye y prueba el grafo de llamadas internas "
        "del proyecto Django anfitrion."
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
            default=2,
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

        resumen = (
            construir_resumen_llamadas()
        )

        self.stdout.write("")
        self.stdout.write(
            "=" * 100
        )

        self.stdout.write(
            "IA-HOST006 - GRAFO DE LLAMADAS INTERNAS"
        )

        self.stdout.write(
            "=" * 100
        )

        self.stdout.write("")
        self.stdout.write(
            "INDICE"
        )

        self.stdout.write(
            "-" * 100
        )

        self.stdout.write(
            f"Simbolos:     "
            f"{resumen['totales']['simbolos']}"
        )

        self.stdout.write(
            f"Funciones:    "
            f"{resumen['totales']['funciones']}"
        )

        self.stdout.write(
            f"Clases:       "
            f"{resumen['totales']['clases']}"
        )

        self.stdout.write(
            f"Errores:      "
            f"{resumen['totales']['errores']}"
        )

        self.stdout.write("")
        self.stdout.write(
            f"RAIZ: {simbolo}"
        )

        self.stdout.write(
            f"PROFUNDIDAD: {profundidad}"
        )

        self.stdout.write(
            "-" * 100
        )

        grafo = (
            construir_grafo_llamadas(
                simbolo,
                profundidad=profundidad,
            )
        )

        if not grafo[
            "candidatos"
        ]:

            self.stdout.write(
                "No se encontro el simbolo raiz."
            )

            return

        def imprimir_nodo(
            nodo,
            nivel=0,
        ):

            sangria = (
                "    "
                * nivel
            )

            self.stdout.write("")
            self.stdout.write(
                f"{sangria}"
                f"{nodo['qualname']}"
            )

            self.stdout.write(
                f"{sangria}"
                f"  archivo: "
                f"{nodo['archivo']}"
            )

            self.stdout.write(
                f"{sangria}"
                f"  lineas: "
                f"{nodo['linea_inicio']}"
                "-"
                f"{nodo['linea_fin']}"
            )

            for llamada in nodo[
                "llamadas"
            ]:

                if llamada[
                    "resuelta"
                ]:
                    estado = "INTERNA"

                elif llamada[
                    "ambigua"
                ]:
                    estado = "AMBIGUA"

                else:
                    estado = "EXTERNA"

                self.stdout.write(
                    f"{sangria}"
                    f"    L{llamada['linea']} "
                    f"{llamada['llamada']} "
                    f"[{estado}]"
                )

                for destino in llamada[
                    "destinos"
                ]:

                    self.stdout.write(
                        f"{sangria}"
                        f"        -> "
                        f"{destino['qualname']}"
                    )

                    subnodo = (
                        destino.get(
                            "nodo"
                        )
                    )

                    if subnodo:

                        imprimir_nodo(
                            subnodo,
                            nivel + 1,
                        )

        for candidato in grafo[
            "candidatos"
        ]:

            imprimir_nodo(
                candidato
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "IA-HOST006 completado."
            )
        )