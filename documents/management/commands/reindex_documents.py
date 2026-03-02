"""
Reindexa el texto extraído de archivos (Document.file, DocumentAttachment, FolderFile).
Soporta PDF, DOCX, XLS, XLSX.
Útil para rellenar content_extract y extracted_text después de subir archivos
o al activar la extracción por primera vez.
"""
from django.core.management.base import BaseCommand
from documents.models import Document, FolderFile, DocumentAttachment
from documents.text_extraction import extract_text_from_file


class Command(BaseCommand):
    help = "Extrae texto de PDF/DOCX/XLS/XLSX en Document, DocumentAttachment y FolderFile"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo mostrar qué se procesaría, sin guardar",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        updated_docs = 0
        updated_attachments = 0
        updated_files = 0

        for doc in Document.objects.exclude(file="").exclude(file__isnull=True):
            path = getattr(doc.file, "path", None)
            if not path:
                self.stdout.write(self.style.WARNING(f"Document {doc.pk} ({doc.code}): file sin path (storage remoto?)"))
                continue
            try:
                text = extract_text_from_file(doc.file)
                if not dry_run and text != doc.content_extract:
                    Document.objects.filter(pk=doc.pk).update(content_extract=text)
                    updated_docs += 1
                elif dry_run and text:
                    self.stdout.write(f"Document {doc.pk} ({doc.code}): extraería {len(text)} caracteres")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Document {doc.pk}: {e}"))

        for att in DocumentAttachment.objects.exclude(file=""):
            path = getattr(att.file, "path", None)
            if not path:
                self.stdout.write(self.style.WARNING(f"DocumentAttachment {att.pk}: file sin path"))
                continue
            try:
                text = extract_text_from_file(att.file)
                if not dry_run and text != att.extracted_text:
                    DocumentAttachment.objects.filter(pk=att.pk).update(extracted_text=text)
                    updated_attachments += 1
                elif dry_run and text:
                    self.stdout.write(f"DocumentAttachment {att.pk}: extraería {len(text)} caracteres")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"DocumentAttachment {att.pk}: {e}"))

        for ff in FolderFile.objects.exclude(file=""):
            path = getattr(ff.file, "path", None)
            if not path:
                self.stdout.write(self.style.WARNING(f"FolderFile {ff.pk} ({ff.name}): file sin path"))
                continue
            try:
                text = extract_text_from_file(ff.file)
                if not dry_run and text != ff.extracted_text:
                    FolderFile.objects.filter(pk=ff.pk).update(extracted_text=text)
                    updated_files += 1
                elif dry_run and text:
                    self.stdout.write(f"FolderFile {ff.pk} ({ff.name}): extraería {len(text)} caracteres")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"FolderFile {ff.pk}: {e}"))

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run: no se guardó nada."))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Documentos: {updated_docs}. Adjuntos: {updated_attachments}. Archivos de carpeta: {updated_files}."
            ))
