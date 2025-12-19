# -*- coding: utf-8 -*-
"""
generate_desk_report_v3_fixheader.py — KM&CO Institutional Header/Footer (final DEBUG)
- Génère un rapport DOCX institutionnel
- Injecte proprement un en-tête 3 blocs (gauche/centre/droite) et un pied de page
- Journalisation complète des opérations d’injection XML
"""

import os
import zipfile
from datetime import datetime
from xml.etree import ElementTree as ET
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# ==============================
# CONFIGURATION
# ==============================
SRC_MD   = r"D:\trading\News Last 48H\out\report.md"
OUT_DIR  = r"D:\trading\KMCO_out"
HEADER_BLUE = RGBColor(0, 51, 102)
LINE_GRAY   = "A0A0A0"

# Namespaces
NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PACKAGE_RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
ET.register_namespace("w", NS_W)
ET.register_namespace("r", NS_R)


# ==============================
# UTILITAIRES
# ==============================
def format_date_fr(dt: datetime) -> str:
    mois = ["janvier","février","mars","avril","mai","juin",
            "juillet","août","septembre","octobre","novembre","décembre"]
    return f"{dt.day} {mois[dt.month-1]} {dt.year}"

def _add_field(paragraph, instr: str):
    """Ajoute un champ Word (PAGE/NUMPAGES)."""
    p = paragraph._p
    fld_begin = OxmlElement('w:fldChar'); fld_begin.set(qn('w:fldCharType'), 'begin')
    instr_text = OxmlElement('w:instrText'); instr_text.text = instr
    fld_sep   = OxmlElement('w:fldChar'); fld_sep.set(qn('w:fldCharType'), 'separate')
    fld_end   = OxmlElement('w:fldChar'); fld_end.set(qn('w:fldCharType'), 'end')
    p.append(fld_begin); p.append(instr_text); p.append(fld_sep); p.append(fld_end)

def add_page_fields(paragraph):
    """Ajoute: 'Page ' + PAGE + ' of ' + NUMPAGES'."""
    run_prefix = paragraph.add_run("Page "); run_prefix.font.size = Pt(8)
    _add_field(paragraph, "PAGE")
    run_mid = paragraph.add_run(" of "); run_mid.font.size = Pt(8)
    _add_field(paragraph, "NUMPAGES")

def add_footer(document: Document):
    """Crée le pied de page aligné à droite."""
    for section in document.sections:
        footer = section.footer
        for p in list(footer.paragraphs)[1:]:
            p._element.getparent().remove(p._element)
        p = footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = p.add_run("KÉNAEL MARTINI & CO. | FX & Macro Strategy Desk | ")
        r.font.size = Pt(8)
        add_page_fields(p)


# ==============================
# DOCUMENT DOCX DE BASE
# ==============================
def md_to_docx(md_path: str, output_path: str, report_date: str):
    print(f"[STEP] Lecture du markdown: {md_path}")
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    doc = Document()

    # Marges ~1 cm
    for s in doc.sections:
        s.top_margin = Cm(1.0)
        s.bottom_margin = Cm(1.0)
        s.left_margin = Cm(1.0)
        s.right_margin = Cm(1.0)

    # Pied de page uniquement
    add_footer(doc)

    # Corps
    for raw in lines:
        line = raw.strip()
        if not line:
            doc.add_paragraph()
            continue
        def add_snapshot_line(doc, label: str, price: str, lag_s: int | None, stale: bool = False):
            p = doc.add_paragraph(style="List Bullet")

            run = p.add_run(f"{label}: {price} ")
            run.italic = False

            if lag_s is not None:
                lag_run = p.add_run(f"(lag {lag_s}s)")
                lag_run.italic = True

            if stale:
                stale_run = p.add_run(" STALE")
                stale_run.italic = False

        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.space_after = Pt(6)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    print(f"[OK] DOCX sauvegardé → {output_path}")


# ==============================
# XML HELPER FUNCTIONS
# ==============================
def _read_xml(zf: zipfile.ZipFile, path: str) -> ET.ElementTree:
    try:
        with zf.open(path) as f:
            print(f"[READ] {path}")
            return ET.parse(f)
    except KeyError:
        print(f"[WARN] {path} introuvable, création d'un XML vierge.")
        root = ET.Element("root")
        return ET.ElementTree(root)

def _write_xml(zf: zipfile.ZipFile, path: str, tree: ET.ElementTree):
    xml_bytes = ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True)
    zf.writestr(path, xml_bytes)
    print(f"[WRITE] {path} mis à jour.")

def _ensure_header_relationship(zf: zipfile.ZipFile, rels_path: str, target_header: str) -> str:
    print(f"[STEP] Vérification des relations dans {rels_path}...")
    try:
        rels = _read_xml(zf, rels_path)
        root = rels.getroot()
    except KeyError:
        print("[INFO] Aucune relation trouvée, création d'un nouveau fichier.")
        root = ET.Element("Relationships", xmlns=NS_PACKAGE_RELS)
        rels = ET.ElementTree(root)

    found_id = None
    for rel in root.findall(f"{{{NS_PACKAGE_RELS}}}Relationship"):
        if rel.get("Type") == f"{NS_R}/header" and rel.get("Target") == target_header:
            found_id = rel.get("Id")
            print(f"[OK] Relation header existante trouvée: {found_id}")
            break

    if not found_id:
        used_ids = {r.get("Id") for r in root.findall(f"{{{NS_PACKAGE_RELS}}}Relationship")}
        new_id = "rIdKMCOHeader"
        i = 1
        while new_id in used_ids:
            new_id = f"rIdKMCOHeader{i}"; i += 1

        ET.SubElement(
            root, f"{{{NS_PACKAGE_RELS}}}Relationship",
            {"Id": new_id, "Type": f"{NS_R}/header", "Target": target_header}
        )
        _write_xml(zf, rels_path, rels)
        print(f"[ADD] Nouvelle relation header ajoutée: {new_id}")
        found_id = new_id

    return found_id

def _force_section_to_use_header(zf: zipfile.ZipFile, doc_path: str, header_rId: str):
    print(f"[STEP] Injection du header {header_rId} dans {doc_path}...")
    tree = _read_xml(zf, doc_path)
    doc = tree.getroot()
    body = doc.find(f".//{{{NS_W}}}body")

    sectPr = body.find(f"./{{{NS_W}}}sectPr")
    if sectPr is None:
        paras = body.findall(f"./{{{NS_W}}}p")
        for p in reversed(paras):
            sectPr = p.find(f"./{{{NS_W}}}pPr/{{{NS_W}}}sectPr")
            if sectPr is not None:
                print("[OK] sectPr trouvée dans le dernier paragraphe.")
                break
    if sectPr is None:
        print("[INFO] Aucune sectPr trouvée, création en fin de document.")
        sectPr = ET.SubElement(body, f"{{{NS_W}}}sectPr")

    for ref in list(sectPr.findall(f"./{{{NS_W}}}headerReference")):
        sectPr.remove(ref)
    print("[CLEAN] Anciennes références supprimées.")

    for htype in ("default", "even", "first"):
        href = ET.SubElement(sectPr, f"{{{NS_W}}}headerReference")
        href.set(f"{{{NS_W}}}type", htype)
        href.set(f"{{{NS_R}}}id", header_rId)
        print(f"[ADD] Référence header ajoutée: type={htype}, id={header_rId}")

    _write_xml(zf, doc_path, tree)
    print("[DONE] headerReference écrit dans le document.")

def inject_kmco_header(docx_path: str, report_date: str):
    print("==============================================")
    print("🔧 Injection propre du header KM&CO")
    print("==============================================")

    header_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:hdr xmlns:w="{NS_W}" xmlns:r="{NS_R}">
  <w:p>
    <w:pPr><w:jc w:val="left"/></w:pPr>
    <w:r><w:t>Kénael MARTINI</w:t></w:r><w:r><w:br/></w:r>
    <w:r><w:t>Kenael.martini@orange.fr</w:t></w:r><w:r><w:br/></w:r>
    <w:r><w:t>Kénael MARTINI &amp; Co. – Lyon</w:t></w:r>
  </w:p>
  <w:p>
    <w:pPr><w:jc w:val="center"/></w:pPr>
    <w:r><w:t>FX &amp; Macro Strategy Desk</w:t></w:r><w:r><w:br/></w:r>
    <w:r><w:t>{report_date}</w:t></w:r>
  </w:p>
  <w:p>
    <w:pPr><w:jc w:val="right"/></w:pPr>
    <w:r><w:rPr><w:b/><w:color w:val="003366"/></w:rPr><w:t>KÉNAEL MARTINI &amp; CO.</w:t></w:r>
  </w:p>
  <w:p>
    <w:pPr><w:pBdr><w:bottom w:val="single" w:sz="6" w:space="1" w:color="A0A0A0"/></w:pBdr></w:pPr>
  </w:p>
</w:hdr>""".strip()

    # 1. On rouvre le .docx
    with zipfile.ZipFile(docx_path, "a") as z:
        # 2. On écrit le header XML
        print("[WRITE] Création du fichier word/headerKMCO.xml")
        z.writestr("word/headerKMCO.xml", header_xml)

        # 3. Lecture et nettoyage des relations
        rels = _read_xml(z, "word/_rels/document.xml.rels")
        rel_root = rels.getroot()
        for rel in rel_root.findall(f"{{{NS_PACKAGE_RELS}}}Relationship"):
            if rel.get("Type") == f"{NS_R}/header":
                rel_root.remove(rel)
        print("[CLEAN] Anciennes relations header supprimées.")

        # 4. Nouvelle relation propre
        ET.SubElement(
            rel_root, f"{{{NS_PACKAGE_RELS}}}Relationship",
            {"Id": "rIdKMCOHeader", "Type": f"{NS_R}/header", "Target": "headerKMCO.xml"}
        )
        _write_xml(z, "word/_rels/document.xml.rels", rels)

        # 5. Réécriture de document.xml pour pointer vers ce header
        doc_tree = _read_xml(z, "word/document.xml")
        body = doc_tree.getroot().find(f".//{{{NS_W}}}body")
        sectPr = body.find(f"./{{{NS_W}}}sectPr")
        if sectPr is None:
            sectPr = ET.SubElement(body, f"{{{NS_W}}}sectPr")

        for ref in sectPr.findall(f"./{{{NS_W}}}headerReference"):
            sectPr.remove(ref)
        ET.SubElement(sectPr, f"{{{NS_W}}}headerReference",
                      {f"{{{NS_W}}}type": "default", f"{{{NS_R}}}id": "rIdKMCOHeader"})
        _write_xml(z, "word/document.xml", doc_tree)

    print("✅ Header KM&CO injecté proprement sans corruption XML.\n")



    with zipfile.ZipFile(docx_path, "a") as z:
        print(f"[WRITE] Injection du fichier word/header1.xml dans {docx_path}")
        z.writestr("word/header1.xml", header_xml)

        print("[STEP] Ajout de la relation vers le header...")
        rel_id = _ensure_header_relationship(z, "word/_rels/document.xml.rels", "header1.xml")
        print(f"[RESULT] Relationship ID utilisé: {rel_id}")

        print("[STEP] Forçage de la section à utiliser le header...")
        _force_section_to_use_header(z, "word/document.xml", rel_id)

    print("✅ Injection du header KM&CO terminée.\n")


# ==============================
# MAIN
# ==============================
def main():
    print("=====================================================")
    print("  Construction du Rapport Institutionnel (KM&CO)")
    print("=====================================================")

    report_date = format_date_fr(datetime.now())

    if not os.path.isfile(SRC_MD):
        os.makedirs(os.path.dirname(SRC_MD), exist_ok=True)
        with open(SRC_MD, "w", encoding="utf-8") as f:
            f.write(f"Analyse Globale du Marché — {report_date}\n\n"
                    "Contenu de test. Remplacez ce fichier par le vrai report.md.\n")
        print(f"[INFO] Placeholder créé: {SRC_MD}")

    out_name = f"KMCO_Global_Macro_Report_{datetime.now().strftime('%Y-%m-%d')}.docx"
    out_path = os.path.join(OUT_DIR, out_name)
    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"[DEBUG] Lecture:   {SRC_MD}")
    print(f"[DEBUG] Écriture:  {out_path}")

    md_to_docx(SRC_MD, out_path, report_date)
    inject_kmco_header(out_path, report_date)
    print("✅ inject_kmco_header appelée correctement")

    print("🎯 Rapport final prêt.")

if __name__ == "__main__":
    main()
