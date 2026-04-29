#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


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


def collect_professionals(base_dir: Path) -> dict[str, list[Professional]]:
    people: dict[tuple[str, str], Professional] = {}

    for png in sorted(base_dir.glob("*.png")):
        stem = png.stem
        match = FILENAME_RE.match(stem)
        if not match:
            continue

        specialty = normalize_specialty(match.group("spec"))
        name_slug = match.group("name")
        kind = match.group("kind")
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

    for specialty in grouped:
        grouped[specialty].sort(key=lambda p: p.full_name.lower())

    return dict(grouped)


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for font_path in candidates:
        path = Path(font_path)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int) -> ImageFont.ImageFont:
    size = start_size
    while size >= 28:
        font = load_font(size, bold=True)
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            return font
        size -= 2
    return load_font(28, bold=True)


def draw_centered_text(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, font: ImageFont.ImageFont, color: tuple[int, int, int]) -> None:
    left, top, right, bottom = box
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = left + (right - left - tw) // 2
    y = top + (bottom - top - th) // 2 - 2
    draw.text((x, y), text, fill=color, font=font)


def paste_qr(canvas: Image.Image, qr_path: Path | None, box: tuple[int, int, int, int]) -> None:
    if not qr_path or not qr_path.exists():
        return
    left, top, right, bottom = box
    target_w = right - left
    target_h = bottom - top
    qr = Image.open(qr_path).convert("RGB")
    qr = qr.resize((target_w, target_h), Image.Resampling.LANCZOS)
    canvas.paste(qr, (left, top))


def render_one_page(template: Image.Image, specialty_label: str, left: Professional | None, right: Professional | None) -> Image.Image:
    page = template.copy().convert("RGB")
    draw = ImageDraw.Draw(page)

    # Cover fixed "ELECTRICA" label from base template and inject dynamic specialty.
    draw.rounded_rectangle((210, 95, 790, 230), radius=26, fill=(1, 33, 99))
    spec_font = fit_text(draw, specialty_label, max_width=550, start_size=72)
    draw_centered_text(draw, (220, 105, 780, 220), specialty_label, spec_font, (255, 214, 0))

    # Name boxes.
    slots = [
        ((42, 590, 465, 710), (42, 832, 253, 1145), (257, 832, 468, 1145)),
        ((557, 590, 979, 710), (558, 832, 769, 1145), (773, 832, 984, 1145)),
    ]
    people = [left, right]

    for person, (name_box, phone_box, wa_box) in zip(people, slots, strict=True):
        if person is None:
            continue
        name = person.full_name
        name_font = fit_text(draw, name, max_width=(name_box[2] - name_box[0]) - 20, start_size=66)
        draw_centered_text(draw, name_box, name, name_font, (255, 255, 255))
        paste_qr(page, person.phone_qr, phone_box)
        paste_qr(page, person.whatsapp_qr, wa_box)

    return page


def format_specialty_label(specialty: str) -> str:
    if specialty in SPECIALTY_LABELS:
        return SPECIALTY_LABELS[specialty]
    return specialty.replace("-", " ").upper()


def build_outputs(base_dir: Path, output_dir: Path, use_model_template: bool = True) -> list[Path]:
    template_path = base_dir / ("modelo-plantilla.png" if use_model_template else "modelo_plantilla.png")
    if not template_path.exists():
        raise FileNotFoundError(f"No se encontro la plantilla: {template_path}")

    grouped = collect_professionals(base_dir)
    if not grouped:
        raise RuntimeError("No se encontraron archivos QR con patron valido.")

    template = Image.open(template_path).convert("RGB")
    output_dir.mkdir(parents=True, exist_ok=True)

    generated: list[Path] = []
    for specialty in sorted(grouped):
        pros = grouped[specialty]
        pages: list[Image.Image] = []
        total_pages = math.ceil(len(pros) / 2)
        for idx in range(total_pages):
            left = pros[idx * 2]
            right = pros[idx * 2 + 1] if idx * 2 + 1 < len(pros) else None
            page = render_one_page(template, format_specialty_label(specialty), left, right)
            pages.append(page)

        out_pdf = output_dir / f"letreros_{specialty}.pdf"
        pages[0].save(str(out_pdf), "PDF", save_all=True, append_images=pages[1:], resolution=300.0)
        generated.append(out_pdf)

    # Consolidated PDF across all specialties.
    all_pages: list[Image.Image] = []
    for specialty in sorted(grouped):
        pros = grouped[specialty]
        for idx in range(math.ceil(len(pros) / 2)):
            left = pros[idx * 2]
            right = pros[idx * 2 + 1] if idx * 2 + 1 < len(pros) else None
            all_pages.append(render_one_page(template, format_specialty_label(specialty), left, right))

    merged_pdf = output_dir / "letreros_todos.pdf"
    all_pages[0].save(str(merged_pdf), "PDF", save_all=True, append_images=all_pages[1:], resolution=300.0)
    generated.append(merged_pdf)

    report = output_dir / "reporte_qr_faltantes.txt"
    with report.open("w", encoding="utf-8") as f:
        for specialty in sorted(grouped):
            for prof in grouped[specialty]:
                missing = []
                if not prof.phone_qr:
                    missing.append("telefono")
                if not prof.whatsapp_qr:
                    missing.append("whatsapp")
                if missing:
                    f.write(f"{specialty} | {prof.full_name} | faltante: {', '.join(missing)}\n")
    generated.append(report)

    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera letreros con QR por especialidad")
    parser.add_argument("--base-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "output_letreros")
    args = parser.parse_args()

    generated = build_outputs(args.base_dir, args.output_dir)
    print("Archivos generados:")
    for path in generated:
        print(f"- {path}")


if __name__ == "__main__":
    main()
