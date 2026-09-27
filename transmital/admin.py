from django.contrib import admin

from .models import Transmital, TransmitalFolderConfig, TransmitalFolderLog,\
     ProjectEventLink, ProjectEventLink, TraceSourceCoverage 


@admin.register(Transmital)
class TransmitalAdmin(admin.ModelAdmin):
    list_display = (
        "codigo_transmital",
        "consecutivo",
        "fecha_envio",
        "revision",
        "updated_at",
    )
    search_fields = ("codigo_transmital", "destinatario", "empresa", "referencia")
    list_filter = ("fecha_envio", "fecha_caratula", "revision")
    ordering = ("-consecutivo",)


@admin.register(TransmitalFolderConfig)
class TransmitalFolderConfigAdmin(admin.ModelAdmin):
    list_display = ("base_path", "current_number", "updated_at")
    search_fields = ("base_path",)


@admin.register(TransmitalFolderLog)
class TransmitalFolderLogAdmin(admin.ModelAdmin):
    list_display = ("folder_name", "sequence_number", "created_at")
    search_fields = ("folder_name", "folder_path")
    list_filter = ("created_at",)
    ordering = ("-sequence_number",)


from django.contrib import admin

from .models import (
    Transmital,
    ProjectEvent,
    ProjectEventLink,
    TraceSourceCoverage,
)


@admin.register(ProjectEvent)
class ProjectEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_date",
        "event_type",
        "source_key",
        "source_model",
        "origin",
        "data_quality",
        "source_completeness",
    )

    list_filter = (
        "event_type",
        "origin",
        "data_quality",
        "source_completeness",
        "date_precision",
        "source_app",
        "source_model",
    )

    search_fields = (
        "event_uid",
        "source_key",
        "title",
        "summary",
        "search_text",
        "actor",
        "company",
    )

    ordering = (
        "-event_date",
        "-event_datetime",
        "-id",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    date_hierarchy = "event_date"

    fieldsets = (
        (
            "Evento",
            {
                "fields": (
                    "event_uid",
                    "event_type",
                    "origin",
                    "data_quality",
                    "source_completeness",
                )
            },
        ),
        (
            "Fecha",
            {
                "fields": (
                    "event_date",
                    "event_datetime",
                    "date_precision",
                    "date_source",
                    "observed_at",
                )
            },
        ),
        (
            "Fuente original",
            {
                "fields": (
                    "source_app",
                    "source_model",
                    "source_pk",
                    "source_key",
                )
            },
        ),
        (
            "Descripción",
            {
                "fields": (
                    "title",
                    "summary",
                    "search_text",
                )
            },
        ),
        (
            "Cambios",
            {
                "fields": (
                    "status_before",
                    "status_after",
                    "revision_before",
                    "revision_after",
                    "changes",
                )
            },
        ),
        (
            "Actores",
            {
                "fields": (
                    "actor",
                    "company",
                )
            },
        ),
        (
            "Datos adicionales",
            {
                "fields": (
                    "metadata",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(ProjectEventLink)
class ProjectEventLinkAdmin(admin.ModelAdmin):
    list_display = (
        "event",
        "entity_type",
        "entity_key",
        "relation_role",
        "relation_basis",
        "confidence",
    )

    list_filter = (
        "entity_type",
        "relation_role",
        "relation_basis",
    )

    search_fields = (
        "entity_key",
        "entity_pk",
        "entity_model",
        "entity_app",
        "entity_revision",
        "event__source_key",
        "event__title",
    )

    autocomplete_fields = (
        "event",
    )

    ordering = (
        "-event__event_date",
        "-id",
    )

    readonly_fields = (
        "created_at",
    )


@admin.register(TraceSourceCoverage)
class TraceSourceCoverageAdmin(admin.ModelAdmin):
    list_display = (
        "source_type",
        "coverage_start",
        "coverage_end",
        "coverage_status",
        "basis",
    )

    list_filter = (
        "source_type",
        "coverage_status",
    )

    search_fields = (
        "description",
        "basis",
    )

    ordering = (
        "source_type",
        "coverage_start",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )