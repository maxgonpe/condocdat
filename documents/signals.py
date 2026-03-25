from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out

from .models import Document, FolderFile, DocumentAttachment, UserSessionLog
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


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    Audita el inicio de sesión (solo para usuarios staff).
    """
    try:
        if not user or not getattr(user, "is_staff", False):
            return
        ip = None
        try:
            ip = request.META.get("REMOTE_ADDR")
        except Exception:
            ip = None
        ua = ""
        try:
            ua = request.META.get("HTTP_USER_AGENT", "")[:512]
        except Exception:
            ua = ""
        UserSessionLog.objects.create(
            user=user,
            action=UserSessionLog.ACTION_LOGIN,
            session_key=getattr(getattr(request, "session", None), "session_key", None) or "",
            ip_address=ip,
            user_agent=ua,
        )
    except Exception:
        # Nunca bloquear el login por auditoría
        pass


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """
    Audita el fin de sesión (solo para usuarios staff).
    """
    try:
        if not user or not getattr(user, "is_staff", False):
            return
        ip = None
        try:
            ip = request.META.get("REMOTE_ADDR")
        except Exception:
            ip = None
        ua = ""
        try:
            ua = request.META.get("HTTP_USER_AGENT", "")[:512]
        except Exception:
            ua = ""
        UserSessionLog.objects.create(
            user=user,
            action=UserSessionLog.ACTION_LOGOUT,
            session_key=getattr(getattr(request, "session", None), "session_key", None) or "",
            ip_address=ip,
            user_agent=ua,
        )
    except Exception:
        # Nunca bloquear el logout por auditoría
        pass
