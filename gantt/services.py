from __future__ import annotations

from datetime import date, datetime, timedelta
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


def _safe_percent(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return round(float(v), 2)
    except Exception:
        pass
    s = str(v).strip().replace("%", "").replace(",", ".")
    if not s:
        return None
    try:
        return round(float(s), 2)
    except Exception:
        return None


def _first_percent(task, candidates) -> float | None:
    for getter in candidates:
        try:
            value = getter()
        except Exception:
            continue
        parsed = _safe_percent(value)
        if parsed is not None:
            return parsed
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
        # Soporte robusto: primero campos custom usados en nuestros layouts,
        # luego fallback a campos estándar de MS Project.
        avance_planificado = _first_percent(
            t,
            [
                lambda: t.get(TaskField.NUMBER1),
                lambda: t.get(TaskField.TEXT10),
                lambda: t.getPercentageComplete(),
                lambda: t.get(TaskField.PERCENT_COMPLETE),
            ],
        )
        trabajo_completado = _first_percent(
            t,
            [
                lambda: t.get(TaskField.NUMBER2),
                lambda: t.get(TaskField.TEXT11),
                lambda: t.getPercentageWorkComplete(),
                lambda: t.get(TaskField.PERCENT_WORK_COMPLETE),
                lambda: t.getPercentageComplete(),
                lambda: t.get(TaskField.PERCENT_COMPLETE),
            ],
        )
        if avance_planificado is None:
            try:
                avance_planificado = _safe_percent(t.get(TaskField.PERCENT_COMPLETE))
            except Exception:
                pass
        if trabajo_completado is None:
            try:
                trabajo_completado = _safe_percent(t.get(TaskField.PERCENT_WORK_COMPLETE))
            except Exception:
                pass
        rows.append(
            {
                "excel_row": row_num,
                "task_id": int(task_id) if task_id is not None else None,
                "unique_id": int(unique_id) if unique_id is not None else None,
                "nombre_tarea": nombre,
                "esp": _safe_text(t.getWBS()),
                "especialidad": _safe_text(t.get(TaskField.TEXT25)),
                "duracion": _safe_text(t.getDuration()),
                "avance_planificado": avance_planificado,
                "trabajo_completado": trabajo_completado,
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


def _schedule_fraction_at_day(task_start: datetime, task_end: datetime, day: date) -> float:
    """Fracción lineal del período [inicio, fin] alcanzada en la fecha calendario `day`."""
    s = timezone.localtime(task_start).date()
    e = timezone.localtime(task_end).date()
    if day < s:
        return 0.0
    if day >= e:
        return 1.0
    span = (e - s).days
    if span <= 0:
        return 1.0
    return min(1.0, max(0.0, (day - s).days / span))


# Umbral mínimo de brecha (pts. %) para considerar partida en atraso vs línea base lineal.
_GANTT_ESTADO_UMBRAL_BRECHA_PCT = 0.5


def build_estado_atraso_records(archivo: GanttArchivo) -> list[dict[str, Any]]:
    """
    Partidas con especialidad y fechas, donde al día de hoy el % completado real
    queda por debajo del % esperado por una línea base lineal entre 0 y % planificado.

    Devuelve dicts listos para JSON (métricas de atraso son estimaciones orientativas).
    """
    today = timezone.localdate()
    rows: list[dict[str, Any]] = []

    for t in archivo.tasks.all().order_by("task_id", "id"):
        esp = str(t.especialidad or "").strip()
        if not esp:
            continue
        if not t.comienzo or not t.fin:
            continue

        s_d = timezone.localtime(t.comienzo).date()
        e_d = timezone.localtime(t.fin).date()
        if today < s_d:
            continue

        pp = float(t.avance_planificado or 0)
        pa = float(t.trabajo_completado or 0)

        f_hoy = _schedule_fraction_at_day(t.comienzo, t.fin, today)
        esperado_hoy = round(pp * f_hoy, 2)
        brecha = round(esperado_hoy - pa, 2)

        if brecha <= _GANTT_ESTADO_UMBRAL_BRECHA_PCT:
            continue

        dur_days = max(1, (e_d - s_d).days)

        dias_superacion_fin = 0
        if today > e_d and pa + _GANTT_ESTADO_UMBRAL_BRECHA_PCT < pp:
            dias_superacion_fin = (today - e_d).days

        dias_atraso_estimado = 0.0
        if pp > 0.05:
            ritmo_pct_por_dia = pp / dur_days
            dias_atraso_estimado = round(brecha / max(ritmo_pct_por_dia, 0.02), 1)
        elif dias_superacion_fin > 0:
            dias_atraso_estimado = float(dias_superacion_fin)

        if brecha >= 25 or dias_superacion_fin >= 30:
            severidad = "alta"
        elif brecha >= 10 or dias_superacion_fin >= 7:
            severidad = "media"
        else:
            severidad = "baja"

        rows.append(
            {
                "id": t.pk,
                "task_id": t.task_id,
                "nombre_tarea": t.nombre_tarea or "",
                "especialidad": esp,
                "esp": t.esp or "",
                "comienzo": t.comienzo.isoformat() if t.comienzo else "",
                "fin": t.fin.isoformat() if t.fin else "",
                "avance_planificado": pp,
                "trabajo_completado": pa,
                "esperado_hoy_pct": esperado_hoy,
                "brecha_pct": brecha,
                "dias_atraso_estimado": dias_atraso_estimado,
                "dias_superacion_fin": dias_superacion_fin,
                "severidad": severidad,
            }
        )

    rows.sort(key=lambda r: (-r["brecha_pct"], -r["dias_superacion_fin"]))
    return rows


def build_s_curve_series(
    archivo: GanttArchivo,
    *,
    step_days: int = 7,
    max_points: int = 260,
) -> list[dict[str, Any]]:
    """
    Serie temporal para curva S (planeado vs real).

    Solo participan tareas con especialidad definida y fechas comienzo/fin,
    ponderadas por duración en días (mínimo 1 día).

    Para cada fecha de muestreo, el avance acumulado ponderado usa los %
    guardados (`avance_planificado`, `trabajo_completado`) escalados por la
    fracción de tiempo transcurrido en cada tarea (distribución lineal).
    """
    tasks: list[GanttTask] = []
    for t in archivo.tasks.all():
        if not str(t.especialidad or "").strip():
            continue
        if not t.comienzo or not t.fin:
            continue
        tasks.append(t)

    if not tasks:
        return []

    dates_min = min(timezone.localtime(x.comienzo).date() for x in tasks)
    dates_max = max(timezone.localtime(x.fin).date() for x in tasks)
    today = timezone.localdate()
    if dates_max < today:
        dates_max = today

    span_days = (dates_max - dates_min).days + 1
    step = max(1, step_days)
    if span_days // step > max_points:
        step = max(step, span_days // max_points)

    weighted: list[tuple[datetime, datetime, float, float, float]] = []
    total_w = 0.0
    for t in tasks:
        s = t.comienzo
        e = t.fin
        dur_days = max(
            1.0,
            (timezone.localtime(e) - timezone.localtime(s)).total_seconds() / 86400.0,
        )
        pp = float(t.avance_planificado or 0)
        pa = float(t.trabajo_completado or 0)
        weighted.append((s, e, dur_days, pp, pa))
        total_w += dur_days

    if total_w <= 0:
        return []

    sample_days: list[date] = []
    d = dates_min
    while d < dates_max:
        sample_days.append(d)
        d += timedelta(days=step)
    if not sample_days or sample_days[-1] != dates_max:
        sample_days.append(dates_max)

    points: list[dict[str, Any]] = []
    for day in sample_days:
        plan_sum = 0.0
        real_sum = 0.0
        for s, e, w, pp, pa in weighted:
            f = _schedule_fraction_at_day(s, e, day)
            plan_sum += w * pp * f
            real_sum += w * pa * f
        points.append(
            {
                "fecha": day,
                "planificado": round(plan_sum / total_w, 2),
                "real": round(real_sum / total_w, 2),
            }
        )

    return points


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
        "% Avance planificado",
        "% Trabajo completado",
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
                t.avance_planificado,
                t.trabajo_completado,
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
            "avance_planificado",
            "trabajo_completado",
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
                t.avance_planificado if t.avance_planificado is not None else "",
                t.trabajo_completado if t.trabajo_completado is not None else "",
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
        if db.avance_planificado is not None:
            try:
                jt.setPercentageComplete(float(db.avance_planificado))
            except Exception:
                pass
        if db.trabajo_completado is not None:
            try:
                jt.setPercentageWorkComplete(float(db.trabajo_completado))
            except Exception:
                pass
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
