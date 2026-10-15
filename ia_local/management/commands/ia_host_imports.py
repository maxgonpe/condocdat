from django.core.management.base import BaseCommand

from ia_local.services.host.inspector_imports import (
    analizar_imports_simbolo,
)
from ia_local.services.host.inspector_llamadas import (
    buscar_simbolo,
    construir_indice_simbolos,
    resolver_llamada_interna,
)


class Command(BaseCommand):
    help = (
        "Inspecciona imports y prueba la resolucion "
        "de llamadas internas mediante imports reales."
    )

    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "simbolo",
            nargs="?",
            default=(
                "ia_local.services.host."
                "respuesta_llm.responder_pregunta_host"
            ),
        )

        parser.add_argument(
            "--llamada",
            default="construir_contexto_llm",
        )

    def handle(
        self,
        *args,
        **options,
    ):

        qualname = options[
            "simbolo"
        ]

        llamada = options[
            "llamada"
        ]

        candidatos = buscar_simbolo(
            qualname
        )

        simbolo = None

        for candidato in candidatos:

            if candidato[
                "qualname"
            ] == qualname:

                simbolo = candidato
                break

        self.stdout.write("")
        self.stdout.write(
            "=" * 100
        )

        self.stdout.write(
            "IA-HOST009 - RESOLUCION POR IMPORTS"
        )

        self.stdout.write(
            "=" * 100
        )

        if simbolo is None:

            self.stdout.write(
                self.style.ERROR(
                    "No se encontro el simbolo."
                )
            )

            return

        self.stdout.write(
            f"Simbolo: "
            f"{simbolo['qualname']}"
        )

        self.stdout.write(
            f"Archivo: "
            f"{simbolo['archivo']}"
        )

        imports = (
            analizar_imports_simbolo(
                simbolo
            )
        )

        self.stdout.write("")
        self.stdout.write(
            "IMPORTS"
        )

        self.stdout.write(
            "-" * 100
        )

        for item in imports[
            "imports"
        ]:

            self.stdout.write(
                f"L{item['linea']} "
                f"{item['visible']} "
                f"-> "
                f"{item['destino']}"
            )

        indice = (
            construir_indice_simbolos()
        )

        resolucion = (
            resolver_llamada_interna(
                llamada,
                simbolo_origen=simbolo,
                indice=indice,
            )
        )

        self.stdout.write("")
        self.stdout.write(
            "PRUEBA"
        )

        self.stdout.write(
            "-" * 100
        )

        self.stdout.write(
            f"Llamada:     "
            f"{llamada}"
        )

        self.stdout.write(
            f"Resuelta:    "
            f"{resolucion['resuelta']}"
        )

        self.stdout.write(
            f"Ambigua:     "
            f"{resolucion['ambigua']}"
        )

        self.stdout.write(
            f"Metodo:      "
            f"{resolucion.get('metodo_resolucion')}"
        )

        self.stdout.write(
            f"Destinos:    "
            f"{len(resolucion['destinos'])}"
        )

        for destino in resolucion[
            "destinos"
        ]:

            self.stdout.write(
                f"    -> "
                f"{destino['qualname']}"
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "IA-HOST009 completado."
            )
        )