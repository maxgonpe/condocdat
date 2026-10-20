from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from ia_local.services.query.regresion_seguridad import (
    ejecutar_regresion_query,
)


class Command(BaseCommand):

    help = (
        "IA-QUERY012: batería de seguridad "
        "y regresión QUERY001-QUERY011."
    )

    def handle(
        self,
        *args,
        **options,
    ):

        resultado = (
            ejecutar_regresion_query()
        )

        self.stdout.write(
            json.dumps(
                resultado,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )

        if not resultado.get(
            "ok"
        ):

            raise SystemExit(
                1
            )