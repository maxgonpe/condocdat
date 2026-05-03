from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .forms import GanttTaskForm
from .models import GanttCambioLog, GanttTask
from .services import (
    build_csv_bytes,
    build_excel_buffer,
    build_mspdi_xml_bytes,
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
