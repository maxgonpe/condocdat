from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
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


@login_required
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
            base = Path(cfg.base_path).expanduser()
            if not base.exists():
                messages.error(request, f"La ruta base no existe: {base}")
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
    return render(
        request,
        "transmital/folder_builder.html",
        {
            "form": form,
            "cfg": cfg,
            "next_number": next_number,
            "next_name": next_name,
            "logs": logs,
        },
    )
