import zipfile, tempfile, shutil, re
from pathlib import Path

src = Path(r"D:\trading\KMCO_out\KMCO_Global_Macro_Report_2025-10-24_FULLFIX.docx")
dst = src.with_name(src.stem + "_FINAL.docx")

print("🧽 Suppression des balises vides…")

tmp = Path(tempfile.mkdtemp())
with zipfile.ZipFile(src, "r") as zin:
    zin.extractall(tmp)

docxml = tmp / "word" / "document.xml"
xml = docxml.read_text(encoding="utf-8")

# supprime paragraphes/runs auto-fermants (<w:p/> ou <w:r/>)
xml = re.sub(r"<w:(p|r)\s*/>", "", xml)
docxml.write_text(xml, encoding="utf-8")

with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as zout:
    for f in sorted(tmp.rglob("*")):
        if f.is_file():
            zout.write(f, f.relative_to(tmp))

shutil.rmtree(tmp)
print(f"✅ Fichier nettoyé : {dst}")
