# Planos iniciales (hojas por especialidad en .xls/.xlsx)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rdi", "0003_planosimport_planosrecord"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlanosInicialesImport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="planos_iniciales/%Y/%m/")),
                ("original_filename", models.CharField(max_length=255)),
                ("snapshot_datetime", models.DateTimeField(blank=True, null=True)),
                ("imported_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Planos iniciales Import",
                "verbose_name_plural": "Planos iniciales Imports",
                "ordering": ["-snapshot_datetime", "-imported_at"],
            },
        ),
        migrations.CreateModel(
            name="PlanosInicialesRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("specialty", models.CharField(db_index=True, max_length=16)),
                (
                    "excel_row",
                    models.PositiveIntegerField(
                        help_text="Número de fila en la hoja Excel (1 = encabezados).",
                    ),
                ),
                ("columns_json", models.JSONField(default=dict)),
                ("column_headers_order", models.JSONField(default=list)),
                ("search_text", models.TextField(blank=True, default="")),
                ("last_snapshot_datetime", models.DateTimeField(blank=True, null=True)),
                ("last_diff_fields", models.TextField(blank=True, default="")),
                (
                    "last_import",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="rdi.planosinicialesimport",
                    ),
                ),
            ],
            options={
                "verbose_name": "Planos iniciales Record",
                "verbose_name_plural": "Planos iniciales Records",
                "ordering": ["specialty", "excel_row"],
            },
        ),
        migrations.AddConstraint(
            model_name="planosinicialesrecord",
            constraint=models.UniqueConstraint(
                fields=("specialty", "excel_row"),
                name="uniq_planos_iniciales_specialty_excel_row",
            ),
        ),
    ]
