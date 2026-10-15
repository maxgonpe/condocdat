from django.core.management.base import BaseCommand

from ia_local.services.host.inspector_apps import (
    construir_resumen_apps,
)


class Command(BaseCommand):
    help = (
        "Clasifica y perfila las apps del proyecto "
        "anfitrion de ia_local."
    )

    def handle(
        self,
        *args,
        **options,
    ):
        resumen = (
            construir_resumen_apps()
        )

        totales = resumen[
            "totales"
        ]

        self.stdout.write("")
        self.stdout.write(
            "=" * 88
        )

        self.stdout.write(
            "IA-HOST002 - PERFIL DE APPS DEL PROYECTO ANFITRION"
        )

        self.stdout.write(
            "=" * 88
        )

        self.stdout.write("")
        self.stdout.write(
            "TOTALES"
        )

        self.stdout.write(
            "-" * 88
        )

        self.stdout.write(
            f"Apps:             "
            f"{totales['apps']}"
        )

        self.stdout.write(
            f"Dominio:          "
            f"{totales['dominio']}"
        )

        self.stdout.write(
            f"Infraestructura:  "
            f"{totales['infraestructura']}"
        )

        self.stdout.write(
            f"ia_local:         "
            f"{totales['ia_local']}"
        )

        self.stdout.write("")
        self.stdout.write(
            "APPS DE DOMINIO"
        )

        self.stdout.write(
            "-" * 88
        )

        for app in resumen[
            "dominio"
        ]:

            self.stdout.write("")
            self.stdout.write(
                f"{app['label']}"
            )

            self.stdout.write(
                f"  ruta:               "
                f"{app['path']}"
            )

            self.stdout.write(
                f"  modelos:            "
                f"{app['total_modelos']}"
            )

            self.stdout.write(
                f"  urls:               "
                f"{app['total_urls']}"
            )

            self.stdout.write(
                f"  python:             "
                f"{app['total_archivos_python']}"
            )

            self.stdout.write(
                f"  templates:          "
                f"{app['total_templates']}"
            )

            self.stdout.write(
                f"  views.py:           "
                f"{app['tiene_views']}"
            )

            self.stdout.write(
                f"  forms.py:           "
                f"{app['tiene_forms']}"
            )

            self.stdout.write(
                f"  signals.py:         "
                f"{app['tiene_signals']}"
            )

            self.stdout.write(
                f"  urls.py:            "
                f"{app['tiene_urls']}"
            )

            self.stdout.write(
                f"  admin.py:           "
                f"{app['tiene_admin']}"
            )

            self.stdout.write(
                f"  services/:          "
                f"{app['tiene_services']}"
            )

            self.stdout.write(
                f"  management cmds:    "
                f"{app['management_commands']}"
            )

            if app[
                "modelos"
            ]:

                self.stdout.write(
                    "  modelos detectados:"
                )

                for modelo in app[
                    "modelos"
                ]:

                    self.stdout.write(
                        f"    - {modelo}"
                    )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "IA-HOST002 completado."
            )
        )