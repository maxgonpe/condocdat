from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse
from django.db.models import Q

from .models import Document, Folder, FolderFile, DocumentAttachment
from .search_backend import search_unified


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
        docs = []
        for d in qs[:500]:
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
    """Listado de carpetas (transmittals)."""
    folders = Folder.objects.prefetch_related('documents', 'folder_files').order_by('-date', '-created_at')[:500]
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
