"""
Backend de búsqueda unificada — solo PostgreSQL.

Documentos: se exigen SIEMPRE todos los términos (o la frase completa).
- Frase completa en códigos o en algún adjunto (icontains).
- content_extract: cada término como palabra completa (PostgreSQL \\m\\M + iregex).
- Adjuntos: cada término como palabra completa en extracted_text (iregex).
No se usa FTS suelto para documentos para evitar coincidencias con una sola palabra.
Carpetas y archivos de carpeta: FTS con todos los términos o frase exacta.
"""
import re
from django.db import connection
from django.db.models import Q, F, Prefetch
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

from .models import Document, Folder, FolderFile, DocumentAttachment
from .text_search_match import pg_word_anchored_regex, text_matches_all_terms_as_words


def _normalize_terms(query):
    """Limpia la consulta y devuelve lista de términos (mín. 1 carácter)."""
    if not query or not isinstance(query, str):
        return []
    terms = [t.strip() for t in re.split(r"\s+", query.strip()) if len(t.strip()) >= 1]
    return terms


def _build_fts_query(terms, config="spanish"):
    """AND de todos los términos (plain = stemmed)."""
    if not terms:
        return None
    q = SearchQuery(terms[0], config=config, search_type="plain")
    for t in terms[1:]:
        q = q & SearchQuery(t, config=config, search_type="plain")
    return q


def _document_ids_with_attachment_containing_all_terms(terms):
    """IDs de documentos que tienen al menos un adjunto cuyo extracted_text contiene TODOS los términos."""
    if not terms:
        return set()
    qs = DocumentAttachment.objects.all()
    for t in terms:
        if t:
            qs = qs.filter(extracted_text__iregex=pg_word_anchored_regex(t))
    return set(qs.values_list("document_id", flat=True).distinct())


def search_unified(query, limit=200):
    """
    Búsqueda unificada (PostgreSQL).
    Documentos: solo coinciden si tienen la frase completa O todos los términos (en content_extract o en algún adjunto).
    """
    q = (query or "").strip()
    terms = _normalize_terms(q)
    if not terms:
        return {"documents": [], "folders": [], "folder_files": []}

    if connection.vendor != "postgresql":
        return {"documents": [], "folders": [], "folder_files": []}

    config = "spanish"

    # —— Documentos: solo condiciones que exigen TODOS los términos o la frase completa
    # (1) Frase completa en códigos o en texto de algún adjunto
    doc_related = (
        Q(project__code__icontains=q)
        | Q(company__code__icontains=q)
        | Q(process__code__icontains=q)
        | Q(doc_type__code__icontains=q)
        | Q(attachments__extracted_text__icontains=q)
    )
    # (2) content_extract contiene todos los términos
    content_has_all = Q(content_extract__isnull=False) & ~Q(content_extract="")
    for t in terms:
        if t:
            content_has_all = content_has_all & Q(content_extract__iregex=pg_word_anchored_regex(t))
    # (3) Algún adjunto tiene todos los términos en extracted_text
    doc_ids_attachment = _document_ids_with_attachment_containing_all_terms(terms)
    doc_filter = doc_related | content_has_all
    if doc_ids_attachment:
        doc_filter = doc_filter | Q(pk__in=doc_ids_attachment)

    doc_vector = (
        SearchVector("code", weight="A", config=config)
        + SearchVector("title", weight="A", config=config)
        + SearchVector("description", weight="B", config=config)
        + SearchVector("revision", weight="B", config=config)
        + SearchVector("content_extract", weight="C", config=config)
        + SearchVector("project__code", weight="A", config=config)
        + SearchVector("company__code", weight="A", config=config)
        + SearchVector("process__code", weight="A", config=config)
        + SearchVector("doc_type__code", weight="A", config=config)
    )
    phrase_query = SearchQuery(q, config=config, search_type="phrase") if len(q) >= 2 else None
    doc_search_rank = _build_fts_query(terms, config)
    rank_expr = SearchRank(doc_vector, doc_search_rank, normalization=2, cover_density=True)
    documents = list(
        Document.objects.annotate(search=doc_vector, rank=rank_expr)
        .filter(doc_filter)
        .select_related("project", "company", "process", "doc_type", "folder")
        .distinct()
        .order_by(F("rank").desc(nulls_last=True), "-date", "-created_at")[:limit]
    )

    # —— Carpetas: FTS (todos los términos o frase)
    doc_search = _build_fts_query(terms, config)
    folder_vector = (
        SearchVector("code", weight="A", config=config)
        + SearchVector("title", weight="A", config=config)
        + SearchVector("description", weight="B", config=config)
    )
    folder_filter = Q(search=doc_search)
    if phrase_query is not None:
        folder_filter = folder_filter | Q(search=phrase_query)
    folders = list(
        Folder.objects.annotate(
            search=folder_vector,
            rank=SearchRank(folder_vector, doc_search, normalization=2),
        )
        .filter(folder_filter)
        .order_by(F("rank").desc(nulls_last=True), "-date", "-created_at")[:limit]
    )

    # —— Archivos de carpeta: FTS o todos los términos en extracted_text
    file_vector = (
        SearchVector("name", weight="A", config=config)
        + SearchVector("extracted_text", weight="B", config=config)
    )
    file_filter = Q(search=doc_search)
    if phrase_query is not None:
        file_filter = file_filter | Q(search=phrase_query)
    file_content_all = Q(extracted_text__isnull=False) & ~Q(extracted_text="")
    for t in terms:
        if t:
            file_content_all = file_content_all & Q(extracted_text__iregex=pg_word_anchored_regex(t))
    file_filter = file_filter | file_content_all
    folder_files = list(
        FolderFile.objects.annotate(search=file_vector)
        .filter(file_filter)
        .select_related("folder")
        .order_by("folder__code", "name")[:limit]
    )

    if len(terms) > 1:
        documents = _strict_multi_term_document_order(documents, terms)
        folders = [
            f
            for f in folders
            if text_matches_all_terms_as_words(
                "\n".join(x for x in (f.code, f.title or "", f.description or "") if x),
                terms,
            )
        ]
        folder_files = [
            ff
            for ff in folder_files
            if text_matches_all_terms_as_words(
                "\n".join(x for x in (ff.name or "", ff.extracted_text or "") if x),
                terms,
            )
        ]

    return {"documents": documents, "folders": folders, "folder_files": folder_files}


def _strict_multi_term_document_order(documents, terms):
    """Refina coincidencias multi-término (heurística anti-OCR) conservando el orden."""
    if not documents:
        return documents
    order = [d.pk for d in documents]
    loaded = (
        Document.objects.filter(pk__in=order)
        .prefetch_related(
            Prefetch(
                "attachments",
                queryset=DocumentAttachment.objects.only("extracted_text", "document_id"),
            )
        )
        .only("id", "content_extract")
    )
    allowed = set()
    for d in loaded:
        parts = [d.content_extract or ""]
        for a in d.attachments.all():
            if a.extracted_text:
                parts.append(a.extracted_text)
        blob = "\n".join(parts)
        if text_matches_all_terms_as_words(blob, terms):
            allowed.add(d.pk)
    return [d for d in documents if d.pk in allowed]
