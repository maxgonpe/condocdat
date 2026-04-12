from django.contrib import admin

from .models import (
    PlanosImport,
    PlanosInicialesImport,
    PlanosInicialesRecord,
    PlanosRecord,
    RDIImport,
    RDIRecord,
)


@admin.register(RDIImport)
class RDIImportAdmin(admin.ModelAdmin):
    list_display = ("id", "original_filename", "snapshot_datetime", "imported_at", "file")
    readonly_fields = ("imported_at",)
    search_fields = ("original_filename",)


@admin.register(RDIRecord)
class RDIRecordAdmin(admin.ModelAdmin):
    list_display = (
        "csv_id",
        "title",
        "status",
        "informado",
        "due_date",
        "created_at",
        "updated_at",
        "associated_to_document",
        "last_snapshot_datetime",
    )
    list_filter = ("status", "informado")
    search_fields = ("title", "question", "response")
    ordering = ("csv_id",)


@admin.register(PlanosImport)
class PlanosImportAdmin(admin.ModelAdmin):
    list_display = ("id", "original_filename", "snapshot_datetime", "imported_at", "file")
    readonly_fields = ("imported_at",)
    search_fields = ("original_filename",)


@admin.register(PlanosRecord)
class PlanosRecordAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "version",
        "folder_path",
        "last_update_at",
        "updated_by",
        "revision",
        "last_snapshot_datetime",
    )
    list_filter = ("version",)
    search_fields = ("name", "folder_path", "title", "description", "revision")
    ordering = ("name", "folder_path")


@admin.register(PlanosInicialesImport)
class PlanosInicialesImportAdmin(admin.ModelAdmin):
    list_display = ("id", "original_filename", "snapshot_datetime", "imported_at", "file")
    readonly_fields = ("imported_at",)
    search_fields = ("original_filename",)


@admin.register(PlanosInicialesRecord)
class PlanosInicialesRecordAdmin(admin.ModelAdmin):
    list_display = (
        "specialty",
        "excel_row",
        "last_snapshot_datetime",
        "last_import",
    )
    list_filter = ("specialty",)
    search_fields = ("search_text", "specialty")
    ordering = ("specialty", "excel_row")

