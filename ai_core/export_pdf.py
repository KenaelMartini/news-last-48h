# -*- coding: utf-8 -*-
"""
export_pdf.py — KM&CO Institutional PDF Generator (template v3)
Version : Full CrimsonPro, en-tête non gras
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageTemplate, Frame
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from datetime import datetime
from pathlib import Path
import re
import unicodedata
from reportlab.lib.fonts import addMapping

# =================================================================
# CONFIG
# =================================================================

SOURCE_PATH = Path(r"D:\trading\News Last 48H\out\KMCO_Global_Macro_AI_Report.txt")
PDF_PATH = Path(r"D:\trading\News Last 48H\out\KMCO_Global_Macro_Report.pdf")
FONT_DIR = Path(r"D:\trading\News Last 48H\assets\fonts")

# =================================================================
# FONTS
# =================================================================

regular_font = FONT_DIR / "CrimsonPro-Regular.ttf"
bold_font = FONT_DIR / "CrimsonPro-Bold.ttf"

if not regular_font.exists():
    raise FileNotFoundError(f"❌ Police manquante : {regular_font}")

pdfmetrics.registerFont(TTFont("CrimsonPro-Regular", str(regular_font)))
pdfmetrics.registerFont(TTFont("CrimsonPro-Bold", str(bold_font)))

# Mapping explicite pour éviter l’erreur ps2tt
addMapping("CrimsonPro", 0, 0, "CrimsonPro-Regular")
addMapping("CrimsonPro", 1, 0, "CrimsonPro-Bold")

KMCO_BLUE = colors.HexColor("#1F3A7D")
GREY_LINE = colors.HexColor("#BFBFBF")

# =================================================================
# STYLES
# =================================================================

styles = getSampleStyleSheet()

body = ParagraphStyle(
    "body",
    parent=styles["Normal"],
    fontName="CrimsonPro-Regular",
    fontSize=11,
    leading=15,
    alignment=4,
    spaceAfter=10,
    textColor=colors.black,
)

section_title = ParagraphStyle(
    "section_title",
    parent=styles["Normal"],
    fontName="CrimsonPro-Bold",
    fontSize=11,
    leading=15,
    alignment=0,
    spaceBefore=10,
    spaceAfter=6,
    textColor=colors.black,
)

main_title = ParagraphStyle(
    "main_title",
    parent=styles["Normal"],
    fontName="CrimsonPro-Bold",
    fontSize=13,
    leading=17,
    alignment=0,
    spaceAfter=14,
    textColor=colors.black,
)

# =================================================================
# HEADER & FOOTER
# =================================================================

def header_footer(canvas, doc):
    canvas.saveState()
    width, height = A4

    # Header
    canvas.setFont("CrimsonPro-Regular", 9)
    canvas.drawString(1.5*cm, height - 1.2*cm, "Kénael MARTINI")
    canvas.drawString(1.5*cm, height - 1.7*cm, "Kenaelmartini@gmail.com")
    canvas.drawString(1.5*cm, height - 2.2*cm, "Kénael MARTINI & Co. – Lyon")

    canvas.drawCentredString(width/2, height - 1.3*cm, "FX & Macro Strategy Desk")
    canvas.drawCentredString(width/2, height - 1.8*cm, datetime.now().strftime("%d %B %Y"))

    canvas.setFillColor(KMCO_BLUE)
    canvas.drawRightString(width - 1.5*cm, height - 1.5*cm, "KÉNAEL MARTINI & CO.")
    canvas.setFillColor(colors.black)

    # Ligne grise
    canvas.setStrokeColor(GREY_LINE)
    canvas.setLineWidth(0.4)
    canvas.line(1.5*cm, height - 2.8*cm, width - 1.5*cm, height - 2.8*cm)

    # Footer
    canvas.setFont("CrimsonPro-Regular", 8.5)
    page_num = doc.page
    canvas.drawRightString(
        width - 1.5*cm,
        1.2*cm,
        f"KÉNAEL MARTINI & CO. | FX & Macro Strategy Desk | Page {page_num}"
    )

    canvas.restoreState()

# =================================================================
# BUILD PDF
# =================================================================

def normalize_text(text):
    # Garde les accents, supprime seulement les caractères invisibles
    return unicodedata.normalize("NFC", text)

def build_pdf():
    text = SOURCE_PATH.read_text(encoding="utf-8")
    text = normalize_text(text)

    replacements = {
        "—": "-", "–": "-", "•": "-", "‣": "-",
        "■": "-", "●": "-", "▪": "-",
        "“": "\"", "”": "\"", "‘": "'", "’": "'",
        "«": "\"", "»": "\"",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    text = re.sub(r"^Analyse\s+Globale\s+du\s+Marché\s*[-–]\s*\d{1,2}\s+\w+\s+\d{4}", "", text, flags=re.MULTILINE)

    sections = text.split("\n\n")
    story = []

    date_str = datetime.now().strftime("%d %B %Y")
    story.append(Paragraph(f"Analyse Globale du Marché – {date_str}", main_title))
    story.append(Spacer(1, 0.3*cm))

    for section in sections:
        if not section.strip():
            continue
        if re.match(r"^\d+\.\s", section.strip()):
            story.append(Paragraph(section.strip(), section_title))
        else:
            story.append(Paragraph(section.strip().replace("\n", "<br/>"), body))
        story.append(Spacer(1, 0.4*cm))

    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm,
        topMargin=3.2*cm,
        bottomMargin=2.2*cm,
    )

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="KMCO", frames=[frame], onPage=header_footer)
    doc.addPageTemplates([template])
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)

    print(f"✅ Rapport PDF généré avec succès → {PDF_PATH}")

# =================================================================
# MAIN
# =================================================================

if __name__ == "__main__":
    build_pdf()
