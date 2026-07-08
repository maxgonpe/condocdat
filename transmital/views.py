import io
import re
import zipfile
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.core.files.base import ContentFile
from django.db import connection, transaction
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from documents.models import (
    Document,
    DocumentType,
    ExecutingCompany,
    Folder,
    Process,
    Project,
)
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
        action = (request.POST.get("action") or "").strip()
        form = TransmitalForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            obj.refresh_from_db()
            try:
                sync_transmital_to_excel(obj)
                if action == "create_document":
                    doc, created = _create_or_update_document_from_transmital(obj)
                    if created:
                        messages.success(request, f"Documento creado automáticamente: {doc.code}")
                    else:
                        messages.success(request, f"Documento actualizado automáticamente: {doc.code}")
                    return redirect("document_detail", pk=doc.pk)
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


def _folder_title_from_number(n: int) -> str:
    return f"PROPAMAT-A-ODATA-{n:05d}"


def _folder_title_from_code(code: str) -> str:
    m = re.search(r"(\d{5})$", (code or "").strip())
    if m:
        return f"PROPAMAT-A-ODATA-{m.group(1)}"
    return "PROPAMAT-A-ODATA"


def _sequence_number_from_transmital_code(code: str, consecutivo: int | None = None) -> int:
    """
    Número de secuencia desde el código de carpeta/transmital.
    Ej: ODATA-ST01-F5-TTAL-PPT-00306 -> 306
    """
    raw = (code or "").strip().upper()
    m = re.search(r"ODATA-ST01-F5-TTAL-PPT-(\d{5})$", raw, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m2 = re.search(r"(\d{5})$", raw)
    if m2:
        return int(m2.group(1))
    if consecutivo is not None and int(consecutivo) > 0:
        return int(consecutivo)
    raise RuntimeError(
        f"No se pudo obtener el número de secuencia desde el código: {code!r}"
    )


def _resolve_transmital_document_fk_config():
    """
    Resuelve FK requeridas para crear documents.Document desde Transmital.
    Usa códigos configurables y fallback al primer registro.
    """
    proj_code = (getattr(settings, "TRANSMITAL_DOC_PROJECT_CODE", "ODATA") or "").strip()
    comp_code = (getattr(settings, "TRANSMITAL_DOC_COMPANY_CODE", "ST01") or "").strip()
    proc_code = (getattr(settings, "TRANSMITAL_DOC_PROCESS_CODE", "F5") or "").strip()
    dtype_code = (getattr(settings, "TRANSMITAL_DOC_TYPE_CODE", "TTAL-PPT") or "").strip()

    project = Project.objects.filter(code__iexact=proj_code).first()
    company = ExecutingCompany.objects.filter(code__iexact=comp_code).first()
    process = Process.objects.filter(code__iexact=proc_code).first()
    doc_type = DocumentType.objects.filter(code__iexact=dtype_code).first()

    missing = []
    if not project:
        missing.append(f"Project({proj_code})")
    if not company:
        missing.append(f"Company({comp_code})")
    if not process:
        missing.append(f"Process({proc_code})")
    if not doc_type:
        missing.append(f"DocType({dtype_code})")
    if missing:
        raise RuntimeError(
            "No hay datos maestros para crear Document automáticamente: "
            + ", ".join(missing)
        )
    return project, company, process, doc_type


def _number_to_spanish_compact(n: int) -> str:
    """
    Entero positivo a letras en español, MAYÚSCULAS y sin espacios.
    Ej: 306 -> TRESCIENTOSSEIS
    """
    if n == 0:
        return "CERO"
    if n < 0 or n > 99999:
        return str(n)

    units = {
        1: "UNO",
        2: "DOS",
        3: "TRES",
        4: "CUATRO",
        5: "CINCO",
        6: "SEIS",
        7: "SIETE",
        8: "OCHO",
        9: "NUEVE",
    }
    teens = {
        10: "DIEZ",
        11: "ONCE",
        12: "DOCE",
        13: "TRECE",
        14: "CATORCE",
        15: "QUINCE",
        16: "DIECISEIS",
        17: "DIECISIETE",
        18: "DIECIOCHO",
        19: "DIECINUEVE",
        20: "VEINTE",
    }
    tens = {
        30: "TREINTA",
        40: "CUARENTA",
        50: "CINCUENTA",
        60: "SESENTA",
        70: "SETENTA",
        80: "OCHENTA",
        90: "NOVENTA",
    }
    hundreds = {
        100: "CIEN",
        200: "DOSCIENTOS",
        300: "TRESCIENTOS",
        400: "CUATROCIENTOS",
        500: "QUINIENTOS",
        600: "SEISCIENTOS",
        700: "SETECIENTOS",
        800: "OCHOCIENTOS",
        900: "NOVECIENTOS",
    }

    def under_100(x: int) -> str:
        if x == 0:
            return ""
        if x <= 20:
            return teens.get(x, units.get(x, ""))
        if x < 30:
            return "VEINTI" + units[x - 20]
        t = (x // 10) * 10
        u = x % 10
        if u == 0:
            return tens[t]
        return tens[t] + "Y" + units[u]

    def under_1000(x: int) -> str:
        if x < 100:
            return under_100(x)
        h = (x // 100) * 100
        r = x % 100
        if x == 100:
            return "CIEN"
        head = "CIENTO" if h == 100 else hundreds[h]
        return head + under_100(r)

    if n < 1000:
        return under_1000(n)

    th = n // 1000
    rem = n % 1000
    if th == 1:
        prefix = "MIL"
    else:
        prefix = under_1000(th) + "MIL"
    return prefix + (under_1000(rem) if rem else "")


def _create_or_update_document_from_transmital(obj: Transmital) -> tuple[Document, bool]:
    """
    Crea o actualiza un documents.Document asociado al código de transmital.
    Mantiene un registro único por transmital mediante marcador interno.
    """
    code = (obj.codigo_transmital or "").strip()
    if not code:
        raise RuntimeError("El transmital no tiene código.")

    folder_title = _folder_title_from_code(code)
    folder, _ = Folder.objects.get_or_create(
        code=code,
        defaults={
            "title": folder_title,
            "date": obj.fecha_envio or timezone.localdate(),
        },
    )
    if (folder.title or "").strip() != folder_title:
        folder.title = folder_title
        folder.save(update_fields=["title", "updated_at"])

    project, company, process, doc_type = _resolve_transmital_document_fk_config()
    number = _sequence_number_from_transmital_code(code, obj.consecutivo)
    title_auto = _number_to_spanish_compact(number)
    desired_code = Document.build_code(
        project.code, company.code, process.code, doc_type.code, number
    )
    marker = f"[AUTO-TRANSMITAL:{obj.pk}]"

    doc = (
        Document.objects.filter(folder=folder, description__icontains=marker)
        .order_by("-created_at")
        .first()
    )
    if doc is None:
        doc = Document.objects.filter(code=desired_code).first()
    created = False
    if doc is None:
        doc = Document(
            project=project,
            company=company,
            process=process,
            doc_type=doc_type,
            number=number,
            title=title_auto,
            description=f"{marker}\nTransmital: {code}\nEmpresa: {obj.empresa or ''}\nDestinatario: {obj.destinatario or ''}",
            revision=(obj.revision or "").strip() or "0",
            date=obj.fecha_envio or timezone.localdate(),
            status=Document.STATUS_ISSUED,
            folder=folder,
        )
        doc.save()
        created = True
    else:
        doc.project = project
        doc.company = company
        doc.process = process
        doc.doc_type = doc_type
        doc.number = number
        doc.title = title_auto
        doc.revision = (obj.revision or "").strip() or doc.revision or "0"
        doc.date = obj.fecha_envio or doc.date or timezone.localdate()
        doc.status = doc.status or Document.STATUS_ISSUED
        doc.folder = folder
        if marker not in (doc.description or ""):
            doc.description = ((doc.description or "").strip() + "\n" + marker).strip()
        doc.save(
            update_fields=[
                "project",
                "company",
                "process",
                "doc_type",
                "number",
                "title",
                "revision",
                "date",
                "status",
                "folder",
                "description",
                "code",
                "updated_at",
            ]
        )

    pdf_buf = build_transmital_pdf_buffer(obj)
    pdf_name = f"{code}.pdf"
    doc.file.save(pdf_name, ContentFile(pdf_buf.getvalue()), save=False)
    doc.save(update_fields=["file", "updated_at"])
    return doc, created


def _folder_log_has_title_column() -> bool:
    """Compatibilidad: algunas BD tienen columna title en transmitalfolderlog y otras no."""
    table = TransmitalFolderLog._meta.db_table
    with connection.cursor() as cursor:
        desc = connection.introspection.get_table_description(cursor, table)
    cols = {c.name for c in desc}
    return "title" in cols


def _create_folder_log(folder_name: str, folder_path: str, sequence_number: int) -> None:
    """
    Crea log de carpeta soportando ambos esquemas:
    - con columna title (NOT NULL) en BD
    - sin columna title
    """
    if _folder_log_has_title_column():
        table = connection.ops.quote_name(TransmitalFolderLog._meta.db_table)
        now = timezone.now()
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {table} (folder_name, title, folder_path, sequence_number, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [
                    folder_name,
                    _folder_title_from_number(sequence_number),
                    folder_path,
                    sequence_number,
                    now,
                ],
            )
        return

    TransmitalFolderLog.objects.create(
        folder_name=folder_name,
        folder_path=folder_path,
        sequence_number=sequence_number,
    )


def _ensure_documents_folder(folder_name: str, sequence_number: int) -> None:
    """
    Garantiza que exista el registro en documents.Folder con:
    - code:  ODATA-ST01-F5-TTAL-PPT-00xxx
    - title: PROPAMAT-A-ODATA-00xxx
    """
    title = _folder_title_from_number(sequence_number)
    folder, created = Folder.objects.get_or_create(
        code=folder_name,
        defaults={"title": title},
    )
    if not created and (folder.title or "").strip() != title:
        folder.title = title
        folder.save(update_fields=["title", "updated_at"])


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
            _create_folder_log(
                folder_name=folder_name,
                folder_path=f"local:{folder_name}",
                sequence_number=next_number,
            )
            _ensure_documents_folder(folder_name, next_number)
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
            _create_folder_log(
                folder_name=folder_name,
                folder_path=f"local:{folder_name}",
                sequence_number=next_number,
            )
            _ensure_documents_folder(folder_name, next_number)
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
            _create_folder_log(
                folder_name=folder_name,
                folder_path=str(folder_path),
                sequence_number=next_number,
            )
            _ensure_documents_folder(folder_name, next_number)
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
