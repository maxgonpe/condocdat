"""
Trazabilidad de transmittals ODATA / TRN: documentos en carpetas de seguimiento
y recorrido inferido por revisiones / apariciones en el sistema.
"""
import os
import re
from collections import defaultdict
from datetime import datetime, time
from typing import Any, Dict, List, Optional, Tuple

from django.db.models import Prefetch, Q
from django.utils import timezone as dj_tz

from .models import Document, FolderFile


# Carpetas de interés (patrones en Folder.code)
ODATA_FOLDER_SUB = "ODATA-ST01-F5-TTAL-PPT"
ODATA_BUF_MARKER = "ODATA-BUF"
TRN_FOLDER_SUB = "TRN-PRO-CM-TRN"

_RE_TRN_CODE = re.compile(r"TRN-PRO-CM-TRN-\d+", re.IGNORECASE)
_RE_ODATA_TTAL = re.compile(r"ODATA-ST01-F5-TTAL-PPT-\d+", re.IGNORECASE)


def traceability_folder_filter() -> Q:
    return (
        Q(folder__code__icontains=ODATA_FOLDER_SUB)
        | Q(folder__code__icontains=TRN_FOLDER_SUB)
        | Q(folder__code__icontains=ODATA_BUF_MARKER)
    )


def _is_odata_style_folder_code(folder_code: str) -> bool:
    if not folder_code:
        return False
    u = folder_code.upper()
    return ODATA_FOLDER_SUB in u or ODATA_BUF_MARKER.upper() in u


def normalize_title_key(title: str) -> str:
    """
    Agrupa variantes del mismo documento (Rev., sufijos _0, espacios).
    """
    if not title:
        return ""
    t = title.strip()
    t = re.sub(r"\bRev\.?\s*[\d.]+\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"_\d+\s*$", "", t)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t[:160]


def folder_side_label(folder_code: str) -> Tuple[str, str]:
    """(código corto para UI, slug interno: odata | trn | otro)"""
    if not folder_code:
        return ("—", "otro")
    u = folder_code.upper()
    if ODATA_BUF_MARKER.upper() in u:
        return ("ODATA (BUF)", "odata")
    if ODATA_FOLDER_SUB in u:
        return ("ODATA (PPT)", "odata")
    if TRN_FOLDER_SUB in u:
        return ("TRN (Propamat)", "trn")
    return (folder_code[:40], "otro")


def extract_transmittal_codes(text: str) -> Tuple[List[str], List[str]]:
    if not text:
        return [], []
    trn = sorted(set(_RE_TRN_CODE.findall(text)))
    odata = sorted(set(_RE_ODATA_TTAL.findall(text)))
    return trn, odata


def _name_matches_search(name: str, q: str) -> bool:
    """True si todos los términos de q aparecen en el nombre (como la búsqueda del listado)."""
    if not name or not (q or "").strip():
        return False
    terms = [t for t in re.split(r"\s+", q.strip()) if t]
    if not terms:
        return False
    n = name.lower()
    return all(t.lower() in n for t in terms)


def _trace_chrono_instant(doc: Document) -> datetime:
    """
    Solo fecha/hora de creación del documento (Document.created_at).
    Más reciente arriba. No usa fechas de la carpeta ni updated_at.
    """
    if doc.created_at:
        return doc.created_at
    if doc.date:
        return dj_tz.make_aware(datetime.combine(doc.date, time.min))
    return dj_tz.now()


def _build_steps_for_documents(
    docs: List[Document],
    q: str,
    matched_ids: set,
) -> Tuple[List[Dict[str, Any]], Document]:
    """
    Orden: más reciente primero (arriba) → origen al final (abajo).
    Solo un instante fecha+hora por paso; nunca código ni número de transmittal.
    """
    docs_sorted = sorted(
        docs,
        key=lambda d: (_trace_chrono_instant(d), d.pk),
        reverse=True,
    )
    primary = docs_sorted[0]
    steps: List[Dict[str, Any]] = []
    n = len(docs_sorted)
    for i, d in enumerate(docs_sorted):
        side_label, side = folder_side_label(d.folder.code if d.folder else "")
        blob = (d.content_extract or "") + " "
        for att in d.attachments.all()[:40]:
            blob += (att.extracted_text or "") + " "
        trn_refs, odata_refs = extract_transmittal_codes(blob)

        attachments: List[Dict[str, Any]] = []
        if d.file:
            bn = os.path.basename(d.file.name) if d.file.name else "Documento principal"
            attachments.append(
                {
                    "name": bn,
                    "url": d.file.url,
                    "highlight": _name_matches_search(bn, q),
                    "kind": "principal",
                }
            )
        for att in d.attachments.all():
            bn = os.path.basename(att.file.name) if att.file and att.file.name else "Adjunto"
            attachments.append(
                {
                    "name": bn,
                    "url": att.file.url if att.file else None,
                    "highlight": _name_matches_search(bn, q),
                    "kind": "adjunto",
                }
            )

        folder_files: List[Dict[str, Any]] = []
        if d.folder:
            for ff in d.folder.folder_files.all():
                fn = ff.name or (os.path.basename(ff.file.name) if ff.file else "")
                folder_files.append(
                    {
                        "name": fn,
                        "url": ff.file.url if ff.file else None,
                        "highlight": _name_matches_search(fn, q) or _name_matches_search(
                            os.path.basename(ff.file.name) if ff.file else "", q
                        ),
                    }
                )

        trace_instant = _trace_chrono_instant(d)
        steps.append(
            {
                "order": i + 1,
                "step_label": "Más reciente" if i == 0 else ("Origen (inicio)" if i == n - 1 else ""),
                "trace_instant": trace_instant,
                "document_id": d.pk,
                "code": d.code,
                "title": d.title,
                "revision": d.revision,
                "date": d.date,
                "created_at": d.created_at,
                "updated_at": d.updated_at,
                "status": d.status,
                "status_display": d.get_status_display(),
                "informado": d.informado,
                "informado_display": d.get_informado_display(),
                "folder_id": d.folder_id,
                "folder_code": d.folder.code if d.folder else "",
                "folder_title": (d.folder.title or "") if d.folder else "",
                "folder_date": d.folder.date if d.folder else None,
                "side": side,
                "side_label": side_label,
                "refs_trn": trn_refs[:12],
                "refs_odata": odata_refs[:12],
                "is_search_hit": d.pk in matched_ids,
                "attachments": attachments,
                "folder_files": folder_files,
            }
        )
    return steps, primary


def _doc_matches_query(doc: Document, q: str) -> bool:
    q = (q or "").strip().lower()
    if not q:
        return True
    terms = [t for t in re.split(r"\s+", q) if t]
    if not terms:
        return True
    haystack = " ".join(
        [
            doc.code or "",
            doc.title or "",
            doc.description or "",
            doc.content_extract or "",
            doc.revision or "",
            doc.folder.code if doc.folder else "",
            doc.folder.title if doc.folder else "",
        ]
    ).lower()
    try:
        for att in doc.attachments.all():
            if att.file:
                haystack += " " + (att.file.name or "").lower()
        if doc.folder:
            for ff in doc.folder.folder_files.all():
                haystack += " " + (ff.name or "").lower()
                if ff.file:
                    haystack += " " + (ff.file.name or "").lower()
    except Exception:
        pass
    return all(t in haystack for t in terms)


def build_journeys_for_query(
    q: str,
    *,
    scope_limit: int = 4000,
    max_journeys: int = 80,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Devuelve (journeys, summary) donde cada journey es un grupo de documentos
    (mismo título base) ordenados del más reciente al más antiguo, filtrado por q.
    """
    qs = (
        Document.objects.filter(traceability_folder_filter())
        .filter(folder__isnull=False)
        .select_related("folder", "project", "company", "process", "doc_type")
        .prefetch_related(
            "attachments",
            Prefetch(
                "folder__folder_files",
                queryset=FolderFile.objects.order_by("name"),
            ),
        )
        .order_by("-date", "-created_at")[:scope_limit]
    )
    scope_list = list(qs)
    key_to_docs: Dict[str, List[Document]] = defaultdict(list)
    for d in scope_list:
        key = normalize_title_key(d.title) or f"__id_{d.pk}"
        key_to_docs[key].append(d)

    q_stripped = (q or "").strip()
    if not q_stripped:
        odata_n = sum(
            1 for d in scope_list if d.folder and _is_odata_style_folder_code(d.folder.code)
        )
        trn_n = sum(
            1
            for d in scope_list
            if d.folder and TRN_FOLDER_SUB in (d.folder.code or "").upper()
        )
        summary = {
            "scope_documents": len(scope_list),
            "journeys_shown": 0,
            "odata_folder_marker": ODATA_FOLDER_SUB,
            "trn_folder_marker": TRN_FOLDER_SUB,
            "odata_docs": odata_n,
            "trn_docs": trn_n,
            "needs_query": True,
        }
        return [], summary

    matched_ids = {d.pk for d in scope_list if _doc_matches_query(d, q_stripped)}

    journeys: List[Dict[str, Any]] = []
    for key, docs in key_to_docs.items():
        if not any(d.pk in matched_ids for d in docs):
            continue
        steps, primary = _build_steps_for_documents(docs, q_stripped, matched_ids)
        journeys.append(
            {
                "key": key,
                "title_hint": (primary.title or primary.code)[:200],
                "n_steps": len(docs),
                "sort_instant": _trace_chrono_instant(primary),
                "steps": steps,
                "folder_codes": sorted({d.folder.code for d in docs if d.folder}),
            }
        )

    # Más pasos primero; a igual número de pasos, recorrido con documento más reciente primero
    # (antes se desempataba por título alfabético y el orden por hora parecía aleatorio).
    journeys.sort(key=lambda j: (j["n_steps"], j["sort_instant"]), reverse=True)
    odata_n = sum(1 for d in scope_list if d.folder and _is_odata_style_folder_code(d.folder.code))
    trn_n = sum(
        1 for d in scope_list if d.folder and TRN_FOLDER_SUB in (d.folder.code or "").upper()
    )
    summary = {
        "scope_documents": len(scope_list),
        "journeys_shown": min(len(journeys), max_journeys),
        "odata_folder_marker": ODATA_FOLDER_SUB,
        "trn_folder_marker": TRN_FOLDER_SUB,
        "odata_docs": odata_n,
        "trn_docs": trn_n,
        "needs_query": False,
    }
    return journeys[:max_journeys], summary
