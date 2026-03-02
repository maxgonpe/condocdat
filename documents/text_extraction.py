"""
Extracción de texto de archivos (PDF, DOCX, XLS, XLSX) para indexación y búsqueda.
"""
import os
import logging

logger = logging.getLogger(__name__)


def extract_text_from_file(file_field):
    """
    Extrae texto de un archivo (FileField o path).
    Soporta: PDF, DOCX, XLS, XLSX.
    Retorna str o '' si no se puede extraer.
    """
    if not file_field:
        return ""
    path = getattr(file_field, "path", None) or (file_field if isinstance(file_field, (str, os.PathLike)) else None)
    if not path or not os.path.isfile(path):
        return ""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".pdf":
            return _extract_pdf(path)
        if ext in (".docx", ".doc"):
            return _extract_docx(path)
        if ext == ".xls":
            return _extract_xls(path)
        if ext == ".xlsx":
            return _extract_xlsx(path)
    except Exception as e:
        logger.warning("No se pudo extraer texto de %s: %s", path, e)
    return ""


def _extract_pdf(path):
    from pypdf import PdfReader
    reader = PdfReader(path)
    parts = []
    for page in reader.pages:
        try:
            t = page.extract_text()
            if t:
                parts.append(t)
        except Exception:
            pass
    return "\n".join(parts) if parts else ""


def _extract_docx(path):
    from docx import Document as DocxDocument
    doc = DocxDocument(path)
    parts = []
    for p in doc.paragraphs:
        if p.text.strip():
            parts.append(p.text)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    parts.append(cell.text)
    return "\n".join(parts) if parts else ""


def _extract_xls(path):
    """Extrae texto de Excel .xls (Excel 97-2003) usando xlrd."""
    import xlrd
    book = xlrd.open_workbook(path)
    parts = []
    for sheet in book.sheets():
        for row_idx in range(sheet.nrows):
            for col_idx in range(sheet.ncols):
                cell = sheet.cell(row_idx, col_idx)
                if cell.ctype == xlrd.XL_CELL_TEXT and cell.value.strip():
                    parts.append(cell.value)
                elif cell.ctype == xlrd.XL_CELL_NUMBER:
                    parts.append(str(cell.value))
                elif cell.ctype == xlrd.XL_CELL_DATE:
                    parts.append(str(cell.value))
    return "\n".join(parts) if parts else ""


def _extract_xlsx(path):
    """Extrae texto de Excel .xlsx usando openpyxl."""
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    parts = []
    for sheet in wb.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value is not None and str(cell.value).strip():
                    parts.append(str(cell.value))
    wb.close()
    return "\n".join(parts) if parts else ""
