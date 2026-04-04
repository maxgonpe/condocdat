from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from .services import (
    attach_rdi_csv,
    get_rdi_records_for_ajax,
    get_rdi_cost_schedule_impacts_for_ajax,
)


def _date_short(value):
    # Espera ISO "YYYY-MM-DD..." (o None)
    if not value:
        return ""
    return str(value)[:10]


def _escape_html_for_paragraph(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # En ReportLab, una fila de Table no se parte entre páginas.
    # Quitamos saltos para evitar celdas con altura extrema.
    s = s.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    # Colapsa espacios múltiples.
    s = " ".join(s.split())
    return s


@login_required
@require_GET
def rdi_export_excel(request):
    import openpyxl
    from openpyxl.utils import get_column_letter
    from io import BytesIO

    q = request.GET.get("q", "").strip()
    # Debe coincidir con lo que muestra la tabla (AJAX usa limit=200 por defecto).
    records = get_rdi_records_for_ajax(q=q, limit=200)

    headers = [
        "CSV ID",
        "Fecha de archivo (versión)",
        "Titulo",
        "Estado",
        "Consulta",
        "Respuesta",
        "Fecha vencimiento",
        "Fecha creación",
        "Fecha actualización",
        "Disciplina",
        "Empresa",
        "Asignado a",
        "Tipo asignación",
        "Respuesta sugerida",
        "Ubicación detalle",
        "Creado por",
        "Actualizado por",
        "Lista distribución",
        "Impacto costo",
        "Impacto plazo",
        "Prioridad",
        "Categoría",
        "Referencia",
        "Asociado a documento",
        "Informado (código)",
        "Informado",
        "ID interno",
        "Last diff fields",
        "Last import ID",
    ]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "RDI"

    from django.utils import timezone
    fecha_str = timezone.now().strftime("%d-%m-%Y")
    filtro_str = (f"Filtro: {q}" if q else "Filtro: (vacío)")
    ws["A1"] = filtro_str + f" | Generado: {fecha_str}"
    # Fusiona la fila del filtro sobre todas las columnas exportadas.
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))

    # Fila 2: headers
    ws.append(headers)

    # Datos desde fila 3
    for r in records:
        ws.append([
            r.get("csv_id", ""),
            _date_short(r.get("last_snapshot_datetime")),
            r.get("title", ""),
            r.get("status_label", r.get("status", "")),
            r.get("question", ""),
            r.get("response", ""),
            _date_short(r.get("due_date")),
            _date_short(r.get("created_at")),
            _date_short(r.get("updated_at")),
            r.get("discipline", ""),
            r.get("company", ""),
            r.get("assigned_to", ""),
            r.get("assignee_type", ""),
            r.get("suggested_answer", ""),
            r.get("location_details", ""),
            r.get("created_by", ""),
            r.get("updated_by", ""),
            r.get("distribution_list", ""),
            r.get("cost_impact", ""),
            r.get("schedule_impact", ""),
            r.get("priority", ""),
            r.get("category", ""),
            r.get("reference", ""),
            "Sí" if r.get("associated_to_document") is True else ("No" if r.get("associated_to_document") is False else ""),
            r.get("informado", ""),
            r.get("informado_label", ""),
            r.get("id", ""),
            r.get("last_diff_fields", ""),
            r.get("last_import_id", ""),
        ])

    # Estilos y ancho simple + wrap
    wrap_text = openpyxl.styles.Alignment(wrap_text=True, vertical="top")
    for col in range(1, len(headers) + 1):
        letter = get_column_letter(col)
        # Anchos aproximados
        ws.column_dimensions[letter].width = 18 if col in (1, 2, 4, 7, 8, 9, 24, 25, 26, 27, 28, 29) else 28

    # Alinea y activa wrap en todas las filas excepto A1 (fusionado)
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=len(headers)):
        for cell in row:
            cell.alignment = wrap_text

    # Congelar panes: mantener headers visibles
    ws.freeze_panes = "A3"

    # Filtros automáticos en la fila de encabezados (fila 2)
    last_col_letter = get_column_letter(len(headers))
    n_data = len(records) + 2
    ws.auto_filter.ref = f"A2:{last_col_letter}{n_data}"

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"RDI_export-{fecha_str}.xlsx"
    resp = HttpResponse(
        buf.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


@login_required
@require_GET
def rdi_export_pdf(request):
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

    q = request.GET.get("q", "").strip()
    # Para evitar LayoutError (filas demasiado altas), limitamos.
    records = get_rdi_records_for_ajax(q=q, limit=200)

    headers = ["CSV ID", "Titulo", "Estado", "Consulta", "Respuesta", "Fecha vencimiento", "Fecha creación", "Fecha actualización"]

    styles = getSampleStyleSheet()
    style_title = styles["Title"]
    style_body = styles["BodyText"]
    style_cell = ParagraphStyle(
        "cell",
        parent=style_body,
        fontSize=9,
        leading=11,
        wordWrap="CJK",
    )
    style_cell_bold = ParagraphStyle(
        "cell_bold",
        parent=style_body,
        fontSize=9,
        leading=11,
        textColor=colors.white,
    )

    def cell_paragraph(txt, bold=False, max_chars=600):
        if txt is None:
            txt = ""
        txt = str(txt)
        if len(txt) > max_chars:
            txt = txt[:max_chars] + " …"
        txt = _escape_html_for_paragraph(txt)
        return Paragraph(txt, style_cell_bold if bold else style_cell)

    pdf_buf = BytesIO()
    doc = SimpleDocTemplate(pdf_buf, pagesize=A4, rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=24)

    title = Paragraph("RDI - Exportación", style_title)
    filtro = Paragraph(f"Filtro: {q}" if q else "Filtro: (vacío)", style_body)

    data = []
    header_row = [cell_paragraph(h, bold=True, max_chars=200) for h in headers]
    data.append(header_row)

    for r in records:
        data.append([
            cell_paragraph(r.get("csv_id", "")),
            cell_paragraph(r.get("title", ""), max_chars=220),
            cell_paragraph(r.get("status_label", r.get("status", "")), max_chars=60),
            cell_paragraph(r.get("question", ""), max_chars=450),
            cell_paragraph(r.get("response", ""), max_chars=450),
            cell_paragraph(_date_short(r.get("due_date", ""))),
            cell_paragraph(_date_short(r.get("created_at", ""))),
            cell_paragraph(_date_short(r.get("updated_at", ""))),
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E5090")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ]
        )
    )

    doc.build([title, Spacer(1, 10), filtro, Spacer(1, 12), table])
    pdf_buf.seek(0)

    resp = HttpResponse(pdf_buf.read(), content_type="application/pdf")
    resp["Content-Disposition"] = 'inline; filename="RDI_export.pdf"'
    return resp


@login_required
@require_GET
def rdi_list_view(request):
    return render(request, "rdi/rdi_list.html")


@login_required
@require_GET
def informar_bim_list_view(request):
    """Listado tipo RDI para «Informar desde BIM» (misma fuente AJAX que RDI)."""
    return render(request, "rdi/informar_bim_list.html")


@login_required
@require_GET
def rdi_increments_decrements_view(request):
    """
    Listado de RDI con impacto en costo o plazo (yes/si).
    """
    return render(request, "rdi/rdi_increments_decrements.html")


@login_required
@require_GET
def rdi_increments_decrements_export_excel(request):
    import openpyxl
    from openpyxl.utils import get_column_letter
    from io import BytesIO
    from django.utils import timezone

    q = request.GET.get("q", "").strip()
    records = get_rdi_cost_schedule_impacts_for_ajax(q=q, limit=1000)
    headers = [
        "CSV ID",
        "Estado",
        "Ubicacion",
        "Impacto de costo",
        "Impacto de plazo",
        "Disciplina",
        "Prioridad",
        "Pregunta",
        "Respuesta",
    ]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Aumentos-Disminuciones"
    fecha_str = timezone.now().strftime("%d-%m-%Y")
    filtro_str = (f"Filtro: {q}" if q else "Filtro: (vacío)")
    ws["A1"] = filtro_str + f" | Generado: {fecha_str}"
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
    ws.append(headers)

    for r in records:
        ws.append(
            [
                r.get("csv_id", ""),
                r.get("status_label", r.get("status", "")),
                r.get("location_details", ""),
                r.get("cost_impact_label", r.get("cost_impact", "")),
                r.get("schedule_impact_label", r.get("schedule_impact", "")),
                r.get("discipline", ""),
                r.get("priority_label", r.get("priority", "")),
                r.get("question", ""),
                r.get("response", ""),
            ]
        )

    wrap_text = openpyxl.styles.Alignment(wrap_text=True, vertical="top")
    for col in range(1, len(headers) + 1):
        letter = get_column_letter(col)
        ws.column_dimensions[letter].width = 18 if col in (1, 2, 4, 5, 7) else 38

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=len(headers)):
        for cell in row:
            cell.alignment = wrap_text

    ws.freeze_panes = "A3"
    last_col_letter = get_column_letter(len(headers))
    n_data = len(records) + 2
    ws.auto_filter.ref = f"A2:{last_col_letter}{n_data}"

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"Aumentos-disminuciones-{fecha_str}.xlsx"
    resp = HttpResponse(
        buf.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


@login_required
@require_GET
def rdi_increments_decrements_export_pdf(request):
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

    q = request.GET.get("q", "").strip()
    records = get_rdi_cost_schedule_impacts_for_ajax(q=q, limit=600)
    headers = [
        "CSV ID",
        "Estado",
        "Ubicacion",
        "Impacto costo",
        "Impacto plazo",
        "Disciplina",
        "Prioridad",
    ]

    styles = getSampleStyleSheet()
    style_title = styles["Title"]
    style_body = styles["BodyText"]
    style_cell = ParagraphStyle("cell", parent=style_body, fontSize=8.5, leading=10.5, wordWrap="CJK")
    style_cell_bold = ParagraphStyle("cell_bold", parent=style_body, fontSize=8.5, leading=10.5, textColor=colors.white)

    def cell_paragraph(txt, bold=False, max_chars=500):
        if txt is None:
            txt = ""
        txt = str(txt)
        if len(txt) > max_chars:
            txt = txt[:max_chars] + " …"
        txt = _escape_html_for_paragraph(txt)
        return Paragraph(txt, style_cell_bold if bold else style_cell)

    pdf_buf = BytesIO()
    doc = SimpleDocTemplate(
        pdf_buf,
        pagesize=landscape(A4),
        rightMargin=18,
        leftMargin=18,
        topMargin=18,
        bottomMargin=18,
    )
    title = Paragraph("Aumentos/disminuciones - RDI", style_title)
    filtro = Paragraph(f"Filtro: {q}" if q else "Filtro: (vacío)", style_body)
    data = [[cell_paragraph(h, bold=True, max_chars=180) for h in headers]]
    for r in records:
        data.append(
            [
                cell_paragraph(r.get("csv_id", "")),
                cell_paragraph(r.get("status_label", r.get("status", "")), max_chars=60),
                cell_paragraph(r.get("location_details", ""), max_chars=280),
                cell_paragraph(r.get("cost_impact_label", r.get("cost_impact", "")), max_chars=60),
                cell_paragraph(r.get("schedule_impact_label", r.get("schedule_impact", "")), max_chars=60),
                cell_paragraph(r.get("discipline", ""), max_chars=90),
                cell_paragraph(r.get("priority_label", r.get("priority", "")), max_chars=60),
            ]
        )

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E5090")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ]
        )
    )

    doc.build([title, Spacer(1, 8), filtro, Spacer(1, 10), table])
    pdf_buf.seek(0)
    resp = HttpResponse(pdf_buf.read(), content_type="application/pdf")
    resp["Content-Disposition"] = 'inline; filename="Aumentos-disminuciones-RDI.pdf"'
    return resp


@login_required
@require_POST
def rdi_import_view(request):
    uploaded = request.FILES.get("file")
    if not uploaded:
        messages.error(request, "No se recibió ningún archivo CSV.")
        return redirect("rdi_list")

    original_filename = uploaded.name

    try:
        attach_rdi_csv(uploaded, original_filename=original_filename)
        messages.success(
            request,
            f"CSV importado correctamente: {original_filename}.",
        )
    except Exception as e:
        messages.error(request, f"Error importando CSV: {e}")

    return redirect("rdi_list")


@login_required
@require_GET
def rdi_records_json(request):
    q = request.GET.get("q", "").strip()
    data = get_rdi_records_for_ajax(q=q)
    return JsonResponse({"records": data})


@login_required
@require_GET
def rdi_increments_decrements_json(request):
    q = request.GET.get("q", "").strip()
    data = get_rdi_cost_schedule_impacts_for_ajax(q=q)
    return JsonResponse({"records": data})

