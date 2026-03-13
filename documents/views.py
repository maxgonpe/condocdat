from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
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
from .search_backend import search_unified, _normalize_terms
from .snippets import extract_snippets, extract_snippets_multi_term


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
    Extrae del extracto (carta) lo que está después de «Asunto:» y antes de «Atención:».
    Puede ser varias líneas. Se usa en Estatus Cartas para la columna Asunto.
    """
    if not content_extract or not isinstance(content_extract, str):
        return ""
    t = content_extract
    tu = t.upper()
    idx = tu.find("ASUNTO:")
    if idx < 0:
        return ""
    start = idx + len("ASUNTO:")
    while start < len(t) and t[start] in " :\t":
        start += 1
    if start >= len(t):
        return ""
    # Cortar en "Atención:" o "Atencion:"
    end_pos = len(t)
    for mark in ("ATENCIÓN:", "ATENCION:"):
        pos = tu.find(mark, start)
        if pos >= 0:
            end_pos = min(end_pos, pos)
    block = t[start:end_pos].strip()
    return block[:500] if len(block) > 500 else block


def _parse_enviado_a_despues_senor(content_extract):
    """
    Extrae lo que está después de «Señor» (o «Señor») y antes de «ODATA» en el extracto.
    Ejemplo: «Señor\nPablo Bravo\nODATA CHILE SPA» → «Pablo Bravo».
    """
    if not content_extract or not isinstance(content_extract, str):
        return ""
    t = content_extract
    tu = t.upper()
    idx = tu.find("SEÑOR")
    if idx < 0:
        idx = tu.find("SENOR")
    if idx < 0:
        return ""
    start = idx + (5 if "SEÑOR" in t[idx : idx + 6].upper() else 5)
    while start < len(t) and (t[start] in " \n\r\t:" or t[start].isspace()):
        start += 1
    if start >= len(t):
        return ""
    pos_odata = tu.find("ODATA", start)
    if pos_odata >= 0:
        block = t[start:pos_odata].strip()
    else:
        block = t[start:].strip()
    return block[:300] if len(block) > 300 else block


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


def _log_rows_stats(rows):
    """A partir de filas de logs (referencia, descripcion, documento_archivo), devuelve conteos por tipo."""
    total = len(rows)
    ultimo_transmittal = (rows[0].get("transmittal") or "").strip() if rows else ""
    text_key = lambda r: " ".join([
        str(r.get("referencia") or ""),
        str(r.get("descripcion") or ""),
        str(r.get("documento_archivo") or ""),
    ]).lower()
    acreditaciones = 0
    acreditacion_personal = 0
    acreditacion_equipos = 0
    procedimientos = 0
    for r in rows:
        t = text_key(r)
        if "acreditacion" in t or "acreditación" in t:
            acreditaciones += 1
            if "personal" in t or "trabajador" in t or "trabajadores" in t:
                acreditacion_personal += 1
            if "equipo" in t or "equipos" in t:
                acreditacion_equipos += 1
        if "procedimiento" in t:
            procedimientos += 1
    return {
        "total": total,
        "ultimo_transmittal": ultimo_transmittal[:50] if ultimo_transmittal else "—",
        "acreditaciones": acreditaciones,
        "acreditacion_personal": acreditacion_personal,
        "acreditacion_equipos": acreditacion_equipos,
        "procedimientos": procedimientos,
    }


@login_required
def pizarra(request):
    """Pizarra: sección por defecto al abrir el sitio. Aquí irán datos de logs, cartas y estadísticas."""
    rows_cartas = _get_cartas_status_rows()
    total = len(rows_cartas)
    propamat_a_odata = sum(1 for r in rows_cartas if "ODATA-ST01-F5-TTAL-PPT" in (r.get("transmittal") or ""))
    odata_a_propamat = sum(1 for r in rows_cartas if "TRN" in (r.get("transmittal") or "") and "ODATA-ST01-F5-TTAL-PPT" not in (r.get("transmittal") or ""))
    requiere_respuesta = sum(1 for r in rows_cartas if r.get("requiere_respuesta") == "SI")
    no_respondidas = sum(1 for r in rows_cartas if r.get("requiere_respuesta") == "SI" and not (r.get("respuesta") or "").strip())
    si_respondidas = sum(1 for r in rows_cartas if r.get("requiere_respuesta") == "SI" and (r.get("respuesta") or "").strip())

    rows_propamat = _get_logs_folder_rows("TRN")
    rows_odata = _get_logs_folder_rows("Odata")
    logs_propamat = _log_rows_stats(rows_propamat)
    logs_odata = _log_rows_stats(rows_odata)

    return render(request, "pizarra.html", {
        "cartas_total": total,
        "cartas_propamat_a_odata": propamat_a_odata,
        "cartas_odata_a_propamat": odata_a_propamat,
        "cartas_requieren_respuesta": requiere_respuesta,
        "cartas_no_respondidas": no_respondidas,
        "cartas_si_respondidas": si_respondidas,
        "logs_propamat": logs_propamat,
        "logs_odata": logs_odata,
    })


@login_required
def dashboard(request):
    """Panel principal del proyecto. Solo usuarios autenticados."""
    return render(request, "dashboard.html")


# ---------- Listado de documentos (CRUD: listar, ver, borrar) ----------

@login_required
@require_GET
def document_list(request):
    """Listado de documentos. Si piden JSON (AJAX), usa búsqueda unificada (FTS) y devuelve lista con hits/snippets."""
    q = request.GET.get('q', '').strip()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        # Búsqueda unificada (PostgreSQL FTS) cuando hay consulta; si no hay q, listar todos
        if q:
            result = search_unified(q, limit=500)
            docs_for_list = result['documents']
        else:
            docs_for_list = list(
                Document.objects.select_related('project', 'company', 'process', 'doc_type', 'folder')
                .order_by('-date', '-created_at')[:500]
            )
        doc_map = {d.pk: d for d in docs_for_list}
        qs_json = Document.objects.filter(pk__in=[d.pk for d in docs_for_list]).prefetch_related('attachments')
        terms = _normalize_terms(q)
        use_multi = len(terms) > 1
        docs = []
        for d in qs_json:
            hits = []
            if q and d.content_extract:
                text_lower = d.content_extract.lower()
                if use_multi and all(t.lower() in text_lower for t in terms):
                    snippets = extract_snippets_multi_term(d.content_extract, terms, context_words=10, max_snippets=5)
                elif not use_multi and q.lower() in text_lower:
                    snippets = extract_snippets(d.content_extract, q, context_words=10, max_snippets=5)
                else:
                    snippets = []
                if snippets:
                    file_name = d.file.name if d.file else 'Documento principal'
                    hits.append({
                        'source': 'document',
                        'file_name': file_name.split('/')[-1] if file_name else 'Documento principal',
                        'file_url': d.file.url if d.file else None,
                        'snippets': snippets,
                    })
            for att in d.attachments.all():
                if q and att.extracted_text:
                    text_lower = att.extracted_text.lower()
                    if use_multi and all(t.lower() in text_lower for t in terms):
                        snippets = extract_snippets_multi_term(att.extracted_text, terms, context_words=10, max_snippets=5)
                    elif not use_multi and q.lower() in text_lower:
                        snippets = extract_snippets(att.extracted_text, q, context_words=10, max_snippets=5)
                    else:
                        snippets = []
                    if snippets:
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
    # HTML: listado inicial (sin búsqueda)
    qs = Document.objects.select_related('project', 'company', 'process', 'doc_type', 'folder').order_by('-date', '-created_at')
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
    """Búsqueda por nombre/código y contenido. Responde HTML o JSON. Documentos y archivos de carpeta incluyen hits con snippets (igual lógica que listado de documentos)."""
    q = request.GET.get('q', '').strip()
    result = search_unified(q, limit=200)
    terms = _normalize_terms(q)
    use_multi = len(terms) > 1

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        # Documentos: mismo payload que document_list (con hits/snippets)
        doc_ids = [d.id for d in result['documents']]
        qs_docs = Document.objects.filter(pk__in=doc_ids).prefetch_related('attachments').select_related('project', 'company', 'process', 'doc_type', 'folder')
        docs = []
        for d in qs_docs:
            hits = []
            if q and d.content_extract:
                text_lower = d.content_extract.lower()
                if use_multi and all(t.lower() in text_lower for t in terms):
                    snippets = extract_snippets_multi_term(d.content_extract, terms, context_words=10, max_snippets=5)
                elif not use_multi and q.lower() in text_lower:
                    snippets = extract_snippets(d.content_extract, q, context_words=10, max_snippets=5)
                else:
                    snippets = []
                if snippets:
                    file_name = d.file.name if d.file else 'Documento principal'
                    hits.append({
                        'source': 'document',
                        'file_name': file_name.split('/')[-1] if file_name else 'Documento principal',
                        'file_url': d.file.url if d.file else None,
                        'snippets': snippets,
                    })
            for att in d.attachments.all():
                if q and att.extracted_text:
                    text_lower = att.extracted_text.lower()
                    if use_multi and all(t.lower() in text_lower for t in terms):
                        snippets = extract_snippets_multi_term(att.extracted_text, terms, context_words=10, max_snippets=5)
                    elif not use_multi and q.lower() in text_lower:
                        snippets = extract_snippets(att.extracted_text, q, context_words=10, max_snippets=5)
                    else:
                        snippets = []
                    if snippets:
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
                'status_display': d.get_status_display(),
                'date': d.date.isoformat() if d.date else '',
                'folder_id': d.folder_id,
                'folder_code': d.folder.code if d.folder else None,
                'file_url': d.file.url if d.file else None,
                'has_file': bool(d.file),
                'hits': hits,
            })
        folders_data = [
            {'id': f.id, 'code': f.code, 'title': f.title or '', 'date': f.date.isoformat() if f.date else ''}
            for f in result['folders']
        ]
        files_data = []
        for ff in result['folder_files']:
            hits = []
            if q and ff.extracted_text:
                text_lower = ff.extracted_text.lower()
                if use_multi and all(t.lower() in text_lower for t in terms):
                    snippets = extract_snippets_multi_term(ff.extracted_text, terms, context_words=10, max_snippets=5)
                elif not use_multi and q.lower() in text_lower:
                    snippets = extract_snippets(ff.extracted_text, q, context_words=10, max_snippets=5)
                else:
                    snippets = []
                if snippets:
                    hits.append({
                        'source': 'folder_file',
                        'file_name': ff.name,
                        'file_url': ff.file.url if ff.file else None,
                        'snippets': snippets,
                    })
            files_data.append({
                'id': ff.id,
                'name': ff.name,
                'file_url': ff.file.url if ff.file else None,
                'folder_id': ff.folder_id,
                'folder_code': ff.folder.code if ff.folder else None,
                'folder_title': (ff.folder.title or '') if ff.folder else '',
                'hits': hits,
            })
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
        # Primer adjunto del documento (para extraer "enviado a" cuando el nombre no comienza con ODA)
        first_att = d.attachments.order_by("pk").first()
        first_extract = (first_att.extracted_text if first_att and first_att.extracted_text else None) or d.content_extract or ""
        for att in d.attachments.all():
            nombre_archivo = os.path.basename(att.file.name) if att.file else ""
            if not _is_carta_filename(nombre_archivo):
                continue
            # Si el nombre del archivo NO comienza con ODA: es otro formato → Requiere respuesta = NO, Enviado a = después de Señor hasta ODATA
            comienza_con_oda = (nombre_archivo or "").upper().startswith("ODA")
            if not comienza_con_oda:
                requiere = "NO"
                enviado_a = _parse_enviado_a_despues_senor(first_extract)
                if not enviado_a:
                    enviado_a = _parse_atencion(first_extract)
            else:
                requiere = _parse_requiere_respuesta(att.extracted_text)
                if not requiere:
                    requiere = _parse_requiere_respuesta(d.content_extract)
                enviado_a = _parse_atencion(att.extracted_text)
                if not enviado_a:
                    enviado_a = _parse_atencion(d.content_extract)
            detalle = _parse_asunto(att.extracted_text)
            if not detalle:
                detalle = _parse_asunto(d.content_extract)
            if not detalle:
                detalle = d.description or ""
            asunto = _parse_asunto(att.extracted_text)
            if not asunto:
                asunto = _parse_asunto(d.content_extract)
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
                "asunto": asunto or "",
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
    # Orden: fecha más reciente primero, luego por ID del registro (mayor a menor)
    def _sort_key(r):
        fe = r.get("fecha_envio") or date.min
        ord_val = fe.toordinal() if hasattr(fe, "toordinal") else 0
        doc = r.get("document")
        pk = doc.pk if doc is not None else 0
        return (-ord_val, -pk)
    rows.sort(key=_sort_key)
    return rows


def _cartas_status_excel_response(rows, list_name=None):
    """Genera HttpResponse con el listado en Excel.
    Texto con ajuste de línea (wrap) en las celdas para no truncar. list_name: nombre para archivo/hoja."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment
    from io import BytesIO
    fecha_str = timezone.now().strftime("%d-%m-%Y")
    if list_name:
        safe_name = list_name.replace(" ", "-").replace("/", "-")[:40]
        filename = f"{safe_name}-{fecha_str}.xlsx"
        sheet_title = safe_name[:31]
    else:
        filename = f"Estatus-Cartas-al-{fecha_str}.xlsx"
        sheet_title = "Estatus Cartas"
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title
    headers = [
        "Transmittal", "Asunto", "Fecha envío (emisor)", "Responsable", "Documento - Archivo",
        "Estado", "Detalle", "Enviado a", "Requiere respuesta?", "Respuesta", "Fecha respuesta",
    ]
    ws.append(headers)
    for h in range(1, len(headers) + 1):
        c = ws.cell(row=1, column=h)
        c.font = Font(bold=True)
        c.alignment = Alignment(wrap_text=True, vertical="top")
    for row in rows:
        fe = row.get("fecha_envio")
        fe_str = fe.strftime("%d/%m/%Y") if hasattr(fe, "strftime") else str(fe or "")
        fr = row.get("fecha_respuesta")
        fr_str = fr.strftime("%d/%m/%Y") if fr and hasattr(fr, "strftime") else ""
        trans = (row.get("transmittal") or "")[:25]
        ws.append([
            trans,
            row.get("asunto") or "",
            fe_str,
            row.get("responsable") or "",
            row.get("documento_archivo") or "",
            row.get("estado") or "",
            row.get("detalle") or "",
            row.get("enviado_a") or "",
            row.get("requiere_respuesta") or "",
            row.get("respuesta") or "",
            fr_str,
        ])
    # Ajuste de texto en todas las celdas de datos (sin truncar; añade líneas)
    wrap_align = Alignment(wrap_text=True, vertical="top")
    for r in range(1, ws.max_row + 1):
        for c in range(1, len(headers) + 1):
            ws.cell(row=r, column=c).alignment = wrap_align
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    response = HttpResponse(buf.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _cartas_status_pdf_response(rows, inline=False, list_name=None):
    """Genera HttpResponse con el listado en PDF.
    Celdas con Paragraph para que el texto se ajuste en varias líneas sin truncar."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.units import cm
    from io import BytesIO
    fecha_str = timezone.now().strftime("%d-%m-%Y")
    if list_name:
        safe_name = list_name.replace(" ", "-").replace("/", "-")[:40]
        filename = f"{safe_name}-{fecha_str}.pdf"
        pagesize = A4
    else:
        filename = f"Estatus-Cartas-al-{fecha_str}.pdf"
        # Horizontal explícito (ancho, alto) = (A4[1], A4[0]) para evitar diferencias por versión de ReportLab
        pagesize = (A4[1], A4[0])
    buf = BytesIO()
    left_right_margin = 0.5 * cm
    doc = SimpleDocTemplate(buf, pagesize=pagesize, rightMargin=left_right_margin, leftMargin=left_right_margin, topMargin=1.2*cm, bottomMargin=1*cm)
    styles = getSampleStyleSheet()
    para_cell = ParagraphStyle("Cell", parent=styles["Normal"], fontName="Helvetica", fontSize=6, leading=7, leftIndent=0, rightIndent=0, spaceBefore=0, spaceAfter=0)
    para_header = ParagraphStyle("Header", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7, leading=8)

    def safe_para(text, style=para_cell):
        if text is None:
            text = ""
        s = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
        return Paragraph(s or " ", style)

    headers = [
        "Transmittal", "Asunto", "F.Envio", "Responsable", "Documento - Archivo",
        "Estado", "Detalle", "Enviado a", "Req.Resp", "Respuesta", "F.Resp",
    ]
    data = [[safe_para(h, para_header) for h in headers]]
    for row in rows:
        fe = row.get("fecha_envio")
        fe_str = fe.strftime("%d/%m/%Y") if hasattr(fe, "strftime") else str(fe or "")
        fr = row.get("fecha_respuesta")
        fr_str = fr.strftime("%d/%m/%Y") if fr and hasattr(fr, "strftime") else ""
        data.append([
            safe_para((row.get("transmittal") or "")[:25]),
            safe_para(row.get("asunto") or ""),
            safe_para(fe_str),
            safe_para(row.get("responsable") or ""),
            safe_para(row.get("documento_archivo") or ""),
            safe_para(row.get("estado") or ""),
            safe_para(row.get("detalle") or ""),
            safe_para(row.get("enviado_a") or ""),
            safe_para(row.get("requiere_respuesta") or ""),
            safe_para(row.get("respuesta") or ""),
            safe_para(fr_str),
        ])
    col_widths = [2.8*cm, 5*cm, 1.6*cm, 2.8*cm, 3.2*cm, 1.5*cm, 3.2*cm, 2.5*cm, 1.2*cm, 2.8*cm, 1.6*cm]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
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


def _extract_referencia_from_text(text):
    """
    Extrae el texto que sigue a 'Referencia:' en el extracto.
    Incluye todo el párrafo (varias líneas) hasta un doble salto de línea,
    para capturar por ejemplo "Detalle documentos Adjuntos:" y las líneas siguientes
    (ej. "- Workshop Compilado comentarios"). Máximo 2000 caracteres.
    """
    if not text or not isinstance(text, str):
        return ""
    t = text
    ref_lower = "referencia"
    idx = t.lower().find(ref_lower)
    if idx < 0:
        return ""
    start = idx + len(ref_lower)
    while start < len(t) and (t[start] == ":" or t[start].isspace()):
        start += 1
    rest = t[start:].strip()
    # Tomar todo el párrafo hasta doble salto (no cortar en la primera línea)
    for sep in ("\n\n", "\r\n\r\n"):
        if sep in rest:
            rest = rest.split(sep)[0].strip()
            break
    return rest[:2000] if len(rest) > 2000 else rest


def _extract_unidad_emisora_from_text(text):
    """
    Extrae el texto que sigue a 'Unidad emisora' en el extracto (ej. "BUFFER Pablo Andrés Soto Calderón").
    Toma una línea o hasta doble salto. Máximo 500 caracteres.
    """
    if not text or not isinstance(text, str):
        return ""
    t = text
    label = "unidad emisora"
    idx = t.lower().find(label)
    if idx < 0:
        return ""
    start = idx + len(label)
    while start < len(t) and (t[start] == ":" or t[start].isspace()):
        start += 1
    rest = t[start:].strip()
    for sep in ("\n\n", "\r\n\r\n", "\n", "\r\n"):
        if sep in rest:
            rest = rest.split(sep)[0].strip()
            break
    return rest[:500] if len(rest) > 500 else rest


def _get_main_extract_for_folder(folder):
    """
    Devuelve el extracto donde se buscan Referencia, Responsable y Documento-Archivo en los logs.
    Ese texto está en el DOCUMENTO PRINCIPAL de la carpeta (content_extract), no en los PDF adjuntos.
    Orden: primer documento con content_extract (documento maestro, antes de los adjuntos),
    luego primer archivo de carpeta (FolderFile). No se usan extractos de adjuntos.
    """
    for doc in folder.documents.all():
        if doc.content_extract and doc.content_extract.strip():
            return doc.content_extract
    for ff in folder.folder_files.all():
        if ff.extracted_text and ff.extracted_text.strip():
            return ff.extracted_text
    return ""


def _extract_detalle_documentos_adjuntos_from_text(text):
    """
    Para listado TRN (Propamat→Odata): extrae el fragmento entre 'Detalle documentos Adjuntos:'
    y 'Destinatario:'. Se usa la ÚLTIMA aparición de esa etiqueta antes de 'Destinatario'
    para evitar tomar una tabla anterior (p. ej. que suelte "Rev.00"). Solo se incluyen
    líneas que parecen nombres de documentos; se deja de incluir al detectar cabeceras
    de tabla o secciones (Unidad revisora/emisora).
    """
    if not text or not isinstance(text, str):
        return ""
    t = text
    t_lower = t.lower()
    pos_dest = t_lower.find("destinatario")
    if pos_dest < 0:
        pos_dest = len(t)
    # Última aparición de "detalle documentos adjuntos" ANTES de "Destinatario"
    label = "detalle documentos adjuntos"
    last_start = -1
    pos = 0
    while pos < pos_dest:
        idx = t_lower.find(label, pos)
        if idx < 0 or idx >= pos_dest:
            break
        start = idx + len(label)
        while start < len(t) and (t[start] in ":\n\r\t" or t[start].isspace()):
            start += 1
        last_start = start
        pos = idx + 1
    if last_start < 0:
        return ""
    block = t[last_start:pos_dest].strip()

    # Dejar de añadir líneas al llegar a cabeceras de tabla o siguiente sección
    stop_markers = (
        "ítem",
        "n° documento",
        "nº documento",
        "rev.",
        "título / descripción documento",
        "titulo / descripcion documento",
        "comentarios:",
        "unidad revisora",
        "unidad emisora",
    )

    def should_stop(line):
        low = line.strip().lower()
        if not low:
            return True
        for m in stop_markers:
            if low == m:
                return True
            if (m.endswith(":") or m.endswith(" ")) and low.startswith(m):
                return True
            if not m.endswith(":") and (low.startswith(m + " ") or low.startswith(m + ":")):
                return True
        if low.isdigit():
            return True
        if len(low) <= 4 and low.startswith("-") and low[1:].replace(" ", "").isdigit():
            return True
        # No incluir líneas que son solo revisión (Rev.00, Rev.01, N/A)
        if re.match(r"^rev\.?\s*\d*$", low) or low == "n/a":
            return True
        return False

    lines = []
    for ln in block.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if should_stop(ln):
            break
        lines.append(ln)
    if not lines:
        return ""
    formatted = "\n".join("• " + ln for ln in lines)
    return formatted[:1500] if len(formatted) > 1500 else formatted


def _extract_after_referencia_from_text(text):
    """
    Extrae y lista lo que está después de "Referencia:" en el extracto.
    Se corta al encontrar "Detalle documentos Adjuntos:" o "Destinatario:".
    Ejemplo: después de "Referencia:" puede venir texto y luego líneas como
    "Flujo Financiero_Histograma DC ODATA R0", "Listado de equipos criticos...", etc.
    """
    if not text or not isinstance(text, str):
        return ""
    t_lower = text.lower()
    idx = t_lower.find("referencia:")
    if idx < 0:
        return ""
    start = idx + len("referencia:")
    while start < len(text) and (text[start] in ":\n\r\t" or text[start].isspace()):
        start += 1
    rest = text[start:]
    # Cortar en la siguiente sección
    for stop in ("detalle documentos adjuntos", "destinatario"):
        pos = rest.lower().find(stop)
        if pos >= 0:
            rest = rest[:pos]
            break
    rest = rest.strip()
    lines = [ln.strip() for ln in rest.splitlines() if ln.strip()]
    if not lines:
        return ""
    return "\n".join("• " + ln for ln in lines)[:1500]


def _extract_detalle_documentos_adjuntos_odata_from_text(text):
    """
    Extrae para logs Odata→Propamat el bloque entre "(4)" y "Comentarios:" del extracto
    del documento maestro (content_extract). Ese bloque son las filas de la tabla, p. ej.:
      Ítem Rev. (1) (2) (3) (4)
      1 N/A OT 11 VI 1
      2 N/A OT 11 VI 1
      3 N/A OT 11 VI 1
      4 N/A OT 11 VI 1
      Comentarios:
    Se devuelve la lista de líneas después de "(4)" y antes de "Comentarios:" (con viñeta).
    """
    if not text or not isinstance(text, str):
        return ""
    idx_coment = text.lower().find("comentarios:")
    if idx_coment < 0:
        return ""
    before_comentarios = text[:idx_coment]
    # Última aparición de "(4)" (cabecera suele ser "Ítem Rev. (1) (2) (3) (4)")
    marker = "(4)"
    last_pos = -1
    pos = 0
    while True:
        found = before_comentarios.find(marker, pos)
        if found < 0:
            break
        last_pos = found
        pos = found + 1
    if last_pos < 0:
        return ""
    # Justo después de "(4)" hasta Comentarios: = filas de la tabla (1 N/A OT 11 VI 1, etc.)
    start = last_pos + len(marker)
    rest = before_comentarios[start:].strip()
    # No incluir líneas que ya sean la leyenda (por si el orden del PDF variara)
    stop_markers = (
        "(1) tipo", "(2) identificación", "(3) tipo de copia", "(4) número de copias",
        "unidad revisora", "unidad emisora", "document type", "submission identification",
        "copy type", "number of copies",
    )
    lines_out = []
    for ln in rest.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        low = ln.lower()
        if any(low.startswith(m) for m in stop_markers):
            break
        lines_out.append(ln)
    if not lines_out:
        return ""
    formatted = "\n".join("• " + ln for ln in lines_out)
    return formatted[:1500] if len(formatted) > 1500 else formatted


def _extract_titulo_descripcion_documento_from_text(text):
    """
    Extrae el texto que sigue al encabezado 'Título / Descripción Documento' en el extracto.
    Ese contenido suele ser la descripción del documento en la tabla del PDF.
    Si la tabla está como imagen en el PDF, el extracto no lo contendrá (limitación de la capa de texto).
    """
    if not text or not isinstance(text, str):
        return ""
    t = text
    # Variantes del encabezado (con/sin tilde, con espacio o barra)
    for label in ("título / descripción documento", "titulo / descripcion documento",
                  "título/descripción documento", "titulo/descripcion documento",
                  "título - descripción documento", "descripción documento"):
        idx = t.lower().find(label)
        if idx >= 0:
            start = idx + len(label)
            while start < len(t) and (t[start] in ":-\n\r\t" or t[start].isspace()):
                start += 1
            rest = t[start:].strip()
            # Tomar hasta doble salto o hasta otra cabecera típica
            for sep in ("\n\n", "\r\n\r\n"):
                if sep in rest:
                    rest = rest.split(sep)[0].strip()
                    break
            # Una sola línea si hay muchas (primera línea suele ser la descripción)
            if "\n" in rest:
                rest = rest.split("\n")[0].strip()
            return rest[:500] if len(rest) > 500 else rest
    return ""


def _get_logs_folder_rows(code_filter, order_by="-date", then_by="-code"):
    """
    Construye filas para los listados de logs por tipo de carpeta.
    Misma lógica para ambos: filtrar carpetas por código, tomar el primer extracto del documento
    asociado a la carpeta y extraer de ahí Referencia, Responsable y Documento-Archivo.

    - Odata a Propamat (funciona 100%): code_filter 'TRN' → code__icontains='TRN'.
    - Propamat a Odata: code_filter 'Odata' → carpetas con formato ODATA-ST01-F5-TTAL-PPT-?????
      (code__icontains='ODATA-ST01-F5-TTAL-PPT'); el documento asociado tiene ese mismo formato
      y ahí está el primer extracto con la lista de archivos (entre (4) y Comentarios:).
    """
    if code_filter and code_filter.lower() == "odata":
        folders = (
            Folder.objects.filter(code__icontains="ODATA-ST01-F5-TTAL-PPT")
            .prefetch_related("folder_files", "documents__attachments")
            .order_by(order_by, then_by)[:500]
        )
    else:
        folders = (
            Folder.objects.filter(code__icontains=code_filter)
            .prefetch_related("folder_files", "documents__attachments")
            .order_by(order_by, then_by)[:500]
        )
    rows = []
    is_odata_list = "odata" in (code_filter or "").lower()
    for f in folders:
        main_extract = _get_main_extract_for_folder(f)
        if is_odata_list:
            # Propamat a Odata: listar lo que está después de "Referencia:" hasta Detalle/Destinatario
            doc_arch = _extract_after_referencia_from_text(main_extract)
            if not doc_arch:
                doc_arch = _extract_detalle_documentos_adjuntos_odata_from_text(main_extract)
        else:
            doc_arch = _extract_detalle_documentos_adjuntos_from_text(main_extract)
        if not doc_arch:
            doc_arch = _extract_titulo_descripcion_documento_from_text(main_extract)
            # No mostrar fallback si es solo revisión (Rev.00) o celda de tabla
            if doc_arch and not is_odata_list and re.match(r"^Rev\.?\s*\d*$", doc_arch.strip(), re.IGNORECASE):
                doc_arch = ""
        rows.append({
            "folder": f,
            "document": None,
            "transmittal": f.code,
            "transmittal_title": f.title or "",
            "descripcion": f.description or "",
            "referencia": _extract_referencia_from_text(main_extract),
            "fecha_envio": f.date,
            "responsable": _extract_unidad_emisora_from_text(main_extract),
            "documento_archivo": doc_arch,
            "estado": "",
            "detalle": "",
            "enviado_a": "",
            "requiere_respuesta": "",
            "respuesta": "",
            "fecha_respuesta": None,
            "para": "",
            "file_url": None,
        })
    return rows


def _format_log_row_for_export(row, request=None):
    """
    Formatea una fila de log con la misma lógica que los templates:
    Transmittal (+ título), Especialidad, Referencia, Fecha, Responsable, Documento-Archivo, Estado, Link.
    """
    trans = (row.get("transmittal") or "")
    if row.get("transmittal_title"):
        trans = trans + " — " + (row.get("transmittal_title") or "")
    fe = row.get("fecha_envio")
    fecha_str = fe.strftime("%d/%m/%Y") if fe and hasattr(fe, "strftime") else "—"
    link = "Ver"
    if request:
        if row.get("folder"):
            link = request.build_absolute_uri(reverse("folder_detail", args=[row["folder"].pk]))
        elif row.get("document"):
            link = request.build_absolute_uri(reverse("document_detail", args=[row["document"].pk]))
    return {
        "transmittal": trans,
        "especialidad": (row.get("descripcion") or "").strip(),
        "referencia": (row.get("referencia") or "—").strip(),
        "fecha_envio": fecha_str,
        "responsable": (row.get("responsable") or "—").strip(),
        "documento_archivo": (row.get("documento_archivo") or "—").strip(),
        "estado": (row.get("estado") or "—").strip(),
        "link": link,
    }


def _logs_excel_response(rows, list_name, request=None):
    """
    Excel para listados de logs (Propamat↔Odata) con las mismas 8 columnas que el template.
    Celdas con wrap, márgenes pequeños, filtros automáticos en la fila de encabezado.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    from openpyxl.worksheet.page import PageMargins
    from io import BytesIO
    fecha_str = timezone.now().strftime("%d-%m-%Y")
    safe_name = (list_name or "Logs").replace(" ", "-").replace("/", "-")[:40]
    filename = f"{safe_name}-{fecha_str}.xlsx"
    sheet_title = safe_name[:31]
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title
    headers = [
        "Transmittal", "Especialidad", "Referencia", "Fecha envío (emisor)",
        "Responsable", "Documento - Archivo", "Estado",
    ]
    ws.append(headers)
    thin = Side(style="thin", color="4472C4")
    for col in range(1, len(headers) + 1):
        c = ws.cell(row=1, column=col)
        c.font = Font(bold=True, color="FFFFFF")
        c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="left")
        c.border = Border(top=thin, left=thin, right=thin, bottom=thin)
        c.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    for row in rows:
        d = _format_log_row_for_export(row, request)
        ws.append([
            d["transmittal"],
            d["especialidad"],
            d["referencia"],
            d["fecha_envio"],
            d["responsable"],
            d["documento_archivo"],
            d["estado"],
        ])
    wrap_align = Alignment(wrap_text=True, vertical="top", horizontal="left")
    light = Side(style="thin", color="CCCCCC")
    for r in range(1, ws.max_row + 1):
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=r, column=col)
            cell.alignment = wrap_align
            if r > 1:
                cell.border = Border(top=light, left=light, right=light, bottom=light)
    # Filtros automáticos en la primera fila (encabezados)
    n_data = len(rows) + 1
    ws.auto_filter.ref = f"A1:G{n_data}"
    # Márgenes pequeños para más espacio de tabla
    ws.page_margins = PageMargins(left=0.25, right=0.25, top=0.4, bottom=0.4, header=0.2, footer=0.2)
    # Anchos de columna razonables
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 28
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 20
    ws.column_dimensions["F"].width = 36
    ws.column_dimensions["G"].width = 12
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    response = HttpResponse(buf.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _logs_pdf_response(rows, list_name, inline=False):
    """
    PDF para listados de logs: mismas 8 columnas que el template.
    Orientación horizontal, márgenes pequeños, celdas multilínea (Paragraph), estilo elegante.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.units import cm
    from io import BytesIO
    fecha_str = timezone.now().strftime("%d-%m-%Y")
    safe_name = (list_name or "Logs").replace(" ", "-").replace("/", "-")[:40]
    filename = f"{safe_name}-{fecha_str}.pdf"
    # Horizontal (landscape)
    pagesize = (A4[1], A4[0])
    buf = BytesIO()
    left_right = 0.4 * cm
    top_bottom = 0.6 * cm
    doc = SimpleDocTemplate(buf, pagesize=pagesize, leftMargin=left_right, rightMargin=left_right, topMargin=top_bottom, bottomMargin=top_bottom)
    styles = getSampleStyleSheet()
    para_cell = ParagraphStyle("LogCell", parent=styles["Normal"], fontName="Helvetica", fontSize=6, leading=7.5, leftIndent=0, rightIndent=0, spaceBefore=0, spaceAfter=0)
    para_header = ParagraphStyle("LogHeader", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7, leading=8)

    def truncate_for_pdf_cell(text, max_chars=900, max_lines=35):
        """Evita que una celda tenga tanto texto que la fila supere la altura de la página (LayoutError)."""
        if not text:
            return ""
        s = str(text).strip()
        lines = s.splitlines()
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            s = "\n".join(lines) + " …"
        if len(s) > max_chars:
            s = s[:max_chars].rstrip() + " …"
        return s

    def safe_para(text, style=para_cell):
        if text is None:
            text = ""
        t = truncate_for_pdf_cell(str(text))
        s = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
        return Paragraph(s or " ", style)

    headers = [
        "Transmittal", "Especialidad", "Referencia", "Fecha envío (emisor)",
        "Responsable", "Documento - Archivo", "Estado",
    ]
    data = [[safe_para(h, para_header) for h in headers]]
    for row in rows:
        d = _format_log_row_for_export(row, request=None)
        data.append([
            safe_para(d["transmittal"]),
            safe_para(d["especialidad"]),
            safe_para(d["referencia"]),
            safe_para(d["fecha_envio"]),
            safe_para(d["responsable"]),
            safe_para(d["documento_archivo"]),
            safe_para(d["estado"]),
        ])
    # Anchos repartidos para landscape A4 (~27.7 cm útil), 7 columnas
    col_widths = [3.5*cm, 3*cm, 3.5*cm, 2.4*cm, 3*cm, 6.5*cm, 2.2*cm]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E5090")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B0BEC5")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ECEFF1")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
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
def logs_propamat_odata(request):
    """
    Logs Propamat a Odata: carpetas cuyo código contiene TRN.
    """
    rows = _get_logs_folder_rows("TRN")
    if request.GET.get("format") == "excel":
        # Hoja/archivo claramente identificados como TRN (Propamat → Odata)
        return _logs_excel_response(rows, list_name="Logs TRN Propamat a Odata", request=request)
    if request.GET.get("format") == "pdf":
        open_inline = request.GET.get("open") == "1"
        return _logs_pdf_response(rows, list_name="Logs TRN Propamat a Odata", inline=open_inline)
    return render(
        request,
        "documents/logs_propamat_odata.html",
        {"rows": rows, "page_title": "Logs Propamat a Odata", "page_subtitle": "Carpetas TRN."},
    )


@login_required
@require_GET
def logs_odata_propamat(request):
    """
    Logs Odata a Propamat: carpetas cuyo código contiene Odata.
    """
    rows = _get_logs_folder_rows("Odata")
    if request.GET.get("format") == "excel":
        # Hoja/archivo claramente identificados como ODATA-ST01 (Odata → Propamat)
        return _logs_excel_response(rows, list_name="Logs ODATA-ST01 Odata a Propamat", request=request)
    if request.GET.get("format") == "pdf":
        open_inline = request.GET.get("open") == "1"
        return _logs_pdf_response(rows, list_name="Logs ODATA-ST01 Odata a Propamat", inline=open_inline)
    return render(
        request,
        "documents/logs_odata_propamat.html",
        {"rows": rows, "page_title": "Logs Odata a Propamat", "page_subtitle": "Carpetas Odata."},
    )
