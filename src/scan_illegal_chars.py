import zipfile
from pathlib import Path

docx_path = Path(r"D:\trading\KMCO_out\KMCO_Global_Macro_Report_2025-10-24_WORD_FIXED_REBUILT.docx")

def check_file(zf, name):
    data = zf.read(name).decode("utf-8", errors="ignore")
    bads = [c for c in data if ord(c) in (0, 11, 12, 13, 14, 15, 16, 26)]
    if bads:
        print(f"⚠️ {name}: caractères non valides ->", bads)
    if "ï»¿" in data or "\ufeff" in data:
        print(f"⚠️ {name}: contient un BOM UTF-8 caché")
    if "<w:" not in data:
        print(f"❌ {name}: pas de balises Word (probablement du texte brut)")

with zipfile.ZipFile(docx_path, "r") as zf:
    for name in ["word/document.xml", "word/headerKMCO.xml"]:
        if name in zf.namelist():
            check_file(zf, name)
        else:
            print(f"❌ Fichier manquant dans le zip: {name}")
