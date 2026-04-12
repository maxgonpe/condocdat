from django.contrib import admin

from .models import (
    EquiposAsset,
    EquiposCambioLog,
    EquiposLibro,
    EquiposLocation,
    EquiposOtro,
    EquiposResumenFila,
    EquiposSignificadoFila,
)


@admin.register(EquiposLibro)
class EquiposLibroAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "imported_at", "updated_at")
    readonly_fields = ("imported_at", "updated_at")


@admin.register(EquiposResumenFila)
class EquiposResumenFilaAdmin(admin.ModelAdmin):
    list_display = ("libro", "excel_row", "etiqueta", "cuenta")


@admin.register(EquiposSignificadoFila)
class EquiposSignificadoFilaAdmin(admin.ModelAdmin):
    list_display = ("libro", "excel_row", "status")


@admin.register(EquiposLocation)
class EquiposLocationAdmin(admin.ModelAdmin):
    list_display = ("libro", "excel_row", "code", "space_name")


@admin.register(EquiposAsset)
class EquiposAssetAdmin(admin.ModelAdmin):
    list_display = ("libro", "excel_row", "row_type", "tag_number", "estado")
    list_filter = ("row_type",)


@admin.register(EquiposOtro)
class EquiposOtroAdmin(admin.ModelAdmin):
    list_display = ("libro", "excel_row", "row_type", "tag_number", "estado")


@admin.register(EquiposCambioLog)
class EquiposCambioLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "modelo", "record_id", "campo")
    list_filter = ("modelo",)
