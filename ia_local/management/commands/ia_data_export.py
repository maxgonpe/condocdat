from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import django
from django.apps import apps
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError


FORMATO = "IA-LOCAL-DATA-v1"
APP_LABEL = "ia_local"


class Command(BaseCommand):

    help = (
        "Exporta todos los registros de los modelos de ia_local "
        "a un archivo JSON portable."
    )


    def add_arguments(self, parser):

        parser.add_argument(
            "archivo",
            nargs="?",
            default="ia_local_data.json",
            help="Archivo JSON de salida.",
        )

        parser.add_argument(
            "--inventario",
            action="store_true",
            help=(
                "Muestra los modelos y cantidades detectadas "
                "antes de exportar."
            ),
        )


    def handle(self, *args, **options):

        try:
            app_config = apps.get_app_config(
                APP_LABEL
            )
        except LookupError as exc:
            raise CommandError(
                "La app ia_local no está registrada."
            ) from exc

        modelos = sorted(
            [
                modelo
                for modelo
                in app_config.get_models()
                if not modelo._meta.auto_created
            ],
            key=lambda modelo: modelo._meta.label_lower,
        )

        if not modelos:
            raise CommandError(
                "No se detectaron modelos en ia_local."
            )

        objetos_serializados = []
        inventario = []

        self.stdout.write("")
        self.stdout.write(
            "=" * 78
        )
        self.stdout.write(
            "IA_LOCAL - EXPORTACIÓN DE DATOS"
        )
        self.stdout.write(
            "=" * 78
        )

        for modelo in modelos:

            label = modelo._meta.label
            tabla = modelo._meta.db_table

            queryset = modelo._default_manager.all()

            pk_nombre = (
                modelo._meta.pk.name
                if modelo._meta.pk
                else None
            )

            if pk_nombre:
                queryset = queryset.order_by(
                    pk_nombre
                )

            cantidad = queryset.count()

            inventario.append(
                {
                    "modelo": label,
                    "tabla": tabla,
                    "cantidad": cantidad,
                }
            )

            self.stdout.write(
                f"{label:<45} "
                f"{cantidad:>8} registros"
            )

            if cantidad == 0:
                continue

            texto = serializers.serialize(
                "json",
                queryset,
                use_natural_foreign_keys=False,
                use_natural_primary_keys=False,
            )

            datos = json.loads(
                texto
            )

            objetos_serializados.extend(
                datos
            )

        payload = {
            "formato":
                FORMATO,

            "app":
                APP_LABEL,

            "django_version":
                django.get_version(),

            "generado_en":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "modelos":
                inventario,

            "total_modelos":
                len(
                    modelos
                ),

            "total_registros":
                len(
                    objetos_serializados
                ),

            "objetos":
                objetos_serializados,
        }

        destino = Path(
            options["archivo"]
        ).expanduser().resolve()

        destino.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with destino.open(
            "w",
            encoding="utf-8",
        ) as archivo:

            json.dump(
                payload,
                archivo,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

            archivo.write(
                "\n"
            )

        self.stdout.write("")
        self.stdout.write(
            "-" * 78
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Exportación terminada: {destino}"
            )
        )

        self.stdout.write(
            f"Modelos detectados: {len(modelos)}"
        )

        self.stdout.write(
            f"Registros exportados: "
            f"{len(objetos_serializados)}"
        )

        self.stdout.write(
            f"Formato: {FORMATO}"
        )