#!/usr/bin/env python3
"""
Letrero 2 profesionales por hoja (tel + WhatsApp), especialidad configurable.
Tamano QR via atributos width/height en <img> (LibreOffice respeta mejor que solo CSS).

Numeros bajo el nombre: se obtienen decodificando el QR de telefono (tel:+569...)
Requiere ImageMagick `convert` y, para decodificar, el entorno .venv_qr con pyzbar:
  cd doc/letreros && python3 -m venv .venv_qr && .venv_qr/bin/pip install pyzbar pillow
"""
from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "output_letreros"
VENV_PYTHON = BASE_DIR / ".venv_qr" / "bin" / "python"

DEFAULT_QR_PX = 260

TITULO_POR_PREFIJO: dict[str, str] = {
    "electrica": "ELECTRICA",
    "clima": "CLIMATIZACION",
    "bms": "BMS",
}


def tel_payload_a_etiqueta(payload: str) -> str:
    """tel:+56994369022 -> +56 9 9436 9022"""
    payload = payload.strip()
    m = re.search(r"(?:tel:)?\+?569\s*(\d{8})", payload, re.I)
    if not m:
        m = re.search(r"569\s*(\d{8})", payload.replace(" ", ""))
    if not m:
        return ""
    rest = m.group(1)
    return f"+56 9 {rest[:4]} {rest[4:]}"


def decode_qr_svg_payload(svg_path: Path) -> str:
    """Devuelve cadena cruda del QR (tel:... o https://wa.me/...) o ''."""
    if not VENV_PYTHON.exists():
        return ""
    png = OUT_DIR / f".decode_tmp_{svg_path.stem}.png"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["convert", str(svg_path), "-resize", "800x800", str(png)],
            check=True,
            capture_output=True,
            text=True,
        )
        code = (
            "from PIL import Image\n"
            "from pyzbar.pyzbar import decode\n"
            "import sys\n"
            "d = decode(Image.open(sys.argv[1]))\n"
            "print(d[0].data.decode('utf-8') if d else '')\n"
        )
        rc = subprocess.run(
            [str(VENV_PYTHON), "-c", code, str(png)],
            capture_output=True,
            text=True,
        )
        return rc.stdout.strip() if rc.returncode == 0 else ""
    except (subprocess.CalledProcessError, OSError, IndexError):
        return ""
    finally:
        png.unlink(missing_ok=True)


def qr_block(label: str, svg_path: Path, size_px: int) -> str:
    src = html.escape(str(svg_path.resolve()).replace("\\", "/"))
    w = h = int(size_px)
    return f"""
    <div class="qr-box">
      <div class="qr-tag">{html.escape(label)}</div>
      <img
        src="file://{src}"
        alt="{html.escape(label)}"
        width="{w}"
        height="{h}"
        style="width:{w}px; height:{h}px; display:block; margin:0 auto;"
      />
    </div>
    """


def card(name: str, telefono_etiqueta: str, tel_svg: Path, wa_svg: Path, size_px: int) -> str:
    phone_html = ""
    if telefono_etiqueta.strip():
        phone_html = f'<div class="phone-line">{html.escape(telefono_etiqueta.strip())}</div>'
    return f"""
    <tr>
      <td class="card-cell">
        <div class="name-bar">{html.escape(name)}</div>
        {phone_html}
        <table class="qr-table" width="100%" border="0" cellspacing="0" cellpadding="0">
          <tr>
            <td width="50%" align="center" valign="top">{qr_block("LLAMAR", tel_svg, size_px)}</td>
            <td width="50%" align="center" valign="top">{qr_block("WHATSAPP", wa_svg, size_px)}</td>
          </tr>
        </table>
      </td>
    </tr>
    """


def descubrir_pares(prefijo: str) -> list[tuple[str, Path, Path]]:
    """Lista de (nombre_mostrar, telefono.svg, whatsapp.svg) ordenado por nombre."""
    pares: list[tuple[str, Path, Path]] = []
    pat = re.compile(rf"^{re.escape(prefijo)}-(?P<slug>.+)-telefono\.svg$", re.I)
    for tel in sorted(BASE_DIR.glob(f"{prefijo}-*-telefono.svg")):
        m = pat.match(tel.name)
        if not m:
            continue
        slug = m.group("slug")
        wa = BASE_DIR / f"{prefijo}-{slug}-whatsapp.svg"
        if not wa.exists():
            continue
        nombre = " ".join(part.capitalize() for part in slug.split("-"))
        pares.append((nombre, tel, wa))
    pares.sort(key=lambda x: x[0].lower())
    return pares


def build_html(prefijo: str, titulo: str, size_px: int) -> str:
    pares = descubrir_pares(prefijo)
    if len(pares) != 2:
        raise ValueError(
            f"Se esperaban exactamente 2 profesionales con prefijo {prefijo!r}; "
            f"encontrados: {len(pares)}. Archivos: "
            + ", ".join(str(p[1].name) for p in pares)
        )
    bloques_cards = []
    for nombre, tel_svg, wa_svg in pares:
        raw = decode_qr_svg_payload(tel_svg)
        if raw.startswith("tel:"):
            etiqueta = tel_payload_a_etiqueta(raw)
        elif "wa.me/" in raw:
            num = raw.split("wa.me/")[-1].strip("/").lstrip("+")
            etiqueta = tel_payload_a_etiqueta(f"tel:+{num}")
        else:
            etiqueta = tel_payload_a_etiqueta(raw)
        bloques_cards.append(card(nombre, etiqueta or "", tel_svg, wa_svg, size_px))
    cards_html = "\n".join(bloques_cards)

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>Letrero {html.escape(titulo)}</title>
  <style>
    @page {{ size: A4 portrait; margin: 6mm; }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      color: #08255e;
      background: #ffffff;
    }}
    .page-outer {{
      width: 100%;
      height: 275mm;
      border-collapse: collapse;
    }}
    .page-outer td {{
      padding: 0;
    }}
    .sheet {{
      text-align: left;
      width: 92%;
      max-width: 180mm;
      margin: 0 auto;
      border: 2px solid #123f9c;
      border-radius: 10px;
      padding: 6px;
    }}
    .head {{
      background: #05286f;
      color: #ffd300;
      font-size: 24pt;
      font-weight: 700;
      text-align: center;
      border-radius: 8px;
      padding: 6px 5px;
      margin-bottom: 6px;
      letter-spacing: 0.5px;
    }}
    .hint {{
      background: #eaf0fb;
      border: 1px solid #123f9c;
      border-radius: 8px;
      text-align: center;
      font-size: 10.5pt;
      padding: 4px 5px;
      margin-bottom: 6px;
    }}
    .cards {{
      width: 100%;
      border-collapse: separate;
      border-spacing: 0 6px;
      table-layout: fixed;
    }}
    .card-cell {{
      border: 1px solid #123f9c;
      border-radius: 8px;
      padding: 4px 5px;
      background: #ffffff;
    }}
    .name-bar {{
      background: #0a2f7f;
      color: #ffffff;
      text-align: center;
      font-size: 16pt;
      font-weight: 700;
      border-radius: 8px;
      padding: 4px;
      margin-bottom: 2px;
    }}
    .phone-line {{
      text-align: center;
      font-size: 11pt;
      font-weight: 700;
      color: #05286f;
      margin-bottom: 6px;
      letter-spacing: 0.3px;
    }}
    .qr-table {{
      width: 100%;
      border-collapse: separate;
      border-spacing: 4px 0;
      table-layout: fixed;
    }}
    .qr-table td {{
      width: 50%;
      vertical-align: top;
    }}
    .qr-box {{
      border: 1px solid #0f5cd1;
      border-radius: 8px;
      padding: 2px 3px 3px;
      text-align: center;
    }}
    .qr-tag {{
      color: #0f5cd1;
      font-size: 9pt;
      font-weight: 700;
      margin-bottom: 2px;
    }}
  </style>
</head>
<body>
  <table class="page-outer" width="100%" height="100%" border="0" cellspacing="0" cellpadding="0">
    <tr>
      <td align="center" valign="middle" width="100%" height="100%">
        <div class="sheet">
    <div class="head">{html.escape(titulo)}</div>
    <div class="hint">Escanee el codigo QR segun el medio de contacto que prefiera.</div>
    <table class="cards" width="100%" border="0" cellspacing="0" cellpadding="0">
      {cards_html}
    </table>
        </div>
      </td>
    </tr>
  </table>
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
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    out = output_dir / f"{html_path.stem}.docx"
    if not out.exists():
        raise RuntimeError("No se pudo generar el DOCX")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Letrero 2 profesionales por especialidad (SVG)")
    ap.add_argument(
        "--prefijo",
        type=str,
        required=True,
        help='Prefijo de archivos en carpeta letreros, ej. "electrica", "clima"',
    )
    ap.add_argument("--titulo", type=str, default="", help='Titulo del encabezado (default segun prefijo)')
    ap.add_argument("--qr-px", type=int, default=DEFAULT_QR_PX)
    ap.add_argument("--out-name", type=str, default="", help="Base nombre salida (default letrero_<prefijo>_2_profesionales)")
    args = ap.parse_args()

    prefijo = args.prefijo.strip().lower()
    titulo = args.titulo.strip().upper() if args.titulo.strip() else TITULO_POR_PREFIJO.get(prefijo, prefijo.upper())
    out_base_default = f"letrero_{prefijo}_2_profesionales"
    out_base = args.out_name.strip() or out_base_default

    try:
        html_body = build_html(prefijo, titulo, args.qr_px)
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{out_base}_qr{args.qr_px}px"
    html_path = OUT_DIR / f"{stem}.html"
    html_path.write_text(html_body, encoding="utf-8")
    docx_path = convert_html_to_docx(html_path, OUT_DIR)
    html_path.unlink(missing_ok=True)

    alias = OUT_DIR / f"{out_base}.docx"
    try:
        import shutil

        shutil.copyfile(docx_path, alias)
    except OSError:
        pass

    print(f"Generado: {docx_path}")
    if alias.exists():
        print(f"Copia:    {alias}")
    print(f"QR px: {args.qr_px}")
    if not VENV_PYTHON.exists():
        print(
            "Aviso: sin .venv_qr/pybar no se muestra telefono bajo el nombre; "
            "ver docstring del script.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
