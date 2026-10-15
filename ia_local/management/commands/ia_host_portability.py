from django.core.management.base import BaseCommand

from ia_local.services.host.portabilidad import (
    auditar_portabilidad,
)


class Command(BaseCommand):
    help = (
        "Audita dependencias de ia_local respecto "
        "del proyecto Django anfitrion."
    )

    def handle(
        self,
        *args,
        **options,
    ):

        resultado = (
            auditar_portabilidad()
        )

        resumen = resultado[
            "resumen"
        ]

        self.stdout.write("")
        self.stdout.write(
            "=" * 100
        )

        self.stdout.write(
            "IA-HOST013 - AUDITORIA DE PORTABILIDAD"
        )

        self.stdout.write(
            "=" * 100
        )

        self.stdout.write("")
        self.stdout.write(
            "RESUMEN"
        )

        self.stdout.write(
            "-" * 100
        )

        self.stdout.write(
            f"Apps host:                    "
            f"{resumen['apps_host']}"
        )

        self.stdout.write(
            f"Imports directos al host:     "
            f"{resumen['imports_host']}"
        )

        self.stdout.write(
            f"Templates usados:             "
            f"{resumen['templates_usados']}"
        )

        self.stdout.write(
            f"Templates no autocontenidos:  "
            f"{resumen['templates_no_autocontenidos']}"
        )

        self.stdout.write(
            f"Errores AST:                  "
            f"{resumen['errores_ast']}"
        )

        # ====================================================
        # APPS HOST
        # ====================================================

        self.stdout.write("")
        self.stdout.write(
            "APPS DEL HOST"
        )

        self.stdout.write(
            "-" * 100
        )

        for item in resultado[
            "apps_host"
        ][
            "host"
        ]:

            self.stdout.write(
                f"{item['label']} "
                f"| {item['name']}"
            )

        # ====================================================
        # IMPORTS
        # ====================================================

        self.stdout.write("")
        self.stdout.write(
            "IMPORTS DIRECTOS DE IA_LOCAL AL HOST"
        )

        self.stdout.write(
            "-" * 100
        )

        if not resultado[
            "imports_host"
        ]:

            self.stdout.write(
                "Ninguno."
            )

        for item in resultado[
            "imports_host"
        ]:

            simbolo = (
                f".{item['simbolo']}"
                if item[
                    "simbolo"
                ]
                else ""
            )

            self.stdout.write(
                f"{item['archivo']}:"
                f"{item['linea']} "
                f"-> "
                f"{item['modulo']}"
                f"{simbolo}"
            )

        # ====================================================
        # TEMPLATES
        # ====================================================

        self.stdout.write("")
        self.stdout.write(
            "TEMPLATES USADOS POR IA_LOCAL"
        )

        self.stdout.write(
            "-" * 100
        )

        if not resultado[
            "templates_usados"
        ]:

            self.stdout.write(
                "Ninguno detectado."
            )

        for item in resultado[
            "templates_usados"
        ]:

            estado = (
                "OK"
                if item[
                    "autocontenido"
                ]
                else "EXTERNO"
            )

            self.stdout.write(
                f"[{estado}] "
                f"{item['archivo']}:"
                f"{item['linea']} "
                f"-> {item['template']}"
            )

            for encontrado in item[
                "encontrados"
            ]:

                self.stdout.write(
                    f"    "
                    f"{encontrado['origen']} "
                    f"-> "
                    f"{encontrado['ruta']}"
                )

        # ====================================================
        # CONFIG
        # ====================================================

        config = resultado[
            "configuracion"
        ]

        self.stdout.write("")
        self.stdout.write(
            "CONFIGURACION"
        )

        self.stdout.write(
            "-" * 100
        )

        self.stdout.write(
            f"ia_local instalada: "
            f"{config['ia_local_instalada']}"
        )

        self.stdout.write(
            f"ROOT_URLCONF: "
            f"{config['root_urlconf']}"
        )

        self.stdout.write(
            f"IA_LOCAL_OLLAMA_URL: "
            f"{config['ollama_url']}"
        )

        self.stdout.write(
            f"IA_LOCAL_OLLAMA_MODEL: "
            f"{config['ollama_model']}"
        )

        self.stdout.write(
            f"IA_LOCAL_OLLAMA_TIMEOUT: "
            f"{config['ollama_timeout']}"
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "IA-HOST013 auditoria completada."
            )
        )