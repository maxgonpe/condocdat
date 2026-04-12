from __future__ import annotations

import io
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable

from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel as xl_from_excel
from openpyxl.utils.datetime import to_excel as xl_to_excel

from .models import (
    EquiposAsset,
    EquiposCambioLog,
    EquiposLibro,
    EquiposLocation,
    EquiposOtro,
    EquiposResumenFila,
    EquiposSignificadoFila,
)

SHEET_RESUMEN = "Resumen - TD"
SHEET_SIGNIFICADO = "Significado status"
SHEET_LOCATIONS = "Locations"
SHEET_ASSET = "Asset"
SHEET_OTROS = "Otros equipos"

# Misma ruta que `equipos_libro_upload_to` en models.py
EQUIPOS_LIBRO_REL_PATH = "equipos/libro_actual.xlsx"


def build_equipos_download_filename(
    libro: EquiposLibro, when: date | None = None
) -> str:
    """
    Nombre sugerido al descargar: <nombre base del libro subido>_YYYY-MM-DD.xlsx
    (fecha = día de la descarga, hora local del sitio).
    """
    when = when or timezone.localdate()
    raw = (libro.original_filename or "control_equipos").strip()
    if raw.lower().endswith(".xlsx"):
        raw = raw[:-5]
    raw = raw.replace(" ", "_")
    raw = re.sub(r"[^a-zA-Z0-9_.\-]", "_", raw)
    raw = re.sub(r"_+", "_", raw).strip("_")[:160] or "control_equipos"
    return f"{raw}_{when.isoformat()}.xlsx"


def build_equipos_pdf_download_filename(
    libro: EquiposLibro, when: date | None = None
) -> str:
    xlsx = build_equipos_download_filename(libro, when=when)
    return xlsx[:-5] + ".pdf" if xlsx.lower().endswith(".xlsx") else xlsx + ".pdf"


def _str_cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v).strip()


def _cell_to_date(v: Any):
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, (int, float)):
        try:
            dt = xl_from_excel(float(v))
            return dt.date() if isinstance(dt, datetime) else None
        except Exception:
            return None
    return None


def _date_to_excel(d: date | None) -> Any:
    if d is None:
        return None
    return xl_to_excel(datetime.combine(d, datetime.min.time()))


def _cell_to_decimal(v: Any) -> Decimal | None:
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v))
    except Exception:
        return None


def latest_libro() -> EquiposLibro | None:
    return EquiposLibro.objects.order_by("-imported_at").first()


def ultima_cambio_formulario_map(
    libro: EquiposLibro | None, modelo: str, record_ids: list[int]
) -> dict[int, datetime]:
    """Última fecha de cambio desde formulario (EquiposCambioLog) por record_id."""
    if not libro or not record_ids:
        return {}
    rows = (
        EquiposCambioLog.objects.filter(
            libro=libro, modelo=modelo, record_id__in=record_ids
        )
        .values("record_id")
        .annotate(last=Max("created_at"))
    )
    return {r["record_id"]: r["last"] for r in rows}


def ultima_cambio_un_registro(
    libro: EquiposLibro | None, modelo: str, record_id: int
) -> datetime | None:
    if not libro:
        return None
    row = (
        EquiposCambioLog.objects.filter(
            libro=libro, modelo=modelo, record_id=record_id
        )
        .aggregate(last=Max("created_at"))
    )
    return row["last"]


def format_ultima_cambio_para_json(dt: datetime | None) -> tuple[str | None, str]:
    """(iso o None, texto dd/mm/aaaa HH:MM en zona local) para APIs y tablas."""
    if dt is None:
        return None, ""
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    local = timezone.localtime(dt)
    return (local.isoformat(), local.strftime("%d/%m/%Y %H:%M"))


@transaction.atomic
def replace_libro_with_import(uploaded_file, original_filename: str) -> EquiposLibro:
    """
    Sustituye datos y un único fichero en disco (`equipos/libro_actual.xlsx`).
    Elimina filas en cascada y borra el archivo anterior para no acumular copias.
    """
    for old in EquiposLibro.objects.all():
        if old.file:
            old.file.delete(save=False)
    EquiposLibro.objects.all().delete()

    if default_storage.exists(EQUIPOS_LIBRO_REL_PATH):
        default_storage.delete(EQUIPOS_LIBRO_REL_PATH)

    libro = EquiposLibro(
        original_filename=(original_filename or "equipos.xlsx").strip(),
    )
    uploaded_file.seek(0)
    libro.file.save("libro_actual.xlsx", uploaded_file, save=True)
    _import_into_libro(libro)
    return libro


def _row_empty_asset(ws, row: int, cmin: int = 2, cmax: int = 22) -> bool:
    for c in range(cmin, cmax + 1):
        v = ws.cell(row=row, column=c).value
        if v is not None and str(v).strip() != "":
            return False
    return True


def _import_into_libro(libro: EquiposLibro) -> None:
    path = libro.file.path
    wb = load_workbook(path, data_only=True)

    ws = wb[SHEET_RESUMEN]
    for r in range(6, 14):
        etiqueta = _str_cell(ws.cell(row=r, column=1).value)
        cuenta = ws.cell(row=r, column=2).value
        fr = ws.cell(row=r, column=3).value
        ci = None
        if cuenta is not None and str(cuenta).strip() != "":
            try:
                ci = int(float(cuenta))
            except (TypeError, ValueError):
                ci = None
        cf = None
        if fr is not None and str(fr).strip() != "":
            try:
                cf = float(fr)
            except (TypeError, ValueError):
                cf = None
        EquiposResumenFila.objects.create(
            libro=libro,
            excel_row=r,
            etiqueta=etiqueta,
            cuenta=ci,
            fraccion=cf,
        )

    ws = wb[SHEET_SIGNIFICADO]
    for r in range(4, (ws.max_row or 0) + 1):
        flujo = _str_cell(ws.cell(row=r, column=2).value)
        st = _str_cell(ws.cell(row=r, column=3).value)
        sig = _str_cell(ws.cell(row=r, column=4).value)
        if not flujo and not st and not sig:
            continue
        EquiposSignificadoFila.objects.create(
            libro=libro,
            excel_row=r,
            flujo=flujo,
            status=st,
            significado=sig,
        )

    ws = wb[SHEET_LOCATIONS]
    max_r = ws.max_row or 0
    for r in range(4, max_r + 1):
        if _row_empty_asset(ws, r, 2, 10):
            continue
        EquiposLocation.objects.create(
            libro=libro,
            excel_row=r,
            campus=_str_cell(ws.cell(row=r, column=2).value),
            building=_str_cell(ws.cell(row=r, column=3).value),
            zones=_str_cell(ws.cell(row=r, column=4).value),
            floors=_str_cell(ws.cell(row=r, column=5).value),
            space_name=_str_cell(ws.cell(row=r, column=6).value),
            fase=_str_cell(ws.cell(row=r, column=8).value),
            area_m2=_cell_to_decimal(ws.cell(row=r, column=9).value),
            code=_str_cell(ws.cell(row=r, column=10).value),
        )

    ws = wb[SHEET_ASSET]
    max_r = ws.max_row or 0
    for r in range(4, max_r + 1):
        if _row_empty_asset(ws, r, 2, 22):
            continue
        raw_tipe = _str_cell(ws.cell(row=r, column=2).value).upper()
        if raw_tipe == EquiposAsset.ROW_TITULO:
            rt = EquiposAsset.ROW_TITULO
        elif raw_tipe == EquiposAsset.ROW_SUBTITULO:
            rt = EquiposAsset.ROW_SUBTITULO
        else:
            rt = EquiposAsset.ROW_TAREA
        EquiposAsset.objects.create(
            libro=libro,
            excel_row=r,
            row_type=rt,
            tipe=_str_cell(ws.cell(row=r, column=2).value),
            especialidad=_str_cell(ws.cell(row=r, column=3).value),
            tag_number=_str_cell(ws.cell(row=r, column=4).value),
            asset_name=_str_cell(ws.cell(row=r, column=5).value),
            space_room=_str_cell(ws.cell(row=r, column=6).value),
            unit=_str_cell(ws.cell(row=r, column=7).value),
            quantity=_str_cell(ws.cell(row=r, column=8).value),
            phase=_str_cell(ws.cell(row=r, column=9).value),
            zones=_str_cell(ws.cell(row=r, column=10).value),
            proveedor=_str_cell(ws.cell(row=r, column=11).value),
            vendor=_str_cell(ws.cell(row=r, column=12).value),
            estado=_str_cell(ws.cell(row=r, column=13).value),
            con_oc=_str_cell(ws.cell(row=r, column=14).value),
            fecha_compra=_cell_to_date(ws.cell(row=r, column=15).value),
            rdi_ttal=_str_cell(ws.cell(row=r, column=16).value),
            fecha_llegada_obra=_cell_to_date(ws.cell(row=r, column=17).value),
            fecha_planificacion=_cell_to_date(ws.cell(row=r, column=18).value),
            cumple=_str_cell(ws.cell(row=r, column=19).value),
            dias=_str_cell(ws.cell(row=r, column=20).value),
            avance_montaje=_str_cell(ws.cell(row=r, column=21).value),
            avance_conexion=_str_cell(ws.cell(row=r, column=22).value),
        )

    ws = wb[SHEET_OTROS]
    max_r = ws.max_row or 0
    for r in range(2, max_r + 1):
        if _row_empty_asset(ws, r, 2, 10):
            continue
        esp = _str_cell(ws.cell(row=r, column=3).value)
        tipe = _str_cell(ws.cell(row=r, column=2).value)
        tag = _str_cell(ws.cell(row=r, column=4).value)
        asset = _str_cell(ws.cell(row=r, column=5).value)
        st = _str_cell(ws.cell(row=r, column=6).value)
        rdi = _str_cell(ws.cell(row=r, column=7).value)
        fe = _str_cell(ws.cell(row=r, column=8).value)
        fr = _str_cell(ws.cell(row=r, column=9).value)
        oc = _str_cell(ws.cell(row=r, column=10).value)
        is_section = (
            esp
            and not tipe
            and not tag
            and not asset
            and not st
            and not rdi
            and not fe
            and not fr
            and not oc
        )
        EquiposOtro.objects.create(
            libro=libro,
            excel_row=r,
            row_type=EquiposOtro.ROW_SECTION if is_section else EquiposOtro.ROW_DATA,
            tipe=tipe,
            especialidad=esp,
            tag_number=tag,
            asset_name=asset,
            estado=st,
            rdi_ttal=rdi,
            fecha_envio_rdi=fe,
            fecha_respuesta_rdi=fr,
            con_oc=oc,
        )

    wb.close()


def log_changes(
    libro: EquiposLibro,
    user,
    modelo: str,
    record_id: int,
    excel_row: int | None,
    before: dict[str, Any],
    after: dict[str, Any],
    fields: Iterable[str],
) -> None:
    for f in fields:
        ov = before.get(f)
        nv = after.get(f)
        ovs = "" if ov is None else str(ov)
        nvs = "" if nv is None else str(nv)
        if ovs == nvs:
            continue
        EquiposCambioLog.objects.create(
            libro=libro,
            user=user,
            modelo=modelo,
            record_id=record_id,
            excel_row=excel_row,
            campo=f,
            valor_anterior=ovs,
            valor_nuevo=nvs,
        )


def sync_libro_to_excel(libro: EquiposLibro) -> None:
    """Escribe los valores del modelo en el archivo .xlsx del libro (mismo path)."""
    path = libro.file.path
    wb = load_workbook(path, keep_vba=False)

    ws = wb[SHEET_RESUMEN]
    for row in libro.resumen_filas.all():
        r = row.excel_row
        ws.cell(row=r, column=1, value=row.etiqueta or None)
        ws.cell(row=r, column=2, value=row.cuenta)
        ws.cell(row=r, column=3, value=row.fraccion)

    ws = wb[SHEET_SIGNIFICADO]
    for row in libro.significado_filas.all():
        r = row.excel_row
        ws.cell(row=r, column=2, value=row.flujo or None)
        ws.cell(row=r, column=3, value=row.status or None)
        ws.cell(row=r, column=4, value=row.significado or None)

    ws = wb[SHEET_LOCATIONS]
    for row in libro.locations.all():
        r = row.excel_row
        ws.cell(row=r, column=2, value=row.campus or None)
        ws.cell(row=r, column=3, value=row.building or None)
        ws.cell(row=r, column=4, value=row.zones or None)
        ws.cell(row=r, column=5, value=row.floors or None)
        ws.cell(row=r, column=6, value=row.space_name or None)
        ws.cell(row=r, column=8, value=row.fase or None)
        ws.cell(row=r, column=9, value=float(row.area_m2) if row.area_m2 is not None else None)
        ws.cell(row=r, column=10, value=row.code or None)

    ws = wb[SHEET_ASSET]
    for row in libro.assets.all():
        r = row.excel_row
        ws.cell(row=r, column=2, value=row.tipe or None)
        ws.cell(row=r, column=3, value=row.especialidad or None)
        ws.cell(row=r, column=4, value=row.tag_number or None)
        ws.cell(row=r, column=5, value=row.asset_name or None)
        ws.cell(row=r, column=6, value=row.space_room or None)
        ws.cell(row=r, column=7, value=row.unit or None)
        ws.cell(row=r, column=8, value=row.quantity or None)
        ws.cell(row=r, column=9, value=row.phase or None)
        ws.cell(row=r, column=10, value=row.zones or None)
        ws.cell(row=r, column=11, value=row.proveedor or None)
        ws.cell(row=r, column=12, value=row.vendor or None)
        ws.cell(row=r, column=13, value=row.estado or None)
        ws.cell(row=r, column=14, value=row.con_oc or None)
        ws.cell(row=r, column=15, value=_date_to_excel(row.fecha_compra))
        ws.cell(row=r, column=16, value=row.rdi_ttal or None)
        ws.cell(row=r, column=17, value=_date_to_excel(row.fecha_llegada_obra))
        ws.cell(row=r, column=18, value=_date_to_excel(row.fecha_planificacion))
        ws.cell(row=r, column=19, value=row.cumple or None)
        ws.cell(row=r, column=20, value=row.dias or None)
        ws.cell(row=r, column=21, value=row.avance_montaje or None)
        ws.cell(row=r, column=22, value=row.avance_conexion or None)

    ws = wb[SHEET_OTROS]
    for row in libro.otros.all():
        r = row.excel_row
        ws.cell(row=r, column=2, value=row.tipe or None)
        ws.cell(row=r, column=3, value=row.especialidad or None)
        ws.cell(row=r, column=4, value=row.tag_number or None)
        ws.cell(row=r, column=5, value=row.asset_name or None)
        ws.cell(row=r, column=6, value=row.estado or None)
        ws.cell(row=r, column=7, value=row.rdi_ttal or None)
        ws.cell(row=r, column=8, value=row.fecha_envio_rdi or None)
        ws.cell(row=r, column=9, value=row.fecha_respuesta_rdi or None)
        ws.cell(row=r, column=10, value=row.con_oc or None)

    wb.save(path)
    wb.close()
    EquiposLibro.objects.filter(pk=libro.pk).update(updated_at=timezone.now())


def build_pdf_buffer(libro: EquiposLibro) -> io.BytesIO:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=24,
        rightMargin=24,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="EqTitle",
        parent=styles["Heading2"],
        fontSize=11,
        spaceAfter=6,
    )
    story = []
    story.append(
        Paragraph(
            f"Control de equipos — {libro.original_filename} — {libro.imported_at:%d/%m/%Y %H:%M}",
            title_style,
        )
    )
    story.append(Spacer(1, 8))

    def add_table(headers: list[str], rows: list[list[str]], caption: str):
        story.append(Paragraph(caption, title_style))
        data = [headers] + rows[:400]
        t = Table(data, repeatRows=1, hAlign="LEFT")
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
                    ("FONTSIZE", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 10))

    assets = libro.assets.filter(row_type=EquiposAsset.ROW_TAREA).order_by("excel_row")[:500]
    if assets.exists():
        add_table(
            ["Fila", "TAG", "Asset", "Estado", "Zona", "Proveedor"],
            [
                [
                    str(a.excel_row),
                    a.tag_number,
                    (a.asset_name or "")[:80],
                    (a.estado or "")[:40],
                    (a.zones or "")[:30],
                    (a.proveedor or "")[:30],
                ]
                for a in assets
            ],
            "Asset (solo filas TAREA)",
        )

    otros = libro.otros.filter(row_type=EquiposOtro.ROW_DATA).order_by("excel_row")[:400]
    if otros.exists():
        add_table(
            ["Fila", "TAG", "Asset", "Estado", "RDI"],
            [
                [
                    str(o.excel_row),
                    o.tag_number,
                    (o.asset_name or "")[:80],
                    (o.estado or "")[:40],
                    o.rdi_ttal,
                ]
                for o in otros
            ],
            "Otros equipos",
        )

    locs = libro.locations.order_by("excel_row")[:300]
    if locs.exists():
        add_table(
            ["Código", "Space", "Zona", "Área"],
            [
                [
                    l.code,
                    (l.space_name or "")[:60],
                    l.zones,
                    str(l.area_m2 or ""),
                ]
                for l in locs
            ],
            "Locations",
        )

    doc.build(story)
    buf.seek(0)
    return buf
