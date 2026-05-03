from datetime import date

from django.db import models
from django.utils import timezone


def default_fecha_caratula():
    """Fecha por defecto en carátula (plantilla histórica)."""
    return date(2026, 1, 28)


def transmital_upload_to(instance, filename):
    code = (instance.codigo_transmital or "sin_codigo").strip().replace("/", "-")
    return f"transmital/{code}.xlsx"


class Transmital(models.Model):
    ITEM_COUNT = 16

    consecutivo = models.PositiveIntegerField(unique=True, db_index=True)
    codigo_transmital = models.CharField(max_length=64, unique=True, db_index=True)
    revision = models.CharField(max_length=32, blank=True, default="")
    fecha_caratula = models.DateField(
        null=True,
        blank=True,
        default=default_fecha_caratula,
    )
    fecha_envio = models.DateField(
        null=True,
        blank=True,
        default=timezone.localdate,
    )
    numero_paginas = models.PositiveIntegerField(default=1)
    destinatario = models.CharField(max_length=255, blank=True, default="")
    empresa = models.CharField(max_length=255, blank=True, default="")
    referencia = models.TextField(blank=True, default="")
    emision = models.CharField(max_length=255, blank=True, default="")
    unidad_revisora = models.CharField(max_length=255, blank=True, default="")
    unidad_emisora = models.CharField(max_length=255, blank=True, default="")
    file = models.FileField(upload_to=transmital_upload_to)
    imported_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    acreditacion_personal = models.BooleanField(default=False, blank=True)
    acreditacion_maquinas = models.BooleanField(default=False, blank=True)
    procedimientos = models.BooleanField(default=False, blank=True)
    protocolos = models.BooleanField(default=False, blank=True)
    informacion = models.BooleanField(default=False, blank=True)
    otros = models.BooleanField(default=False, blank=True)

    item_01_documento = models.CharField(max_length=255, blank=True, default="")
    item_01_rev_documento = models.CharField(max_length=32, blank=True, default="")
    item_01_titulo = models.CharField(max_length=512, blank=True, default="")
    item_01_rev_emisor = models.CharField(max_length=32, blank=True, default="")
    item_01_estatus = models.CharField(max_length=128, blank=True, default="")
    item_02_documento = models.CharField(max_length=255, blank=True, default="")
    item_02_rev_documento = models.CharField(max_length=32, blank=True, default="")
    item_02_titulo = models.CharField(max_length=512, blank=True, default="")
    item_02_rev_emisor = models.CharField(max_length=32, blank=True, default="")
    item_02_estatus = models.CharField(max_length=128, blank=True, default="")
    item_03_documento = models.CharField(max_length=255, blank=True, default="")
    item_03_rev_documento = models.CharField(max_length=32, blank=True, default="")
    item_03_titulo = models.CharField(max_length=512, blank=True, default="")
    item_03_rev_emisor = models.CharField(max_length=32, blank=True, default="")
    item_03_estatus = models.CharField(max_length=128, blank=True, default="")
    item_04_documento = models.CharField(max_length=255, blank=True, default="")
    item_04_rev_documento = models.CharField(max_length=32, blank=True, default="")
    item_04_titulo = models.CharField(max_length=512, blank=True, default="")
    item_04_rev_emisor = models.CharField(max_length=32, blank=True, default="")
    item_04_estatus = models.CharField(max_length=128, blank=True, default="")
    item_05_documento = models.CharField(max_length=255, blank=True, default="")
    item_05_rev_documento = models.CharField(max_length=32, blank=True, default="")
    item_05_titulo = models.CharField(max_length=512, blank=True, default="")
    item_05_rev_emisor = models.CharField(max_length=32, blank=True, default="")
    item_05_estatus = models.CharField(max_length=128, blank=True, default="")
    item_06_documento = models.CharField(max_length=255, blank=True, default="")
    item_06_rev_documento = models.CharField(max_length=32, blank=True, default="")
    item_06_titulo = models.CharField(max_length=512, blank=True, default="")
    item_06_rev_emisor = models.CharField(max_length=32, blank=True, default="")
    item_06_estatus = models.CharField(max_length=128, blank=True, default="")
    item_07_documento = models.CharField(max_length=255, blank=True, default="")
    item_07_rev_documento = models.CharField(max_length=32, blank=True, default="")
    item_07_titulo = models.CharField(max_length=512, blank=True, default="")
    item_07_rev_emisor = models.CharField(max_length=32, blank=True, default="")
    item_07_estatus = models.CharField(max_length=128, blank=True, default="")
    item_08_documento = models.CharField(max_length=255, blank=True, default="")
    item_08_rev_documento = models.CharField(max_length=32, blank=True, default="")
    item_08_titulo = models.CharField(max_length=512, blank=True, default="")
    item_08_rev_emisor = models.CharField(max_length=32, blank=True, default="")
    item_08_estatus = models.CharField(max_length=128, blank=True, default="")
    item_09_documento = models.CharField(max_length=255, blank=True, default="")
    item_09_rev_documento = models.CharField(max_length=32, blank=True, default="")
    item_09_titulo = models.CharField(max_length=512, blank=True, default="")
    item_09_rev_emisor = models.CharField(max_length=32, blank=True, default="")
    item_09_estatus = models.CharField(max_length=128, blank=True, default="")
    item_10_documento = models.CharField(max_length=255, blank=True, default="")
    item_10_rev_documento = models.CharField(max_length=32, blank=True, default="")
    item_10_titulo = models.CharField(max_length=512, blank=True, default="")
    item_10_rev_emisor = models.CharField(max_length=32, blank=True, default="")
    item_10_estatus = models.CharField(max_length=128, blank=True, default="")
    item_11_documento = models.CharField(max_length=255, blank=True, default="")
    item_11_rev_documento = models.CharField(max_length=32, blank=True, default="")
    item_11_titulo = models.CharField(max_length=512, blank=True, default="")
    item_11_rev_emisor = models.CharField(max_length=32, blank=True, default="")
    item_11_estatus = models.CharField(max_length=128, blank=True, default="")
    item_12_documento = models.CharField(max_length=255, blank=True, default="")
    item_12_rev_documento = models.CharField(max_length=32, blank=True, default="")
    item_12_titulo = models.CharField(max_length=512, blank=True, default="")
    item_12_rev_emisor = models.CharField(max_length=32, blank=True, default="")
    item_12_estatus = models.CharField(max_length=128, blank=True, default="")
    item_13_documento = models.CharField(max_length=255, blank=True, default="")
    item_13_rev_documento = models.CharField(max_length=32, blank=True, default="")
    item_13_titulo = models.CharField(max_length=512, blank=True, default="")
    item_13_rev_emisor = models.CharField(max_length=32, blank=True, default="")
    item_13_estatus = models.CharField(max_length=128, blank=True, default="")
    item_14_documento = models.CharField(max_length=255, blank=True, default="")
    item_14_rev_documento = models.CharField(max_length=32, blank=True, default="")
    item_14_titulo = models.CharField(max_length=512, blank=True, default="")
    item_14_rev_emisor = models.CharField(max_length=32, blank=True, default="")
    item_14_estatus = models.CharField(max_length=128, blank=True, default="")
    item_15_documento = models.CharField(max_length=255, blank=True, default="")
    item_15_rev_documento = models.CharField(max_length=32, blank=True, default="")
    item_15_titulo = models.CharField(max_length=512, blank=True, default="")
    item_15_rev_emisor = models.CharField(max_length=32, blank=True, default="")
    item_15_estatus = models.CharField(max_length=128, blank=True, default="")
    item_16_documento = models.CharField(max_length=255, blank=True, default="")
    item_16_rev_documento = models.CharField(max_length=32, blank=True, default="")
    item_16_titulo = models.CharField(max_length=512, blank=True, default="")
    item_16_rev_emisor = models.CharField(max_length=32, blank=True, default="")
    item_16_estatus = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        ordering = ["-consecutivo"]
        verbose_name = "Transmital"
        verbose_name_plural = "Transmitales"

    def __str__(self):
        return self.codigo_transmital


class TransmitalFolderConfig(models.Model):
    base_path = models.CharField(max_length=1024, default="/home/max/condocdat/doc")
    current_number = models.PositiveIntegerField(default=293)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración creador carpetas transmital"
        verbose_name_plural = "Configuración creador carpetas transmital"

    def __str__(self):
        return f"{self.base_path} ({self.current_number})"


class TransmitalFolderLog(models.Model):
    folder_name = models.CharField(max_length=128, unique=True)
    folder_path = models.CharField(max_length=2048, unique=True)
    sequence_number = models.PositiveIntegerField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sequence_number"]
        verbose_name = "Carpeta transmital creada"
        verbose_name_plural = "Carpetas transmital creadas"

    def __str__(self):
        return self.folder_name
