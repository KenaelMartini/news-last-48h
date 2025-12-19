import zipfile, os, xml.etree.ElementTree as ET
from pathlib import Path

docx_path = Path(r"D:\trading\KMCO_out\KMCO_Global_Macro_Report_2025-10-24.docx")

if not docx_path.exists():
    print("❌ Fichier introuvable :", docx_path)
    exit()

with zipfile.ZipFile(docx_path, "r") as zf:
    files = zf.namelist()
    print("📁 Contenu du .docx :", len(files), "fichiers")

    for name in ["word/_rels/document.xml.rels", "word/document.xml",
                 "word/headerKMCO.xml", "[Content_Types].xml"]:
        print("\n---", name, "---")
        if name not in files:
            print("❌ Manquant :", name)
            continue
        data = zf.read(name)
        try:
            ET.fromstring(data)
            print("✅ XML valide")
        except ET.ParseError as e:
            print("❌ XML corrompu :", e)
