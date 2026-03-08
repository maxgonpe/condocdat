from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.utils import timezone
import os
import re
from datetime import date

from .models import Document, Folder, FolderFile, DocumentAttachment
from .search_backend import search_unified
from .snippets import extract_snippets


def _parse_requiere_respuesta(content_extract):
    """
    Extrae «Requiere respuesta» SI o NO según la cadena 'SI  NO  X' o 'SI  X  NO' en el extracto.
    Esa cadena puede estar al final, tras "REQUIERE RESPUESTA", o en cualquier otra posición.
    Se consulta el extracto y se busca en todo el texto la primera zona con SI, NO y X.
    """
    if not content_extract or not isinstance(content_extract, str):
        return ""

    t = content_extract.upper().replace("\r\n", " ").replace("\n", " ")
    t = t.replace("\u00CD", "I").replace("Í", "I")
    for char in ("\u2713", "\u2714", "\u2612", "\u2611", "\u25A0"):
        t = t.replace(char, "X")

    def find_word(seg, word):
        i = 0
        while True:
            p = seg.find(word, i)
            if p < 0:
                return -1
            before_ok = p == 0 or not seg[p - 1].isalnum()
            end = p + len(word)
            after_ok = end >= len(seg) or not seg[end].isalnum()
            if before_ok and after_ok:
                return p
            i = p + 1

    def decide_from_segment(segment):
        if len(segment) < 5:
            return ""
        pos_si = find_word(segment, "SI")
        if pos_si < 0:
            pos_si = find_word(segment, " SI ")
        pos_no = find_word(segment, " NO ")
        if pos_no < 0:
            pos_no = find_word(segment, "NO")
        if pos_si < 0 or pos_no < 0:
            return ""
        pos_x = -1
        j = max(0, pos_si)
        while j < len(segment):
            x_pos = segment.find("X", j)
            if x_pos < 0:
                break
            if x_pos <= pos_no + 50 or x_pos < pos_si + 120:
                pos_x = x_pos
                break
            j = x_pos + 1
        if pos_x < 0:
            return ""
        orden = sorted([(pos_si, "SI"), (pos_no, "NO"), (pos_x, "X")], key=lambda x: x[0])
        secuencia = [eti for _, eti in orden]
        if secuencia[-1] == "X":
            return "NO"
        if secuencia[1] == "X":
            return "SI"
        if secuencia[0] == "X":
            return "SI"
        return ""

    # 1) Tras "REQUIERE RESPUESTA" si existe
    if "REQUIERE RESPUESTA" in t:
        idx = t.find("REQUIERE RESPUESTA")
        r = decide_from_segment(t[idx : idx + 500])
        if r:
            return r

    # 2) Final del documento
    seg_end = t[-500:] if len(t) >= 500 else t
    r = decide_from_segment(seg_end)
    if r:
        return r

    # 3) Buscar en todo el extracto (la cadena puede estar en cualquier sitio)
    window = 220
    i = 0
    while i < len(t):
        p_si = t.find(" SI ", i)
        p_no = t.find(" NO ", i)
        p = -1
        if p_si >= 0 and p_no >= 0:
            p = min(p_si, p_no)
        elif p_si >= 0:
            p = p_si
        elif p_no >= 0:
            p = p_no
        if p < 0:
            break
        start = max(0, p - 30)
        end = min(len(t), p + window)
        r = decide_from_segment(t[start:end])
        if r:
            return r
        i = p + 1

    return ""


def _parse_asunto(content_extract):
    """
    Extrae del extracto el texto que sigue a «Asunto:» (ej. «Asunto: Aprobación de Profesionales PROPAMAT»).
    Devuelve solo la parte después de «Asunto:», hasta fin de línea o un límite razonable.
    """
    if not content_extract or not isinstance(content_extract, str):
        return ""
    t = content_extract
    idx = t.upper().find("ASUNTO:")
    if idx < 0:
        return ""
    # Empezar después de "Asunto:" (y posibles espacios o dos puntos extra)
    start = idx + 7
    while start < len(t) and t[start] in " :\t":
        start += 1
    if start >= len(t):
        return ""
    # Hasta el siguiente salto de línea o hasta 300 caracteres
    end = start
    while end < len(t) and end < start + 300:
        if t[end] in "\r\n":
            break
        end += 1
    return t[start:end].strip()


def _parse_atencion(content_extract):
    """
    Extrae del extracto el texto que sigue a «Atención:» (ej. «Atención: Sr. Ignacio Bravo G.»).
    Devuelve solo la parte después de «Atención:», hasta fin de línea o un límite razonable.
    """
    if not content_extract or not isinstance(content_extract, str):
        return ""
    t = content_extract
    tu = t.upper()
    idx = tu.find("ATENCIÓN:")
    if idx < 0:
        idx = tu.find("ATENCION:")
    if idx < 0:
        return ""
    # Buscar los dos puntos y empezar después
    colon = t.find(":", idx)
    if colon < 0:
        return ""
    start = colon + 1
    while start < len(t) and t[start] in " \t":
        start += 1
    if start >= len(t):
        return ""
    end = start
    while end < len(t) and end < start + 200:
        if t[end] in "\r\n":
            break
        end += 1
    return t[start:end].strip()


def _parse_saluda_atentamente(content_extract):
    """
    Extrae del extracto el bloque tras «Saluda atentamente,» hasta «PROPAMAT».
    Corresponde a la firma: nombre y cargo (ej. Claudio Simonetti / Administrador de Contrato).
    Sirve para cartas de respuesta donde puede firmar otra persona.
    """
    if not content_extract or not isinstance(content_extract, str):
        return ""
    t = content_extract
    tu = t.upper()
    idx = tu.find("SALUDA ATENTAMENTE")
    if idx < 0:
        return ""
    # Empezar después de la frase (y coma si existe)
    start = idx + len("SALUDA ATENTAMENTE")
    while start < len(t) and t[start] in " ,\t\r\n":
        start += 1
    if start >= len(t):
        return ""
    # Buscar «PROPAMAT» como fin del bloque (nombre de empresa)
    end_mark = tu.find("PROPAMAT", start)
    if end_mark >= 0:
        end = end_mark
    else:
        end = len(t)
    block = t[start:end]
    # Limpiar: quitar líneas vacías al final, normalizar espacios internos
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    return " ".join(lines) if lines else ""


# Meses en español (clave en mayúsculas sin tildes para comparar)
_MESES = {
    "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6,
    "JULIO": 7, "AGOSTO": 8, "SEPTIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12,
}


def _parse_fecha_envio(content_extract):
    """
    Extrae del extracto una fecha tipo «Santiago, 26 de FEBRERO de 2026» y la devuelve como date.
    Busca el patrón: día (1-31) + " de " + mes (nombre) + " de " + año (4 dígitos).
    Devuelve date o None si no se encuentra o no es válida.
    """
    if not content_extract or not isinstance(content_extract, str):
        return None
    t = content_extract.strip()
    # Patrón: opcional ciudad + coma + espacios, luego día, " de ", mes, " de ", año
    m = re.search(
        r"(\d{1,2})\s+de\s+([A-Za-zÁ-Úá-ú]+)\s+de\s+(\d{4})\b",
        t,
        re.IGNORECASE,
    )
    if not m:
        return None
    day = int(m.group(1))
    month_name = m.group(2).upper().replace("Í", "I").replace("É", "E").replace("Ú", "U").replace("Á", "A").replace("Ó", "O")
    year = int(m.group(3))
    month = _MESES.get(month_name)
    if not month:
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _normalize_car_code(nombre_archivo_or_code):
    """
    Extrae y normaliza el código CAR desde el nombre de archivo (ej. ODA-BUF-CC-CAR-0005.pdf).
    Devuelve algo como ODA-BUF-CC-CAR-0005 para poder hacer match con referencias en otros extractos.
    """
    if not nombre_archivo_or_code:
        return ""
    s = os.path.splitext(nombre_archivo_or_code)[0].strip().upper()
    # Si ya parece un código CAR (contiene CAR y dígitos), normalizar número a 4 dígitos
    m = re.search(r"(.*-CAR-)(\d+)$", s, re.IGNORECASE)
    if m:
        prefix, num = m.group(1).upper(), m.group(2)
        return prefix + num.zfill(4)
    return s


def _find_car_references_in_text(text):
    """
    Busca en el texto referencias a códigos de carta tipo ODA-BUF-CC-CAR-XXXX.
    Devuelve set de códigos normalizados (ODA-BUF-CC-CAR-0005, etc.) a los que se hace referencia.
    """
    if not text:
        return set()
    refs = set()
    # Coincidir ODA-BUF-CC-CAR-5, ODA-BUF-CC-CAR-0005, etc.
    for m in re.finditer(r"ODA-BUF-CC-CAR-0*(\d+)", text, re.IGNORECASE):
        refs.add("ODA-BUF-CC-CAR-" + m.group(1).zfill(4))
    return refs


def _build_respuesta_map():
    """
    Construye un mapa: código CAR referenciado -> extracto de la carta de respuesta.
    Solo documentos en carpetas de la contraparte ODATA: ODATA-ST01-F5-TTAL-PPT.
    En el extracto del adjunto se busca si referencian alguna CAR (ej. ODA-BUF-CC-CAR-0005).
    """
    from .models import Folder
    folders_odata = Folder.objects.filter(code__icontains="ODATA-ST01-F5-TTAL-PPT")
    docs_odata = (
        Document.objects
        .filter(folder__in=folders_odata, attachments__file__icontains="CAR")
        .distinct()
        .prefetch_related("attachments")
    )
    out = {}
    for d in docs_odata:
        for att in d.attachments.all():
            if "CAR" not in (att.file.name or "").upper():
                continue
            extract = (att.extracted_text or "") or (d.content_extract or "")
            for ref in _find_car_references_in_text(extract):
                if ref not in out:
                    out[ref] = extract
    return out


class CustomLoginView(LoginView):
    """Vista de login con template propio (misma lógica que mantto)."""
    template_name = 'login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url and next_url != '/':
            return next_url
        return '/'


def custom_logout(request):
    """Cerrar sesión y redirigir al login."""
    logout(request)
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('login')


@login_required
def dashboard(request):
    """Panel principal del proyecto (raíz). Solo usuarios autenticados."""
    return render(request, 'dashboard.html')


# ---------- Listado de documentos (CRUD: listar, ver, borrar) ----------

@login_required
@require_GET
def document_list(request):
    """Listado de documentos. Si piden JSON (AJAX), devuelve lista para búsqueda."""
    qs = Document.objects.select_related('project', 'company', 'process', 'doc_type', 'folder').order_by('-date', '-created_at')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(code__icontains=q) |
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(content_extract__icontains=q) |
            Q(attachments__extracted_text__icontains=q) |
            Q(project__code__icontains=q) |
            Q(company__code__icontains=q) |
            Q(process__code__icontains=q) |
            Q(doc_type__code__icontains=q)
        ).distinct()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        # Con búsqueda por texto, pre-cargar adjuntos y calcular hits (archivo + fragmentos de contexto)
        qs_json = qs.prefetch_related('attachments')[:500]
        docs = []
        for d in qs_json:
            hits = []
            if q and d.content_extract and (q.lower() in d.content_extract.lower()):
                snippets = extract_snippets(d.content_extract, q, context_words=10, max_snippets=5)
                file_name = d.file.name if d.file else 'Documento principal'
                hits.append({
                    'source': 'document',
                    'file_name': file_name.split('/')[-1] if file_name else 'Documento principal',
                    'file_url': d.file.url if d.file else None,
                    'snippets': snippets,
                })
            for att in d.attachments.all():
                if q and att.extracted_text and (q.lower() in att.extracted_text.lower()):
                    snippets = extract_snippets(att.extracted_text, q, context_words=10, max_snippets=5)
                    name = att.file.name.split('/')[-1] if att.file.name else 'Adjunto'
                    hits.append({
                        'source': 'attachment',
                        'file_name': name,
                        'file_url': att.file.url if att.file else None,
                        'snippets': snippets,
                    })
            docs.append({
                'id': d.id,
                'code': d.code,
                'title': d.title or '',
                'status': d.status,
                'status_display': d.get_status_display(),
                'date': d.date.isoformat() if d.date else '',
                'revision': d.revision or '',
                'project': d.project.code,
                'company': d.company.code,
                'process': d.process.code,
                'doc_type': d.doc_type.code,
                'file_url': d.file.url if d.file else None,
                'has_file': bool(d.file),
                'folder_id': d.folder_id,
                'folder_code': d.folder.code if d.folder else None,
                'hits': hits,
            })
        return JsonResponse({'documents': docs})
    return render(request, 'documents/document_list.html', {'document_list': qs[:100]})


@login_required
@require_GET
def document_detail(request, pk):
    """Detalle de un documento, archivo principal y adjuntos."""
    doc = get_object_or_404(
        Document.objects.select_related('project', 'company', 'process', 'doc_type', 'folder').prefetch_related('attachments'),
        pk=pk
    )
    return render(request, 'documents/document_detail.html', {'document': doc})


@login_required
@require_POST
def document_delete(request, pk):
    """Eliminar documento. Esperado por AJAX; devuelve JSON."""
    doc = get_object_or_404(Document, pk=pk)
    code = doc.code
    doc.delete()
    return JsonResponse({'success': True, 'message': f'Documento {code} eliminado.', 'id': int(pk)})


@login_required
@require_POST
def document_upload_attachments(request, pk):
    """Añadir varios archivos adjuntos a un documento. POST con input name='files' (múltiple)."""
    doc = get_object_or_404(Document, pk=pk)
    files = request.FILES.getlist('files')
    if not files:
        messages.warning(request, 'No se seleccionó ningún archivo.')
        return redirect('document_detail', pk=pk)
    created = 0
    for f in files:
        if not f.name:
            continue
        DocumentAttachment.objects.create(document=doc, file=f)
        created += 1
    if created:
        messages.success(request, f'Se añadieron {created} archivo(s) adjunto(s).')
    return redirect('document_detail', pk=pk)


# ---------- Carpetas ----------

@login_required
@require_GET
def folder_list(request):
    """Listado de carpetas (transmittals) con cantidad de documentos y archivos."""
    folders = (
        Folder.objects
        .annotate(
            document_count=Count('documents', distinct=True),
            folder_file_count=Count('folder_files', distinct=True),
            attachment_count=Count('documents__attachments', distinct=True),
        )
        .order_by('-date', '-created_at')[:500]
    )
    return render(request, 'documents/folder_list.html', {'folder_list': folders})


@login_required
@require_GET
def folder_detail(request, pk):
    """Detalle de una carpeta: documentos y archivos que contiene."""
    folder = get_object_or_404(
        Folder.objects.prefetch_related('documents', 'folder_files'),
        pk=pk
    )
    documents = folder.documents.select_related('project', 'company', 'process', 'doc_type').order_by('-date')
    folder_files = folder.folder_files.order_by('name')
    return render(request, 'documents/folder_detail.html', {
        'folder': folder,
        'documents': documents,
        'folder_files': folder_files,
    })


@login_required
@require_POST
def folder_upload_files(request, pk):
    """Añadir varios archivos a una carpeta. POST con input name='files' (múltiple)."""
    folder = get_object_or_404(Folder, pk=pk)
    files = request.FILES.getlist('files')
    if not files:
        messages.warning(request, 'No se seleccionó ningún archivo.')
        return redirect('folder_detail', pk=pk)
    created = 0
    for f in files:
        if not f.name:
            continue
        FolderFile.objects.create(folder=folder, name=f.name, file=f)
        created += 1
    if created:
        messages.success(request, f'Se añadieron {created} archivo(s) a la carpeta.')
    return redirect('folder_detail', pk=pk)


# ---------- Búsqueda unificada (nombre + contenido) ----------

@login_required
@require_GET
def search_unified_view(request):
    """Búsqueda por nombre/código y contenido extraído. Responde HTML o JSON."""
    q = request.GET.get('q', '').strip()
    result = search_unified(q, limit=200)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        docs = []
        for d in result['documents']:
            docs.append({
                'id': d.id,
                'code': d.code,
                'title': d.title or '',
                'status_display': d.get_status_display(),
                'date': d.date.isoformat() if d.date else '',
                'folder_id': d.folder_id,
                'folder_code': d.folder.code if d.folder else None,
                'file_url': d.file.url if d.file else None,
                'has_file': bool(d.file),
            })
        folders_data = [
            {'id': f.id, 'code': f.code, 'title': f.title or '', 'date': f.date.isoformat() if f.date else ''}
            for f in result['folders']
        ]
        files_data = [
            {
                'id': ff.id,
                'name': ff.name,
                'file_url': ff.file.url if ff.file else None,
                'folder_id': ff.folder_id,
                'folder_code': ff.folder.code if ff.folder else None,
            }
            for ff in result['folder_files']
        ]
        return JsonResponse({
            'documents': docs,
            'folders': folders_data,
            'folder_files': files_data,
        })

    return render(request, 'documents/search_unified.html', {
        'query': q,
        'documents': result['documents'],
        'folders': result['folders'],
        'folder_files': result['folder_files'],
    })


# ---------- Estatus Cartas (documentos transmittal ODATA-BUF-CM-TTAL-*; info en extracto de adjuntos) ----------

# Solo considerar "carta" si el nombre del archivo contiene CAR o CARTAS como palabra (no "carga", etc.)
_CARTA_FILENAME_RE = re.compile(r"(^|[-_./\\])(CAR|CARTAS)([-_./\\]|$)", re.IGNORECASE)


def _is_carta_filename(name):
    """True si el nombre de archivo contiene CAR o CARTAS como palabra completa (ej. -CAR- o cartas.pdf)."""
    if not name:
        return False
    return bool(_CARTA_FILENAME_RE.search(name))


def _get_cartas_status_rows():
    """Construye la lista de filas del listado Estatus Cartas (reutilizable para HTML y export)."""
    # CAR/CARTAS como palabra en la ruta del adjunto (evita que entren "carga", "carro", etc.)
    # Sin backslash en el patrón para compatibilidad con todos los backends de BD.
    carta_regex = r"(^|[-_./])(CAR|CARTAS)([-_./]|$)"
    docs = (
        Document.objects
        .filter(code__icontains="TTAL", attachments__file__iregex=carta_regex)
        .distinct()
        .select_related("project", "company", "process", "doc_type", "folder")
        .prefetch_related("attachments")
        .order_by("-date", "-created_at")[:500]
    )
    respuesta_map = _build_respuesta_map()
    rows = []
    for d in docs:
        for att in d.attachments.all():
            nombre_archivo = os.path.basename(att.file.name) if att.file else ""
            if not _is_carta_filename(nombre_archivo):
                continue
            requiere = _parse_requiere_respuesta(att.extracted_text)
            if not requiere:
                requiere = _parse_requiere_respuesta(d.content_extract)
            detalle = _parse_asunto(att.extracted_text)
            if not detalle:
                detalle = _parse_asunto(d.content_extract)
            if not detalle:
                detalle = d.description or ""
            enviado_a = _parse_atencion(att.extracted_text)
            if not enviado_a:
                enviado_a = _parse_atencion(d.content_extract)
            fecha_envio = _parse_fecha_envio(att.extracted_text)
            if fecha_envio is None:
                fecha_envio = _parse_fecha_envio(d.content_extract)
            if fecha_envio is None:
                fecha_envio = d.date
            fecha_respuesta = None
            respuesta = ""
            if requiere == "SI":
                car_key = _normalize_car_code(nombre_archivo)
                if car_key and car_key in respuesta_map:
                    extract_respuesta = respuesta_map[car_key]
                    fecha_respuesta = _parse_fecha_envio(extract_respuesta)
                    respuesta = _parse_saluda_atentamente(extract_respuesta)
                    if not respuesta:
                        respuesta = _parse_atencion(extract_respuesta)
            rows.append({
                "document": d,
                "transmittal": d.folder.code if d.folder else "",
                "transmittal_title": (d.folder.title if d.folder else "") or "",
                "tipo": "CAR",
                "descripcion": d.title or d.description or nombre_archivo or "",
                "fecha_envio": fecha_envio,
                "responsable": d.company.name or d.company.code,
                "documento_archivo": nombre_archivo or d.code,
                "estado": d.get_status_display(),
                "detalle": detalle,
                "enviado_a": enviado_a,
                "requiere_respuesta": requiere,
                "respuesta": respuesta,
                "fecha_respuesta": fecha_respuesta,
                "para": "",
                "file_url": att.file.url if att.file else None,
            })
    return rows


def _cartas_status_excel_response(rows):
    """Genera HttpResponse con el listado en Excel. Nombre: Estatus-Cartas-al-DD-MM-YYYY.xlsx"""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    fecha_str = timezone.now().strftime("%d-%m-%Y")
    filename = f"Estatus-Cartas-al-{fecha_str}.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Estatus Cartas"
    headers = [
        "Transmittal", "Tipo", "Descripción", "Fecha envío (emisor)", "Responsable",
        "Documento - Archivo", "Estado", "Detalle", "Enviado a", "Requiere respuesta?",
        "Respuesta", "Fecha respuesta", "Para", "Link",
    ]
    ws.append(headers)
    for h in range(1, len(headers) + 1):
        ws.cell(row=1, column=h).font = Font(bold=True)
    for row in rows:
        fe = row.get("fecha_envio")
        fe_str = fe.strftime("%d/%m/%Y") if hasattr(fe, "strftime") else str(fe or "")
        fr = row.get("fecha_respuesta")
        fr_str = fr.strftime("%d/%m/%Y") if fr and hasattr(fr, "strftime") else ""
        trans = (row.get("transmittal") or "") + (" — " + (row.get("transmittal_title") or "") if row.get("transmittal_title") else "")
        ws.append([
            trans,
            row.get("tipo") or "",
            row.get("descripcion") or "",
            fe_str,
            row.get("responsable") or "",
            row.get("documento_archivo") or "",
            row.get("estado") or "",
            row.get("detalle") or "",
            row.get("enviado_a") or "",
            row.get("requiere_respuesta") or "",
            row.get("respuesta") or "",
            fr_str,
            row.get("para") or "",
            row.get("file_url") or "",
        ])
    from io import BytesIO
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    response = HttpResponse(buf.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _cartas_status_pdf_response(rows, inline=False):
    """Genera HttpResponse con el listado en PDF. Nombre: Estatus-Cartas-al-DD-MM-YYYY.pdf
    Si inline=True, Content-Disposition: inline para abrir en pestaña y guardar desde el visor."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    from reportlab.lib.units import cm
    from io import BytesIO
    fecha_str = timezone.now().strftime("%d-%m-%Y")
    filename = f"Estatus-Cartas-al-{fecha_str}.pdf"
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=1*cm, leftMargin=1*cm, topMargin=1.5*cm, bottomMargin=1*cm)
    headers = [
        "Transmittal", "Tipo", "Descripción", "F.Envio", "Responsable", "Documento",
        "Estado", "Detalle", "Enviado a", "Req.Resp", "Respuesta", "F.Resp", "Para", "Link",
    ]
    data = [headers]
    for row in rows:
        fe = row.get("fecha_envio")
        fe_str = fe.strftime("%d/%m/%Y") if hasattr(fe, "strftime") else str(fe or "")
        fr = row.get("fecha_respuesta")
        fr_str = fr.strftime("%d/%m/%Y") if fr and hasattr(fr, "strftime") else ""
        trans = (row.get("transmittal") or "") + (" " + (row.get("transmittal_title") or "")[:20] if row.get("transmittal_title") else "")
        data.append([
            trans[:20], row.get("tipo") or "", (row.get("descripcion") or "")[:25], fe_str,
            (row.get("responsable") or "")[:15], (row.get("documento_archivo") or "")[:18],
            row.get("estado") or "", (row.get("detalle") or "")[:20], (row.get("enviado_a") or "")[:15],
            row.get("requiere_respuesta") or "", (row.get("respuesta") or "")[:15], fr_str,
            row.get("para") or "", "",
        ])
    t = Table(data, colWidths=[2*cm, 1.2*cm, 3*cm, 1.8*cm, 2.2*cm, 2.5*cm, 1.5*cm, 2.5*cm, 2.2*cm, 1*cm, 2.2*cm, 1.5*cm, 1.5*cm, 1*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("FONTSIZE", (0, 1), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#E7E6E6")]),
    ]))
    doc.build([t])
    buf.seek(0)
    response = HttpResponse(buf.read(), content_type="application/pdf")
    if inline:
        response["Content-Disposition"] = f'inline; filename="{filename}"'
    else:
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_GET
def cartas_status(request):
    """
    Lista solo cartas: documentos transmittal (TTAL) que tengan al menos un adjunto tipo CAR.
    Si ?format=excel o ?format=pdf, devuelve el archivo para descarga (Estatus-Cartas-al-DD-MM-YYYY).
    """
    rows = _get_cartas_status_rows()

    if request.GET.get("format") == "excel":
        return _cartas_status_excel_response(rows)
    if request.GET.get("format") == "pdf":
        open_inline = request.GET.get("open") == "1"
        return _cartas_status_pdf_response(rows, inline=open_inline)

    n_si = sum(1 for r in rows if r.get("requiere_respuesta") == "SI")
    n_no = sum(1 for r in rows if r.get("requiere_respuesta") == "NO")
    n_vacio = sum(1 for r in rows if not r.get("requiere_respuesta"))
    print(f"[cartas_status] RESUMEN: filas(adjuntos)={len(rows)} | SI={n_si} | NO={n_no} | vacío={n_vacio}")

    return render(request, "documents/cartas_status.html", {"rows": rows})
