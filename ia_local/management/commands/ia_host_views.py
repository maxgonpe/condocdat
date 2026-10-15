from django.core.management.base import BaseCommand

from ia_local.services.host.inspector_views import (
    construir_resumen_views,
)


class Command(BaseCommand):
    help = (
        "Inspecciona las views reales enlazadas "
        "desde las URLs del proyecto anfitrion."
    )

    def handle(
        self,
        *args,
        **options,
    ):

        resumen = (
            construir_resumen_views()
        )

        totales = resumen[
            "totales"
        ]

        self.stdout.write("")
        self.stdout.write(
            "=" * 96
        )

        self.stdout.write(
            "IA-HOST004 - MAPA VIEW -> CODIGO -> LLAMADAS"
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
            f"Views:            "
            f"{totales['views']}"
        )

        self.stdout.write(
            f"Encontradas AST:  "
            f"{totales['encontradas']}"
        )

        self.stdout.write(
            f"No encontradas:   "
            f"{totales['no_encontradas']}"
        )

        self.stdout.write(
            f"ia_local:         "
            f"{totales['ia_local']}"
        )

        self.stdout.write(
            f"Proyecto:         "
            f"{totales['proyecto']}"
        )

        self.stdout.write("")
        self.stdout.write(
            "VIEWS IA_LOCAL"
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
                f"View:       {item['view']}"
            )

            self.stdout.write(
                f"Archivo:    {item['archivo']}"
            )

            self.stdout.write(
                f"Encontrada: {item['encontrada']}"
            )

            self.stdout.write(
                f"Tipo:       {item['tipo_real']}"
            )

            self.stdout.write(
                f"Lineas:     "
                f"{item['linea_inicio']}"
                f"-"
                f"{item['linea_fin']}"
            )

            self.stdout.write(
                f"Llamadas:   "
                f"{item['total_llamadas']}"
            )

            for llamada in item[
                "llamadas"
            ]:

                self.stdout.write(
                    f"    "
                    f"L{llamada['linea']} "
                    f"{llamada['nombre']}"
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "IA-HOST004 completado."
            )
        )