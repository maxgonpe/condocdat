from django.db import models


RDI_STATUS_BORRADOR = "BORRADOR"
RDI_STATUS_REMITIDA = "REMITIDA"
RDI_STATUS_ABIERTA = "ABIERTA"
RDI_STATUS_RESPONDIDA = "RESPONDIDA"
RDI_STATUS_RECHAZADA = "RECHAZADA"
RDI_STATUS_CERRADA = "CERRADA"
RDI_STATUS_NULA = "NULA"


RDI_STATUS_CHOICES = [
    (RDI_STATUS_BORRADOR, "Borrador"),
    (RDI_STATUS_REMITIDA, "Remitida"),
    (RDI_STATUS_ABIERTA, "Abierta"),
    (RDI_STATUS_RESPONDIDA, "Respondida"),
    (RDI_STATUS_RECHAZADA, "Rechazada"),
    (RDI_STATUS_CERRADA, "Cerrada"),
    (RDI_STATUS_NULA, "Nula"),
]

# Mismas opciones que Document.informado (seguimiento «Informar»)
RDI_INFORMADO_NO = "no_informados"
RDI_INFORMADO_SI = "informados"
RDI_INFORMADO_OTRA = "otra_vez_informados"
RDI_INFORMADO_CHOICES = [
    (RDI_INFORMADO_NO, "No informados"),
    (RDI_INFORMADO_SI, "Informados"),
    (RDI_INFORMADO_OTRA, "Otra vez informados"),
]


class RDIImport(models.Model):
    """
    Guarda el CSV importado y la fecha/hora extraída desde el nombre del archivo.
    """

    file = models.FileField(upload_to="rdi/%Y/%m/")
    original_filename = models.CharField(max_length=255)
    snapshot_datetime = models.DateTimeField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "RDI Import"
        verbose_name_plural = "RDI Imports"
        ordering = ["-snapshot_datetime", "-imported_at"]

    def __str__(self) -> str:
        return self.original_filename or f"RDIImport #{self.pk}"


class RDIRecord(models.Model):
    """
    Una fila del CSV: cada columna del CSV -> un campo.
    """

    csv_id = models.IntegerField(unique=True)

    title = models.CharField(max_length=400, blank=True, default="")
    question = models.TextField(blank=True, default="")
    suggested_answer = models.TextField(blank=True, default="")
    location_details = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=12, choices=RDI_STATUS_CHOICES, default=RDI_STATUS_NULA
    )
    informado = models.CharField(
        max_length=32,
        choices=RDI_INFORMADO_CHOICES,
        default=RDI_INFORMADO_NO,
        db_index=True,
        help_text="Estado de información (mismo criterio que documentos Informar).",
    )
    response = models.TextField(blank=True, default="")
    assigned_to = models.CharField(max_length=255, blank=True, default="")
    assignee_type = models.CharField(max_length=255, blank=True, default="")
    company = models.CharField(max_length=255, blank=True, default="")

    due_date = models.DateTimeField(null=True, blank=True)
    associated_to_document = models.BooleanField(null=True, blank=True)

    created_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=255, blank=True, default="")
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.CharField(max_length=255, blank=True, default="")

    distribution_list = models.TextField(blank=True, default="")
    cost_impact = models.CharField(max_length=60, blank=True, default="")
    schedule_impact = models.CharField(max_length=60, blank=True, default="")
    priority = models.CharField(max_length=60, blank=True, default="")
    discipline = models.TextField(blank=True, default="")
    category = models.TextField(blank=True, default="")
    reference = models.TextField(blank=True, default="")

    # Internos para saber con qué import se actualizó y qué cambió.
    last_snapshot_datetime = models.DateTimeField(null=True, blank=True)
    last_diff_fields = models.TextField(blank=True, default="")
    last_import = models.ForeignKey(RDIImport, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "RDI Record"
        verbose_name_plural = "RDI Records"
        ordering = ["csv_id"]

    def __str__(self) -> str:
        return f"RDI {self.csv_id} - {self.title[:40]}"


class PlanosImport(models.Model):
    """
    Guarda el XLSX importado y la fecha/hora de snapshot extraída del nombre.
    """

    file = models.FileField(upload_to="planos/%Y/%m/")
    original_filename = models.CharField(max_length=255)
    snapshot_datetime = models.DateTimeField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Planos Import"
        verbose_name_plural = "Planos Imports"
        ordering = ["-snapshot_datetime", "-imported_at"]

    def __str__(self) -> str:
        return self.original_filename or f"PlanosImport #{self.pk}"


class PlanosRecord(models.Model):
    """
    Registro de planos/documentos del reporte "Contenido del informe".
    """

    folder_path = models.TextField(blank=True, default="")
    name = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    version = models.CharField(max_length=80, blank=True, default="")
    size = models.CharField(max_length=80, blank=True, default="")

    last_update_raw = models.CharField(max_length=120, blank=True, default="")
    last_update_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.CharField(max_length=255, blank=True, default="")

    last_upload_raw = models.CharField(max_length=120, blank=True, default="")
    last_upload_at = models.DateTimeField(null=True, blank=True)
    uploaded_by = models.CharField(max_length=255, blank=True, default="")

    review_mark = models.CharField(max_length=255, blank=True, default="")
    incidence = models.CharField(max_length=255, blank=True, default="")
    sdi = models.CharField(max_length=255, blank=True, default="")
    review_status = models.CharField(max_length=255, blank=True, default="")
    set_name = models.CharField(max_length=255, blank=True, default="")
    issue_date_raw = models.CharField(max_length=120, blank=True, default="")
    issue_date = models.DateField(null=True, blank=True)
    sheet_number = models.CharField(max_length=255, blank=True, default="")
    title = models.TextField(blank=True, default="")
    revision = models.CharField(max_length=255, blank=True, default="")

    last_snapshot_datetime = models.DateTimeField(null=True, blank=True)
    last_diff_fields = models.TextField(blank=True, default="")
    last_import = models.ForeignKey(PlanosImport, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Planos Record"
        verbose_name_plural = "Planos Records"
        ordering = ["name", "folder_path"]
        constraints = [
            models.UniqueConstraint(
                fields=["folder_path", "name"],
                name="uniq_planos_folder_name",
            )
        ]

    def __str__(self) -> str:
        return self.name or f"Plano #{self.pk}"


def _empty_json_dict():
    return {}


def _empty_json_list():
    return []


# Hojas de especialidad en planos_iniciales.xls (comparación sin distinguir mayúsculas).
PLANOS_INICIALES_SHEET_SLUGS = (
    "arq",
    "est",
    "ele",
    "aut",
    "san",
    "cli",
    "pci",
    "com",
    "bim",
    "bms",
    "geo",
    "pav",
    "hid",
)


class PlanosInicialesImport(models.Model):
    """Archivo .xls importado (planos por especialidad)."""

    file = models.FileField(upload_to="planos_iniciales/%Y/%m/")
    original_filename = models.CharField(max_length=255)
    snapshot_datetime = models.DateTimeField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Planos iniciales Import"
        verbose_name_plural = "Planos iniciales Imports"
        ordering = ["-snapshot_datetime", "-imported_at"]

    def __str__(self) -> str:
        return self.original_filename or f"PlanosInicialesImport #{self.pk}"


class PlanosInicialesRecord(models.Model):
    """
    Una fila de una hoja de especialidad. Todas las columnas del Excel van en
    columns_json (cabecera -> valor texto); column_headers_order conserva el orden.
    """

    specialty = models.CharField(max_length=16, db_index=True)
    excel_row = models.PositiveIntegerField(
        help_text="Número de fila en la hoja Excel (1 = encabezados).",
    )
    columns_json = models.JSONField(default=_empty_json_dict)
    column_headers_order = models.JSONField(default=_empty_json_list)
    search_text = models.TextField(blank=True, default="")

    last_snapshot_datetime = models.DateTimeField(null=True, blank=True)
    last_diff_fields = models.TextField(blank=True, default="")
    last_import = models.ForeignKey(
        PlanosInicialesImport, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = "Planos iniciales Record"
        verbose_name_plural = "Planos iniciales Records"
        ordering = ["specialty", "excel_row"]
        constraints = [
            models.UniqueConstraint(
                fields=["specialty", "excel_row"],
                name="uniq_planos_iniciales_specialty_excel_row",
            )
        ]

    def __str__(self) -> str:
        return f"{self.specialty.upper()} fila {self.excel_row}"

