from django.conf import settings
from django.db import models


def equipos_libro_upload_to(instance, filename):
    """
    Un solo archivo en media: siempre la misma ruta para importar y sincronizar
    (evita sufijos aleatorios tipo archivo_abc123.xlsx).
    """
    return "equipos/libro_actual.xlsx"


class EquiposLibro(models.Model):
    """Un libro Excel cargado (control de equipos). Solo el más reciente se usa en la UI."""

    file = models.FileField(upload_to=equipos_libro_upload_to)
    original_filename = models.CharField(max_length=255)
    imported_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Libro equipos"
        verbose_name_plural = "Libros equipos"
        ordering = ["-imported_at"]

    def __str__(self) -> str:
        return self.original_filename or f"Libro #{self.pk}"


class EquiposResumenFila(models.Model):
    """Hoja «Resumen - TD»: filas de la tabla pivot (etiqueta, cuenta, fracción)."""

    libro = models.ForeignKey(
        EquiposLibro, on_delete=models.CASCADE, related_name="resumen_filas"
    )
    excel_row = models.PositiveIntegerField()
    etiqueta = models.CharField(max_length=255, blank=True, default="")
    cuenta = models.IntegerField(null=True, blank=True)
    fraccion = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["excel_row"]
        constraints = [
            models.UniqueConstraint(
                fields=["libro", "excel_row"], name="equipos_resumen_libro_row_uniq"
            )
        ]

    def __str__(self) -> str:
        return f"{self.etiqueta} ({self.cuenta})"


class EquiposSignificadoFila(models.Model):
    """Hoja «Significado status»."""

    libro = models.ForeignKey(
        EquiposLibro, on_delete=models.CASCADE, related_name="significado_filas"
    )
    excel_row = models.PositiveIntegerField()
    flujo = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=255, blank=True, default="")
    significado = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["excel_row"]
        constraints = [
            models.UniqueConstraint(
                fields=["libro", "excel_row"], name="equipos_signif_libro_row_uniq"
            )
        ]


class EquiposLocation(models.Model):
    """Hoja «Locations»."""

    libro = models.ForeignKey(
        EquiposLibro, on_delete=models.CASCADE, related_name="locations"
    )
    excel_row = models.PositiveIntegerField()
    campus = models.CharField(max_length=255, blank=True, default="")
    building = models.CharField(max_length=255, blank=True, default="")
    zones = models.CharField(max_length=255, blank=True, default="")
    floors = models.CharField(max_length=64, blank=True, default="")
    space_name = models.CharField(max_length=512, blank=True, default="")
    fase = models.CharField(max_length=64, blank=True, default="")
    area_m2 = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True
    )
    code = models.CharField(max_length=128, blank=True, default="", db_index=True)

    class Meta:
        ordering = ["excel_row"]
        constraints = [
            models.UniqueConstraint(
                fields=["libro", "excel_row"], name="equipos_loc_libro_row_uniq"
            )
        ]


class EquiposAsset(models.Model):
    """Hoja «Asset» (incluye filas TITULO / SUBTITULO / TAREA)."""

    ROW_TITULO = "TITULO"
    ROW_SUBTITULO = "SUBTITULO"
    ROW_TAREA = "TAREA"
    ROW_CHOICES = [
        (ROW_TITULO, "Título"),
        (ROW_SUBTITULO, "Subtítulo"),
        (ROW_TAREA, "Tarea"),
    ]

    libro = models.ForeignKey(
        EquiposLibro, on_delete=models.CASCADE, related_name="assets"
    )
    excel_row = models.PositiveIntegerField()
    row_type = models.CharField(max_length=16, choices=ROW_CHOICES, default=ROW_TAREA)
    tipe = models.CharField(max_length=64, blank=True, default="")
    especialidad = models.CharField(max_length=64, blank=True, default="")
    tag_number = models.CharField(max_length=128, blank=True, default="", db_index=True)
    asset_name = models.CharField(max_length=512, blank=True, default="")
    space_room = models.CharField(max_length=512, blank=True, default="")
    unit = models.CharField(max_length=64, blank=True, default="")
    quantity = models.CharField(max_length=64, blank=True, default="")
    phase = models.CharField(max_length=64, blank=True, default="")
    zones = models.CharField(max_length=255, blank=True, default="")
    proveedor = models.CharField(max_length=255, blank=True, default="")
    vendor = models.CharField(max_length=255, blank=True, default="")
    estado = models.CharField(max_length=255, blank=True, default="")
    con_oc = models.CharField(max_length=64, blank=True, default="")
    fecha_compra = models.DateField(null=True, blank=True)
    rdi_ttal = models.CharField(max_length=128, blank=True, default="")
    fecha_llegada_obra = models.DateField(null=True, blank=True)
    fecha_planificacion = models.DateField(null=True, blank=True)
    cumple = models.CharField(max_length=32, blank=True, default="")
    dias = models.CharField(max_length=32, blank=True, default="")
    avance_montaje = models.CharField(max_length=255, blank=True, default="")
    avance_conexion = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["excel_row"]
        constraints = [
            models.UniqueConstraint(
                fields=["libro", "excel_row"], name="equipos_asset_libro_row_uniq"
            )
        ]


class EquiposOtro(models.Model):
    """Hoja «Otros equipos»."""

    ROW_SECTION = "SECTION"
    ROW_DATA = "DATA"
    ROW_CHOICES = [
        (ROW_SECTION, "Encabezado especialidad"),
        (ROW_DATA, "Fila datos"),
    ]

    libro = models.ForeignKey(
        EquiposLibro, on_delete=models.CASCADE, related_name="otros"
    )
    excel_row = models.PositiveIntegerField()
    row_type = models.CharField(max_length=16, choices=ROW_CHOICES, default=ROW_DATA)
    tipe = models.CharField(max_length=64, blank=True, default="")
    especialidad = models.CharField(max_length=64, blank=True, default="")
    tag_number = models.CharField(max_length=128, blank=True, default="", db_index=True)
    asset_name = models.CharField(max_length=512, blank=True, default="")
    estado = models.CharField(max_length=255, blank=True, default="")
    rdi_ttal = models.CharField(max_length=128, blank=True, default="")
    fecha_envio_rdi = models.CharField(max_length=64, blank=True, default="")
    fecha_respuesta_rdi = models.CharField(max_length=64, blank=True, default="")
    con_oc = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["excel_row"]
        verbose_name = "Otro equipo"
        verbose_name_plural = "Otros equipos"
        constraints = [
            models.UniqueConstraint(
                fields=["libro", "excel_row"], name="equipos_otro_libro_row_uniq"
            )
        ]


class EquiposCambioLog(models.Model):
    """Registro de cambios desde formularios (no incluye reimportación completa)."""

    libro = models.ForeignKey(
        EquiposLibro, on_delete=models.CASCADE, related_name="cambios"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipos_cambios",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modelo = models.CharField(max_length=64, db_index=True)
    record_id = models.PositiveIntegerField()
    excel_row = models.PositiveIntegerField(null=True, blank=True)
    campo = models.CharField(max_length=128)
    valor_anterior = models.TextField(blank=True, default="")
    valor_nuevo = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Cambio equipos"
        verbose_name_plural = "Cambios equipos"

    def __str__(self) -> str:
        return f"{self.modelo}#{self.record_id} {self.campo}"
