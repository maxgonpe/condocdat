from django.core.management.base import BaseCommand

from ia_local.services.host.inspector_proyecto import (
    construir_resumen_proyecto,
)


class Command(BaseCommand):
    help = (
        "Inspecciona estructuralmente el proyecto Django "
        "anfitrion de ia_local."
    )

    def handle(
        self,
        *args,
        **options,
    ):
        resumen = (
            construir_resumen_proyecto()
        )

        identidad = resumen[
            "identidad"
        ]

        totales = resumen[
            "totales"
        ]

        self.stdout.write("")
        self.stdout.write(
            "=" * 80
        )

        self.stdout.write(
            "IA-HOST001 - INSPECTOR DEL PROYECTO ANFITRION"
        )

        self.stdout.write(
            "=" * 80
        )

        self.stdout.write("")
        self.stdout.write(
            "IDENTIDAD"
        )

        self.stdout.write(
            "-" * 80
        )

        self.stdout.write(
            f"Proyecto:        "
            f"{identidad['nombre']}"
        )

        self.stdout.write(
            f"BASE_DIR:        "
            f"{identidad['base_dir']}"
        )

        self.stdout.write(
            f"ROOT_URLCONF:     "
            f"{identidad['root_urlconf']}"
        )

        self.stdout.write(
            f"SETTINGS_MODULE:  "
            f"{identidad['settings_module']}"
        )

        self.stdout.write("")
        self.stdout.write(
            "TOTALES"
        )

        self.stdout.write(
            "-" * 80
        )

        self.stdout.write(
            f"Apps instaladas:  "
            f"{totales['apps']}"
        )

        self.stdout.write(
            f"Apps proyecto:    "
            f"{totales['apps_proyecto']}"
        )

        self.stdout.write(
            f"Apps Django:      "
            f"{totales['apps_django']}"
        )

        self.stdout.write(
            f"Modelos:          "
            f"{totales['modelos']}"
        )

        self.stdout.write(
            f"URLs:             "
            f"{totales['urls']}"
        )

        self.stdout.write(
            f"Archivos Python:  "
            f"{totales['archivos_python']}"
        )

        self.stdout.write(
            f"Templates:        "
            f"{totales['templates']}"
        )

        self.stdout.write(
            f"Errores URLs:     "
            f"{totales['errores_urls']}"
        )

        self.stdout.write("")
        self.stdout.write(
            "APPS DEL PROYECTO"
        )

        self.stdout.write(
            "-" * 80
        )

        for app in resumen[
            "apps"
        ]:

            if app[
                "tipo"
            ] != "proyecto":
                continue

            self.stdout.write(
                f"{app['label']:<20} "
                f"modelos={app['modelos']:<4} "
                f"{app['path']}"
            )

        self.stdout.write("")
        self.stdout.write(
            "MODELOS"
        )

        self.stdout.write(
            "-" * 80
        )

        for modelo in resumen[
            "modelos"
        ]:

            self.stdout.write(
                f"{modelo['label']:<40} "
                f"tabla={modelo['tabla']} "
                f"campos={modelo['campos']}"
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "IA-HOST001 completado."
            )
        )