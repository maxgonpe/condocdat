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

