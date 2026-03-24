import csv
import re
from datetime import datetime, timedelta, timezone as py_timezone

from django.db import transaction
from django.utils import timezone

from .models import (
    RDIImport,
    RDIRecord,
    RDI_STATUS_CHOICES,
    RDI_STATUS_ABIERTA,
    RDI_STATUS_BORRADOR,
    RDI_STATUS_CERRADA,
    RDI_STATUS_NULA,
    RDI_STATUS_RECHAZADA,
    RDI_STATUS_REMITIDA,
    RDI_STATUS_RESPONDIDA,
)


_FILENAME_SNAPSHOT_RE = re.compile(
    r"SDI\s*-\s*(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<h>\d{2})_(?P<m>\d{2})_(?P<s>\d{2})",
    re.IGNORECASE,
)


def parse_snapshot_datetime_from_filename(filename: str):
    """
    Espera algo como:
      ... - SDI - 2026-03-20 08_41_83
    Retorna datetime timezone-aware o None.
    """
    if not filename:
        return None

    m = _FILENAME_SNAPSHOT_RE.search(filename)
    if not m:
        return None

    try:
        year = int(m.group("date")[:4])
        month = int(m.group("date")[5:7])
        day = int(m.group("date")[8:10])
        hh = int(m.group("h"))
        mm = int(m.group("m"))
        ss = int(m.group("s"))

        # El CSV/archivo puede venir con "segundos" >= 60 (ej. 08_41_83).
        # Usamos timedelta para normalizar overflow hacia minutos/horas.
        dt = datetime(year, month, day, hh, 0, 0) + timedelta(minutes=mm, seconds=ss)
    except Exception:
        return None

    # Usa el timezone actual de Django.
    tz = timezone.get_current_timezone()
    return timezone.make_aware(dt, tz)


def map_csv_status_to_choice(raw_status: str) -> str:
    if not raw_status:
        return RDI_STATUS_NULA
    s = str(raw_status).strip().lower()
    if not s:
        return RDI_STATUS_NULA

    mapping = {
        # lo que trae el CSV que encontramos
        "open": RDI_STATUS_ABIERTA,
        "answered": RDI_STATUS_RESPONDIDA,
        "closed": RDI_STATUS_CERRADA,
        # posibles variantes
        "draft": RDI_STATUS_BORRADOR,
        "borrador": RDI_STATUS_BORRADOR,
        "preliminar": RDI_STATUS_BORRADOR,
        "remitida": RDI_STATUS_REMITIDA,
        "remitido": RDI_STATUS_REMITIDA,
        "enviada": RDI_STATUS_REMITIDA,
        "rejected": RDI_STATUS_RECHAZADA,
        "rechazada": RDI_STATUS_RECHAZADA,
        "rechazado": RDI_STATUS_RECHAZADA,
        "abierta": RDI_STATUS_ABIERTA,
        "respondida": RDI_STATUS_RESPONDIDA,
        "cerrada": RDI_STATUS_CERRADA,
        "nula": RDI_STATUS_NULA,
        "": RDI_STATUS_NULA,
    }
    return mapping.get(s, RDI_STATUS_NULA)


def _parse_csv_datetime(value):
    """
    Parse robusto para valores tipo:
      03/19/2026 12:31 PM (UTC)
      03/23/2026 (UTC)
    """
    if value is None:
        return None
    v = str(value).strip()
    if not v or v == '""':
        return None

    # Normaliza espacios extra.
    v = re.sub(r"\s+", " ", v)

    # Formato con hora 12h
    for fmt in ("%m/%d/%Y %I:%M %p (UTC)", "%m/%d/%Y %H:%M (UTC)"):
        try:
            dt = datetime.strptime(v, fmt)
            return timezone.make_aware(dt, py_timezone.utc)
        except Exception:
            pass

    # Formato solo fecha
    for fmt in ("%m/%d/%Y (UTC)",):
        try:
            d = datetime.strptime(v, fmt).date()
            dt = datetime(d.year, d.month, d.day, 0, 0, 0)
            return timezone.make_aware(dt, py_timezone.utc)
        except Exception:
            pass

    return None


def _parse_csv_bool(value):
    if value is None:
        return None
    s = str(value).strip().lower()
    if not s or s == '""':
        return None
    if s in ("yes", "y", "si", "sí"):
        return True
    if s in ("no", "n"):
        return False
    return None


def _norm_str(x) -> str:
    if x is None:
        return ""
    s = str(x)
    s = s.replace("\r\n", "\n").replace("\r", "\n").strip()
    return s


@transaction.atomic
def attach_rdi_csv(uploaded_file, original_filename: str):
    """
    1) Crea un `RDIImport` a partir del archivo adjunto.
    2) Importa el CSV y actualiza/crea `RDIRecord` por `Id`.
    3) Si llega un CSV posterior, actualiza los campos que cambiaron.
    """
    snapshot_dt = parse_snapshot_datetime_from_filename(original_filename)
    imp = RDIImport.objects.create(
        file=uploaded_file,
        original_filename=original_filename,
        snapshot_datetime=snapshot_dt,
    )

    _import_rdi_csv_file(imp)
    return imp


def _import_rdi_csv_file(imp: RDIImport):
    file_path = imp.file.path
    snapshot_dt = imp.snapshot_datetime

    with open(file_path, "r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            raw_id = (row.get("Id") or "").strip()
            try:
                csv_id = int(raw_id)
            except Exception:
                continue

            new_fields = {
                "csv_id": csv_id,
                "title": _norm_str(row.get("Title")),
                "question": _norm_str(row.get("Question")),
                "suggested_answer": _norm_str(row.get("Suggested answer")),
                "location_details": _norm_str(row.get("Location details")),
                "status": map_csv_status_to_choice(row.get("Status")),
                "response": _norm_str(row.get("Response")),
                "assigned_to": _norm_str(row.get("Assigned to")),
                "assignee_type": _norm_str(row.get("Assignee type")),
                "company": _norm_str(row.get("Company")),
                "due_date": _parse_csv_datetime(row.get("Due date")),
                "associated_to_document": _parse_csv_bool(row.get("Associated to document?")),
                "created_at": _parse_csv_datetime(row.get("Created at")),
                "created_by": _norm_str(row.get("Created by")),
                "updated_at": _parse_csv_datetime(row.get("Updated at")),
                "updated_by": _norm_str(row.get("Updated by")),
                "distribution_list": _norm_str(row.get("Distribution list")),
                "cost_impact": _norm_str(row.get("Cost impact")),
                "schedule_impact": _norm_str(row.get("Schedule impact")),
                "priority": _norm_str(row.get("Priority")),
                "discipline": _norm_str(row.get("Discipline")),
                "category": _norm_str(row.get("Category")),
                "reference": _norm_str(row.get("Reference")),
            }

            existing = RDIRecord.objects.filter(csv_id=csv_id).first()
            if not existing:
                new_fields["last_snapshot_datetime"] = snapshot_dt
                new_fields["last_diff_fields"] = "CREATED"
                new_fields["last_import"] = imp
                RDIRecord.objects.create(**new_fields)
                continue

            changed = []
            for field, new_val in new_fields.items():
                if field == "csv_id":
                    continue
                old_val = getattr(existing, field)
                if old_val != new_val:
                    changed.append(field)
                    setattr(existing, field, new_val)

            # Siempre registramos la última snapshot (aunque no haya cambios de contenido).
            if existing.last_snapshot_datetime != snapshot_dt:
                changed.append("last_snapshot_datetime")
            existing.last_snapshot_datetime = snapshot_dt
            existing.last_import = imp

            existing.last_diff_fields = ", ".join(changed)[:2000]

            # Si no hubo cambios de contenido y el snapshot es igual, evitamos escrituras.
            if changed and existing.last_diff_fields:
                existing.save()
            else:
                # Aun así, el FK last_import debe quedar consistente si era distinto.
                if existing.last_import_id != imp.id:
                    existing.save()


def get_rdi_records_for_ajax(q: str = "", limit: int = 200):
    """
    Devuelve el listado actual (último estado) para renderizar con AJAX.
    """
    qs = RDIRecord.objects.select_related("last_import")

    query = (q or "").strip()
    if query:
        terms = [t for t in re.split(r"\s+", query) if t]
        if terms:
            # Búsqueda por "términos": cada término debe estar en al menos
            # uno de los campos relevantes (AND global).
            from django.db.models import Q

            status_label_to_code = {label.lower(): code for code, label in RDI_STATUS_CHOICES}
            # también permitimos que el usuario busque por el código interno
            status_code_values = {code.lower(): code for code, _ in RDI_STATUS_CHOICES}

            fields = [
                # Nota: csv_id es entero, por eso se filtra aparte si el término es numérico.
                "title",
                "question",
                "suggested_answer",
                "location_details",
                "response",
                "assigned_to",
                "assignee_type",
                "company",
                "priority",
                "discipline",
                "category",
                "reference",
            ]

            combined = None
            for t in terms:
                t_l = t.lower()
                term_q = Q()

                # Si el término es numérico, permite buscar por csv_id exacto.
                if t_l.isdigit():
                    try:
                        term_q |= Q(csv_id=int(t_l))
                    except Exception:
                        pass

                for f in fields:
                    term_q |= Q(**{f + "__icontains": t_l})

                # status por label o por código
                if t_l in status_label_to_code:
                    term_q |= Q(status=status_label_to_code[t_l])
                if t_l in status_code_values:
                    term_q |= Q(status=status_code_values[t_l])

                combined = term_q if combined is None else (combined & term_q)

            if combined is not None:
                qs = qs.filter(combined)

    records = qs.order_by("-last_snapshot_datetime", "-csv_id")[:limit]

    out = []
    for r in records:
        out.append(
            {
                "csv_id": r.csv_id,
                "title": r.title,
                "status": r.status,
                "status_label": dict(RDIRecord._meta.get_field("status").choices).get(
                    r.status, r.status
                ),
                "question": r.question,
                "response": r.response,
                "due_date": r.due_date.isoformat() if r.due_date else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                "last_snapshot_datetime": (
                    r.last_snapshot_datetime.isoformat() if r.last_snapshot_datetime else None
                ),
            }
        )
    return out


def get_rdi_cost_schedule_impacts_for_ajax(q: str = "", limit: int = 300):
    """
    Devuelve registros RDI filtrados por impacto (costo o plazo = yes/si/sí),
    para el listado "Aumentos/disminuciones".
    """
    from django.db.models import Q

    qs = RDIRecord.objects.select_related("last_import").filter(
        Q(cost_impact__iregex=r"^\s*(yes|si|sí)\s*$")
        | Q(schedule_impact__iregex=r"^\s*(yes|si|sí)\s*$")
    )

    query = (q or "").strip()
    if query:
        terms = [t for t in re.split(r"\s+", query) if t]
        if terms:
            combined = None
            for t in terms:
                term_q = (
                    Q(title__icontains=t)
                    | Q(location_details__icontains=t)
                    | Q(cost_impact__icontains=t)
                    | Q(schedule_impact__icontains=t)
                    | Q(discipline__icontains=t)
                    | Q(priority__icontains=t)
                    | Q(status__icontains=t)
                )
                if t.isdigit():
                    try:
                        term_q |= Q(csv_id=int(t))
                    except Exception:
                        pass
                combined = term_q if combined is None else (combined & term_q)
            if combined is not None:
                qs = qs.filter(combined)

    records = qs.order_by("-last_snapshot_datetime", "-csv_id")[:limit]
    status_label_map = dict(RDIRecord._meta.get_field("status").choices)

    def _translate_term_es(value: str) -> str:
        v = (value or "").strip()
        if not v:
            return ""
        key = v.lower()
        translations = {
            "yes": "Sí",
            "no": "No",
            "high": "Alta",
            "hight": "Alta",
            "medium": "Media",
            "low": "Baja",
            "critical": "Crítica",
            "open": "Abierta",
            "closed": "Cerrada",
            "answered": "Respondida",
            "draft": "Borrador",
        }
        return translations.get(key, v)

    out = []
    for r in records:
        out.append(
            {
                "csv_id": r.csv_id,
                "title": r.title,
                "status": r.status,
                "status_label": status_label_map.get(r.status, r.status),
                "location_details": r.location_details,
                "cost_impact": r.cost_impact,
                "cost_impact_label": _translate_term_es(r.cost_impact),
                "schedule_impact": r.schedule_impact,
                "schedule_impact_label": _translate_term_es(r.schedule_impact),
                "discipline": r.discipline,
                "priority": r.priority,
                "priority_label": _translate_term_es(r.priority),
                "question": r.question,
                "response": r.response,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
        )
    return out

