from django.contrib import admin

from .models import GanttArchivo, GanttCambioLog, GanttTask


@admin.register(GanttArchivo)
class GanttArchivoAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "imported_at", "updated_at")
    readonly_fields = ("imported_at", "updated_at")
    search_fields = ("original_filename",)
    ordering = ("-imported_at",)


@admin.register(GanttTask)
class GanttTaskAdmin(admin.ModelAdmin):
    list_display = (
        "archivo",
        "task_id",
        "unique_id",
        "nombre_tarea",
        "especialidad",
        "esp",
        "duracion",
        "avance_planificado",
        "trabajo_completado",
        "comienzo",
        "fin",
    )
    list_filter = ("archivo", "especialidad")
    search_fields = (
        "nombre_tarea",
        "especialidad",
        "esp",
        "predecesoras",
        "sucesoras",
        "notas",
    )
    ordering = ("archivo", "task_id", "id")
    list_per_page = 100


@admin.register(GanttCambioLog)
class GanttCambioLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "archivo", "user", "task_id", "campo")
    list_filter = ("archivo", "campo", "created_at")
    search_fields = ("campo", "valor_anterior", "valor_nuevo")
    ordering = ("-created_at",)
