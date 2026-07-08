"""
Utilidades para envío de correo: lectura de adjuntos, validación de límites y persistencia segura.
"""
from __future__ import annotations

import logging
from typing import Any, List, Tuple

from django.conf import settings

from .models import CorreoEnviado

logger = logging.getLogger(__name__)

# (nombre, contenido bytes, mimetype)
AttachmentTuple = Tuple[str, bytes, str]


def _max_attachment_bytes() -> int:
    return int(getattr(settings, "EMAIL_MAX_ATTACHMENT_BYTES", 22 * 1024 * 1024))


def _max_attachments() -> int:
    return int(getattr(settings, "EMAIL_MAX_ATTACHMENTS", 30))


def _max_recipients() -> int:
    return int(getattr(settings, "EMAIL_MAX_RECIPIENTS", 500))


def format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def read_post_attachments(
    request,
) -> Tuple[List[AttachmentTuple], List[AttachmentTuple], List[AttachmentTuple], int]:
    """
    Lee adjuntos_plantilla y adjuntos_extra del POST una sola vez.
    Devuelve (plantilla, extra, todos, tamaño_total_bytes).
    """
    plantilla: List[AttachmentTuple] = []
    extra: List[AttachmentTuple] = []
    total = 0
    seen_names: set[str] = set()

    def _add_file(f, bucket: List[AttachmentTuple]) -> None:
        nonlocal total
        if not f or not f.name:
            return
        name = f.name
        if name in seen_names:
            base, ext = name.rsplit(".", 1) if "." in name else (name, "")
            suffix = 2
            while name in seen_names:
                name = f"{base}_{suffix}.{ext}" if ext else f"{base}_{suffix}"
                suffix += 1
        seen_names.add(name)
        contenido = f.read()
        total += len(contenido)
        mimetype = getattr(f, "content_type", None) or "application/octet-stream"
        bucket.append((name, contenido, mimetype))

    for f in request.FILES.getlist("adjuntos_plantilla"):
        _add_file(f, plantilla)
    extra_files = list(request.FILES.getlist("adjuntos_extra"))
    extra_files += list(request.FILES.getlist("adjuntos_extra[]"))
    for f in extra_files:
        _add_file(f, extra)

    todos = plantilla + extra
    return plantilla, extra, todos, total


def validate_email_send_limits(
    *,
    to_list: List[str],
    cc_list: List[str],
    adjuntos_list: List[AttachmentTuple],
    total_attachment_bytes: int,
) -> str | None:
    """
    Devuelve mensaje de error en español si no cumple límites; None si OK.
    """
    n_to = len(to_list)
    n_cc = len(cc_list)
    n_total = n_to + n_cc
    max_recip = _max_recipients()
    if n_total > max_recip:
        return (
            f"Demasiados destinatarios ({n_total}). El máximo permitido es {max_recip} "
            f"(Para: {n_to}, CC: {n_cc})."
        )

    max_files = _max_attachments()
    n_files = len(adjuntos_list)
    if n_files > max_files:
        return f"Demasiados adjuntos ({n_files}). El máximo permitido es {max_files}."

    max_bytes = _max_attachment_bytes()
    if total_attachment_bytes > max_bytes:
        return (
            f"Los adjuntos pesan {format_bytes(total_attachment_bytes)} en total; "
            f"el máximo permitido es {format_bytes(max_bytes)} "
            f"(límite de Office 365 ~25 MB por mensaje, incluyendo codificación)."
        )

    # Estimación tamaño mensaje tras base64 (~37 % más) + cuerpo
    encoded_estimate = int(total_attachment_bytes * 1.37) + 64 * 1024
    if encoded_estimate > 26 * 1024 * 1024:
        return (
            f"Con la codificación del correo, el mensaje podría superar ~25 MB "
            f"(estimado {format_bytes(encoded_estimate)}). Reduzca adjuntos o envíe en dos partes."
        )

    return None


def emails_to_storage_value(emails: List[str]) -> str:
    if not emails:
        return ""
    return ", ".join(emails)


def group_names_to_storage_value(groups: List[str]) -> str:
    if not groups:
        return ""
    return ", ".join(groups)


def attachment_names_storage(adjuntos_list: List[AttachmentTuple]) -> str:
    return ", ".join(t[0] for t in adjuntos_list)


def persist_correo_registro(registro: CorreoEnviado, **updates) -> None:
    """Actualiza y guarda el registro; trunca error_msg si hiciera falta."""
    for key, value in updates.items():
        setattr(registro, key, value)
    if registro.error_msg and len(registro.error_msg) > 8000:
        registro.error_msg = registro.error_msg[:7997] + "..."
    try:
        registro.save()
    except Exception:
        logger.exception("No se pudo guardar CorreoEnviado pk=%s", registro.pk)
        raise


def email_send_context_base(request, **extra) -> dict[str, Any]:
    ctx = {
        "email_from": getattr(settings, "EMAIL_HOST_USER", ""),
        "cc_grupos": extra.pop("cc_grupos", None),
        "max_attachment_mb": round(_max_attachment_bytes() / (1024 * 1024), 1),
        "max_attachments": _max_attachments(),
        "max_recipients": _max_recipients(),
        "usar_plantilla_transmittal": extra.pop("usar_plantilla_transmittal", False),
    }
    if ctx["cc_grupos"] is None:
        from .models import GrupoCorreo

        ctx["cc_grupos"] = GrupoCorreo.objects.filter(activo=True).order_by("nombre")
    ctx.update(extra)
    return ctx
