"""
Backend de búsqueda unificada: por nombre/código y por contenido extraído.
Implementación actual: SQLite con icontains. Preparado para cambiar a PostgreSQL
con SearchVector cuando se migre la base de datos.
"""
from django.db import connection
from django.db.models import Q

from .models import Document, Folder, FolderFile


def use_postgresql():
    """True si la BD es PostgreSQL (para usar full-text search)."""
    return connection.vendor == "postgresql"


def search_unified(query, limit=200):
    """
    Búsqueda unificada por término: documentos, carpetas y archivos de carpeta.
    Retorna: dict con keys 'documents', 'folders', 'folder_files'.
    """
    q = (query or "").strip()
    if not q:
        return {"documents": [], "folders": [], "folder_files": []}

    # SQLite (y cualquier BD): filtro con icontains en campos de texto
    term_filter_doc = (
        Q(code__icontains=q)
        | Q(title__icontains=q)
        | Q(description__icontains=q)
        | Q(revision__icontains=q)
        | Q(project__code__icontains=q)
        | Q(company__code__icontains=q)
        | Q(process__code__icontains=q)
        | Q(doc_type__code__icontains=q)
        | Q(content_extract__icontains=q)
        | Q(attachments__extracted_text__icontains=q)
    )
    term_filter_folder = (
        Q(code__icontains=q)
        | Q(title__icontains=q)
        | Q(description__icontains=q)
    )
    term_filter_folder_file = Q(name__icontains=q) | Q(extracted_text__icontains=q)

    # Opcional: si en el futuro usamos PostgreSQL con SearchVector:
    # if use_postgresql():
    #     from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
    #     doc_queryset = Document.objects.annotate(
    #         search=SearchVector('code', 'title', 'description', 'content_extract', ...)
    #     ).filter(search=SearchQuery(q)).order_by('-date')[:limit]
    #     ...

    documents = list(
        Document.objects.filter(term_filter_doc)
        .select_related("project", "company", "process", "doc_type", "folder")
        .distinct()
        .order_by("-date", "-created_at")[:limit]
    )
    folders = list(
        Folder.objects.filter(term_filter_folder).order_by("-date", "-created_at")[:limit]
    )
    folder_files = list(
        FolderFile.objects.filter(term_filter_folder_file)
        .select_related("folder")
        .order_by("folder__code", "name")[:limit]
    )

    return {"documents": documents, "folders": folders, "folder_files": folder_files}
