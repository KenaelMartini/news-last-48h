import zipfile, shutil, tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

docx_path = Path(r"D:\trading\KMCO_out\KMCO_Global_Macro_Report_2025-10-24.docx")
fixed_path = docx_path.with_name(docx_path.stem + "_WORD_FIXED.docx")

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    with zipfile.ZipFile(docx_path, "r") as zf:
        zf.extractall(tmp)

    rels_path = tmp / "word" / "_rels" / "document.xml.rels"
    rels_tree = ET.parse(rels_path)
    rels_root = rels_tree.getroot()

    # Supprime tout doublon de header
    for rel in list(rels_root):
        if "header" in (rel.get("Type") or ""):
            rels_root.remove(rel)

    # Ajoute la relation propre attendue par Word
    ET.SubElement(rels_root, "Relationship", {
        "Id": "rId9",
        "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/header",
        "Target": "headerKMCO.xml",
        "TargetMode": "Internal"
    })
    rels_tree.write(rels_path, encoding="utf-8", xml_declaration=True)

    # Corrige le [Content_Types].xml : vérifie override et ordre
    ct_path = tmp / "[Content_Types].xml"
    ct_tree = ET.parse(ct_path)
    ct_root = ct_tree.getroot()
    CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
    found = False
    for o in ct_root.findall(f"{{{CT_NS}}}Override"):
        if o.get("PartName") == "/word/headerKMCO.xml":
            found = True
    if not found:
        ET.SubElement(ct_root, f"{{{CT_NS}}}Override", {
            "PartName": "/word/headerKMCO.xml",
            "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"
        })
    ct_tree.write(ct_path, encoding="utf-8", xml_declaration=True)

    # Re-zip le tout
    with zipfile.ZipFile(fixed_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for root, _, files in tmp.walk():
            for fn in files:
                p = Path(root) / fn
                zout.write(p, p.relative_to(tmp).as_posix())

print("✅ Fichier corrigé :", fixed_path)
