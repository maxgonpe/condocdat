import io
import zipfile
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .forms import TransmitalFolderConfigForm, TransmitalForm
from .models import Transmital, TransmitalFolderConfig, TransmitalFolderLog
from .services import (
    build_transmital_pdf_buffer,
    create_transmital_from_template,
    sync_transmital_to_excel,
    transmital_download_filename,
    transmital_pdf_filename,
)


@login_required
def transmital_hub(request):
    latest = Transmital.objects.order_by("-consecutivo").first()
    return render(request, "transmital/hub.html", {"latest": latest})


@login_required
@require_POST
def transmital_create(request):
    try:
        obj = create_transmital_from_template()
    except Exception as e:
        messages.error(request, f"No se pudo crear el transmital: {e}")
        return redirect("transmital_hub")
    messages.success(request, f"Transmital creado: {obj.codigo_transmital}")
    return redirect("transmital_edit", pk=obj.pk)


@login_required
def transmital_edit(request, pk: int):
    obj = get_object_or_404(Transmital, pk=pk)
    if request.method == "POST":
        form = TransmitalForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            obj.refresh_from_db()
            try:
                sync_transmital_to_excel(obj)
            except Exception as e:
                messages.warning(request, f"Guardado en BD; error sincronizando Excel: {e}")
            else:
                messages.success(request, "Transmital actualizado y sincronizado.")
            return redirect("transmital_edit", pk=obj.pk)
    else:
        form = TransmitalForm(instance=obj)
    return render(request, "transmital/edit.html", {"form": form, "obj": obj})


@login_required
@require_GET
def transmital_download_xlsx(request, pk: int):
    obj = get_object_or_404(Transmital, pk=pk)
    sync_transmital_to_excel(obj)
    return FileResponse(
        open(obj.file.path, "rb"),
        as_attachment=True,
        filename=transmital_download_filename(obj),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@login_required
@require_GET
def transmital_export_pdf(request, pk: int):
    obj = get_object_or_404(Transmital, pk=pk)
    try:
        sync_transmital_to_excel(obj)
        buf = build_transmital_pdf_buffer(obj)
    except Exception as e:
        return HttpResponse(f"No se pudo generar PDF: {e}", status=500)
    return FileResponse(
        buf,
        as_attachment=True,
        filename=transmital_pdf_filename(obj),
        content_type="application/pdf",
    )


def _folder_name_from_number(n: int) -> str:
    return f"ODATA-ST01-F5-TTAL-PPT-{n:05d}"


def _folder_cfg() -> TransmitalFolderConfig:
    cfg = TransmitalFolderConfig.objects.order_by("id").first()
    if cfg:
        return cfg
    return TransmitalFolderConfig.objects.create()


def _resolved_transmital_folder_base(cfg: TransmitalFolderConfig) -> Path:
    """
    Usa base_path de la config si existe en disco; si no (p. ej. ruta de desarrollo en producción),
    usa CONDOCDAT_DOC_ROOT (por defecto BASE_DIR / 'doc'), igual que el resto del proyecto.
    """
    raw = (cfg.base_path or "").strip()
    if raw:
        p = Path(raw).expanduser()
        if p.is_dir():
            return p
    root = Path(settings.CONDOCDAT_DOC_ROOT)
    if root.is_dir():
        return root
    return Path(raw).expanduser() if raw else root


def _folder_log_is_local_pc(row: TransmitalFolderLog) -> bool:
    return (row.folder_path or "").strip().lower().startswith("local:")


@login_required
@require_POST
def transmital_folder_register_local(request):
    """
    Reserva el siguiente nombre de carpeta y lo registra como creada en el PC del usuario
    (la carpeta física la crea el navegador con showDirectoryPicker, no el servidor).
    """
    cfg = _folder_cfg()
    try:
        with transaction.atomic():
            cfg_locked = TransmitalFolderConfig.objects.select_for_update().get(pk=cfg.pk)
            next_number = cfg_locked.current_number + 1
            folder_name = _folder_name_from_number(next_number)
            if TransmitalFolderLog.objects.filter(folder_name=folder_name).exists():
                return JsonResponse(
                    {"ok": False, "error": "Ese nombre ya está registrado. Recarga la página."},
                    status=409,
                )
            TransmitalFolderLog.objects.create(
                folder_name=folder_name,
                folder_path=f"local:{folder_name}",
                sequence_number=next_number,
            )
            cfg_locked.current_number = next_number
            cfg_locked.save(update_fields=["current_number", "updated_at"])
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
    return JsonResponse(
        {
            "ok": True,
            "folder_name": folder_name,
            "sequence_number": next_number,
        }
    )


@login_required
@require_POST
def transmital_folder_next_zip(request):
    """
    Registra el siguiente nombre y devuelve un ZIP con una carpeta vacía de ese nombre
    (el usuario guarda el ZIP donde quiera y lo descomprime, p. ej. en el escritorio).
    """
    cfg = _folder_cfg()
    buf = io.BytesIO()
    try:
        with transaction.atomic():
            cfg_locked = TransmitalFolderConfig.objects.select_for_update().get(pk=cfg.pk)
            next_number = cfg_locked.current_number + 1
            folder_name = _folder_name_from_number(next_number)
            if TransmitalFolderLog.objects.filter(folder_name=folder_name).exists():
                messages.error(request, "Ese nombre ya está registrado. Recarga la página.")
                return redirect("transmital_folder_builder")
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(f"{folder_name}/", "")
            TransmitalFolderLog.objects.create(
                folder_name=folder_name,
                folder_path=f"local:{folder_name}",
                sequence_number=next_number,
            )
            cfg_locked.current_number = next_number
            cfg_locked.save(update_fields=["current_number", "updated_at"])
    except Exception as e:
        messages.error(request, f"No se pudo generar el ZIP: {e}")
        return redirect("transmital_folder_builder")
    buf.seek(0)
    return FileResponse(
        buf,
        as_attachment=True,
        filename=f"{folder_name}.zip",
        content_type="application/zip",
    )


@login_required
@ensure_csrf_cookie
def transmital_folder_builder(request):
    cfg = _folder_cfg()
    if request.method == "POST":
        action = request.POST.get("action", "").strip()

        if action == "update_config":
            form = TransmitalFolderConfigForm(request.POST, instance=cfg)
            if form.is_valid():
                form.save()
                messages.success(request, "Configuración de secuencia actualizada.")
                return redirect("transmital_folder_builder")
            messages.error(request, "Revisa los datos de configuración.")
        elif action == "create_folder":
            form = TransmitalFolderConfigForm(instance=cfg)
            base = _resolved_transmital_folder_base(cfg)
            if not base.exists():
                hint = settings.CONDOCDAT_DOC_ROOT
                messages.error(
                    request,
                    f"La ruta base no existe: {base}. "
                    f"Crea la carpeta o define CONDOCDAT_DOC_ROOT (p. ej. {hint}).",
                )
                return redirect("transmital_folder_builder")
            if not base.is_dir():
                messages.error(request, f"La ruta base no es una carpeta: {base}")
                return redirect("transmital_folder_builder")
            next_number = cfg.current_number + 1
            folder_name = _folder_name_from_number(next_number)
            folder_path = base / folder_name
            if folder_path.exists():
                messages.error(
                    request,
                    f"La carpeta ya existe: {folder_path}. Ajusta la secuencia y vuelve a intentar.",
                )
                return redirect("transmital_folder_builder")
            folder_path.mkdir(parents=False, exist_ok=False)
            TransmitalFolderLog.objects.create(
                folder_name=folder_name,
                folder_path=str(folder_path),
                sequence_number=next_number,
            )
            cfg.current_number = next_number
            cfg.save(update_fields=["current_number", "updated_at"])
            messages.success(request, f"Carpeta creada: {folder_name}")
            return redirect("transmital_folder_builder")
        elif action == "delete_folder":
            form = TransmitalFolderConfigForm(instance=cfg)
            row = get_object_or_404(TransmitalFolderLog, pk=request.POST.get("log_id"))
            if _folder_log_is_local_pc(row):
                name = row.folder_name
                row.delete()
                messages.success(
                    request,
                    f"Registro eliminado: {name}. Si la carpeta existe en su equipo, bórrela manualmente.",
                )
                return redirect("transmital_folder_builder")
            p = Path(row.folder_path)
            try:
                p.rmdir()
            except FileNotFoundError:
                pass
            except OSError:
                messages.error(
                    request,
                    "No se pudo borrar la carpeta porque no está vacía o no hay permisos.",
                )
                return redirect("transmital_folder_builder")
            row.delete()
            messages.success(request, f"Carpeta eliminada: {p.name}")
            return redirect("transmital_folder_builder")
        else:
            form = TransmitalFolderConfigForm(instance=cfg)
    else:
        form = TransmitalFolderConfigForm(instance=cfg)

    next_number = cfg.current_number + 1
    next_name = _folder_name_from_number(next_number)
    logs = TransmitalFolderLog.objects.all()[:100]
    resolved_base = _resolved_transmital_folder_base(cfg)
    configured = Path((cfg.base_path or "").strip()).expanduser() if (cfg.base_path or "").strip() else None
    base_resolved_note = (
        configured is not None
        and configured != resolved_base
        and not configured.is_dir()
        and resolved_base.is_dir()
    )
    return render(
        request,
        "transmital/folder_builder.html",
        {
            "form": form,
            "cfg": cfg,
            "next_number": next_number,
            "next_name": next_name,
            "logs": logs,
            "resolved_folder_base": str(resolved_base),
            "base_resolved_note": base_resolved_note,
        },
    )
