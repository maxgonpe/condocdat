from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import gantt.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="GanttArchivo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to=gantt.models.gantt_archivo_upload_to)),
                ("original_filename", models.CharField(max_length=255)),
                ("imported_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Archivo Gantt",
                "verbose_name_plural": "Archivos Gantt",
                "ordering": ["-imported_at"],
            },
        ),
        migrations.CreateModel(
            name="GanttTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("excel_row", models.PositiveIntegerField(default=0)),
                ("task_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("unique_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("nombre_tarea", models.CharField(blank=True, default="", max_length=600)),
                ("esp", models.CharField(blank=True, default="", max_length=128)),
                ("duracion", models.CharField(blank=True, default="", max_length=64)),
                ("comienzo", models.DateTimeField(blank=True, null=True)),
                ("fin", models.DateTimeField(blank=True, null=True)),
                ("predecesoras", models.TextField(blank=True, default="")),
                ("sucesoras", models.TextField(blank=True, default="")),
                ("notas", models.TextField(blank=True, default="")),
                ("wbs", models.CharField(blank=True, default="", max_length=128)),
                ("outline_number", models.CharField(blank=True, default="", max_length=128)),
                (
                    "archivo",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tasks", to="gantt.ganttarchivo"),
                ),
            ],
            options={
                "verbose_name": "Tarea Gantt",
                "verbose_name_plural": "Tareas Gantt",
                "ordering": ["task_id", "id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("archivo", "task_id", "unique_id"),
                        name="gantt_task_archivo_task_unique_uniq",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="GanttCambioLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("record_id", models.PositiveIntegerField()),
                ("task_id", models.IntegerField(blank=True, null=True)),
                ("campo", models.CharField(max_length=128)),
                ("valor_anterior", models.TextField(blank=True, default="")),
                ("valor_nuevo", models.TextField(blank=True, default="")),
                (
                    "archivo",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cambios", to="gantt.ganttarchivo"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="gantt_cambios",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Cambio Gantt",
                "verbose_name_plural": "Cambios Gantt",
                "ordering": ["-created_at"],
            },
        ),
    ]
