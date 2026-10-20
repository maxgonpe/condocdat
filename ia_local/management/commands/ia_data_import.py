from __future__ import annotations

import json
from pathlib import Path

from django.apps import apps
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


FORMATO = "IA-LOCAL-DATA-v1"
APP_LABEL = "ia_local"


class Command(BaseCommand):

    help = (
        "Importa un archivo generado por ia_data_export "
        "hacia los modelos de ia_local."
    )


    def add_arguments(self, parser):

        parser.add_argument(
            "archivo",
            type=str,
            help="Archivo JSON generado por ia_data_export.",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Valida el archivo sin modificar "
                "la base de datos."
            ),
        )

        parser.add_argument(
            "--replace",
            action="store_true",
            help=(
                "Elimina primero los registros de ia_local "
                "incluidos en el archivo. Usar con precaución."
            ),
        )


    def handle(self, *args, **options):

        ruta = Path(
            options["archivo"]
        ).expanduser().resolve()

        if not ruta.exists():

            raise CommandError(
                f"No existe el archivo: {ruta}"
            )

        try:

            with ruta.open(
                "r",
                encoding="utf-8",
            ) as archivo:

                payload = json.load(
                    archivo
                )

        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:

            raise CommandError(
                f"No fue posible leer el archivo: {exc}"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):

            raise CommandError(
                "El archivo no contiene un objeto JSON válido."
            )

        if payload.get(
            "formato"
        ) != FORMATO:

            raise CommandError(
                "Formato de exportación no reconocido."
            )

        if payload.get(
            "app"
        ) != APP_LABEL:

            raise CommandError(
                "El archivo no pertenece a ia_local."
            )

        objetos = payload.get(
            "objetos"
        )

        if not isinstance(
            objetos,
            list,
        ):

            raise CommandError(
                "El campo 'objetos' debe ser una lista."
            )

        # -----------------------------------------------------
        # SEGURIDAD:
        # solamente aceptar modelos de ia_local
        # -----------------------------------------------------

        modelos_en_archivo = set()

        for objeto in objetos:

            if not isinstance(
                objeto,
                dict,
            ):

                raise CommandError(
                    "Se encontró un registro inválido."
                )

            label = objeto.get(
                "model"
            )

            if not isinstance(
                label,
                str,
            ):

                raise CommandError(
                    "Un objeto no contiene modelo válido."
                )

            if not label.startswith(
                f"{APP_LABEL}."
            ):

                raise CommandError(
                    (
                        "El archivo intenta importar un modelo "
                        f"externo a ia_local: {label}"
                    )
                )

            try:

                modelo = apps.get_model(
                    label
                )

            except LookupError as exc:

                raise CommandError(
                    (
                        "El modelo del archivo no existe "
                        f"en este proyecto: {label}"
                    )
                ) from exc

            if modelo is None:

                raise CommandError(
                    f"Modelo no encontrado: {label}"
                )

            modelos_en_archivo.add(
                label
            )

        texto_serializado = json.dumps(
            objetos,
            ensure_ascii=False,
        )

        # -----------------------------------------------------
        # VALIDAR DESERIALIZACIÓN
        # -----------------------------------------------------

        try:

            objetos_deserializados = list(
                serializers.deserialize(
                    "json",
                    texto_serializado,
                )
            )

        except Exception as exc:

            raise CommandError(
                (
                    "Django no pudo interpretar "
                    f"los registros: {exc}"
                )
            ) from exc

        self.stdout.write("")
        self.stdout.write(
            "=" * 78
        )

        self.stdout.write(
            "IA_LOCAL - IMPORTACIÓN DE DATOS"
        )

        self.stdout.write(
            "=" * 78
        )

        self.stdout.write(
            f"Archivo: {ruta}"
        )

        self.stdout.write(
            f"Formato: {payload.get('formato')}"
        )

        self.stdout.write(
            f"Generado en: {payload.get('generado_en')}"
        )

        self.stdout.write(
            f"Registros: {len(objetos_deserializados)}"
        )

        self.stdout.write(
            f"Modelos: {len(modelos_en_archivo)}"
        )

        self.stdout.write("")

        for label in sorted(
            modelos_en_archivo
        ):

            cantidad = sum(
                1
                for item
                in objetos
                if item.get(
                    "model"
                ) == label.lower()
                or item.get(
                    "model"
                ) == label
            )

            self.stdout.write(
                f"{label:<45} {cantidad:>8}"
            )

        # -----------------------------------------------------
        # DRY RUN
        # -----------------------------------------------------

        if options["dry_run"]:

            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    "DRY-RUN correcto. "
                    "La base de datos no fue modificada."
                )
            )

            return

        # -----------------------------------------------------
        # IMPORTACIÓN ATÓMICA
        # -----------------------------------------------------

        with transaction.atomic():

            if options["replace"]:

                self.stdout.write("")
                self.stdout.write(
                    self.style.WARNING(
                        "Modo REPLACE activado."
                    )
                )

                modelos = []

                for label in modelos_en_archivo:

                    modelo = apps.get_model(
                        label
                    )

                    if modelo is not None:
                        modelos.append(
                            modelo
                        )

                # Orden inverso como medida conservadora
                # ante posibles dependencias internas.
                for modelo in reversed(
                    modelos
                ):

                    modelo._default_manager.all().delete()

            creados_o_actualizados = 0

            for objeto in objetos_deserializados:

                objeto.save()

                creados_o_actualizados += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Importación terminada correctamente."
            )
        )

        self.stdout.write(
            (
                "Registros aplicados: "
                f"{creados_o_actualizados}"
            )
        )

        self.stdout.write(
            (
                "Modo: "
                + (
                    "REPLACE"
                    if options["replace"]
                    else "MERGE"
                )
            )
        )