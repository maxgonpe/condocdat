from django.core.management.base import BaseCommand

from ia_local.services.host.inspector_urls import (
    construir_resumen_urls,
)


class Command(BaseCommand):
    help = (
        "Construye el mapa universal URL -> View "
        "del proyecto anfitrion."
    )

    def handle(
        self,
        *args,
        **options,
    ):
        resumen = (
            construir_resumen_urls()
        )

        totales = resumen[
            "totales"
        ]

        self.stdout.write("")
        self.stdout.write(
            "=" * 96
        )

        self.stdout.write(
            "IA-HOST003 - MAPA URL -> VIEW DEL PROYECTO ANFITRION"
        )

        self.stdout.write(
            "=" * 96
        )

        self.stdout.write("")
        self.stdout.write(
            "TOTALES"
        )

        self.stdout.write(
            "-" * 96
        )

        self.stdout.write(
            f"URLs:             "
            f"{totales['urls']}"
        )

        self.stdout.write(
            f"Con view:         "
            f"{totales['con_view']}"
        )

        self.stdout.write(
            f"Con app:          "
            f"{totales['con_app']}"
        )

        self.stdout.write(
            f"Proyecto:         "
            f"{totales['proyecto']}"
        )

        self.stdout.write(
            f"ia_local:         "
            f"{totales['ia_local']}"
        )

        self.stdout.write(
            f"Django:           "
            f"{totales['django']}"
        )

        self.stdout.write(
            f"Sin app:          "
            f"{totales['sin_app']}"
        )

        self.stdout.write("")
        self.stdout.write(
            "URLS IA_LOCAL"
        )

        self.stdout.write(
            "-" * 96
        )

        for item in resumen[
            "ia_local"
        ]:

            self.stdout.write("")
            self.stdout.write(
                f"Ruta:       {item['ruta']}"
            )

            self.stdout.write(
                f"Namespace:  {item['namespace']}"
            )

            self.stdout.write(
                f"Name:       {item['name']}"
            )

            self.stdout.write(
                f"View:       {item['view']}"
            )

            self.stdout.write(
                f"Modulo:     {item['modulo']}"
            )

            self.stdout.write(
                f"Simbolo:    {item['simbolo']}"
            )

            self.stdout.write(
                f"Archivo:    {item['archivo']}"
            )

            self.stdout.write(
                f"Tipo:       {item['tipo_probable']}"
            )

        self.stdout.write("")
        self.stdout.write(
            "URLS DEL PROYECTO"
        )

        self.stdout.write(
            "-" * 96
        )

        if not resumen[
            "proyecto"
        ]:

            self.stdout.write(
                "No se detectaron URLs pertenecientes "
                "a apps de dominio del anfitrion."
            )

        else:

            for item in resumen[
                "proyecto"
            ]:

                app = item[
                    "app"
                ]

                self.stdout.write("")
                self.stdout.write(
                    f"Ruta:       {item['ruta']}"
                )

                self.stdout.write(
                    f"App:        {app['label']}"
                )

                self.stdout.write(
                    f"Name:       {item['name']}"
                )

                self.stdout.write(
                    f"View:       {item['view']}"
                )

                self.stdout.write(
                    f"Modulo:     {item['modulo']}"
                )

                self.stdout.write(
                    f"Simbolo:    {item['simbolo']}"
                )

                self.stdout.write(
                    f"Archivo:    {item['archivo']}"
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "IA-HOST003 completado."
            )
        )