from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Document, FolderFile, DocumentAttachment
from .text_extraction import extract_text_from_file


@receiver(post_save, sender=Document)
def document_extract_content(sender, instance, **kwargs):
    """Rellena content_extract al tener file (PDF/DOCX/XLS/XLSX)."""
    if not instance.file:
        return
    path = getattr(instance.file, "path", None)
    if not path:
        return
    try:
        text = extract_text_from_file(instance.file)
        if text != instance.content_extract:
            Document.objects.filter(pk=instance.pk).update(content_extract=text)
    except Exception:
        pass


@receiver(post_save, sender=DocumentAttachment)
def document_attachment_extract_content(sender, instance, **kwargs):
    """Rellena extracted_text del adjunto (PDF/DOCX/XLS/XLSX)."""
    if not instance.file:
        return
    path = getattr(instance.file, "path", None)
    if not path:
        return
    try:
        text = extract_text_from_file(instance.file)
        if text != instance.extracted_text:
            DocumentAttachment.objects.filter(pk=instance.pk).update(extracted_text=text)
    except Exception:
        pass


@receiver(post_save, sender=FolderFile)
def folder_file_extract_content(sender, instance, **kwargs):
    """Rellena extracted_text del archivo de carpeta (PDF/DOCX/XLS/XLSX)."""
    if not instance.file:
        return
    path = getattr(instance.file, "path", None)
    if not path:
        return
    try:
        text = extract_text_from_file(instance.file)
        if text != instance.extracted_text:
            FolderFile.objects.filter(pk=instance.pk).update(extracted_text=text)
    except Exception:
        pass
