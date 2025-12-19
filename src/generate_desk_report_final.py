# -*- coding: utf-8 -*-
"""
KÉNAEL MARTINI & CO. – FX & Macro Strategy Desk
Version stable alignée horizontalement (3 colonnes),
avec teinte bleue institutionnelle et police harmonisée.
"""

from pathlib import Path
from datetime import datetime
from docx import Document
from docx.shared import RGBColor, Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import win32com.client



# =====================================================
# UTILITAIRES
# =====================================================

def deep_clean_text(path: Path) -> str:
    """Nettoie le texte source avant génération du rapport."""
    raw = path.read_text(encoding="utf-8", errors="ignore")
    clean = "".join(
        ch for ch in raw
        if ch in ("\n", "\t", " ") or (32 <= ord(ch) <= 55295) or (57344 <= ord(ch) <= 65533)
    )
    clean = clean.replace("\ufeff", "").replace("\xa0", " ")
    clean = clean.replace("–", "-").replace("—", "-").replace("―", "-")
    clean = clean.replace("•", "-").replace("·", "-").replace("●", "-")
    return clean.strip()

# =====================================================
# CONSTRUCTION DU DOCX
# =====================================================

def build_report_docx(text: str, output_path: Path):
    """Construit le rapport Word avec header KM&CO institutionnel."""
    doc = Document()

    style = doc.styles['Normal']
    style.font.name = "Cambria"
    style.font.size = Pt(11)


    section = doc.sections[0]

    # ---------- En-tête ----------
    header = section.header
    table = header.add_table(rows=1, cols=3, width=Inches(6.5))
    table.autofit = True

    # Colonne gauche
    cell_left = table.cell(0, 0)
    p_left = cell_left.paragraphs[0]
    p_left.add_run("Kénael MARTINI\n").bold = False
    p_left.add_run("Kenael.martini@orange.fr\n")
    p_left.add_run("Kénael MARTINI & Co. – Lyon")
    p_left.alignment = WD_ALIGN_PARAGRAPH.LEFT

    # Colonne centre
    cell_center = table.cell(0, 1)
    p_center = cell_center.paragraphs[0]
    p_center.add_run("FX & Macro Strategy Desk\n").bold = True
    p_center.add_run(datetime.now().strftime("%d %B %Y"))
    p_center.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Colonne droite — logo texte institutionnel
    cell_right = table.cell(0, 2)
    p_right = cell_right.paragraphs[0]
    r = p_right.add_run("KÉNAEL MARTINI & CO.")
    r.bold = False
    r.font.size = Pt(8)
    r.font.color.rgb = RGBColor(10, 36, 89)  # Bleu institutionnel
    r.font.name = "Cambria"
    try:
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Cambria")
        r._element.rPr.rFonts.set(qn("w:ascii"), "Cambria")
        r._element.rPr.rFonts.set(qn("w:hAnsi"), "Cambria")
        r._element.rPr.rFonts.set(qn("w:cs"), "Cambria")
    except Exception:
        # Fallback si Trajan Pro absente
        r.font.name = "Cambria "
    p_right.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    # --- Taille 8 pt pour tout l’en-tête ---
    for para in (p_left, p_center, p_right):
        for run in para.runs:
            run.font.size = Pt(8)
            # optionnel: forcer la police si tu veux la même partout
            # run.font.name = "Cambria"

    # Ligne grise fine sous l'en-tête
    p_line = header.add_paragraph()
    line = p_line.add_run("―" * 52 )
    line.font.color.rgb = RGBColor(190, 190, 190)
    p_line.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ---------- Corps du texte ----------
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        p = doc.add_paragraph(para)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # ---------- Pied de page (safe, sans champs dynamiques) ----------
    footer = section.footer
    p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    # texte institutionnel
    run = p.add_run("KÉNAEL MARTINI & CO. | FX & Macro Strategy Desk")
    run.font.name = "Cambria"
    run.font.size = Pt(8)

    # Sauvegarde
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)

# =====================================================
# MAIN
# =====================================================

def main():
    print("[DEBUG] Lancement du générateur KM&CO...")

    md_path = Path(r"D:\trading\News Last 48H\out\report.md")
    if not md_path.exists():
        print(f"[ERREUR] Fichier introuvable : {md_path}")
        return

    text = deep_clean_text(md_path)
    print("[DEBUG] Taille nettoyée :", len(text), "octets")

    date_str = datetime.now().strftime("%Y-%m-%d")
    output_path = Path(rf"D:\trading\KMCO_out\KMCO_Global_Macro_Report_{date_str}_NEW.docx")

    print("[DEBUG] Construction du DOCX :", output_path)
    build_report_docx(text, output_path)
    print(f"✅ Rapport institutionnel généré : {output_path}")

if __name__ == "__main__":
    main()
