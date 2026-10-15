from django.core.management.base import BaseCommand

from ia_local.services.host.inspector_grafo_negocio import (
    construir_grafo_negocio,
)


class Command(BaseCommand):
    help = (
        "Construye el grafo de negocio unificado "
        "Template -> URL -> View -> Codigo -> Modelo -> ORM -> Tabla."
    )

    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "entrada",
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

        entrada = options[
            "entrada"
        ]

        profundidad = options[
            "profundidad"
        ]

        grafo = (
            construir_grafo_negocio(
                entrada,
                profundidad=profundidad,
            )
        )

        self.stdout.write("")
        self.stdout.write(
            "=" * 110
        )

        self.stdout.write(
            "IA-HOST008 - GRAFO_NEGOCIO UNIFICADO"
        )

        self.stdout.write(
            "=" * 110
        )

        self.stdout.write(
            f"Entrada:       {entrada}"
        )

        self.stdout.write(
            f"Profundidad:  {profundidad}"
        )

        self.stdout.write(
            f"Raices:       {grafo['total_raices']}"
        )

        for raiz in grafo[
            "raices"
        ]:

            self.stdout.write("")
            self.stdout.write(
                "#" * 110
            )

            self.stdout.write(
                f"RAIZ: {raiz['raiz']}"
            )

            self.stdout.write(
                "#" * 110
            )

            stats = raiz[
                "estadisticas"
            ]

            self.stdout.write("")
            self.stdout.write(
                "RESUMEN"
            )

            self.stdout.write(
                "-" * 110
            )

            self.stdout.write(
                f"Templates:            "
                f"{stats['templates']}"
            )

            self.stdout.write(
                f"URLs:                 "
                f"{stats['urls']}"
            )

            self.stdout.write(
                f"Nodos codigo:         "
                f"{stats['nodos_codigo']}"
            )

            self.stdout.write(
                f"Aristas codigo:       "
                f"{stats['aristas_codigo']}"
            )

            self.stdout.write(
                f"Llamadas externas:    "
                f"{stats['llamadas_externas']}"
            )

            self.stdout.write(
                f"Llamadas ambiguas:    "
                f"{stats['llamadas_ambiguas']}"
            )

            self.stdout.write(
                f"Modelos:              "
                f"{stats['modelos']}"
            )

            self.stdout.write(
                f"Operaciones ORM:      "
                f"{stats['operaciones_orm']}"
            )

            self.stdout.write(
                f"Tablas:               "
                f"{stats['tablas']}"
            )

            # ==================================================
            # TEMPLATES
            # ==================================================

            self.stdout.write("")
            self.stdout.write(
                "TEMPLATES -> URL -> VIEW"
            )

            self.stdout.write(
                "-" * 110
            )

            if not raiz[
                "templates"
            ]:

                self.stdout.write(
                    "Sin templates de entrada detectados."
                )

            for item in raiz[
                "templates"
            ]:

                self.stdout.write(
                    f"{item['template']} "
                    f"L{item['linea']} "
                    f"[{item['tipo_referencia']}]"
                )

                self.stdout.write(
                    f"    {item['valor']}"
                )

                self.stdout.write(
                    f"      -> "
                    f"{item['url']['ruta']}"
                )

                self.stdout.write(
                    f"      -> "
                    f"{item['url']['view']}"
                )

            # ==================================================
            # URLS
            # ==================================================

            self.stdout.write("")
            self.stdout.write(
                "URLS"
            )

            self.stdout.write(
                "-" * 110
            )

            if not raiz[
                "urls"
            ]:

                self.stdout.write(
                    "La raiz no tiene URL directa detectada."
                )

            for url in raiz[
                "urls"
            ]:

                nombre = (
                    f"{url['namespace']}:{url['name']}"
                    if (
                        url.get(
                            "namespace"
                        )
                        and url.get(
                            "name"
                        )
                    )
                    else url.get(
                        "name"
                    )
                )

                self.stdout.write(
                    f"{url['ruta']} "
                    f"| {nombre} "
                    f"| {url['view']}"
                )

            # ==================================================
            # CÓDIGO
            # ==================================================

            self.stdout.write("")
            self.stdout.write(
                "GRAFO DE CODIGO"
            )

            self.stdout.write(
                "-" * 110
            )

            for nodo in raiz[
                "codigo"
            ][
                "nodos"
            ]:

                self.stdout.write(
                    f"{nodo['qualname']}"
                )

                self.stdout.write(
                    f"    {nodo['archivo']}:"
                    f"{nodo['linea_inicio']}"
                    f"-"
                    f"{nodo['linea_fin']}"
                )

            self.stdout.write("")
            self.stdout.write(
                "ARISTAS INTERNAS / AMBIGUAS"
            )

            self.stdout.write(
                "-" * 110
            )

            for arista in raiz[
                "codigo"
            ][
                "aristas"
            ]:

                if arista[
                    "estado"
                ] == "externa":
                    continue

                self.stdout.write(
                    f"{arista['origen']}"
                )

                self.stdout.write(
                    f"    L{arista['linea']} "
                    f"{arista['llamada']} "
                    f"[{arista['estado'].upper()}]"
                )

                self.stdout.write(
                    f"      -> "
                    f"{arista['destino']}"
                )

            # ==================================================
            # MODELOS
            # ==================================================

            self.stdout.write("")
            self.stdout.write(
                "MODELOS"
            )

            self.stdout.write(
                "-" * 110
            )

            if not raiz[
                "modelos"
            ]:

                self.stdout.write(
                    "Sin modelos detectados."
                )

            for modelo in raiz[
                "modelos"
            ]:

                self.stdout.write(
                    f"{modelo['label']}"
                    f" -> "
                    f"{modelo['tabla']}"
                )

            # ==================================================
            # ORM
            # ==================================================

            self.stdout.write("")
            self.stdout.write(
                "OPERACIONES ORM"
            )

            self.stdout.write(
                "-" * 110
            )

            if not raiz[
                "operaciones_orm"
            ]:

                self.stdout.write(
                    "Sin operaciones ORM detectadas."
                )

            for op in raiz[
                "operaciones_orm"
            ]:

                self.stdout.write(
                    f"{op['simbolo']}"
                )

                self.stdout.write(
                    f"    L{op['linea']} "
                    f"[{op['modo'].upper()}] "
                    f"{op['modelo']['label']} "
                    f"-> "
                    f"{op['operacion']}"
                )

            # ==================================================
            # TABLAS
            # ==================================================

            self.stdout.write("")
            self.stdout.write(
                "TABLAS"
            )

            self.stdout.write(
                "-" * 110
            )

            if not raiz[
                "tablas"
            ]:

                self.stdout.write(
                    "Sin tablas detectadas."
                )

            for tabla in raiz[
                "tablas"
            ]:

                self.stdout.write(
                    f"{tabla['tabla']}"
                    f" <- "
                    f"{tabla['modelo']}"
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "IA-HOST008 completado."
            )
        )