from django.contrib import admin

from .models import RDIImport, RDIRecord


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

