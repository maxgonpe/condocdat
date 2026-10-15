from django.core.management.base import BaseCommand

from ia_local.services.host.consultor_grafo import (
    buscar_llamadores,
    buscar_modelos,
    buscar_templates,
    buscar_templates_de_view,
    buscar_urls,
    buscar_urls_de_view,
    buscar_views_por_modelo,
    consultar_entrada,
)


class Command(BaseCommand):
    help = (
        "Consulta el grafo estructural del proyecto "
        "Django anfitrion."
    )

    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "texto",
        )

        parser.add_argument(
            "--tipo",
            choices=[
                "general",
                "url",
                "template",
                "modelo",
                "view",
                "llamadores",
                "grafo",
            ],
            default="general",
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

        texto = options[
            "texto"
        ]

        tipo = options[
            "tipo"
        ]

        profundidad = options[
            "profundidad"
        ]

        self.stdout.write("")
        self.stdout.write(
            "=" * 100
        )

        self.stdout.write(
            "IA-HOST010 - CONSULTA DEL GRAFO"
        )

        self.stdout.write(
            "=" * 100
        )

        self.stdout.write(
            f"Consulta: {texto}"
        )

        self.stdout.write(
            f"Tipo:     {tipo}"
        )

        # ====================================================
        # URL
        # ====================================================

        if tipo in {
            "general",
            "url",
        }:

            urls = buscar_urls(
                texto
            )

            self.stdout.write("")
            self.stdout.write(
                "URLS"
            )

            self.stdout.write(
                "-" * 100
            )

            for item in urls:

                self.stdout.write(
                    f"{item.get('ruta')} "
                    f"| {item.get('namespace')}:"
                    f"{item.get('name')} "
                    f"| {item.get('view')}"
                )

            if not urls:

                self.stdout.write(
                    "Sin coincidencias."
                )

        # ====================================================
        # TEMPLATE
        # ====================================================

        if tipo in {
            "general",
            "template",
        }:

            templates = (
                buscar_templates(
                    texto
                )
            )

            self.stdout.write("")
            self.stdout.write(
                "TEMPLATES"
            )

            self.stdout.write(
                "-" * 100
            )

            for item in templates:

                self.stdout.write(
                    str(
                        item.get(
                            "archivo"
                        )
                    )
                )

            if not templates:

                self.stdout.write(
                    "Sin coincidencias."
                )

        # ====================================================
        # MODELO
        # ====================================================

        if tipo == "modelo":

            modelos = buscar_modelos(
                texto
            )

            self.stdout.write("")
            self.stdout.write(
                "MODELOS"
            )

            self.stdout.write(
                "-" * 100
            )

            for modelo in modelos:

                self.stdout.write(
                    f"{modelo['label']} "
                    f"-> {modelo['tabla']}"
                )

            if not modelos:

                self.stdout.write(
                    "Sin coincidencias."
                )

            self.stdout.write("")
            self.stdout.write(
                "VIEWS QUE ALCANZAN EL MODELO"
            )

            self.stdout.write(
                "-" * 100
            )

            views = (
                buscar_views_por_modelo(
                    texto,
                    profundidad=profundidad,
                )
            )

            for item in views:

                self.stdout.write("")
                self.stdout.write(
                    item[
                        "view"
                    ]
                )

                for url in item[
                    "urls"
                ]:

                    self.stdout.write(
                        f"    URL: "
                        f"{url.get('ruta')}"
                    )

                for op in item[
                    "operaciones_orm"
                ]:

                    self.stdout.write(
                        f"    ORM: "
                        f"{op['operacion']} "
                        f"L{op['linea']} "
                        f"en {op['simbolo']}"
                    )

            if not views:

                self.stdout.write(
                    "Sin views detectadas."
                )

        # ====================================================
        # VIEW
        # ====================================================

        if tipo == "view":

            urls = (
                buscar_urls_de_view(
                    texto
                )
            )

            templates = (
                buscar_templates_de_view(
                    texto
                )
            )

            self.stdout.write("")
            self.stdout.write(
                "URLS DE LA VIEW"
            )

            self.stdout.write(
                "-" * 100
            )

            for item in urls:

                self.stdout.write(
                    f"{item.get('ruta')} "
                    f"| {item.get('namespace')}:"
                    f"{item.get('name')}"
                )

            if not urls:

                self.stdout.write(
                    "Sin URLs."
                )

            self.stdout.write("")
            self.stdout.write(
                "TEMPLATES QUE APUNTAN A LA VIEW"
            )

            self.stdout.write(
                "-" * 100
            )

            for item in templates:

                self.stdout.write(
                    item[
                        "template"
                    ]
                )

                for ref in item[
                    "referencias"
                ]:

                    self.stdout.write(
                        f"    L{ref['linea']} "
                        f"{ref['valor']}"
                    )

            if not templates:

                self.stdout.write(
                    "Sin templates."
                )

        # ====================================================
        # LLAMADORES
        # ====================================================

        if tipo == "llamadores":

            resultado = (
                buscar_llamadores(
                    texto
                )
            )

            self.stdout.write("")
            self.stdout.write(
                "LLAMADORES"
            )

            self.stdout.write(
                "-" * 100
            )

            for item in resultado:

                self.stdout.write(
                    item[
                        "simbolo"
                    ][
                        "qualname"
                    ]
                )

                for llamada in item[
                    "llamadas"
                ]:

                    self.stdout.write(
                        f"    L"
                        f"{llamada.get('linea')} "
                        f"{llamada.get('nombre')}"
                    )

            if not resultado:

                self.stdout.write(
                    "Sin llamadores."
                )

        # ====================================================
        # GRAFO
        # ====================================================

        if tipo == "grafo":

            resultado = (
                consultar_entrada(
                    texto,
                    profundidad=profundidad,
                )
            )

            self.stdout.write("")
            self.stdout.write(
                "GRAFO"
            )

            self.stdout.write(
                "-" * 100
            )

            self.stdout.write(
                f"Raices: "
                f"{resultado['total_raices']}"
            )

            for raiz in resultado[
                "raices"
            ]:

                stats = raiz[
                    "estadisticas"
                ]

                self.stdout.write("")
                self.stdout.write(
                    raiz[
                        "raiz"
                    ]
                )

                self.stdout.write(
                    f"    Templates: "
                    f"{stats['templates']}"
                )

                self.stdout.write(
                    f"    URLs: "
                    f"{stats['urls']}"
                )

                self.stdout.write(
                    f"    Nodos: "
                    f"{stats['nodos_codigo']}"
                )

                self.stdout.write(
                    f"    Modelos: "
                    f"{stats['modelos']}"
                )

                self.stdout.write(
                    f"    ORM: "
                    f"{stats['operaciones_orm']}"
                )

                self.stdout.write(
                    f"    Tablas: "
                    f"{stats['tablas']}"
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "IA-HOST010 completado."
            )
        )