from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from .forms import (
    EquiposAssetForm,
    EquiposLocationForm,
    EquiposOtroForm,
    EquiposResumenFilaForm,
    EquiposSignificadoFilaForm,
)
from .models import (
    EquiposAsset,
    EquiposCambioLog,
    EquiposLocation,
    EquiposOtro,
    EquiposResumenFila,
    EquiposSignificadoFila,
)
from .services import (
    build_equipos_download_filename,
    build_equipos_pdf_download_filename,
    build_pdf_buffer,
    format_ultima_cambio_para_json,
    latest_libro,
    log_changes,
    replace_libro_with_import,
    sync_libro_to_excel,
    ultima_cambio_formulario_map,
    ultima_cambio_un_registro,
)


def _require_libro():
    lib = latest_libro()
    if not lib:
        return None
    return lib


def _log_model(user, libro, instance, before: dict, fields: list[str], model_label: str):
    after = model_to_dict(instance, fields=fields)
    for k in list(before.keys()):
        if k not in fields:
            del before[k]
    log_changes(libro, user, model_label, instance.pk, instance.excel_row, before, after, fields)


@login_required
def equipos_hub(request):
    libro = latest_libro()
    _sentinel = 9_000_000_001
    ctx = {
        "libro": libro,
        "n_resumen": libro.resumen_filas.count() if libro else 0,
        "n_signif": libro.significado_filas.count() if libro else 0,
        "n_loc": libro.locations.count() if libro else 0,
        "n_asset": libro.assets.count() if libro else 0,
        "n_otros": libro.otros.count() if libro else 0,
        "url_tpl_asset_edit": reverse("equipos_asset_edit", kwargs={"pk": _sentinel}),
        "url_tpl_location_edit": reverse("equipos_location_edit", kwargs={"pk": _sentinel}),
        "url_tpl_otro_edit": reverse("equipos_otro_edit", kwargs={"pk": _sentinel}),
        "url_sentinel": str(_sentinel),
    }
    return render(request, "equipos/hub.html", ctx)


@login_required
@require_POST
def equipos_import_view(request):
    uploaded = request.FILES.get("file")
    if not uploaded:
        messages.error(request, "No se recibió ningún archivo.")
        return redirect("equipos_hub")

    name = uploaded.name or ""
    if not name.lower().endswith(".xlsx"):
        messages.error(request, "El archivo debe ser .xlsx")
        return redirect("equipos_hub")

    try:
        replace_libro_with_import(uploaded, original_filename=name)
        messages.success(request, f"Libro importado: {name}.")
    except Exception as e:
        messages.error(request, f"Error al importar: {e}")

    return redirect("equipos_hub")


@login_required
@require_GET
def equipos_download_xlsx(request):
    libro = _require_libro()
    if not libro:
        messages.error(request, "No hay libro cargado.")
        return redirect("equipos_hub")
    try:
        sync_libro_to_excel(libro)
    except Exception as e:
        messages.error(request, f"No se pudo actualizar el Excel: {e}")
        return redirect("equipos_hub")
    libro.refresh_from_db()
    fn = build_equipos_download_filename(libro)
    resp = FileResponse(
        open(libro.file.path, "rb"),
        as_attachment=True,
        filename=fn,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    return resp


@login_required
@require_GET
def equipos_export_pdf(request):
    libro = _require_libro()
    if not libro:
        return HttpResponse("No hay libro cargado.", status=404)
    buf = build_pdf_buffer(libro)
    filename = build_equipos_pdf_download_filename(libro)
    return FileResponse(
        buf,
        as_attachment=True,
        filename=filename,
        content_type="application/pdf",
    )


@login_required
def equipos_cambios_list(request):
    libro = latest_libro()
    base = EquiposCambioLog.objects.select_related("user", "libro")
    if libro:
        base = base.filter(libro=libro)
    qs = base.order_by("-created_at")[:500]
    return render(
        request,
        "equipos/cambios_list.html",
        {"libro": libro, "cambios": qs},
    )


@login_required
def equipos_asset_list(request):
    _s = 9_000_000_001
    return render(
        request,
        "equipos/asset_list.html",
        {
            "libro": latest_libro(),
            "url_tpl_edit": reverse("equipos_asset_edit", kwargs={"pk": _s}),
            "url_sentinel": str(_s),
        },
    )


@login_required
@require_GET
def equipos_asset_records_json(request):
    libro = _require_libro()
    if not libro:
        return JsonResponse({"records": []})
    q = request.GET.get("q", "").strip()
    qs = EquiposAsset.objects.filter(libro=libro).order_by("excel_row")
    if q:
        qs = qs.filter(
            Q(tag_number__icontains=q)
            | Q(asset_name__icontains=q)
            | Q(estado__icontains=q)
            | Q(zones__icontains=q)
            | Q(proveedor__icontains=q)
        )
    records = []
    batch = list(qs[:800])
    ids = [o.pk for o in batch]
    cambios = ultima_cambio_formulario_map(libro, "EquiposAsset", ids)
    for o in batch:
        iso, fmt = format_ultima_cambio_para_json(cambios.get(o.pk))
        records.append(
            {
                "id": o.pk,
                "excel_row": o.excel_row,
                "row_type": o.row_type,
                "tag_number": o.tag_number,
                "asset_name": o.asset_name,
                "estado": o.estado,
                "zones": o.zones,
                "proveedor": o.proveedor,
                "ultima_cambio": iso,
                "ultima_cambio_fmt": fmt,
            }
        )
    return JsonResponse({"records": records})


@login_required
def equipos_asset_edit(request, pk: int):
    libro = _require_libro()
    if not libro:
        messages.error(request, "No hay libro cargado.")
        return redirect("equipos_hub")
    obj = get_object_or_404(EquiposAsset, pk=pk, libro=libro)
    fields = list(EquiposAssetForm.Meta.fields)
    if request.method == "POST":
        before = model_to_dict(obj, fields=fields)
        form = EquiposAssetForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            obj.refresh_from_db()
            _log_model(request.user, libro, obj, before, fields, "EquiposAsset")
            try:
                sync_libro_to_excel(libro)
            except Exception as e:
                messages.warning(request, f"Guardado en BD; error al sincronizar Excel: {e}")
            else:
                messages.success(request, "Registro actualizado y Excel sincronizado.")
            return redirect("equipos_asset_list")
    else:
        form = EquiposAssetForm(instance=obj)
    _, ultima_cambio_fmt = format_ultima_cambio_para_json(
        ultima_cambio_un_registro(libro, "EquiposAsset", obj.pk)
    )
    return render(
        request,
        "equipos/asset_edit.html",
        {
            "form": form,
            "obj": obj,
            "libro": libro,
            "ultima_cambio_fmt": ultima_cambio_fmt,
        },
    )


@login_required
def equipos_location_list(request):
    _s = 9_000_000_001
    return render(
        request,
        "equipos/location_list.html",
        {
            "libro": latest_libro(),
            "url_tpl_edit": reverse("equipos_location_edit", kwargs={"pk": _s}),
            "url_sentinel": str(_s),
        },
    )


@login_required
@require_GET
def equipos_location_records_json(request):
    libro = _require_libro()
    if not libro:
        return JsonResponse({"records": []})
    q = request.GET.get("q", "").strip()
    qs = EquiposLocation.objects.filter(libro=libro).order_by("excel_row")
    if q:
        qs = qs.filter(
            Q(code__icontains=q)
            | Q(space_name__icontains=q)
            | Q(zones__icontains=q)
            | Q(building__icontains=q)
        )
    records = []
    batch = list(qs[:800])
    ids = [o.pk for o in batch]
    cambios = ultima_cambio_formulario_map(libro, "EquiposLocation", ids)
    for o in batch:
        iso, fmt = format_ultima_cambio_para_json(cambios.get(o.pk))
        records.append(
            {
                "id": o.pk,
                "excel_row": o.excel_row,
                "code": o.code,
                "space_name": o.space_name,
                "zones": o.zones,
                "area_m2": str(o.area_m2) if o.area_m2 is not None else "",
                "ultima_cambio": iso,
                "ultima_cambio_fmt": fmt,
            }
        )
    return JsonResponse({"records": records})


@login_required
def equipos_location_edit(request, pk: int):
    libro = _require_libro()
    if not libro:
        messages.error(request, "No hay libro cargado.")
        return redirect("equipos_hub")
    obj = get_object_or_404(EquiposLocation, pk=pk, libro=libro)
    fields = list(EquiposLocationForm.Meta.fields)
    if request.method == "POST":
        before = model_to_dict(obj, fields=fields)
        form = EquiposLocationForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            obj.refresh_from_db()
            _log_model(request.user, libro, obj, before, fields, "EquiposLocation")
            try:
                sync_libro_to_excel(libro)
            except Exception as e:
                messages.warning(request, f"Guardado en BD; error al sincronizar Excel: {e}")
            else:
                messages.success(request, "Ubicación actualizada y Excel sincronizado.")
            return redirect("equipos_location_list")
    else:
        form = EquiposLocationForm(instance=obj)
    _, ultima_cambio_fmt = format_ultima_cambio_para_json(
        ultima_cambio_un_registro(libro, "EquiposLocation", obj.pk)
    )
    return render(
        request,
        "equipos/location_edit.html",
        {
            "form": form,
            "obj": obj,
            "libro": libro,
            "ultima_cambio_fmt": ultima_cambio_fmt,
        },
    )


@login_required
def equipos_otro_list(request):
    _s = 9_000_000_001
    return render(
        request,
        "equipos/otro_list.html",
        {
            "libro": latest_libro(),
            "url_tpl_edit": reverse("equipos_otro_edit", kwargs={"pk": _s}),
            "url_sentinel": str(_s),
        },
    )


@login_required
@require_GET
def equipos_otro_records_json(request):
    libro = _require_libro()
    if not libro:
        return JsonResponse({"records": []})
    q = request.GET.get("q", "").strip()
    qs = EquiposOtro.objects.filter(libro=libro).order_by("excel_row")
    if q:
        qs = qs.filter(
            Q(tag_number__icontains=q)
            | Q(asset_name__icontains=q)
            | Q(estado__icontains=q)
            | Q(especialidad__icontains=q)
        )
    records = []
    batch = list(qs[:800])
    ids = [o.pk for o in batch]
    cambios = ultima_cambio_formulario_map(libro, "EquiposOtro", ids)
    for o in batch:
        iso, fmt = format_ultima_cambio_para_json(cambios.get(o.pk))
        records.append(
            {
                "id": o.pk,
                "excel_row": o.excel_row,
                "row_type": o.row_type,
                "tag_number": o.tag_number,
                "asset_name": o.asset_name,
                "estado": o.estado,
                "rdi_ttal": o.rdi_ttal,
                "ultima_cambio": iso,
                "ultima_cambio_fmt": fmt,
            }
        )
    return JsonResponse({"records": records})


@login_required
def equipos_otro_edit(request, pk: int):
    libro = _require_libro()
    if not libro:
        messages.error(request, "No hay libro cargado.")
        return redirect("equipos_hub")
    obj = get_object_or_404(EquiposOtro, pk=pk, libro=libro)
    fields = list(EquiposOtroForm.Meta.fields)
    if request.method == "POST":
        before = model_to_dict(obj, fields=fields)
        form = EquiposOtroForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            obj.refresh_from_db()
            _log_model(request.user, libro, obj, before, fields, "EquiposOtro")
            try:
                sync_libro_to_excel(libro)
            except Exception as e:
                messages.warning(request, f"Guardado en BD; error al sincronizar Excel: {e}")
            else:
                messages.success(request, "Registro actualizado y Excel sincronizado.")
            return redirect("equipos_otro_list")
    else:
        form = EquiposOtroForm(instance=obj)
    _, ultima_cambio_fmt = format_ultima_cambio_para_json(
        ultima_cambio_un_registro(libro, "EquiposOtro", obj.pk)
    )
    return render(
        request,
        "equipos/otro_edit.html",
        {
            "form": form,
            "obj": obj,
            "libro": libro,
            "ultima_cambio_fmt": ultima_cambio_fmt,
        },
    )


@login_required
def equipos_resumen_list(request):
    libro = _require_libro()
    row_data = []
    if libro:
        rows = list(libro.resumen_filas.all().order_by("excel_row"))
        ids = [r.pk for r in rows]
        m = ultima_cambio_formulario_map(libro, "EquiposResumenFila", ids)
        for r in rows:
            row_data.append({"row": r, "ultima_cambio": m.get(r.pk)})
    return render(
        request,
        "equipos/resumen_list.html",
        {"libro": libro, "row_data": row_data},
    )


@login_required
def equipos_resumen_edit(request, pk: int):
    libro = _require_libro()
    if not libro:
        return redirect("equipos_hub")
    obj = get_object_or_404(EquiposResumenFila, pk=pk, libro=libro)
    fields = list(EquiposResumenFilaForm.Meta.fields)
    if request.method == "POST":
        before = model_to_dict(obj, fields=fields)
        form = EquiposResumenFilaForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            obj.refresh_from_db()
            _log_model(request.user, libro, obj, before, fields, "EquiposResumenFila")
            try:
                sync_libro_to_excel(libro)
            except Exception as e:
                messages.warning(request, f"Guardado en BD; error al sincronizar Excel: {e}")
            else:
                messages.success(request, "Resumen actualizado y Excel sincronizado.")
            return redirect("equipos_resumen_list")
    else:
        form = EquiposResumenFilaForm(instance=obj)
    _, ultima_cambio_fmt = format_ultima_cambio_para_json(
        ultima_cambio_un_registro(libro, "EquiposResumenFila", obj.pk)
    )
    return render(
        request,
        "equipos/resumen_edit.html",
        {
            "form": form,
            "obj": obj,
            "libro": libro,
            "ultima_cambio_fmt": ultima_cambio_fmt,
        },
    )


@login_required
def equipos_significado_list(request):
    libro = _require_libro()
    row_data = []
    if libro:
        rows = list(libro.significado_filas.all().order_by("excel_row"))
        ids = [r.pk for r in rows]
        m = ultima_cambio_formulario_map(libro, "EquiposSignificadoFila", ids)
        for r in rows:
            row_data.append({"row": r, "ultima_cambio": m.get(r.pk)})
    return render(
        request,
        "equipos/significado_list.html",
        {"libro": libro, "row_data": row_data},
    )


@login_required
def equipos_significado_edit(request, pk: int):
    libro = _require_libro()
    if not libro:
        return redirect("equipos_hub")
    obj = get_object_or_404(EquiposSignificadoFila, pk=pk, libro=libro)
    fields = list(EquiposSignificadoFilaForm.Meta.fields)
    if request.method == "POST":
        before = model_to_dict(obj, fields=fields)
        form = EquiposSignificadoFilaForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            obj.refresh_from_db()
            _log_model(request.user, libro, obj, before, fields, "EquiposSignificadoFila")
            try:
                sync_libro_to_excel(libro)
            except Exception as e:
                messages.warning(request, f"Guardado en BD; error al sincronizar Excel: {e}")
            else:
                messages.success(request, "Significado actualizado y Excel sincronizado.")
            return redirect("equipos_significado_list")
    else:
        form = EquiposSignificadoFilaForm(instance=obj)
    _, ultima_cambio_fmt = format_ultima_cambio_para_json(
        ultima_cambio_un_registro(libro, "EquiposSignificadoFila", obj.pk)
    )
    return render(
        request,
        "equipos/significado_edit.html",
        {
            "form": form,
            "obj": obj,
            "libro": libro,
            "ultima_cambio_fmt": ultima_cambio_fmt,
        },
    )


@login_required
@require_GET
def equipos_search_json(request):
    """Búsqueda unificada (pequeña muestra por tipo) para el hub."""
    libro = _require_libro()
    if not libro:
        return JsonResponse({"libro": None, "assets": [], "locations": [], "otros": []})
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"libro": libro.id, "assets": [], "locations": [], "otros": []})

    assets = EquiposAsset.objects.filter(libro=libro).filter(
        Q(tag_number__icontains=q) | Q(asset_name__icontains=q)
    )[:15]
    locs = EquiposLocation.objects.filter(libro=libro).filter(
        Q(code__icontains=q) | Q(space_name__icontains=q)
    )[:15]
    otros = EquiposOtro.objects.filter(libro=libro).filter(
        Q(tag_number__icontains=q) | Q(asset_name__icontains=q)
    )[:15]

    return JsonResponse(
        {
            "libro": libro.id,
            "assets": [
                {"id": a.pk, "kind": "asset", "label": a.tag_number or a.asset_name[:40]}
                for a in assets
            ],
            "locations": [
                {"id": l.pk, "kind": "location", "label": l.code or (l.space_name or "")[:40]}
                for l in locs
            ],
            "otros": [
                {"id": o.pk, "kind": "otro", "label": o.tag_number or (o.asset_name or "")[:40]}
                for o in otros
            ],
        }
    )
