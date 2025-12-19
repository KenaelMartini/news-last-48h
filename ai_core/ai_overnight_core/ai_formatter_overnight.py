from datetime import datetime
from docx import Document
from docx.shared import Pt, RGBColor, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import re
from pathlib import Path

KMCO_BLUE = RGBColor(0, 51, 153)
GREY_LINE = "BFBFBF"

# Regex titres
HEADER_RE = re.compile(
    r'^\s*(?:\d+\s*[.)]\s*)?('
    r'Top\s+Overnight\s+Drivers|'
    r'Central\s+Banks|'
    r'Market\s+Snapshot\s*\(FX,\s*Rates,\s*Commodities\)|'
    r'FX\s+Bias|'
    r'Sc[ée]narios\s+Binaires|'
    r'Conclusion|'
    r'Implication\s+du\s+desk\s*\(.*?\)'
    r')\s*:?\s*$',
    re.IGNORECASE
)

def _add_bottom_rule_in_header(header_paragraph):
    p = header_paragraph._p
    pPr = p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:color'), GREY_LINE)
    pBdr.append(bottom)
    pPr.append(pBdr)

def _add_page_field(paragraph):
    r = paragraph.add_run()
    fldBegin = OxmlElement('w:fldChar')
    fldBegin.set(qn('w:fldCharType'), 'begin')
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = ' PAGE '
    fldSep = OxmlElement('w:fldChar')
    fldSep.set(qn('w:fldCharType'), 'separate')
    fldEnd = OxmlElement('w:fldChar')
    fldEnd.set(qn('w:fldCharType'), 'end')
    r._r.extend([fldBegin, instr, fldSep, fldEnd])


def format_report(raw_text: str, date=None):
    d = date or datetime.now()
    doc = Document()

    # ===== STYLE NORMAL INSTITUTIONNEL =====
    base = doc.styles["Normal"].font
    base.name = "Crimson Pro"
    base.size = Pt(11)

    # ===== STYLE DE TITRE KMCO =====
    styles = doc.styles
    if "KMCO_Title" not in styles:
        title_style = styles.add_style("KMCO_Title", 1)  # 1 = paragraph style
        title_font = title_style.font
        title_font.name = "Crimson Pro"
        title_font.size = Pt(12)
        title_font.bold = True

    # Marges
    section = doc.sections[0]
    section.top_margin = Cm(2.8)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    section.header_distance = Cm(1.0)
    section.footer_distance = Cm(1.0)

    # ====================== HEADER =========================
    hdr = section.header
    table = hdr.add_table(rows=1, cols=3, width=Inches(6.5))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.columns[0].width = Cm(7)
    table.columns[1].width = Cm(6)
    table.columns[2].width = Cm(7)

    # Left
    left = table.cell(0, 0).paragraphs[0]
    left.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run_l = left.add_run(
        "Kénael MARTINI\n"
        "Kenael.martini@orange.fr\n"
        "Kénael MARTINI & Co. – Lyon"
    )
    run_l.font.size = Pt(9)

    # Center
    center = table.cell(0, 1).paragraphs[0]
    center.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_c = center.add_run(f"FX & Macro Strategy Desk\n{d.strftime('%d %B %Y')}")
    run_c.font.size = Pt(9)

    # Right
    right = table.cell(0, 2).paragraphs[0]
    right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_r = right.add_run("KÉNAEL MARTINI & CO.")
    run_r.font.size = Pt(9)
    run_r.font.color.rgb = KMCO_BLUE

    hr_para = hdr.add_paragraph()
    _add_bottom_rule_in_header(hr_para)

    # ====================== CORPS =========================
    lines = raw_text.replace("\r\n", "\n").split("\n")
    body_buffer = []

    def flush_body():
        if not body_buffer:
            return
        txt = " ".join(s.strip() for s in body_buffer).strip()
        if txt:
            p = doc.add_paragraph(txt)
            p.style = doc.styles["Normal"]
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.space_after = Pt(8)
        body_buffer.clear()

    for line in lines:
        if HEADER_RE.match(line):
            flush_body()
            title = HEADER_RE.match(line).group(1)

            p = doc.add_paragraph()
            p.style = doc.styles["KMCO_Title"]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.space_before = Pt(6)
            p.space_after = Pt(6)

            p.add_run(title.strip().rstrip(":"))
            continue

        elif line.strip() == "":
            flush_body()
        else:
            body_buffer.append(line)

    flush_body()

    # ====================== FOOTER =========================
    ftr = section.footer.paragraphs[0] if section.footer.paragraphs else section.footer.add_paragraph()
    ftr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    ftr.text = "KÉNAEL MARTINI & CO. | FX & Macro Strategy Desk | Page "
    _add_page_field(ftr)

    for run in ftr.runs:
        run.font.size = Pt(8.5)

    # ====================== SAUVEGARDE =========================
    base_dir = Path("D:/trading/News Last 48H/KMCO_out/Overnight_check")
    base_dir.mkdir(parents=True, exist_ok=True)

    timestamp = d.strftime("%Y-%m-%d_%H-%M-%S")
    output_path = base_dir / f"report_overnight_{timestamp}.docx"
    doc.save(str(output_path))

    print(f"✅ Rapport institutionnel Word généré : {output_path}")
    return str(output_path)
