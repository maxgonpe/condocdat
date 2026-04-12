# Generated manually for equipos app

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EquiposLibro",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("file", models.FileField(upload_to="equipos/%Y/%m/")),
                ("original_filename", models.CharField(max_length=255)),
                ("imported_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Libro equipos",
                "verbose_name_plural": "Libros equipos",
                "ordering": ["-imported_at"],
            },
        ),
        migrations.CreateModel(
            name="EquiposResumenFila",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("excel_row", models.PositiveIntegerField()),
                ("etiqueta", models.CharField(blank=True, default="", max_length=255)),
                ("cuenta", models.IntegerField(blank=True, null=True)),
                ("fraccion", models.FloatField(blank=True, null=True)),
                (
                    "libro",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="resumen_filas",
                        to="equipos.equiposlibro",
                    ),
                ),
            ],
            options={
                "ordering": ["excel_row"],
            },
        ),
        migrations.CreateModel(
            name="EquiposSignificadoFila",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("excel_row", models.PositiveIntegerField()),
                ("flujo", models.CharField(blank=True, default="", max_length=64)),
                ("status", models.CharField(blank=True, default="", max_length=255)),
                ("significado", models.TextField(blank=True, default="")),
                (
                    "libro",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="significado_filas",
                        to="equipos.equiposlibro",
                    ),
                ),
            ],
            options={
                "ordering": ["excel_row"],
            },
        ),
        migrations.CreateModel(
            name="EquiposLocation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("excel_row", models.PositiveIntegerField()),
                ("campus", models.CharField(blank=True, default="", max_length=255)),
                ("building", models.CharField(blank=True, default="", max_length=255)),
                ("zones", models.CharField(blank=True, default="", max_length=255)),
                ("floors", models.CharField(blank=True, default="", max_length=64)),
                ("space_name", models.CharField(blank=True, default="", max_length=512)),
                ("fase", models.CharField(blank=True, default="", max_length=64)),
                (
                    "area_m2",
                    models.DecimalField(
                        blank=True, decimal_places=4, max_digits=14, null=True
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        blank=True, db_index=True, default="", max_length=128
                    ),
                ),
                (
                    "libro",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="locations",
                        to="equipos.equiposlibro",
                    ),
                ),
            ],
            options={
                "ordering": ["excel_row"],
            },
        ),
        migrations.CreateModel(
            name="EquiposAsset",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("excel_row", models.PositiveIntegerField()),
                (
                    "row_type",
                    models.CharField(
                        choices=[
                            ("TITULO", "Título"),
                            ("SUBTITULO", "Subtítulo"),
                            ("TAREA", "Tarea"),
                        ],
                        default="TAREA",
                        max_length=16,
                    ),
                ),
                ("tipe", models.CharField(blank=True, default="", max_length=64)),
                (
                    "especialidad",
                    models.CharField(blank=True, default="", max_length=64),
                ),
                (
                    "tag_number",
                    models.CharField(
                        blank=True, db_index=True, default="", max_length=128
                    ),
                ),
                ("asset_name", models.CharField(blank=True, default="", max_length=512)),
                ("space_room", models.CharField(blank=True, default="", max_length=512)),
                ("unit", models.CharField(blank=True, default="", max_length=64)),
                ("quantity", models.CharField(blank=True, default="", max_length=64)),
                ("phase", models.CharField(blank=True, default="", max_length=64)),
                ("zones", models.CharField(blank=True, default="", max_length=255)),
                ("proveedor", models.CharField(blank=True, default="", max_length=255)),
                ("vendor", models.CharField(blank=True, default="", max_length=255)),
                ("estado", models.CharField(blank=True, default="", max_length=255)),
                ("con_oc", models.CharField(blank=True, default="", max_length=64)),
                ("fecha_compra", models.DateField(blank=True, null=True)),
                ("rdi_ttal", models.CharField(blank=True, default="", max_length=128)),
                ("fecha_llegada_obra", models.DateField(blank=True, null=True)),
                ("fecha_planificacion", models.DateField(blank=True, null=True)),
                ("cumple", models.CharField(blank=True, default="", max_length=32)),
                ("dias", models.CharField(blank=True, default="", max_length=32)),
                (
                    "avance_montaje",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "avance_conexion",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "libro",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assets",
                        to="equipos.equiposlibro",
                    ),
                ),
            ],
            options={
                "ordering": ["excel_row"],
            },
        ),
        migrations.CreateModel(
            name="EquiposOtro",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("excel_row", models.PositiveIntegerField()),
                (
                    "row_type",
                    models.CharField(
                        choices=[
                            ("SECTION", "Encabezado especialidad"),
                            ("DATA", "Fila datos"),
                        ],
                        default="DATA",
                        max_length=16,
                    ),
                ),
                ("tipe", models.CharField(blank=True, default="", max_length=64)),
                (
                    "especialidad",
                    models.CharField(blank=True, default="", max_length=64),
                ),
                (
                    "tag_number",
                    models.CharField(
                        blank=True, db_index=True, default="", max_length=128
                    ),
                ),
                ("asset_name", models.CharField(blank=True, default="", max_length=512)),
                ("estado", models.CharField(blank=True, default="", max_length=255)),
                ("rdi_ttal", models.CharField(blank=True, default="", max_length=128)),
                (
                    "fecha_envio_rdi",
                    models.CharField(blank=True, default="", max_length=64),
                ),
                (
                    "fecha_respuesta_rdi",
                    models.CharField(blank=True, default="", max_length=64),
                ),
                ("con_oc", models.CharField(blank=True, default="", max_length=64)),
                (
                    "libro",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="otros",
                        to="equipos.equiposlibro",
                    ),
                ),
            ],
            options={
                "verbose_name": "Otro equipo",
                "verbose_name_plural": "Otros equipos",
                "ordering": ["excel_row"],
            },
        ),
        migrations.CreateModel(
            name="EquiposCambioLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("modelo", models.CharField(db_index=True, max_length=64)),
                ("record_id", models.PositiveIntegerField()),
                ("excel_row", models.PositiveIntegerField(blank=True, null=True)),
                ("campo", models.CharField(max_length=128)),
                ("valor_anterior", models.TextField(blank=True, default="")),
                ("valor_nuevo", models.TextField(blank=True, default="")),
                (
                    "libro",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cambios",
                        to="equipos.equiposlibro",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="equipos_cambios",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Cambio equipos",
                "verbose_name_plural": "Cambios equipos",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="equiposresumenfila",
            constraint=models.UniqueConstraint(
                fields=("libro", "excel_row"), name="equipos_resumen_libro_row_uniq"
            ),
        ),
        migrations.AddConstraint(
            model_name="equipossignificadofila",
            constraint=models.UniqueConstraint(
                fields=("libro", "excel_row"), name="equipos_signif_libro_row_uniq"
            ),
        ),
        migrations.AddConstraint(
            model_name="equiposlocation",
            constraint=models.UniqueConstraint(
                fields=("libro", "excel_row"), name="equipos_loc_libro_row_uniq"
            ),
        ),
        migrations.AddConstraint(
            model_name="equiposasset",
            constraint=models.UniqueConstraint(
                fields=("libro", "excel_row"), name="equipos_asset_libro_row_uniq"
            ),
        ),
        migrations.AddConstraint(
            model_name="equiposotro",
            constraint=models.UniqueConstraint(
                fields=("libro", "excel_row"), name="equipos_otro_libro_row_uniq"
            ),
        ),
    ]
