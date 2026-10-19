from __future__ import annotations

import json

from django.contrib.auth import (
    get_user_model,
)
from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.test import Client
from django.urls import reverse


class Command(BaseCommand):

    help = (
        "IA-BRIDGE006 - Prueba HTTP autenticada del "
        "endpoint web del nuevo pipeline BRIDGE."
    )


    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "pregunta",
            type=str,
        )

        parser.add_argument(
            "--limite",
            type=int,
            default=20,
        )

        parser.add_argument(
            "--diagnostico",
            action="store_true",
        )


    def handle(
        self,
        *args,
        **options,
    ):

        User = get_user_model()

        usuario = (
            User.objects
            .filter(
                is_active=True,
                is_staff=True,
            )
            .order_by(
                "pk"
            )
            .first()
        )

        if usuario is None:

            raise CommandError(
                (
                    "No existe ningún usuario staff "
                    "activo para realizar la prueba."
                )
            )

        # ====================================================
        # CLIENT HTTP
        # ====================================================
        #
        # El Client de Django usa "testserver" por defecto.
        #
        # Este proyecto no incluye "testserver" en ALLOWED_HOSTS,
        # correctamente.
        #
        # Para no modificar settings únicamente por esta prueba,
        # simulamos localhost, que ya es un host autorizado.
        # ====================================================

        cliente = Client(
            HTTP_HOST="localhost",
        )

        cliente.force_login(
            usuario
        )

        url = reverse(
            "ia_local:bridge_consultar"
        )

        datos = {
            "pregunta":
                options[
                    "pregunta"
                ],

            "limite":
                options[
                    "limite"
                ],
        }

        if options.get(
            "diagnostico"
        ):

            datos[
                "diagnostico"
            ] = "1"

        respuesta = cliente.post(
            url,
            data=datos,
        )

        self.stdout.write(
            (
                f"URL: {url}\n"
                f"HTTP: {respuesta.status_code}\n"
                f"Usuario staff: {usuario.pk}\n"
            )
        )

        try:

            contenido = respuesta.json()

        except ValueError:

            contenido = {
                "contenido":
                    respuesta.content.decode(
                        "utf-8",
                        errors="replace",
                    )
            }

        self.stdout.write(
            json.dumps(
                contenido,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )