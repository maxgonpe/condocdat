from datetime import date
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone


def default_transmital_folder_base_path() -> str:
    """Ruta por defecto alineada con el despliegue (p. ej. /app/doc en Docker)."""
    return str(Path(settings.CONDOCDAT_DOC_ROOT))


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
    base_path = models.CharField(max_length=1024, default=default_transmital_folder_base_path)
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


from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q


class ProjectEvent(models.Model):
    """
    Evento histórico transversal del proyecto.

    NO reemplaza las tablas originales.
    NO copia documentos completos.

    Funciona como índice cronológico para reconstruir:
    - trazabilidad;
    - revisiones;
    - estados;
    - respuestas;
    - envíos;
    - relaciones;
    - antecedentes de un asunto.

    Las tablas originales siguen siendo la fuente oficial.
    """

    # ============================================================
    # ORIGEN DEL EVENTO
    # ============================================================

    ORIGIN_BACKFILL = "BACKFILL"
    ORIGIN_LIVE = "LIVE"
    ORIGIN_IMPORT = "IMPORT"
    ORIGIN_RECONCILIATION = "RECONCILIATION"
    ORIGIN_MANUAL = "MANUAL"

    ORIGIN_CHOICES = [
        (ORIGIN_BACKFILL, "Reconstrucción histórica"),
        (ORIGIN_LIVE, "Registro en línea"),
        (ORIGIN_IMPORT, "Importación externa"),
        (ORIGIN_RECONCILIATION, "Reconciliación"),
        (ORIGIN_MANUAL, "Registro manual"),
    ]

    # ============================================================
    # TIPO DE EVENTO
    # ============================================================

    EVENT_CREATED = "CREATED"
    EVENT_UPDATED = "UPDATED"
    EVENT_SENT = "SENT"
    EVENT_RECEIVED = "RECEIVED"
    EVENT_STATUS_CHANGED = "STATUS_CHANGED"
    EVENT_REVISION_CHANGED = "REVISION_CHANGED"
    EVENT_RESPONSE = "RESPONSE"
    EVENT_ATTACHED = "ATTACHED"
    EVENT_LINKED = "LINKED"
    EVENT_UNLINKED = "UNLINKED"
    EVENT_IMPORTED = "IMPORTED"
    EVENT_SUPERSEDED = "SUPERSEDED"
    EVENT_APPROVED = "APPROVED"
    EVENT_REJECTED = "REJECTED"
    EVENT_ISSUED = "ISSUED"
    EVENT_DELETED = "DELETED"

    EVENT_TYPE_CHOICES = [
        (EVENT_CREATED, "Creado"),
        (EVENT_UPDATED, "Actualizado"),
        (EVENT_SENT, "Enviado"),
        (EVENT_RECEIVED, "Recibido"),
        (EVENT_STATUS_CHANGED, "Cambio de estado"),
        (EVENT_REVISION_CHANGED, "Cambio de revisión"),
        (EVENT_RESPONSE, "Respuesta"),
        (EVENT_ATTACHED, "Archivo adjuntado"),
        (EVENT_LINKED, "Relación establecida"),
        (EVENT_UNLINKED, "Relación eliminada"),
        (EVENT_IMPORTED, "Importado"),
        (EVENT_SUPERSEDED, "Reemplazado"),
        (EVENT_APPROVED, "Aprobado"),
        (EVENT_REJECTED, "Rechazado"),
        (EVENT_ISSUED, "Emitido"),
        (EVENT_DELETED, "Eliminado"),
    ]

    # ============================================================
    # CALIDAD DEL DATO
    # ============================================================

    QUALITY_CONFIRMED = "CONFIRMED"
    QUALITY_RECONSTRUCTED = "RECONSTRUCTED"
    QUALITY_PARTIAL = "PARTIAL"
    QUALITY_INFERRED = "INFERRED"

    QUALITY_CHOICES = [
        (QUALITY_CONFIRMED, "Confirmado"),
        (QUALITY_RECONSTRUCTED, "Reconstruido"),
        (QUALITY_PARTIAL, "Parcial"),
        (QUALITY_INFERRED, "Inferido"),
    ]

    # ============================================================
    # PRECISIÓN TEMPORAL
    # ============================================================

    PRECISION_DATE = "DATE"
    PRECISION_DATETIME = "DATETIME"

    DATE_PRECISION_CHOICES = [
        (PRECISION_DATE, "Solo fecha"),
        (PRECISION_DATETIME, "Fecha y hora"),
    ]

    # ============================================================
    # IDENTIDAD DEL EVENTO
    # ============================================================

    event_uid = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text=(
            "Identificador determinístico utilizado para evitar "
            "duplicados durante backfill y reconciliaciones."
        ),
    )

    event_type = models.CharField(
        max_length=32,
        choices=EVENT_TYPE_CHOICES,
        db_index=True,
    )

    origin = models.CharField(
        max_length=20,
        choices=ORIGIN_CHOICES,
        default=ORIGIN_LIVE,
        db_index=True,
    )

    data_quality = models.CharField(
        max_length=20,
        choices=QUALITY_CHOICES,
        default=QUALITY_CONFIRMED,
        db_index=True,
    )

    source_completeness = models.BooleanField(
        default=True,
        help_text=(
            "False cuando sabemos que el contexto histórico "
            "de la fuente es incompleto."
        ),
    )

    # ============================================================
    # TIEMPO DEL EVENTO
    # ============================================================

    event_date = models.DateField(
        db_index=True,
        help_text="Fecha funcional en que ocurrió el evento.",
    )

    event_datetime = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "Fecha/hora real cuando la fuente la entrega. "
            "No debe inventarse para registros que solo tienen fecha."
        ),
    )

    date_precision = models.CharField(
        max_length=10,
        choices=DATE_PRECISION_CHOICES,
        default=PRECISION_DATE,
    )

    date_source = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text=(
            "Campo fuente de la fecha. Ej: Document.date, "
            "Transmital.fecha_envio, RDIRecord.created_at."
        ),
    )

    # Momento en que CONDOCdat conoció/detectó el evento.
    #
    # Es especialmente importante para RDI/planos provenientes
    # de importaciones periódicas.
    observed_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    # ============================================================
    # FUENTE ORIGINAL
    # ============================================================

    source_app = models.CharField(
        max_length=50,
        db_index=True,
    )

    source_model = models.CharField(
        max_length=80,
        db_index=True,
    )

    source_pk = models.CharField(
        max_length=80,
        blank=True,
        default="",
        db_index=True,
    )

    source_key = models.CharField(
        max_length=512,
        db_index=True,
        help_text=(
            "Identidad funcional estable del registro. "
            "Ej: código documental, RDI-184, TTAL-00184."
        ),
    )

    # ============================================================
    # DESCRIPCIÓN DEL EVENTO
    # ============================================================

    title = models.CharField(
        max_length=512,
        blank=True,
        default="",
    )

    summary = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Resumen factual y breve del evento. "
            "No almacenar aquí documentos completos."
        ),
    )

    # ============================================================
    # CAMBIOS IMPORTANTES
    # ============================================================

    status_before = models.CharField(
        max_length=128,
        blank=True,
        default="",
    )

    status_after = models.CharField(
        max_length=128,
        blank=True,
        default="",
    )

    revision_before = models.CharField(
        max_length=128,
        blank=True,
        default="",
    )

    revision_after = models.CharField(
        max_length=128,
        blank=True,
        default="",
    )

    # ============================================================
    # ACTORES
    # ============================================================

    actor = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    company = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    # ============================================================
    # DATOS FLEXIBLES
    # ============================================================

    changes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Campos que cambiaron y valores anterior/nuevo.",
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Información auxiliar específica de cada tipo "
            "de evento."
        ),
    )

    # Texto breve preparado para búsquedas.
    #
    # No reemplaza:
    # Document.content_extract
    # DocumentAttachment.extracted_text
    # FolderFile.extracted_text
    search_text = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Evento del proyecto"
        verbose_name_plural = "Eventos del proyecto"

        ordering = [
            "event_date",
            "event_datetime",
            "id",
        ]

        indexes = [
            models.Index(
                fields=["event_date", "event_type"],
                name="trace_date_type_idx",
            ),
            models.Index(
                fields=[
                    "source_app",
                    "source_model",
                    "source_pk",
                ],
                name="trace_source_idx",
            ),
            models.Index(
                fields=["source_key", "event_date"],
                name="trace_key_date_idx",
            ),
            models.Index(
                fields=["data_quality", "event_date"],
                name="trace_quality_date_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.event_date} | "
            f"{self.event_type} | "
            f"{self.source_key}"
        )


class ProjectEventLink(models.Model):
    """
    Relaciona un ProjectEvent con una o más entidades del proyecto.

    Permite que un único evento pueda relacionar, por ejemplo:

        Transmittal
            -> Carpeta
            -> Documento
            -> RDI
            -> Plano

    La relación histórica no depende de ForeignKeys hacia las tablas
    originales, por lo que permanece aunque una fuente cambie.
    """

    # ============================================================
    # ENTIDADES
    # ============================================================

    ENTITY_TRANSMITTAL = "TRANSMITTAL"
    ENTITY_FOLDER = "FOLDER"
    ENTITY_DOCUMENT = "DOCUMENT"
    ENTITY_ATTACHMENT = "ATTACHMENT"
    ENTITY_FOLDER_FILE = "FOLDER_FILE"
    ENTITY_RDI = "RDI"
    ENTITY_PLAN = "PLAN"

    ENTITY_TYPE_CHOICES = [
        (ENTITY_TRANSMITTAL, "Transmittal"),
        (ENTITY_FOLDER, "Carpeta"),
        (ENTITY_DOCUMENT, "Documento"),
        (ENTITY_ATTACHMENT, "Adjunto de documento"),
        (ENTITY_FOLDER_FILE, "Archivo de carpeta"),
        (ENTITY_RDI, "RDI"),
        (ENTITY_PLAN, "Plano"),
    ]

    # ============================================================
    # PAPEL DE LA RELACIÓN
    # ============================================================

    ROLE_PRIMARY = "PRIMARY"
    ROLE_CONTAINS = "CONTAINS"
    ROLE_BELONGS_TO = "BELONGS_TO"
    ROLE_REFERENCES = "REFERENCES"
    ROLE_RESPONDS_TO = "RESPONDS_TO"
    ROLE_SUPERSEDES = "SUPERSEDES"
    ROLE_ATTACHMENT_OF = "ATTACHMENT_OF"
    ROLE_RELATED = "RELATED"

    ROLE_CHOICES = [
        (ROLE_PRIMARY, "Entidad principal"),
        (ROLE_CONTAINS, "Contiene"),
        (ROLE_BELONGS_TO, "Pertenece a"),
        (ROLE_REFERENCES, "Referencia"),
        (ROLE_RESPONDS_TO, "Responde a"),
        (ROLE_SUPERSEDES, "Reemplaza"),
        (ROLE_ATTACHMENT_OF, "Adjunto de"),
        (ROLE_RELATED, "Relacionado"),
    ]

    # ============================================================
    # CÓMO SE DETERMINÓ LA RELACIÓN
    # ============================================================

    BASIS_DIRECT = "DIRECT"
    BASIS_FOREIGN_KEY = "FOREIGN_KEY"
    BASIS_EXACT_CODE = "EXACT_CODE"
    BASIS_REFERENCE = "REFERENCE"
    BASIS_IMPORT_MAPPING = "IMPORT_MAPPING"
    BASIS_CONTENT = "CONTENT"
    BASIS_INFERRED = "INFERRED"
    BASIS_MANUAL = "MANUAL"

    BASIS_CHOICES = [
        (BASIS_DIRECT, "Relación directa"),
        (BASIS_FOREIGN_KEY, "ForeignKey existente"),
        (BASIS_EXACT_CODE, "Código exacto"),
        (BASIS_REFERENCE, "Campo de referencia"),
        (BASIS_IMPORT_MAPPING, "Relación desde importación"),
        (BASIS_CONTENT, "Coincidencia de contenido"),
        (BASIS_INFERRED, "Relación inferida"),
        (BASIS_MANUAL, "Relación manual"),
    ]

    event = models.ForeignKey(
        ProjectEvent,
        on_delete=models.CASCADE,
        related_name="links",
    )

    entity_type = models.CharField(
        max_length=32,
        choices=ENTITY_TYPE_CHOICES,
        db_index=True,
    )

    # Información para regresar a la fuente original.
    entity_app = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    entity_model = models.CharField(
        max_length=80,
        blank=True,
        default="",
    )

    entity_pk = models.CharField(
        max_length=80,
        blank=True,
        default="",
        db_index=True,
    )

    # Identidad funcional estable.
    entity_key = models.CharField(
        max_length=512,
        db_index=True,
    )

    entity_revision = models.CharField(
        max_length=128,
        blank=True,
        default="",
    )

    relation_role = models.CharField(
        max_length=32,
        choices=ROLE_CHOICES,
        default=ROLE_RELATED,
        db_index=True,
    )

    relation_basis = models.CharField(
        max_length=32,
        choices=BASIS_CHOICES,
        default=BASIS_DIRECT,
        db_index=True,
    )

    confidence = models.PositiveSmallIntegerField(
        default=100,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
        help_text=(
            "100 = relación comprobada. "
            "Valores menores permiten identificar "
            "relaciones inferidas."
        ),
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "Relación de evento"
        verbose_name_plural = "Relaciones de eventos"

        indexes = [
            models.Index(
                fields=["entity_type", "entity_key"],
                name="trace_entity_key_idx",
            ),
            models.Index(
                fields=["entity_type", "entity_pk"],
                name="trace_entity_pk_idx",
            ),
            models.Index(
                fields=["event", "relation_role"],
                name="trace_event_role_idx",
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "event",
                    "entity_type",
                    "entity_key",
                    "relation_role",
                ],
                name="uniq_project_event_link",
            )
        ]

    def __str__(self):
        return (
            f"{self.event_id} -> "
            f"{self.entity_type}: "
            f"{self.entity_key}"
        )


class TraceSourceCoverage(models.Model):
    """
    Define qué tan completa es la información histórica disponible
    para cada fuente y período.

    Es fundamental para impedir que la IA interprete ausencia de datos
    como ausencia real de acontecimientos.

    Ejemplo:

        TRANSMITTAL
        2026-05-01 -> sin fecha final
        COMPLETE

    significa:

        desde mayo de 2026 la tabla Transmital posee cobertura
        considerada completa.

    Puede existir otro período anterior marcado como PARTIAL.
    """

    SOURCE_TRANSMITTAL = "TRANSMITTAL"
    SOURCE_FOLDER = "FOLDER"
    SOURCE_DOCUMENT = "DOCUMENT"
    SOURCE_ATTACHMENT = "ATTACHMENT"
    SOURCE_FOLDER_FILE = "FOLDER_FILE"
    SOURCE_RDI = "RDI"
    SOURCE_PLAN = "PLAN"

    SOURCE_CHOICES = [
        (SOURCE_TRANSMITTAL, "Transmittals"),
        (SOURCE_FOLDER, "Carpetas"),
        (SOURCE_DOCUMENT, "Documentos"),
        (SOURCE_ATTACHMENT, "Adjuntos"),
        (SOURCE_FOLDER_FILE, "Archivos de carpeta"),
        (SOURCE_RDI, "RDI"),
        (SOURCE_PLAN, "Planos"),
    ]

    COVERAGE_COMPLETE = "COMPLETE"
    COVERAGE_PARTIAL = "PARTIAL"
    COVERAGE_UNKNOWN = "UNKNOWN"

    COVERAGE_CHOICES = [
        (COVERAGE_COMPLETE, "Completa"),
        (COVERAGE_PARTIAL, "Parcial"),
        (COVERAGE_UNKNOWN, "Desconocida"),
    ]

    source_type = models.CharField(
        max_length=32,
        choices=SOURCE_CHOICES,
        db_index=True,
    )

    coverage_start = models.DateField(
        db_index=True,
    )

    # NULL = continúa hasta el presente.
    coverage_end = models.DateField(
        null=True,
        blank=True,
        db_index=True,
    )

    coverage_status = models.CharField(
        max_length=16,
        choices=COVERAGE_CHOICES,
        default=COVERAGE_UNKNOWN,
        db_index=True,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    # Explica por qué consideramos completa/parcial la cobertura.
    basis = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Cobertura histórica de fuente"
        verbose_name_plural = "Coberturas históricas de fuentes"

        ordering = [
            "source_type",
            "coverage_start",
        ]

        indexes = [
            models.Index(
                fields=[
                    "source_type",
                    "coverage_start",
                    "coverage_end",
                ],
                name="trace_coverage_idx",
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["source_type", "coverage_start"],
                name="uniq_trace_source_period",
            ),

            models.CheckConstraint(
                condition=(
                    Q(coverage_end__isnull=True)
                    | Q(coverage_end__gte=F("coverage_start"))
                ),
                name="trace_coverage_dates_ok",
            ),
        ]

    def __str__(self):
        fin = (
            self.coverage_end.isoformat()
            if self.coverage_end
            else "actualidad"
        )

        return (
            f"{self.source_type}: "
            f"{self.coverage_start} - {fin} "
            f"({self.coverage_status})"
        )