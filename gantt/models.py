from django.conf import settings
from django.db import models


def gantt_archivo_upload_to(instance, filename):
    return "gantt/cronograma_actual.mpp"


class GanttArchivo(models.Model):
    file = models.FileField(upload_to=gantt_archivo_upload_to)
    original_filename = models.CharField(max_length=255)
    imported_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Archivo Gantt"
        verbose_name_plural = "Archivos Gantt"
        ordering = ["-imported_at"]

    def __str__(self):
        return self.original_filename or f"Gantt #{self.pk}"


class GanttTask(models.Model):
    archivo = models.ForeignKey(
        GanttArchivo, on_delete=models.CASCADE, related_name="tasks"
    )
    excel_row = models.PositiveIntegerField(default=0)
    task_id = models.IntegerField(null=True, blank=True, db_index=True)
    unique_id = models.IntegerField(null=True, blank=True, db_index=True)
    nombre_tarea = models.CharField(max_length=600, blank=True, default="")
    esp = models.CharField(max_length=128, blank=True, default="")
    especialidad = models.CharField(max_length=128, blank=True, default="", db_index=True)
    duracion = models.CharField(max_length=64, blank=True, default="")
    comienzo = models.DateTimeField(null=True, blank=True)
    fin = models.DateTimeField(null=True, blank=True)
    predecesoras = models.TextField(blank=True, default="")
    sucesoras = models.TextField(blank=True, default="")
    notas = models.TextField(blank=True, default="")
    wbs = models.CharField(max_length=128, blank=True, default="")
    outline_number = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        verbose_name = "Tarea Gantt"
        verbose_name_plural = "Tareas Gantt"
        ordering = ["task_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["archivo", "task_id", "unique_id"],
                name="gantt_task_archivo_task_unique_uniq",
            )
        ]

    def __str__(self):
        base = self.nombre_tarea or "Tarea sin nombre"
        if self.task_id is None:
            return base
        return f"{self.task_id} - {base}"


class GanttCambioLog(models.Model):
    archivo = models.ForeignKey(
        GanttArchivo, on_delete=models.CASCADE, related_name="cambios"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gantt_cambios",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    record_id = models.PositiveIntegerField()
    task_id = models.IntegerField(null=True, blank=True)
    campo = models.CharField(max_length=128)
    valor_anterior = models.TextField(blank=True, default="")
    valor_nuevo = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Cambio Gantt"
        verbose_name_plural = "Cambios Gantt"

    def __str__(self):
        return f"Task#{self.record_id} {self.campo}"
