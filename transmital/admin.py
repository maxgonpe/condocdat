from django.contrib import admin

from .models import Transmital, TransmitalFolderConfig, TransmitalFolderLog


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
