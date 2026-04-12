#!/usr/bin/env python3
"""One-off xlsx inspector using only stdlib (no openpyxl)."""
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def col_row(cell_ref: str):
    m = re.match(r"^([A-Z]+)(\d+)$", cell_ref.replace("$", ""))
    if not m:
        return None, None
    letters, row = m.group(1), int(m.group(2))
    col = 0
    for c in letters:
        col = col * 26 + (ord(c) - ord("A") + 1)
    return col, row


def load_shared_strings(z: zipfile.ZipFile):
    try:
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    out = []
    for si in root.findall("m:si", NS):
        texts = []
        for t in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"):
            if t.text:
                texts.append(t.text)
            if t.tail:
                texts.append(t.tail)
        out.append("".join(texts).strip())
    return out


def sheet_to_grid(z: zipfile.ZipFile, path: str, shared: list, max_row=40):
    root = ET.fromstring(z.read(path))
    grid = {}
    max_c, max_r = 0, 0
    for c in root.findall(".//m:c", NS):
        ref = c.get("r")
        if not ref:
            continue
        col, row = col_row(ref)
        if row is None:
            continue
        max_c = max(max_c, col)
        max_r = max(max_r, row)
        t = c.get("t")
        v_el = c.find("m:v", NS)
        is_el = c.find("m:is", NS)
        val = None
        if t == "s" and v_el is not None and v_el.text is not None:
            try:
                val = shared[int(v_el.text)]
            except (ValueError, IndexError):
                val = v_el.text
        elif is_el is not None:
            t_el = is_el.find(".//m:t", NS)
            val = t_el.text if t_el is not None else ""
        elif v_el is not None:
            val = v_el.text
        grid[(row, col)] = val
    # print rows 1..max_row
    lines = []
    for r in range(1, min(max_row, max_r) + 1):
        row_vals = []
        for c in range(1, max_c + 1):
            row_vals.append(grid.get((r, c), ""))
        if any(str(x).strip() for x in row_vals):
            lines.append((r, row_vals))
    return lines, max_r, max_c


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/home/max/condocdat/doc/ST01-EXP F5-E2_Control de equipos_2026-10-04.xlsx"
    with zipfile.ZipFile(path, "r") as z:
        shared = load_shared_strings(z)
        sheets = [
            ("sheet1.xml", "Resumen - TD"),
            ("sheet2.xml", "Significado status"),
            ("sheet3.xml", "Locations"),
            ("sheet4.xml", "Asset"),
            ("sheet5.xml", "Otros equipos"),
        ]
        for fname, title in sheets:
            print("###", title, "(", fname, ")")
            lines, mr, mc = sheet_to_grid(z, f"xl/worksheets/{fname}", shared, max_row=35)
            for r, row in lines[:25]:
                preview = [x if x is not None else "" for x in row[:22]]
                print(r, preview)
            print(f"   ... max_row~{mr} max_col~{mc}\n")


if __name__ == "__main__":
    main()
