import csv
from io import StringIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .forms import GanttTaskForm
from .models import GanttCambioLog, GanttTask
from .services import (
    build_critical_graph_dataset,
    build_critical_path_filter_options,
    build_critical_path_snapshot,
    build_csv_bytes,
    build_estado_atraso_records,
    build_excel_buffer,
    build_mspdi_xml_bytes,
    build_s_curve_series,
    latest_archivo,
    log_task_changes,
    replace_archivo_with_import,
    ultima_cambio_map,
)


@login_required
def gantt_hub(request):
    archivo = latest_archivo()
    return render(
        request,
        "gantt/hub.html",
        {
            "archivo": archivo,
            "n_tasks": archivo.tasks.count() if archivo else 0,
            "n_cambios": archivo.cambios.count() if archivo else 0,
        },
    )


@login_required
@require_POST
def gantt_import_view(request):
    uploaded = request.FILES.get("file")
    if not uploaded:
        messages.error(request, "No se recibió ningún archivo.")
        return redirect("gantt_hub")
    name = uploaded.name or ""
    if not name.lower().endswith(".mpp"):
        messages.error(request, "El archivo debe ser .mpp")
        return redirect("gantt_hub")
    try:
        archivo = replace_archivo_with_import(uploaded, original_filename=name)
        messages.success(
            request,
            f"Archivo importado: {name}. Tareas cargadas: {archivo.tasks.count()}",
        )
    except Exception as e:
        messages.error(request, f"Error al importar: {e}")
    return redirect("gantt_hub")


@login_required
def gantt_task_list(request):
    return render(request, "gantt/task_list.html", {"archivo": latest_archivo()})


@login_required
@require_GET
def gantt_task_records_json(request):
    archivo = latest_archivo()
    if not archivo:
        return JsonResponse({"records": []})
    q = request.GET.get("q", "").strip()
    qs = GanttTask.objects.filter(archivo=archivo).order_by("task_id", "id")
    if q:
        qs = qs.filter(
            Q(nombre_tarea__icontains=q)
            | Q(especialidad__icontains=q)
            | Q(esp__icontains=q)
            | Q(predecesoras__icontains=q)
            | Q(sucesoras__icontains=q)
            | Q(notas__icontains=q)
        )
    batch = list(qs[:1000])
    changes = ultima_cambio_map(archivo, [x.pk for x in batch])
    records = []
    for t in batch:
        last = changes.get(t.pk)
        records.append(
            {
                "id": t.pk,
                "task_id": t.task_id,
                "nombre_tarea": t.nombre_tarea,
                "especialidad": t.especialidad,
                "esp": t.esp,
                "outline_number": t.outline_number,
                "duracion": t.duracion,
                "avance_planificado": float(t.avance_planificado)
                if t.avance_planificado is not None
                else None,
                "trabajo_completado": float(t.trabajo_completado)
                if t.trabajo_completado is not None
                else None,
                "comienzo": t.comienzo.isoformat() if t.comienzo else "",
                "fin": t.fin.isoformat() if t.fin else "",
                "predecesoras": t.predecesoras,
                "sucesoras": t.sucesoras,
                "notas": t.notas,
                "ultima_cambio": last.isoformat() if last else "",
            }
        )
    return JsonResponse({"records": records})


@login_required
def gantt_estado(request):
    return render(
        request,
        "gantt/estado.html",
        {
            "archivo": latest_archivo(),
            "today_display": timezone.localdate().strftime("%d/%m/%Y"),
        },
    )


@login_required
def gantt_critical_path(request):
    archivo = latest_archivo()
    selected_especialidad = request.GET.get("especialidad", "").strip()
    selected_frente = request.GET.get("frente", "").strip()
    options = (
        build_critical_path_filter_options(archivo)
        if archivo
        else {"especialidades": [], "frentes": []}
    )
    if selected_especialidad and selected_especialidad not in options["especialidades"]:
        selected_especialidad = ""
    if selected_frente and selected_frente not in options["frentes"]:
        selected_frente = ""
    snapshot = (
        build_critical_path_snapshot(
            archivo,
            especialidad=selected_especialidad,
            frente=selected_frente,
        )
        if archivo
        else {
            "nodes": [],
            "project_start": None,
            "project_finish": None,
            "project_span_days": 0,
            "critical_chain_days": 0,
            "palette": {},
        }
    )
    return render(
        request,
        "gantt/critical_path.html",
        {
            "archivo": archivo,
            "nodes": snapshot["nodes"],
            "project_start": snapshot["project_start"],
            "project_finish": snapshot["project_finish"],
            "project_span_days": snapshot["project_span_days"],
            "critical_chain_days": snapshot["critical_chain_days"],
            "color_legend": snapshot["palette"].items(),
            "especialidades": options["especialidades"],
            "frentes": options["frentes"],
            "selected_especialidad": selected_especialidad,
            "selected_frente": selected_frente,
        },
    )


@login_required
def gantt_critical_path_graphic(request):
    archivo = latest_archivo()
    selected_especialidad = request.GET.get("especialidad", "").strip()
    selected_frente = request.GET.get("frente", "").strip()
    options = (
        build_critical_path_filter_options(archivo)
        if archivo
        else {"especialidades": [], "frentes": []}
    )
    if selected_especialidad and selected_especialidad not in options["especialidades"]:
        selected_especialidad = ""
    if selected_frente and selected_frente not in options["frentes"]:
        selected_frente = ""

    snapshot = (
        build_critical_path_snapshot(
            archivo,
            especialidad=selected_especialidad,
            frente=selected_frente,
        )
        if archivo
        else {
            "nodes": [],
            "project_start": None,
            "project_finish": None,
            "project_span_days": 0,
            "critical_chain_days": 0,
            "palette": {},
        }
    )
    full_graph = (
        build_critical_graph_dataset(
            archivo,
            especialidad=selected_especialidad,
            frente=selected_frente,
        )
        if archivo
        else {"nodes": [], "edges": []}
    )
    path_nodes = snapshot["nodes"]
    graph_nodes = []
    graph_edges = []
    for n in path_nodes:
        graph_nodes.append(
            {
                "data": {
                    "id": f"task-{n['task_id']}",
                    "label": f"ID {n['task_id']} | EDT {n.get('edt') or '-'}",
                    "name": n["nombre_tarea"],
                    "dur": n["duracion_dias"],
                    "start": n["comienzo"].strftime("%d/%m/%Y"),
                    "finish": n["fin"].strftime("%d/%m/%Y"),
                    "esp": n.get("especialidad") or "SIN_ESPECIALIDAD",
                    "color": n.get("color") or "#ef4444",
                }
            }
        )
    for prev, nxt in zip(path_nodes, path_nodes[1:]):
        graph_edges.append(
            {
                "data": {
                    "id": f"edge-{prev['task_id']}-{nxt['task_id']}",
                    "source": f"task-{prev['task_id']}",
                    "target": f"task-{nxt['task_id']}",
                    "label": "flujo critico",
                }
            }
        )

    cuello = max(path_nodes, key=lambda x: x["duracion_dias"], default=None)
    flujo_texto = " -> ".join(f"ID {n['task_id']}" for n in path_nodes) if path_nodes else ""
    return render(
        request,
        "gantt/critical_path_graphic.html",
        {
            "archivo": archivo,
            "nodes": path_nodes,
            "graph_elements": graph_nodes + graph_edges,
            "project_start": snapshot["project_start"],
            "project_finish": snapshot["project_finish"],
            "critical_chain_days": snapshot["critical_chain_days"],
            "cuello": cuello,
            "flujo_texto": flujo_texto,
            "especialidades": options["especialidades"],
            "frentes": options["frentes"],
            "selected_especialidad": selected_especialidad,
            "selected_frente": selected_frente,
            "full_graph": full_graph,
            "critical_task_ids": [n["task_id"] for n in path_nodes],
        },
    )


@login_required
@require_GET
def gantt_estado_records_json(request):
    archivo = latest_archivo()
    if not archivo:
        return JsonResponse({"records": []})
    return JsonResponse({"records": build_estado_atraso_records(archivo)})


@login_required
def gantt_task_edit(request, pk: int):
    archivo = latest_archivo()
    if not archivo:
        messages.error(request, "No hay archivo cargado.")
        return redirect("gantt_hub")
    obj = get_object_or_404(GanttTask, pk=pk, archivo=archivo)
    if not str(obj.especialidad or "").strip():
        messages.error(
            request,
            "Esta fila es un título o subtítulo del cronograma; no se puede editar.",
        )
        return redirect("gantt_task_list")
    fields = list(GanttTaskForm.Meta.fields)
    if request.method == "POST":
        before = model_to_dict(obj, fields=fields)
        form = GanttTaskForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            obj.refresh_from_db()
            log_task_changes(archivo, request.user, obj, before, fields)
            messages.success(request, "Tarea actualizada en base de datos.")
            return redirect("gantt_task_list")
    else:
        form = GanttTaskForm(instance=obj)
    return render(
        request,
        "gantt/task_edit.html",
        {"form": form, "obj": obj, "archivo": archivo},
    )


@login_required
def gantt_s_curve(request):
    archivo = latest_archivo()
    if archivo:
        series_data = [
            {
                "fecha": row["fecha"].isoformat(),
                "planificado": row["planificado"],
                "real": row["real"],
            }
            for row in build_s_curve_series(archivo)
        ]
    else:
        series_data = []
    return render(
        request,
        "gantt/s_curve.html",
        {
            "archivo": archivo,
            "series_data": series_data,
            "series_count": len(series_data),
        },
    )


@login_required
@require_GET
def gantt_s_curve_export_csv(request):
    archivo = latest_archivo()
    if not archivo:
        messages.error(request, "No hay archivo Gantt cargado.")
        return redirect("gantt_hub")
    series = build_s_curve_series(archivo)
    if not series:
        messages.warning(
            request,
            "No hay datos para la curva S: se necesitan tareas con especialidad y fechas de comienzo y fin.",
        )
        return redirect("gantt_s_curve")
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["fecha", "planificado_pct", "real_modelado_pct"])
    for row in series:
        writer.writerow([row["fecha"].isoformat(), row["planificado"], row["real"]])
    payload = "\ufeff" + buf.getvalue()
    resp = HttpResponse(payload.encode("utf-8"), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="curva_s_gantt.csv"'
    return resp


@login_required
def gantt_cambios_list(request):
    archivo = latest_archivo()
    qs = GanttCambioLog.objects.select_related("user", "archivo")
    if archivo:
        qs = qs.filter(archivo=archivo)
    return render(
        request,
        "gantt/cambios_list.html",
        {"archivo": archivo, "cambios": qs.order_by("-created_at")[:500]},
    )


@login_required
@require_GET
def gantt_export_excel(request):
    archivo = latest_archivo()
    if not archivo:
        messages.error(request, "No hay archivo Gantt cargado.")
        return redirect("gantt_hub")
    buf = build_excel_buffer(archivo)
    name = f"gantt_actualizado_{archivo.pk}.xlsx"
    return FileResponse(
        buf,
        as_attachment=True,
        filename=name,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@login_required
@require_GET
def gantt_export_csv(request):
    archivo = latest_archivo()
    if not archivo:
        messages.error(request, "No hay archivo Gantt cargado.")
        return redirect("gantt_hub")
    data = build_csv_bytes(archivo)
    name = f"gantt_actualizado_{archivo.pk}.csv"
    resp = HttpResponse(data, content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{name}"'
    return resp


@login_required
@require_GET
def gantt_export_project_xml(request):
    archivo = latest_archivo()
    if not archivo:
        messages.error(request, "No hay archivo Gantt cargado.")
        return redirect("gantt_hub")
    data = build_mspdi_xml_bytes(archivo)
    name = f"gantt_actualizado_{archivo.pk}.xml"
    resp = HttpResponse(data, content_type="application/xml; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{name}"'
    return resp
