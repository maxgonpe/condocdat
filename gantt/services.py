from __future__ import annotations

from datetime import datetime
from io import BytesIO, StringIO
from typing import Any

import csv
import openpyxl
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Max
from django.forms.models import model_to_dict
from django.utils import timezone

from .models import GanttArchivo, GanttCambioLog, GanttTask

GANTT_ARCHIVO_REL_PATH = "gantt/cronograma_actual.mpp"


def latest_archivo() -> GanttArchivo | None:
    return GanttArchivo.objects.order_by("-imported_at").first()


def resolve_archivo_mpp_path(archivo: GanttArchivo) -> str:
    if archivo.file and archivo.file.name and default_storage.exists(archivo.file.name):
        return archivo.file.path
    if default_storage.exists(GANTT_ARCHIVO_REL_PATH):
        if archivo.file.name != GANTT_ARCHIVO_REL_PATH:
            archivo.file.name = GANTT_ARCHIVO_REL_PATH
            archivo.save(update_fields=["file"])
        return archivo.file.path
    raise FileNotFoundError("No se encontró el archivo MPP en storage.")


def _safe_text(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _safe_datetime(v: Any):
    if v is None:
        return None
    try:
        value = v.toLocalDateTime()
        if value and timezone.is_naive(value):
            return timezone.make_aware(value, timezone.get_current_timezone())
        return value
    except Exception:
        pass
    try:
        value = datetime.fromisoformat(str(v))
        if value and timezone.is_naive(value):
            return timezone.make_aware(value, timezone.get_current_timezone())
        return value
    except Exception:
        return None


def _relaciones_txt(rels, side: str) -> str:
    if rels is None:
        return ""
    rows = []
    for r in rels:
        try:
            task = (
                r.getPredecessorTask()
                if side == "pred"
                else r.getSuccessorTask()
            )
            tid = task.getID() if task else None
            rows.append(f"{tid}({r.getType()},{r.getLag()})")
        except Exception:
            continue
    return "; ".join(rows)


def _arranca_jvm_si_corresponde():
    import jpype
    import mpxj  # noqa: F401

    if not jpype.isJVMStarted():
        jpype.startJVM()
    return jpype


def _parse_mpp_to_rows(path: str) -> list[dict[str, Any]]:
    jpype = _arranca_jvm_si_corresponde()
    Reader = jpype.JClass("org.mpxj.reader.UniversalProjectReader")
    TaskField = jpype.JClass("org.mpxj.TaskField")
    project = Reader().read(path)

    rows: list[dict[str, Any]] = []
    row_num = 1
    for t in project.getTasks():
        if t is None:
            continue
        task_id = t.getID()
        unique_id = t.getUniqueID()
        nombre = _safe_text(t.getName())
        if task_id is None and not nombre:
            continue
        rows.append(
            {
                "excel_row": row_num,
                "task_id": int(task_id) if task_id is not None else None,
                "unique_id": int(unique_id) if unique_id is not None else None,
                "nombre_tarea": nombre,
                "esp": _safe_text(t.getWBS()),
                "especialidad": _safe_text(t.get(TaskField.TEXT25)),
                "duracion": _safe_text(t.getDuration()),
                "comienzo": _safe_datetime(t.getStart()),
                "fin": _safe_datetime(t.getFinish()),
                "predecesoras": _relaciones_txt(t.getPredecessors(), "pred"),
                "sucesoras": _relaciones_txt(t.getSuccessors(), "succ"),
                "notas": _safe_text(t.getNotes()),
                "wbs": _safe_text(t.getWBS()),
                "outline_number": _safe_text(t.getOutlineNumber()),
            }
        )
        row_num += 1
    return rows


@transaction.atomic
def replace_archivo_with_import(uploaded_file, original_filename: str) -> GanttArchivo:
    for old in GanttArchivo.objects.all():
        if old.file:
            old.file.delete(save=False)
    GanttArchivo.objects.all().delete()

    if default_storage.exists(GANTT_ARCHIVO_REL_PATH):
        default_storage.delete(GANTT_ARCHIVO_REL_PATH)

    archivo = GanttArchivo(original_filename=(original_filename or "gantt.mpp").strip())
    uploaded_file.seek(0)
    archivo.file.save("cronograma_actual.mpp", uploaded_file, save=True)

    rows = _parse_mpp_to_rows(archivo.file.path)
    GanttTask.objects.bulk_create([GanttTask(archivo=archivo, **r) for r in rows])
    return archivo


def log_task_changes(archivo: GanttArchivo, user, task: GanttTask, before: dict, fields: list[str]):
    after = model_to_dict(task, fields=fields)
    for f in fields:
        ov = "" if before.get(f) is None else str(before.get(f))
        nv = "" if after.get(f) is None else str(after.get(f))
        if ov == nv:
            continue
        GanttCambioLog.objects.create(
            archivo=archivo,
            user=user,
            record_id=task.pk,
            task_id=task.task_id,
            campo=f,
            valor_anterior=ov,
            valor_nuevo=nv,
        )


def ultima_cambio_map(archivo: GanttArchivo | None, record_ids: list[int]) -> dict[int, datetime]:
    if not archivo or not record_ids:
        return {}
    rows = (
        GanttCambioLog.objects.filter(archivo=archivo, record_id__in=record_ids)
        .values("record_id")
        .annotate(last=Max("created_at"))
    )
    return {r["record_id"]: r["last"] for r in rows}


def _task_rows_for_export(archivo: GanttArchivo):
    return list(archivo.tasks.all().order_by("task_id", "id"))


def build_excel_buffer(archivo: GanttArchivo) -> BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Gantt"
    headers = [
        "Task ID",
        "Unique ID",
        "Nombre tarea",
        "Especialidad",
        "ESP (EDT/WBS)",
        "Duracion",
        "Comienzo",
        "Fin",
        "Predecesoras",
        "Sucesoras",
        "Notas",
    ]
    ws.append(headers)
    for t in _task_rows_for_export(archivo):
        ws.append(
            [
                t.task_id,
                t.unique_id,
                t.nombre_tarea,
                t.especialidad,
                t.esp,
                t.duracion,
                t.comienzo.isoformat() if t.comienzo else "",
                t.fin.isoformat() if t.fin else "",
                t.predecesoras,
                t.sucesoras,
                t.notas,
            ]
        )
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def build_csv_bytes(archivo: GanttArchivo) -> bytes:
    out = StringIO()
    w = csv.writer(out)
    w.writerow(
        [
            "task_id",
            "unique_id",
            "nombre_tarea",
            "especialidad",
            "esp",
            "duracion",
            "comienzo",
            "fin",
            "predecesoras",
            "sucesoras",
            "notas",
        ]
    )
    for t in _task_rows_for_export(archivo):
        w.writerow(
            [
                t.task_id or "",
                t.unique_id or "",
                t.nombre_tarea or "",
                t.especialidad or "",
                t.esp or "",
                t.duracion or "",
                t.comienzo.isoformat() if t.comienzo else "",
                t.fin.isoformat() if t.fin else "",
                t.predecesoras or "",
                t.sucesoras or "",
                t.notas or "",
            ]
        )
    return out.getvalue().encode("utf-8")


def _to_local_naive(dt):
    if not dt:
        return None
    local = timezone.localtime(dt)
    return local.replace(tzinfo=None)


def build_mspdi_xml_bytes(archivo: GanttArchivo) -> bytes:
    jpype = _arranca_jvm_si_corresponde()
    Reader = jpype.JClass("org.mpxj.reader.UniversalProjectReader")
    FileFormat = jpype.JClass("org.mpxj.writer.FileFormat")
    UniversalProjectWriter = jpype.JClass("org.mpxj.writer.UniversalProjectWriter")
    TaskField = jpype.JClass("org.mpxj.TaskField")
    LocalDateTime = jpype.JClass("java.time.LocalDateTime")

    project = Reader().read(resolve_archivo_mpp_path(archivo))
    by_unique = {t.unique_id: t for t in archivo.tasks.all() if t.unique_id is not None}
    by_task = {t.task_id: t for t in archivo.tasks.all() if t.task_id is not None}

    for jt in project.getTasks():
        if jt is None:
            continue
        db = None
        uid = jt.getUniqueID()
        tid = jt.getID()
        if uid is not None:
            db = by_unique.get(int(uid))
        if db is None and tid is not None:
            db = by_task.get(int(tid))
        if db is None:
            continue

        jt.setName(db.nombre_tarea or "")
        jt.setNotes(db.notas or "")
        jt.setWBS(db.esp or "")
        jt.set(TaskField.TEXT25, db.especialidad or "")
        if db.comienzo:
            v = _to_local_naive(db.comienzo)
            jt.setStart(LocalDateTime.parse(v.strftime("%Y-%m-%dT%H:%M:%S")))
        if db.fin:
            v = _to_local_naive(db.fin)
            jt.setFinish(LocalDateTime.parse(v.strftime("%Y-%m-%dT%H:%M:%S")))

    tmp_name = f"gantt/export_{archivo.pk}_{int(timezone.now().timestamp())}.xml"
    tmp_path = default_storage.path(tmp_name)
    writer = UniversalProjectWriter(FileFormat.MSPDI)
    writer.write(project, tmp_path)
    with open(tmp_path, "rb") as fh:
        data = fh.read()
    default_storage.delete(tmp_name)
    return data
