from django.db import models, transaction
from django.db.models import F
from django.utils import timezone


class Project(models.Model):
    """
    PROY: Código del proyecto (ej: ODA)
    """
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class ExecutingCompany(models.Model):
    """
    EECC: Empresa ejecutora / contratista (ej: BUF, PROP, DCC...)
    """
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = "EECC"
        verbose_name_plural = "EECC"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Process(models.Model):
    """
    PR: Proceso / disciplina (ej: QA, AR, EL, IC...)
    """
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Proceso"
        verbose_name_plural = "Procesos"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class DocumentType(models.Model):
    """
    TIP: Tipo de documento (ej: MAT, DWG, TRN...)
    """
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Tipo de documento"
        verbose_name_plural = "Tipos de documento"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class DocumentSequence(models.Model):
    """
    Lleva el correlativo por combinación PROY+EECC+PR+TIP.
    Evita colisiones y permite autogeneración simple.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    company = models.ForeignKey(ExecutingCompany, on_delete=models.CASCADE)
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    doc_type = models.ForeignKey(DocumentType, on_delete=models.CASCADE)

    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Secuencia de documento"
        verbose_name_plural = "Secuencias de documento"
        constraints = [
            models.UniqueConstraint(
                fields=["project", "company", "process", "doc_type"],
                name="uniq_sequence_per_combo",
            )
        ]

    def __str__(self) -> str:
        return f"SEQ {self.project.code}-{self.company.code}-{self.process.code}-{self.doc_type.code}: {self.last_number:05d}"


class Document(models.Model):
    """
    Documento codificado:
      PROY-EECC-PR-TIP-00001

    - 'number' es el correlativo (00001)
    - 'code' se autogenera y es único
    """
    STATUS_DRAFT = "DRAFT"
    STATUS_ISSUED = "ISSUED"
    STATUS_OBSOLETE = "OBSOLETE"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Borrador"),
        (STATUS_ISSUED, "Emitido"),
        (STATUS_OBSOLETE, "Obsoleto"),
    ]

    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="documents")
    company = models.ForeignKey(ExecutingCompany, on_delete=models.PROTECT, related_name="documents")
    process = models.ForeignKey(Process, on_delete=models.PROTECT, related_name="documents")
    doc_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT, related_name="documents")

    # correlativo (parte #####)
    number = models.PositiveIntegerField(null=True, blank=True)

    # código completo PROY-EECC-PR-TIP-#####
    code = models.CharField(max_length=64, unique=True, editable=False)

    # metadatos típicos
    title = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    revision = models.CharField(max_length=20, blank=True, default="0")
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    # opcional: adjunto del documento
    file = models.FileField(upload_to="documents/%Y/%m/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["project", "company", "process", "doc_type"]),
            models.Index(fields=["code"]),
        ]

    def __str__(self) -> str:
        return self.code

    @staticmethod
    def build_code(project_code: str, company_code: str, process_code: str, doc_type_code: str, number: int) -> str:
        return f"{project_code}-{company_code}-{process_code}-{doc_type_code}-{number:05d}"

    def save(self, *args, **kwargs):
        """
        Autogenera number (si viene vacío) y code (siempre coherente).
        Con transacción + select_for_update para evitar duplicados en concurrencia.
        """
        if not self.project_id or not self.company_id or not self.process_id or not self.doc_type_id:
            raise ValueError("Debe definir project, company, process y doc_type antes de guardar el Documento.")

        with transaction.atomic():
            if not self.number:
                seq, _ = DocumentSequence.objects.select_for_update().get_or_create(
                    project=self.project,
                    company=self.company,
                    process=self.process,
                    doc_type=self.doc_type,
                    defaults={"last_number": 0},
                )
                seq.last_number = F("last_number") + 1
                seq.save(update_fields=["last_number"])
                seq.refresh_from_db()
                self.number = seq.last_number

            self.code = self.build_code(
                self.project.code,
                self.company.code,
                self.process.code,
                self.doc_type.code,
                int(self.number),
            )

            super().save(*args, **kwargs)
