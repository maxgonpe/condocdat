#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import math
import re
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

VENV_QR_PYTHON = Path(__file__).resolve().parent / ".venv_qr" / "bin" / "python"


FILENAME_RE = re.compile(
    r"^(?P<spec>[a-z0-9]+)-(?P<name>[a-z0-9-]+)-(?P<kind>telefono|whatsapp)(?:-300x300)?-?$"
)

SPECIALTY_LABELS = {
    "elect": "ELECTRICA",
    "clima": "CLIMATIZACION",
    "civil": "OBRAS CIVILES",
    "calidad": "CALIDAD",
    "tens": "PRIMEROS AUXILIOS",
    "ten": "PRIMEROS AUXILIOS",
    "bms": "BMS",
    "ehs": "EHS",
    "otec": "OTEC",
    "rrhh": "RRHH",
}


@dataclass
class Professional:
    specialty: str
    name_slug: str
    phone_qr: Path | None = None
    whatsapp_qr: Path | None = None

    @property
    def full_name(self) -> str:
        return " ".join(part.capitalize() for part in self.name_slug.split("-"))


def normalize_specialty(raw: str) -> str:
    aliases = {
        "clidad": "calidad",
        "ten": "tens",
    }
    return aliases.get(raw, raw)


def format_specialty_label(specialty: str) -> str:
    if specialty in SPECIALTY_LABELS:
        return SPECIALTY_LABELS[specialty]
    return specialty.replace("-", " ").upper()


def collect_professionals(base_dir: Path) -> dict[str, list[Professional]]:
    people: dict[tuple[str, str], Professional] = {}
    for png in sorted(base_dir.glob("*.png")):
        m = FILENAME_RE.match(png.stem)
        if not m:
            continue
        specialty = normalize_specialty(m.group("spec"))
        name_slug = m.group("name")
        kind = m.group("kind")
        key = (specialty, name_slug)
        if key not in people:
            people[key] = Professional(specialty=specialty, name_slug=name_slug)
        if kind == "telefono":
            people[key].phone_qr = png
        else:
            people[key].whatsapp_qr = png

    grouped: dict[str, list[Professional]] = defaultdict(list)
    for prof in people.values():
        grouped[prof.specialty].append(prof)
    for spec in grouped:
        grouped[spec].sort(key=lambda p: p.full_name.lower())
    return dict(grouped)


def qr_cell(image_path: Path | None, label: str) -> str:
    if image_path and image_path.exists():
        src = html.escape(str(image_path.resolve()).replace("\\", "/"))
        img = f'<img src="file://{src}" alt="{label}" />'
    else:
        img = '<div class="missing">QR faltante</div>'
    return f"""
    <div class="qr-box">
      <div class="qr-label">{html.escape(label)}</div>
      {img}
    </div>
    """


def format_phone_label(payload: str) -> str:
    payload = payload.strip()
    match = re.search(r"(?:tel:)?\+?569\s*(\d{8})", payload, re.I)
    if not match:
        compact = re.sub(r"\D", "", payload)
        compact = compact[3:] if compact.startswith("569") else compact
        if len(compact) == 8:
            match_num = compact
        else:
            return ""
    else:
        match_num = match.group(1)
    return f"+56 9 {match_num[:4]} {match_num[4:]}"


def decode_phone_label(phone_qr: Path | None) -> str:
    if not phone_qr or not phone_qr.exists() or not VENV_QR_PYTHON.exists():
        return ""
    code = (
        "from PIL import Image\n"
        "from pyzbar.pyzbar import decode\n"
        "import sys\n"
        "d = decode(Image.open(sys.argv[1]))\n"
        "print(d[0].data.decode('utf-8') if d else '')\n"
    )
    try:
        result = subprocess.run(
            [str(VENV_QR_PYTHON), "-c", code, str(phone_qr)],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ""
    if result.returncode != 0:
        return ""
    return format_phone_label(result.stdout)


def professional_card(person: Professional | None) -> str:
    if person is None:
        return '<div class="card empty"></div>'
    name = html.escape(person.full_name)
    phone_label = decode_phone_label(person.phone_qr)
    phone_html = f'<div class="phone-label">{html.escape(phone_label)}</div>' if phone_label else ""
    return f"""
    <div class="card">
      <div class="name">{name}</div>
      <table class="qr-table">
        <tr>
          <td>{qr_cell(person.phone_qr, "LLAMAR")}</td>
          <td>{qr_cell(person.whatsapp_qr, "WHATSAPP")}</td>
        </tr>
      </table>
      {phone_html}
    </div>
    """


def page_block(spec_label: str, left: Professional | None, right: Professional | None) -> str:
    return f"""
    <section class="page">
      <div class="header">{html.escape(spec_label)}</div>
      <div class="cards vertical">
        {professional_card(left)}
        {professional_card(right)}
      </div>
    </section>
    """


def build_html_document(title: str, pages_html: list[str], force_page_breaks: bool = True) -> str:
    page_break_css = """
    .page { page-break-after: always; }
    .page:last-child { page-break-after: auto; }
    """ if force_page_breaks else """
    .page { page-break-after: auto; }
    """
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(title)}</title>
  <style>
    @page {{ size: A4 portrait; margin: 5mm; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, sans-serif; color: #08255e; }}
    .page {{ width: 100%; min-height: 286mm; display: flex; flex-direction: column; }}
    {page_break_css}
    .header {{
      font-weight: 700; text-align: center; font-size: 20pt;
      background: #0a2f7f; color: #ffd300; border-radius: 8px;
      padding: 6px; margin-bottom: 6px;
    }}
    .cards {{ display: table; width: 100%; table-layout: fixed; border-spacing: 6px; }}
    .cards.vertical {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      flex: 1;
    }}
    .card {{
      display: block; width: 100%;
      border: 1px solid #123f9c; border-radius: 8px; padding: 8px;
      flex: 1;
    }}
    .card.empty {{ border-style: dashed; }}
    .name {{
      background: #0a2f7f; color: #fff; text-align: center; font-size: 17pt;
      font-weight: 700; border-radius: 6px; padding: 6px; margin-bottom: 6px;
      min-height: 36px;
    }}
    .qr-table {{
      width: 100%;
      border-collapse: separate;
      border-spacing: 8px;
      table-layout: fixed;
    }}
    .qr-table td {{
      vertical-align: top;
      width: 50%;
      padding: 0;
    }}
    .qr-box {{
      display: block; width: 100%; border: 1px solid #0f5cd1;
      border-radius: 8px; padding: 8px; text-align: center;
    }}
    .qr-label {{
      font-size: 12pt; font-weight: 700; margin-bottom: 6px;
      color: #0f5cd1;
    }}
    .qr-box img {{ width: 100%; max-width: 185px; height: auto; }}
    .phone-label {{
      margin-top: 8px;
      font-size: 13pt;
      text-align: center;
      font-weight: 700;
      color: #05286f;
    }}
    .missing {{ color: #a00; font-weight: 700; margin: 30px 0; }}
  </style>
</head>
<body>
{''.join(pages_html)}
</body>
</html>
"""


def convert_html_to_docx(html_path: Path, output_dir: Path) -> Path:
    cmd = [
        "libreoffice",
        "--headless",
        "--convert-to",
        "docx:MS Word 2007 XML",
        str(html_path),
        "--outdir",
        str(output_dir),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output_path = output_dir / f"{html_path.stem}.docx"
    for _ in range(20):
        if output_path.exists():
            break
        time.sleep(0.1)
    if not output_path.exists():
        raise RuntimeError(f"No se pudo generar DOCX para {html_path.name}")
    return output_path


def build_outputs(base_dir: Path, output_dir: Path) -> list[Path]:
    grouped = collect_professionals(base_dir)
    if not grouped:
        raise RuntimeError("No se encontraron PNG de QR con patron valido.")
    output_dir.mkdir(parents=True, exist_ok=True)

    generated: list[Path] = []
    all_pages: list[str] = []

    for specialty in sorted(grouped):
        pros = grouped[specialty]
        pages: list[str] = []
        total_pages = math.ceil(len(pros) / 2)
        for idx in range(total_pages):
            left = pros[idx * 2]
            right = pros[idx * 2 + 1] if idx * 2 + 1 < len(pros) else None
            spec_label = format_specialty_label(specialty)
            page_html = page_block(spec_label, left, right)
            pages.append(page_html)
            all_pages.append(page_html)

        html_path = output_dir / f"letreros_{specialty}.html"
        html_path.write_text(
            build_html_document(f"Letreros {specialty}", pages, force_page_breaks=False),
            encoding="utf-8",
        )
        docx_path = convert_html_to_docx(html_path, output_dir)
        generated.append(docx_path)
        html_path.unlink(missing_ok=True)

    all_html = output_dir / "letreros_todos.html"
    all_html.write_text(
        build_html_document("Letreros - Todos", all_pages, force_page_breaks=True),
        encoding="utf-8",
    )
    all_docx = convert_html_to_docx(all_html, output_dir)
    generated.append(all_docx)
    all_html.unlink(missing_ok=True)

    report_path = output_dir / "reporte_qr_faltantes.txt"
    with report_path.open("w", encoding="utf-8") as report:
        for specialty in sorted(grouped):
            for prof in grouped[specialty]:
                missing = []
                if not prof.phone_qr:
                    missing.append("telefono")
                if not prof.whatsapp_qr:
                    missing.append("whatsapp")
                if missing:
                    report.write(f"{specialty} | {prof.full_name} | faltante: {', '.join(missing)}\n")
    generated.append(report_path)
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera letreros QR en formato DOCX editable")
    parser.add_argument("--base-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "output_letreros")
    args = parser.parse_args()

    generated = build_outputs(args.base_dir, args.output_dir)
    print("Archivos generados:")
    for item in generated:
        print(f"- {item}")


if __name__ == "__main__":
    main()
