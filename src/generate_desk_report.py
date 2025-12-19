# -*- coding: utf-8 -*-
"""
generate_desk_report.py — KM&CO unified build
Usage:
    python generate_desk_report.py [--md "chemin\report.md"]

Output:
    D:\trading\KMCO_out\KMCO_Global_Macro_Report_YYYY-MM-DD.docx
Requirements:
    pip install python-docx
"""
import argparse
import os
import re
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

# ---------------------------
# Config utilisateur (modifiable)
# ---------------------------
DEFAULT_MD = Path(__file__).resolve().parents[1] / "KMCO_out" / "report_overnight.md"
OUT_DIR = Path(r"D:\trading\KMCO_out")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Style couleur
DARK_BLUE = "1F3A7D"
GREY_LINE = "BFBFBF"

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
ET.register_namespace("w", NS_W)
ET.register_namespace("r", NS_R)

# ---------------------------
# Helpers Word fields (PAGE/ NUMPAGES)
# ---------------------------
def add_field(paragraph, field_code: str):
    """
    Insère un champ Word (ex: PAGE, NUMPAGES) proprement dans un paragraphe.
    """
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    paragraph._p.append(fld_begin)

    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = field_code
    paragraph._p.append(instr)

    fld_separate = OxmlElement("w:fldChar")
    fld_separate.set(qn("w:fldCharType"), "separate")
    paragraph._p.append(fld_separate)

    # placeholder text
    t = OxmlElement("w:r")
    ttext = OxmlElement("w:t")
    ttext.text = "1"
    t.append(ttext)
    paragraph._p.append(t)

    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    paragraph._p.append(fld_end)


def add_footer_dynamic(doc: Document):
    section = doc.sections[-1]
    footer = section.footer
    # Clear existing paragraphs
    if footer.paragraphs:
        p = footer.paragraphs[0]
    else:
        p = footer.add_paragraph()
    # Compose
    run = p.add_run("KÉNAEL MARTINI & CO. | FX & Macro Strategy Desk | Page ")
    run.font.size = Pt(9)
    add_field(p, "PAGE")
    p.add_run(" of ").font.size = Pt(9)
    add_field(p, "NUMPAGES")
    p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER


# ---------------------------
# Header KM&CO (table 3 cols) via python-docx + small xml for the thin grey line
# ---------------------------
def add_institutional_header(doc: Document, date_str_display: str):
    """
    Construit l'en-tête 3 colonnes: gauche/centre/droite,
    puis ajoute une ligne grise fine en dessous.
    """
    section = doc.sections[0]
    header = section.header

    # Création tableau 1x3
    section = doc.sections[0]
    table = header.add_table(rows=1, cols=3, width=section.page_width)
    table.autofit = True
    table.allow_autofit = True

    # Cell 1 gauche
    c0 = table.cell(0, 0).paragraphs[0]
    c0.add_run("Kénael MARTINI\n").bold = True
    c0.add_run("Kenael.martini@orange.fr\n")
    c0.add_run("Kénael MARTINI & Co. – Lyon")
    c0.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

    # Cell 2 centre
    c1 = table.cell(0, 1).paragraphs[0]
    c1.add_run("FX & Macro Strategy Desk\n").bold = True
    c1.add_run(date_str_display)
    c1.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    # Cell 3 droite
    c2 = table.cell(0, 2).paragraphs[0]
    r = c2.add_run("KÉNAEL MARTINI & CO.")
    r.bold = True
    # couleur via xml (python-docx RGBColor not always reliable in header)
    # Inject color via rPr/color
    r_elem = c2.runs[0]._r
    rPr = r_elem.find("w:rPr", namespaces={'w': NS_W})
    if rPr is None:
        rPr = OxmlElement("w:rPr")
        r_elem.insert(0, rPr)
    color = OxmlElement("w:color")
    color.set(qn("w:val"), DARK_BLUE)
    rPr.append(color)
    c2.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT

    # Ligne grise fine : on ajoute un paragraphe en dessous et met bottom border
    p_line = header.add_paragraph()
    pPr = OxmlElement("w:pPr")
    pBdr = OxmlElement("w:pBdr")
    btm = OxmlElement("w:bottom")
    btm.set(qn("w:val"), "single")
    btm.set(qn("w:sz"), "6")   # fin
    btm.set(qn("w:space"), "1")
    btm.set(qn("w:color"), GREY_LINE)
    pBdr.append(btm)
    pPr.append(pBdr)
    p_line._p.append(pPr)

def sanitize_docx_text(docx_path: Path):
    """Supprime les retours chariot \r non valides dans document.xml"""
    import zipfile, tempfile, shutil, os
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        with zipfile.ZipFile(docx_path, "r") as zin:
            zin.extractall(tmpdir)

        doc_xml = tmpdir / "word" / "document.xml"
        data = doc_xml.read_bytes().decode("utf-8", errors="ignore")
        cleaned = data.replace("\r", "")
        doc_xml.write_bytes(cleaned.encode("utf-8"))

        fixed = docx_path.with_name(docx_path.stem + "_CLEANED.docx")
        with zipfile.ZipFile(fixed, "w", zipfile.ZIP_DEFLATED) as zout:
            for root, _, files in os.walk(tmpdir):
                for fn in files:
                    fp = Path(root) / fn
                    relp = fp.relative_to(tmpdir).as_posix()
                    zout.write(fp, relp)
    print("✅ Fichier nettoyé :", fixed)
    return fixed


# ---------------------------
# Utilities : xml post-processing to ensure rId9 + content types
# ---------------------------
def ensure_header_rid9_and_contenttypes(docx_path: Path):
    """
    Ouvre le docx (zip) et :
    - écrit /word/headerKMCO.xml
    - purge toutes les relations 'header' dans word/_rels/document.xml.rels puis recrée rId9 -> /word/headerKMCO.xml
    - purge toutes les <w:headerReference ...> dans word/document.xml puis recrée une seule <w:headerReference r:id="rId9" w:type="default"/>
    - assure [Content_Types].xml : Override /word/headerKMCO.xml
    - force word/settings.xml -> <w:updateFields w:val="true"/>
    """
    import zipfile, tempfile, shutil, os
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        with zipfile.ZipFile(docx_path, "r") as zin:
            zin.extractall(tmpdir)

        word_dir = tmpdir / "word"
        rels_path = word_dir / "_rels" / "document.xml.rels"
        doc_path = word_dir / "document.xml"
        ct_path = tmpdir / "[Content_Types].xml"
        settings_path = word_dir / "settings.xml"
        header_path = word_dir / "headerKMCO.xml"

        # 1) headerKMCO.xml (simple, propre)
        from xml.etree import ElementTree as ET
        NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        hdr = ET.Element(f"{{{NS_W}}}hdr")
        def para(txt):
            p = ET.SubElement(hdr, f"{{{NS_W}}}p")
            r = ET.SubElement(p, f"{{{NS_W}}}r")
            t = ET.SubElement(r, f"{{{NS_W}}}t")
            t.text = txt
        for line in [
            "Kénael MARTINI",
            "Kenael.martini@orange.fr",
            "Kénael MARTINI & Co. – Lyon",
            "FX & Macro Strategy Desk",
            datetime.now().strftime("%d %B %Y"),
            "KÉNAEL MARTINI & CO.",
        ]:
            para(line)
        # fine grey line
        p_line = ET.SubElement(hdr, f"{{{NS_W}}}p")
        pPr = ET.SubElement(p_line, f"{{{NS_W}}}pPr")
        pBdr = ET.SubElement(pPr, f"{{{NS_W}}}pBdr")
        ET.SubElement(pBdr, f"{{{NS_W}}}bottom", {"val":"single","sz":"6","space":"1","color":"BFBFBF"})
        header_path.write_bytes(ET.tostring(hdr, encoding="utf-8", xml_declaration=True))

        # 2) [Content_Types].xml -> Override /word/headerKMCO.xml
        CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
        ct_tree = ET.parse(ct_path)
        ct_root = ct_tree.getroot()
        if not any(o.get("PartName") == "/word/headerKMCO.xml" for o in ct_root.findall(f"{{{CT_NS}}}Override")):
            ET.SubElement(ct_root, f"{{{CT_NS}}}Override", {
                "PartName": "/word/headerKMCO.xml",
                "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml",
            })
            ct_tree.write(ct_path, encoding="utf-8", xml_declaration=True)

        # 3) PURGE + recréation des relations header dans document.xml.rels
        rels_path.parent.mkdir(parents=True, exist_ok=True)
        if rels_path.exists():
            rels_tree = ET.parse(rels_path)
            rels_root = rels_tree.getroot()
        else:
            rels_root = ET.Element("Relationships", {"xmlns": "http://schemas.openxmlformats.org/package/2006/relationships"})
            rels_tree = ET.ElementTree(rels_root)

        # supprime TOUT ce qui est Type=header (namespace ou pas)
        for rel in list(rels_root):
            typ = rel.get("Type") or ""
            if "officeDocument/2006/relationships/header" in typ:
                rels_root.remove(rel)

        # crée rId9 -> /word/headerKMCO.xml avec TargetMode=Internal
        ET.SubElement(rels_root, "Relationship", {
            "Id": "rId9",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/header",
            "Target": "/word/headerKMCO.xml",
            "TargetMode": "Internal",
        })
        rels_tree.write(rels_path, encoding="utf-8", xml_declaration=True)

        # 4) PURGE + recréation des <w:headerReference> dans document.xml
        doc_tree = ET.parse(doc_path)
        doc_root = doc_tree.getroot()
        ns = {
            "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
            "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        }
        body = doc_root.find("w:body", ns)
        if body is None:
            raise RuntimeError("document.xml invalide: w:body manquant")
        sectPr = None
        for s in doc_root.findall(".//w:sectPr", ns):
            sectPr = s
        if sectPr is None:
            sectPr = ET.SubElement(body, f"{{{ns['w']}}}sectPr")

        # purge toutes les références header (default/first/even)
        for h in list(sectPr.findall("w:headerReference", ns)):
            sectPr.remove(h)
        # crée la seule référence attendue
        new_hdr = ET.Element(f"{{{ns['w']}}}headerReference", {
            f"{{{ns['w']}}}type": "default",
            f"{{{ns['r']}}}id": "rId9",
        })
        sectPr.insert(0, new_hdr)
        doc_tree.write(doc_path, encoding="utf-8", xml_declaration=True)

        # 5) settings.xml -> updateFields true
        if settings_path.exists():
            s_tree = ET.parse(settings_path)
            s_root = s_tree.getroot()
        else:
            s_root = ET.Element(f"{{{ns['w']}}}settings")
            s_tree = ET.ElementTree(s_root)
        upd = s_root.find("w:updateFields", ns)
        if upd is None:
            upd = ET.SubElement(s_root, f"{{{ns['w']}}}updateFields")
        upd.set(f"{{{ns['w']}}}val", "true")
        s_tree.write(settings_path, encoding="utf-8", xml_declaration=True)

        # 6) Nettoyage CR dans TOUS les XML du dossier word/
        for xml_fp in word_dir.rglob("*.xml"):
            raw = xml_fp.read_bytes().decode("utf-8", errors="ignore")
            cleaned = raw.replace("\r", "")
            if cleaned != raw:
                xml_fp.write_bytes(cleaned.encode("utf-8"))

        # 7) Repack in-place
        tmp_out = docx_path.with_suffix(".repacked.tmp")
        if tmp_out.exists():
            tmp_out.unlink()
        with zipfile.ZipFile(tmp_out, "w", zipfile.ZIP_DEFLATED) as zout:
            for root, _, files in os.walk(tmpdir):
                for fn in files:
                    p = Path(root) / fn
                    zout.write(p, p.relative_to(tmpdir).as_posix())
        # Remplace l’original
        shutil.move(str(tmp_out), str(docx_path))



# ---------------------------
# Verify minimal integrity to give feedback
# ---------------------------
def verify_docx_integrity(docx_path: Path):
    import zipfile
    from xml.etree import ElementTree as ET
    with zipfile.ZipFile(docx_path, 'r') as zf:
        # .rels
        rels_root = ET.fromstring(zf.read("word/_rels/document.xml.rels"))
        ok_rel = False
        for rel in rels_root.findall(".//*"):
            if (
                rel.get("Id") == "rId9"
                and "officeDocument/2006/relationships/header" in (rel.get("Type") or "")
                and "/word/headerKMCO.xml" in (rel.get("Target") or "")
            ):
                ok_rel = True
        if not ok_rel:
            raise RuntimeError("Vérif échouée: rId9 manquant/mauvais dans document.xml.rels")

        # headerReference
        doc_root = ET.fromstring(zf.read("word/document.xml"))
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
              "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
        sects = doc_root.findall(".//w:sectPr", ns)
        ok_hdr = False
        for s in sects:
            for h in s.findall("w:headerReference", ns):
                if h.get("{%s}id" % ns["r"]) == "rId9":
                    ok_hdr = True
        if not ok_hdr:
            raise RuntimeError("Vérif échouée: w:headerReference rId9 absent")

        # content types
        CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
        ct_root = ET.fromstring(zf.read("[Content_Types].xml"))
        ok_ct = any(
            o.get("PartName") == "/word/headerKMCO.xml"
            and "header+xml" in (o.get("ContentType") or "")
            for o in ct_root.findall(f"{{{CT_NS}}}Override")
        )
        if not ok_ct:
            raise RuntimeError("Vérif échouée: override headerKMCO manquant")

    return True




# ---------------------------
# Main flow
# ---------------------------
def read_md(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {path}")
    return path.read_text(encoding="utf-8")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--md", type=str, default=None, help="Chemin du report.md (défaut: ./report.md)")
    args = parser.parse_args()

    md_path = Path(args.md) if args.md else DEFAULT_MD
    try:
        md_text = read_md(md_path)
    except Exception as e:
        print(f"[ERREUR] Fichier introuvable: {md_path}", file=sys.stderr)
        sys.exit(1)

    # date strings
    today = datetime.now()
    date_file = today.strftime("%Y-%m-%d")
    date_display = today.strftime("%d %B %Y")

    out_path = OUT_DIR / f"KMCO_Global_Macro_Report_{date_file}.docx"
    # temp docx path
    tmp_docx = Path(tempfile.gettempdir()) / f"kmco_base_{date_file}.docx"

    # build base docx
    doc = Document()
    # margins ~ 1 cm
    for s in doc.sections:
        s.top_margin = Cm(1)
        s.bottom_margin = Cm(1)
        s.left_margin = Cm(1)
        s.right_margin = Cm(1)

    # header/footer
    add_institutional_header(doc, date_display)
    add_footer_dynamic(doc)

    # body: split on blank lines and add paragraphs
    blocks = re.split(r"\n\s*\n", md_text.strip())
    for b in blocks:
        p = doc.add_paragraph(b.strip())
        for run in p.runs:
            run.font.size = Pt(11)

    # save base docx
        # save base docx
    doc.save(tmp_docx)

    # post-process complet et durci
    ensure_header_rid9_and_contenttypes(tmp_docx)

    # déplace vers sortie finale
    shutil.move(str(tmp_docx), str(out_path))

    # vérif stricte
    verify_docx_integrity(out_path)

    print("✅ Rapport final généré sans corruption Word.")
    print(f"📄 Chemin : {out_path}")


if __name__ == "__main__":
    main()
