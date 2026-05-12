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


def _leaf_tasks_with_dates(archivo: GanttArchivo) -> list[GanttTask]:
    """
    Devuelve tareas hoja (no resumen) con fechas válidas.

    Se infiere "resumen" por jerarquía de outline_number para evitar doble
    conteo al agregar el cronograma completo.
    """
    tasks = list(archivo.tasks.exclude(comienzo__isnull=True).exclude(fin__isnull=True))
    if not tasks:
        return []

    outlines = {
        str(t.outline_number or "").strip()
        for t in tasks
        if str(t.outline_number or "").strip()
    }
    summary_outlines: set[str] = set()
    for o in outlines:
        parts = o.split(".")
        prefix = []
        for p in parts[:-1]:
            prefix.append(p)
            summary_outlines.add(".".join(prefix))

    leaf_tasks: list[GanttTask] = []
    for t in tasks:
        o = str(t.outline_number or "").strip()
        if o and o in summary_outlines:
            continue
        leaf_tasks.append(t)
    return leaf_tasks


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
    step_days: int = 1,
    max_points: int = 2000,
) -> list[dict[str, Any]]:
    """
    Serie temporal para curva S (planeado vs real).

    Participan tareas hoja (no resumen) con fechas comienzo/fin, ponderadas
    por duración en días (mínimo 1 día).

    - Curva planificada: 0% -> 100% por tarea sobre su ventana temporal.
      Esto evita depender de un snapshot de "% programado" y alinea la curva
      con el cronograma completo por día.
    - Curva real: referencia al corte actual usando `% trabajo_completado`
      distribuido linealmente hasta hoy (sin reconstruir histórico real).
    """
    tasks = _leaf_tasks_with_dates(archivo)

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

    weighted: list[tuple[datetime, datetime, float, float]] = []
    total_w = 0.0
    for t in tasks:
        s = t.comienzo
        e = t.fin
        dur_days = max(
            1.0,
            (timezone.localtime(e) - timezone.localtime(s)).total_seconds() / 86400.0,
        )
        pa = float(t.trabajo_completado or 0)
        weighted.append((s, e, dur_days, pa))
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
        for s, e, w, pa in weighted:
            f_plan = _schedule_fraction_at_day(s, e, day)
            plan_sum += w * 100.0 * f_plan

            today_or_finish = min(timezone.localtime(e).date(), today)
            if day <= today_or_finish:
                real_span_end = (
                    e if timezone.localtime(e).date() <= today else timezone.now()
                )
                f_real = _schedule_fraction_at_day(s, real_span_end, day)
                real_sum += w * pa * f_real
            else:
                real_sum += w * pa
        points.append(
            {
                "fecha": day,
                "planificado": round(plan_sum / total_w, 2),
                "real": round(real_sum / total_w, 2),
            }
        )

    return points


def _parse_pred_task_ids(predecesoras: str) -> list[int]:
    """
    Extrae IDs de predecesoras desde texto tipo:
    "12(FS,0d); 25(SS,2d)" -> [12, 25]
    """
    text = str(predecesoras or "").strip()
    if not text:
        return []
    ids: list[int] = []
    for raw in text.split(";"):
        token = raw.strip()
        if not token:
            continue
        head = token.split("(", 1)[0].strip()
        if head.isdigit():
            ids.append(int(head))
    return ids


def _frente_from_task(task: GanttTask) -> str:
    outline = str(task.outline_number or "").strip()
    if outline:
        return outline.split(".", 1)[0]
    esp = str(task.esp or "").strip()
    if esp:
        return esp.split(".", 1)[0].split("-", 1)[0].strip()
    return "SIN_FRENTE"


def _tramo_edt_from_task(task: GanttTask) -> str:
    """
    Agrupador de tramo por EDT para expansión gráfica.
    Usa hasta 4 niveles del EDT para no ser ni muy general ni muy específico.
    """
    edt = str(task.esp or task.wbs or task.outline_number or "").strip()
    if not edt:
        return "SIN_EDT"
    parts = [p for p in edt.split(".") if p]
    if not parts:
        return "SIN_EDT"
    return ".".join(parts[: min(4, len(parts))])


def _filter_leaf_tasks(
    archivo: GanttArchivo, *, especialidad: str = "", frente: str = ""
) -> list[GanttTask]:
    tasks = _leaf_tasks_with_dates(archivo)
    especialidad = str(especialidad or "").strip()
    frente = str(frente or "").strip()
    if especialidad:
        tasks = [t for t in tasks if str(t.especialidad or "").strip() == especialidad]
    if frente:
        tasks = [t for t in tasks if _frente_from_task(t) == frente]
    return tasks


def build_critical_path_filter_options(archivo: GanttArchivo) -> dict[str, list[str]]:
    tasks = _leaf_tasks_with_dates(archivo)
    especialidades = sorted(
        {
            str(t.especialidad or "").strip()
            for t in tasks
            if str(t.especialidad or "").strip()
        }
    )
    frentes = sorted({_frente_from_task(t) for t in tasks if _frente_from_task(t)})
    return {"especialidades": especialidades, "frentes": frentes}


def build_critical_path_snapshot(
    archivo: GanttArchivo, *, especialidad: str = "", frente: str = ""
) -> dict[str, Any]:
    """
    Construye una ruta crítica estimada como la cadena de mayor duración
    entre tareas hoja conectadas por predecesoras.
    """
    tasks = _filter_leaf_tasks(archivo, especialidad=especialidad, frente=frente)
    if not tasks:
        return {
            "nodes": [],
            "project_start": None,
            "project_finish": None,
            "project_span_days": 0,
            "critical_chain_days": 0,
            "palette": {},
        }

    by_task_id: dict[int, GanttTask] = {}
    for t in tasks:
        if t.task_id is not None:
            by_task_id[int(t.task_id)] = t

    if not by_task_id:
        return {
            "nodes": [],
            "project_start": None,
            "project_finish": None,
            "project_span_days": 0,
            "critical_chain_days": 0,
            "palette": {},
        }

    valid_ids = set(by_task_id.keys())
    preds: dict[int, list[int]] = {}
    for tid, t in by_task_id.items():
        p = [x for x in _parse_pred_task_ids(t.predecesoras) if x in valid_ids and x != tid]
        preds[tid] = p

    duration_days: dict[int, float] = {}
    for tid, t in by_task_id.items():
        duration_days[tid] = max(
            1.0,
            (timezone.localtime(t.fin) - timezone.localtime(t.comienzo)).total_seconds() / 86400.0,
        )

    unresolved = set(valid_ids)
    order: list[int] = []
    while unresolved:
        progressed = False
        for tid in list(unresolved):
            if all(p in order for p in preds[tid]):
                order.append(tid)
                unresolved.remove(tid)
                progressed = True
        if not progressed:
            # Si hay ciclos/inconsistencias, libera nodos restantes.
            order.extend(sorted(unresolved))
            unresolved.clear()

    best_finish: dict[int, float] = {}
    back: dict[int, int | None] = {}
    for tid in order:
        if not preds[tid]:
            best_finish[tid] = duration_days[tid]
            back[tid] = None
            continue
        best_pred = max(preds[tid], key=lambda p: best_finish.get(p, 0.0))
        best_finish[tid] = best_finish.get(best_pred, 0.0) + duration_days[tid]
        back[tid] = best_pred

    end_tid = max(order, key=lambda t: best_finish.get(t, 0.0))
    path_ids: list[int] = []
    cursor = end_tid
    seen: set[int] = set()
    while cursor is not None and cursor not in seen:
        seen.add(cursor)
        path_ids.append(cursor)
        cursor = back.get(cursor)
    path_ids.reverse()

    project_start = min(timezone.localtime(t.comienzo).date() for t in by_task_id.values())
    project_finish = max(timezone.localtime(t.fin).date() for t in by_task_id.values())
    project_span = max(1, (project_finish - project_start).days)

    cum = 0.0
    nodes: list[dict[str, Any]] = []
    colors = [
        "#ef4444",
        "#f97316",
        "#eab308",
        "#22c55e",
        "#06b6d4",
        "#3b82f6",
        "#8b5cf6",
        "#ec4899",
    ]
    espe_list = sorted(
        {str(by_task_id[tid].especialidad or "").strip() or "SIN_ESPECIALIDAD" for tid in path_ids}
    )
    palette = {esp: colors[i % len(colors)] for i, esp in enumerate(espe_list)}
    for idx, tid in enumerate(path_ids, start=1):
        t = by_task_id[tid]
        start = timezone.localtime(t.comienzo).date()
        finish = timezone.localtime(t.fin).date()
        dur = duration_days[tid]
        left_pct = round(((start - project_start).days / project_span) * 100.0, 2)
        width_pct = round((max(1, (finish - start).days) / project_span) * 100.0, 2)
        cum += dur
        nodes.append(
            {
                "orden": idx,
                "task_id": tid,
                "nombre_tarea": t.nombre_tarea or "",
                "especialidad": t.especialidad or "",
                "edt": (t.esp or t.wbs or "").strip(),
                "comienzo": start,
                "fin": finish,
                "duracion_dias": round(dur, 1),
                "duracion_acumulada_dias": round(cum, 1),
                "left_pct": max(0.0, min(100.0, left_pct)),
                "width_pct": max(1.0, min(100.0, width_pct)),
                "frente": _frente_from_task(t),
                "color": palette.get(
                    str(t.especialidad or "").strip() or "SIN_ESPECIALIDAD", "#ef4444"
                ),
            }
        )

    return {
        "nodes": nodes,
        "project_start": project_start,
        "project_finish": project_finish,
        "project_span_days": project_span,
        "critical_chain_days": round(sum(n["duracion_dias"] for n in nodes), 1),
        "palette": palette,
    }


def build_critical_graph_dataset(
    archivo: GanttArchivo, *, especialidad: str = "", frente: str = ""
) -> dict[str, Any]:
    """
    Dataset completo del tramo filtrado para expansión dinámica en frontend:
    - nodos de tareas hoja
    - aristas por predecesoras directas
    - metadatos de tramo EDT
    """
    tasks = _filter_leaf_tasks(archivo, especialidad=especialidad, frente=frente)
    by_task_id: dict[int, GanttTask] = {}
    for t in tasks:
        if t.task_id is not None:
            by_task_id[int(t.task_id)] = t
    if not by_task_id:
        return {"nodes": [], "edges": []}

    colors = [
        "#ef4444",
        "#f97316",
        "#eab308",
        "#22c55e",
        "#06b6d4",
        "#3b82f6",
        "#8b5cf6",
        "#ec4899",
    ]
    espe_list = sorted(
        {
            str(t.especialidad or "").strip() or "SIN_ESPECIALIDAD"
            for t in by_task_id.values()
        }
    )
    palette = {esp: colors[i % len(colors)] for i, esp in enumerate(espe_list)}

    nodes: list[dict[str, Any]] = []
    for tid, t in by_task_id.items():
        esp = str(t.especialidad or "").strip() or "SIN_ESPECIALIDAD"
        edt = (t.esp or t.wbs or t.outline_number or "").strip()
        nodes.append(
            {
                "id": tid,
                "task_id": tid,
                "label": f"ID {tid} | EDT {edt or '-'}",
                "name": t.nombre_tarea or "",
                "dur": round(
                    max(
                        1.0,
                        (timezone.localtime(t.fin) - timezone.localtime(t.comienzo)).total_seconds()
                        / 86400.0,
                    ),
                    1,
                ),
                "start": timezone.localtime(t.comienzo).date().strftime("%d/%m/%Y"),
                "finish": timezone.localtime(t.fin).date().strftime("%d/%m/%Y"),
                "esp": esp,
                "edt": edt,
                "tramo_edt": _tramo_edt_from_task(t),
                "frente": _frente_from_task(t),
                "color": palette.get(esp, "#ef4444"),
            }
        )

    valid_ids = set(by_task_id.keys())
    edges: list[dict[str, Any]] = []
    for tid, t in by_task_id.items():
        for pred in _parse_pred_task_ids(t.predecesoras):
            if pred in valid_ids and pred != tid:
                edges.append({"source": pred, "target": tid, "label": "pred"})

    return {"nodes": nodes, "edges": edges}


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
