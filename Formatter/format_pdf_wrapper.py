# format_pdf_wrapper.py
import os
from datetime import datetime
from pdf2image import convert_from_path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# === Chemin ABSOLU vers les fonts ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, "fonts")

pdfmetrics.registerFont(TTFont("CrimsonPro", os.path.join(FONT_DIR, "CrimsonPro-Regular.ttf")))
pdfmetrics.registerFont(TTFont("CrimsonPro-Bold", os.path.join(FONT_DIR, "CrimsonPro-Bold.ttf")))

# Poppler
POPLER_BIN = r"D:\poppler\poppler-24.08.0\Library\bin"

# Couleurs KM&CO
KMCO_BLUE = HexColor("#003399")
GREY_LINE = HexColor("#BFBFBF")

PAGE_W, PAGE_H = A4
MARGIN_LR = 2 * cm
HEADER_H = 3 * cm
FOOTER_H = 1.5 * cm


def _draw_header(c: canvas.Canvas, d: datetime):
    """Header KM&CO avec Crimson Pro."""
    c.setFont("CrimsonPro", 10)

    left_margin = 2.4 * cm
    right_margin = 2.4 * cm

    y_top = PAGE_H - 1.8 * cm
    line_gap = 12

    # LEFT
    left_x = left_margin
    lines_left = [
        "Kénael MARTINI",
        "Kenaelmartini@gmail.com",
        "Kénael MARTINI & Co. – Lyon",
    ]
    for i, line in enumerate(lines_left):
        c.drawString(left_x, y_top - i * line_gap, line)

    # CENTER
    center_x = PAGE_W / 2
    lines_center = [
        "FX & Macro Strategy Desk",
        d.strftime("%d %B %Y"),
    ]
    for i, line in enumerate(lines_center):
        c.drawCentredString(center_x, y_top - i * line_gap, line)

    # RIGHT
    right_x = PAGE_W - right_margin
    c.setFont("CrimsonPro", 10)
    c.setFillColor(KMCO_BLUE)
    c.drawRightString(right_x, y_top, "KÉNAEL MARTINI & CO.")
    c.setFillColor(HexColor("#000000"))
    c.setFont("CrimsonPro", 10)

    # GREY LINE
    y_line = PAGE_H - 3.25 * cm
    c.setStrokeColor(GREY_LINE)
    c.setLineWidth(0.6)
    c.line(left_margin, y_line, PAGE_W - right_margin, y_line)
    c.setStrokeColor(HexColor("#000000"))


def _draw_footer(c: canvas.Canvas, page_num: int, total_pages: int):
    c.setFont("CrimsonPro", 8)
    text = f"KÉNAEL MARTINI & CO. | FX & Macro Strategy Desk | Page {page_num}/{total_pages}"
    c.drawRightString(PAGE_W - MARGIN_LR, 0.7 * cm, text)


def format_pdf_to_kmco(pdf_path: str, output_pdf_path: str, date: datetime | None = None):
    d = date or datetime.now()

    pages = convert_from_path(pdf_path, dpi=200, poppler_path=POPLER_BIN)
    total_pages = len(pages)

    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)

    c = canvas.Canvas(output_pdf_path, pagesize=A4)

    content_top = PAGE_H - HEADER_H - 0.5 * cm
    content_bottom = FOOTER_H + 0.5 * cm
    avail_h = content_top - content_bottom
    avail_w = PAGE_W - 2 * MARGIN_LR

    for idx, pil_img in enumerate(pages):
        _draw_header(c, d)

        img = ImageReader(pil_img)
        img_w, img_h = pil_img.size
        scale = min(avail_w / img_w, avail_h / img_h)
        draw_w = img_w * scale
        draw_h = img_h * scale

        x = (PAGE_W - draw_w) / 2
        y = content_bottom + (avail_h - draw_h) / 2

        c.drawImage(img, x, y, width=draw_w, height=draw_h)

        _draw_footer(c, idx + 1, total_pages)
        c.showPage()

    c.save()
