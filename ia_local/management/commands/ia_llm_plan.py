from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.services.llm.planificador_controlado import (
    construir_plan_llm,
)


class Command(BaseCommand):

    help = (
        "IA-LLM001 - Construye un plan HOST validado "
        "mediante fallback Qwen sin ejecutarlo."
    )

    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "pregunta",
            nargs="+",
        )

    def handle(
        self,
        *args,
        **options,
    ):

        pregunta = " ".join(
            options[
                "pregunta"
            ]
        ).strip()

        resultado = construir_plan_llm(
            pregunta
        )

        self.stdout.write(
            json.dumps(
                resultado,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )