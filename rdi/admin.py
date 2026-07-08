from django.contrib import admin

from .models import (
    PlanosDiferenciasMensualesRecord,
    PlanosDiferenciasMensualesSnapshot,
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


class PlanosDiferenciasMensualesRecordInline(admin.TabularInline):
    model = PlanosDiferenciasMensualesRecord
    extra = 0
    fields = (
        "specialty",
        "code",
        "version_matriz",
        "version_planos",
        "planos_last_update",
        "iniciales_last_date",
        "folder_path",
    )
    readonly_fields = ("created_at",)
    show_change_link = True


@admin.register(PlanosDiferenciasMensualesSnapshot)
class PlanosDiferenciasMensualesSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "month_start",
        "total_differences",
        "computed_at",
        "computed_by",
    )
    list_filter = ("month_start",)
    search_fields = ("computed_by",)
    readonly_fields = ("computed_at",)
    ordering = ("-month_start",)
    inlines = (PlanosDiferenciasMensualesRecordInline,)
    date_hierarchy = "month_start"


@admin.register(PlanosDiferenciasMensualesRecord)
class PlanosDiferenciasMensualesRecordAdmin(admin.ModelAdmin):
    list_display = (
        "snapshot",
        "specialty",
        "code",
        "version_matriz",
        "version_planos",
        "planos_last_update",
        "iniciales_last_date",
    )
    list_filter = ("specialty", "snapshot")
    search_fields = ("code", "folder_path", "specialty", "version_transition")
    readonly_fields = ("created_at",)
    ordering = ("snapshot__month_start", "specialty", "code")
    raw_id_fields = ("snapshot",)

