from django.core.management.base import BaseCommand

from ia_local.services.host.inspector_templates import (
    construir_resumen_templates,
)


class Command(BaseCommand):
    help = (
        "Construye el mapa Template -> URL -> View "
        "del proyecto Django anfitrion."
    )

    def handle(
        self,
        *args,
        **options,
    ):

        resumen = (
            construir_resumen_templates()
        )

        totales = resumen[
            "totales"
        ]

        self.stdout.write("")
        self.stdout.write(
            "=" * 100
        )

        self.stdout.write(
            "IA-HOST005 - MAPA TEMPLATE -> URL -> VIEW"
        )

        self.stdout.write(
            "=" * 100
        )

        self.stdout.write("")
        self.stdout.write(
            "TOTALES"
        )

        self.stdout.write(
            "-" * 100
        )

        self.stdout.write(
            f"Templates:         "
            f"{totales['templates']}"
        )

        self.stdout.write(
            f"Referencias:       "
            f"{totales['referencias']}"
        )

        self.stdout.write(
            f"Resueltas:         "
            f"{totales['resueltas']}"
        )

        self.stdout.write(
            f"No resueltas:      "
            f"{totales['no_resueltas']}"
        )

        self.stdout.write(
            f"Proyecto:          "
            f"{totales['proyecto']}"
        )

        self.stdout.write(
            f"ia_local:          "
            f"{totales['ia_local']}"
        )

        self.stdout.write(
            f"Sin app:           "
            f"{totales['sin_app']}"
        )

        self.stdout.write("")
        self.stdout.write(
            "TEMPLATES"
        )

        self.stdout.write(
            "-" * 100
        )

        for template in resumen[
            "templates"
        ]:

            self.stdout.write("")
            self.stdout.write(
                f"Template:    "
                f"{template['archivo']}"
            )

            app = template.get(
                "app"
            )

            if app:

                self.stdout.write(
                    f"App:         "
                    f"{app['label']} "
                    f"({app['tipo']})"
                )

            else:

                self.stdout.write(
                    "App:         "
                    "sin identificar"
                )

            self.stdout.write(
                f"Referencias: "
                f"{template['total_referencias']}"
            )

            self.stdout.write(
                f"Resueltas:   "
                f"{template['referencias_resueltas']}"
            )

            self.stdout.write(
                f"No resueltas:"
                f" {template['referencias_no_resueltas']}"
            )

            for referencia in template[
                "referencias"
            ]:

                estado = (
                    "OK"
                    if referencia[
                        "resuelta"
                    ]
                    else "NO RESUELTA"
                )

                self.stdout.write(
                    ""
                )

                self.stdout.write(
                    f"  L{referencia['linea']} "
                    f"[{referencia['tipo']}] "
                    f"{referencia['valor']} "
                    f"[{estado}]"
                )

                for destino in referencia[
                    "destinos"
                ]:

                    self.stdout.write(
                        f"      -> "
                        f"{destino['ruta']}"
                    )

                    self.stdout.write(
                        f"         "
                        f"{destino['view']}"
                    )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "IA-HOST005 completado."
            )
        )