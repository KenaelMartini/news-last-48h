# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from docx2pdf import convert


KMCO_BLUE = RGBColor(0, 51, 153)
GREY_LINE = "BFBFBF"

# --- Regex parsing ---
# Headings: "### 1) Macro Drivers" OR "1) Macro Drivers"
HEADING_RE = re.compile(r"^\s*(?:#{2,6}\s*)?(\d+\)\s+.+?)\s*$")
# Bold and italic segments like **text** and *text*
MD_BOLD_SEG_RE = re.compile(r"\*\*(.+?)\*\*")
MD_BOLD_ITALIC_RE = re.compile(r"\*\*(.+?)\*\*|\*(?!\*)(.+?)\*")


def _add_grey_rule(paragraph):
    """Thin grey bottom border separator."""
    p = paragraph._p
    pPr = p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")     # thin
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), GREY_LINE)
    pBdr.append(bottom)
    pPr.append(pBdr)


def _set_margins(doc: Document, cm: float = 1.0):
    section = doc.sections[0]
    section.top_margin = Cm(cm)
    section.bottom_margin = Cm(cm)
    section.left_margin = Cm(cm)
    section.right_margin = Cm(cm)


def _add_header(doc: Document, report_date: str):
    """
    KM&CO v3 header (text placeholder for logo):
    Left: coords
    Center: desk + date
    Right: brand in blue
    Grey rule separator
    """
    header = doc.sections[0].header
    header.is_linked_to_previous = False

    table = header.add_table(rows=1, cols=3, width=Cm(18))
    table.autofit = True

    left = table.cell(0, 0).paragraphs[0]
    center = table.cell(0, 1).paragraphs[0]
    right = table.cell(0, 2).paragraphs[0]

    # Left
    left_run = left.add_run("Kénael MARTINI\nKenael.martini@orange.fr\nKénael MARTINI & Co. – Lyon")
    left_run.font.size = Pt(9)

    # Center
    center.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c_run = center.add_run(f"FX & Macro Strategy Desk\n{report_date}")
    c_run.font.size = Pt(9)

    # Right
    right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_run = right.add_run("KÉNAEL MARTINI & CO.")
    r_run.font.size = Pt(10)
    r_run.font.color.rgb = KMCO_BLUE

    # Grey separator
    sep = header.add_paragraph("")
    _add_grey_rule(sep)


def _add_footer(doc: Document):
    footer = doc.sections[0].footer
    footer.is_linked_to_previous = False
    p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph("")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    run = p.add_run("KÉNAEL MARTINI & CO. | FX & Macro Strategy Desk | Page ")
    run.font.size = Pt(8)

    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(t)
    fld.append(r)
    p._p.append(fld)

    run2 = p.add_run(" of ")
    run2.font.size = Pt(8)

    fld2 = OxmlElement("w:fldSimple")
    fld2.set(qn("w:instr"), "NUMPAGES")
    r2 = OxmlElement("w:r")
    t2 = OxmlElement("w:t")
    t2.text = "1"
    r2.append(t2)
    fld2.append(r2)
    p._p.append(fld2)


def _render_price_in_block(price_in: Any) -> list[str]:
    # Returns lines. No markdown.
    return [
        f"Status: {getattr(price_in, 'status', 'NA')} | Score: {getattr(price_in, 'score', 'NA')}/100 | Conviction: {float(getattr(price_in, 'conviction', 0.0)):.2f}",
        f"Regime: risk={getattr(getattr(price_in, 'regime', object()), 'risk', 'NA')} vol={getattr(getattr(price_in, 'regime', object()), 'vol', 'NA')} rates={getattr(getattr(price_in, 'regime', object()), 'rates', 'NA')} liq={getattr(getattr(price_in, 'regime', object()), 'liquidity', 'NA')}",
        f"Positioning: {getattr(getattr(price_in, 'positioning', object()), 'bias', 'NA')} | Constraint: {getattr(getattr(price_in, 'positioning', object()), 'constraint', 'NA')}",
        f"Validation: {getattr(price_in, 'validation', 'NA')}",
        f"Binary: {getattr(price_in, 'binary', 'NA')}",
    ]


def _add_title(doc: Document, title: str):
    p = doc.add_paragraph()
    run = p.add_run(title)
    run.bold = True
    run.font.size = Pt(14)
    p.paragraph_format.space_after = Pt(10)


def _add_paragraph_with_md_bold(doc: Document, text: str, *, bullet: bool = False, space_after_pt: int = 4):
    """
    Converts **bold** and *italic* segments into Word bold/italic runs.
    **bold** => bold run, *italic* => italic run; markers are removed.
    """
    if bullet:
        p = doc.add_paragraph(style="List Bullet")
        space_after_pt = 2
    else:
        p = doc.add_paragraph()

    last = 0
    for m in MD_BOLD_ITALIC_RE.finditer(text):
        if m.start() > last:
            p.add_run(text[last:m.start()])
        if m.group(1) is not None:
            rrun = p.add_run(m.group(1))
            rrun.bold = True
        else:
            rrun = p.add_run(m.group(2))
            rrun.italic = True
        last = m.end()

    if last < len(text):
        p.add_run(text[last:])

    p.paragraph_format.space_after = Pt(space_after_pt)


def _is_md_table_line(s: str) -> bool:
    s = s.strip()
    return s.startswith("|") and s.endswith("|")


def _parse_md_table_block(block: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for ln in block:
        ln = ln.strip()
        if not _is_md_table_line(ln):
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        # skip separator row: |---|---|
        if cells and all(c and set(c) <= {"-"} for c in cells):
            continue
        rows.append(cells)
    return rows


def _add_table(doc: Document, rows: list[list[str]]):
    if not rows:
        return
    ncols = max(len(r) for r in rows)
    table = doc.add_table(rows=1, cols=ncols)
    table.style = "Table Grid"

    # header row
    for j, val in enumerate(rows[0]):
        cell = table.rows[0].cells[j]
        p = cell.paragraphs[0]
        run = p.add_run(val)
        run.bold = True

    # body rows
    for r in rows[1:]:
        tr = table.add_row().cells
        for j in range(ncols):
            tr[j].text = r[j] if j < len(r) else ""


def _add_body(doc: Document, body_text: str):
    """
    Parses:
    - headings "### 1) ..." or "1) ..."
    - bullets "- ..." or "• ..."
    - md tables lines starting with |...|
    - converts **bold** segments into Word bold
    """
    lines = body_text.split("\n")
    i = 0

    while i < len(lines):
        raw = lines[i].rstrip()
        line = raw.strip()

        if not line:
            doc.add_paragraph("")
            i += 1
            continue

        # ---- Markdown table block ----
        if _is_md_table_line(line):
            block: list[str] = []
            while i < len(lines) and _is_md_table_line(lines[i].strip()):
                block.append(lines[i].strip())
                i += 1
            rows = _parse_md_table_block(block)
            _add_table(doc, rows)
            doc.add_paragraph("")  # spacing after table
            continue

        # ---- Heading ----
        mh = HEADING_RE.match(line)
        if mh:
            title = mh.group(1).strip()
            p = doc.add_paragraph()
            r = p.add_run(title)
            r.bold = True
            r.font.size = Pt(12)
            p.paragraph_format.space_after = Pt(8)
            doc.add_paragraph("")  # blank line after heading
            i += 1
            continue

        # ---- Bullets ----
        if line.startswith("• "):
            _add_paragraph_with_md_bold(doc, line[2:].strip(), bullet=True)
            i += 1
            continue
        if line.startswith("- "):
            _add_paragraph_with_md_bold(doc, line[2:].strip(), bullet=True)
            i += 1
            continue

        # ---- Default paragraph ----
        _add_paragraph_with_md_bold(doc, line, bullet=False, space_after_pt=4)
        i += 1


def _add_price_in(doc: Document, price_in: Any):
    p = doc.add_paragraph()
    r = p.add_run("Price-In Check")
    r.bold = True
    r.font.size = Pt(12)
    p.paragraph_format.space_after = Pt(6)

    for ln in _render_price_in_block(price_in):
        _add_paragraph_with_md_bold(doc, ln, bullet=False, space_after_pt=2)

    doc.add_paragraph("")  # spacer


def _render_snapshot_lines(snapshot: dict) -> list[str]:
    """
    Snapshot renderer — STRICT
    Source of truth: snapshot dict injected by generate.
    No Yahoo labels. No calculations. Prices only.
    """

    asof = snapshot.get("asof_utc") or "NA"
    fx = snapshot.get("fx") or {}
    comm = snapshot.get("commodities") or {}
    rates = snapshot.get("rates") or {}

    def fmt(v: dict | None) -> str:
        if not v or v.get("price") is None:
            return "NA"
        px = v["price"]
        lag = v.get("lag_seconds")
        if lag is None:
            return str(px)
        stale = " STALE" if lag > 1800 else ""
        return f"{px} *(lag {lag}s)*{stale}"


    lines: list[str] = []

    lines.append(f"As-of (UTC): {asof}")
    lines.append("")

    lines.append("FX (spot):")
    lines.append(f"- EURUSD: {fmt(fx.get('EURUSD'))}")
    lines.append(f"- EURGBP: {fmt(fx.get('EURGBP'))}")
    lines.append(f"- EURJPY: {fmt(fx.get('EURJPY'))}")
    lines.append(f"- EURCHF: {fmt(fx.get('EURCHF'))}")
    lines.append(f"- EURAUD: {fmt(fx.get('EURAUD'))}")
    lines.append(f"- EURCAD: {fmt(fx.get('EURCAD'))}")
    lines.append(f"- EURNZD: {fmt(fx.get('EURNZD'))}")
    lines.append("")

    lines.append("Commodities (futures):")
    lines.append(f"- WTI (cl.f): {fmt(comm.get('WTI'))}")
    lines.append(f"- Gold (gc.f): {fmt(comm.get('Gold'))}")
    lines.append("")

    lines.append("Rates (futures proxies, prices only):")
    lines.append(f"- UST2Y_FUT (zt.f): {fmt(rates.get('UST2Y_FUT'))}")
    lines.append(f"- UST10Y_FUT (zn.f): {fmt(rates.get('UST10Y_FUT'))}")
    lines.append(f"- UST30Y_FUT (zb.f): {fmt(rates.get('UST30Y_FUT'))}")
    lines.append(f"- BUND_FUT (gg.f): {fmt(rates.get('BUND_FUT'))}")

    return lines


def _add_snapshot_section(doc: Document, snapshot: Dict[str, Any]):
    # Heading "2) Market Snapshot" (produit par le code)
    p = doc.add_paragraph()
    r = p.add_run("2) Market Snapshot")
    r.bold = True
    r.font.size = Pt(12)
    p.paragraph_format.space_after = Pt(8)
    doc.add_paragraph("")

    for ln in _render_snapshot_lines(snapshot):
        _add_paragraph_with_md_bold(doc, ln, bullet=False, space_after_pt=2)

    doc.add_paragraph("")


def format_report(
    *,
    report_date: str,
    report_stamp: str,
    body_text: str,
    price_in: Any,
    snapshot: Dict[str, Any],
    out_docx_path: str,
    out_pdf_path: str,
):
    doc = Document()
    _set_margins(doc, cm=1.0)

    _add_header(doc, report_date=report_date)
    _add_footer(doc)

    _add_title(doc, f"Check Macro Session Européenne – {report_date}")
    _add_price_in(doc, price_in=price_in)

    # Snapshot injected by code (source-of-truth), not by LLM
    _add_snapshot_section(doc, snapshot=snapshot)

    # Rest of the report generated by LLM (sections 1,3,4,5,6,7,8)
    _add_body(doc, body_text)

    out_docx = Path(out_docx_path)
    out_docx.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_docx))

    out_pdf = Path(out_pdf_path)
    try:
        convert(str(out_docx), str(out_pdf))
    except Exception as e:
        raise RuntimeError(f"PDF conversion failed (docx2pdf). Word installed? Details: {e}") from e
